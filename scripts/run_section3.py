"""Section 3: washing-machine power from the aggregate, 1-minute resolution.

    python scripts/run_section3.py --experiments loho,timesplit
    python scripts/run_section3.py --quick          # small smoke test (few trees)

Experiments
  loho       leave-one-house-out: each house is the test house once, the model trains on the other houses
             (last part of each training house's time = validation block for early stopping)
  timesplit  within one house: first part trains (with its own validation block), last part tests
Models: always_off, train_mean, hourly_profile, lgbm_tweedie, lgbm_l2
Outputs (outputs/section3/): metrics_<experiment>.csv, predictions_<experiment>.parquet, importance_<experiment>.csv
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import minute_parquet_path  # noqa: E402
from src.features import context_minutes, make_features  # noqa: E402
from src.metrics import evaluate  # noqa: E402
from src.models import AlwaysOff, HourlyProfile, TrainMean, fit_lgbm, predict_lgbm  # noqa: E402
from src.splits import assert_no_house_overlap, chronological_masks, leave_one_house_out  # noqa: E402


def load_house(cfg, h):
    df = pd.read_parquet(minute_parquet_path(cfg, h))
    return df


def prepare(df, mcfg):
    X = make_features(df["aggregate"], mcfg, use_time=bool(mcfg.get("use_time_features", False)))
    valid = (df["aggregate"].notna() & df["wm"].notna()).to_numpy()
    return X, df["wm"].astype("float64"), valid


def split_train_val(n, mcfg, embargo):
    """Chronological train/validation masks inside the training data of ONE house."""
    return chronological_masks(n, float(mcfg.get("validation_fraction", 0.2)), embargo)


def run_models(train_parts, val_parts, test_X, test_y, test_valid, test_index, mcfg, cycle_params, objectives, quick):
    """train_parts / val_parts: lists of (X, y) with invalid rows already removed. The test part is FULL-LENGTH
    (`test_valid` marks usable minutes). Returns rows, predictions, importance."""
    thr = float(mcfg["on_threshold_w"])
    stride = int(mcfg.get("train_stride", 1))
    if stride > 1:   # neighbouring minutes are almost the same; use every stride-th minute for fitting only
        train_parts = [(X.iloc[::stride], y.iloc[::stride]) for X, y in train_parts]
        val_parts = [(X.iloc[::stride], y.iloc[::stride]) for X, y in val_parts]
    t0 = time.time()
    Xtr = pd.concat([p[0] for p in train_parts]); ytr = pd.concat([p[1] for p in train_parts])
    Xva = pd.concat([p[0] for p in val_parts]); yva = pd.concat([p[1] for p in val_parts])

    frames = [pd.DataFrame({"wm": p[1]}) for p in train_parts]   # baselines see training data only
    Xt = test_X; yt = test_y.to_numpy(); idx = test_index      # full-length test part; `test_valid` marks usable minutes

    preds = {}
    for b in (AlwaysOff(), TrainMean(), HourlyProfile()):
        preds[b.name] = (b.fit(frames).predict(idx), {})

    params = dict(mcfg.get("lgbm", {}))
    if quick:
        params.update(n_estimators=50, early_stopping_rounds=10)
    imp = {}
    for obj in objectives:
        name = "lgbm_tweedie" if obj == "tweedie" else "lgbm_l2"
        t1 = time.time()
        m = fit_lgbm(Xtr, ytr, Xva, yva, "tweedie" if obj == "tweedie" else "regression", params)
        print(f"    fit {name}: {len(Xtr):,} train rows, {time.time() - t1:.0f} s, best iteration {m.best_iteration_}", flush=True)
        val_mae = float(np.mean(np.abs(predict_lgbm(m, Xva) - yva.to_numpy())))
        preds[name] = (predict_lgbm(m, Xt), {"val_mae_w": val_mae, "best_iteration": int(m.best_iteration_ or 0)})
        imp[name] = pd.Series(m.feature_importances_, index=Xtr.columns)

    t2 = time.time()
    rows = []
    for name, (p, extra) in preds.items():
        r = evaluate(yt, p, thr, cycle_params, valid=test_valid)
        r.update({"model": name, **extra})
        rows.append(r)
    print(f"    metrics: {time.time() - t2:.0f} s | whole fold: {time.time() - t0:.0f} s", flush=True)
    pred_df = pd.DataFrame({"y_true": yt, "valid": test_valid, **{f"pred_{k}": v[0] for k, v in preds.items()}}, index=idx)
    return rows, pred_df, pd.DataFrame(imp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--experiments", default="loho,timesplit")
    ap.add_argument("--houses", type=int, nargs="*")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stride", type=int, default=None, help="override model.train_stride")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    cfg = yaml.safe_load(open(a.config))
    mcfg = cfg["model"]
    if a.stride:
        mcfg["train_stride"] = a.stride
    houses = a.houses or mcfg["houses"]
    out_dir = Path(a.out or cfg["paths"]["model_out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    embargo = context_minutes(mcfg)
    cycle_params = dict(
        on_threshold_w=float(mcfg["on_threshold_w"]),
        merge_gap_minutes=int(mcfg.get("cycle_merge_gap_minutes", 5)),
        min_minutes=int(mcfg.get("cycle_min_minutes", 27)),
        min_energy_wh=float(mcfg.get("cycle_min_energy_wh") or 0.0),
    )
    objectives = mcfg.get("objectives", ["tweedie", "l2"])

    data = {}
    for h in houses:
        df = load_house(cfg, h)
        data[h] = prepare(df, mcfg) + (df.index,)
        print(f"house {h}: {len(df):,} minutes, valid {int(data[h][2].sum()):,}")

    for exp in a.experiments.split(","):
        all_rows, all_preds, all_imp = [], [], []
        if exp == "loho":
            for fold in leave_one_house_out(houses):
                te = fold["test"]; assert_no_house_overlap(fold["train"], [te])
                tr_parts, va_parts = [], []
                for h in fold["train"]:
                    X, y, v, idx = data[h]
                    first, last = split_train_val(len(X), mcfg, embargo)
                    tr_parts.append((X[first & v], y[first & v])); va_parts.append((X[last & v], y[last & v]))
                X, y, v, idx = data[te]
                rows, pred_df, imp = run_models(tr_parts, va_parts, X, y, v, idx, mcfg, cycle_params, objectives, a.quick)
                for r in rows: r.update({"experiment": exp, "test_house": te, "train_houses": str(fold["train"])})
                pred_df["house"] = te
                all_rows += rows; all_preds.append(pred_df); all_imp.append(imp.assign(test_house=te))
                print(f"[{exp}] test house {te} done", flush=True)
                pd.DataFrame(all_rows).to_csv(out_dir / f"metrics_{exp}_partial.csv", index=False)
        elif exp == "timesplit":
            frac = 1 - float(mcfg.get("time_split_train_fraction", 0.7))
            for h in houses:
                X, y, v, idx = data[h]
                first, last = chronological_masks(len(X), frac, embargo)
                Xf, yf, vf = X[first], y[first], v[first]
                f2, l2 = split_train_val(len(Xf), mcfg, embargo)
                tr = [(Xf[f2 & vf], yf[f2 & vf])]; va = [(Xf[l2 & vf], yf[l2 & vf])]
                rows, pred_df, imp = run_models(tr, va, X[last], y[last], v[last], idx[last], mcfg, cycle_params, objectives, a.quick)
                for r in rows: r.update({"experiment": exp, "test_house": h, "train_houses": str([h])})
                pred_df["house"] = h
                all_rows += rows; all_preds.append(pred_df); all_imp.append(imp.assign(test_house=h))
                print(f"[{exp}] house {h} done", flush=True)
                pd.DataFrame(all_rows).to_csv(out_dir / f"metrics_{exp}_partial.csv", index=False)
        else:
            raise SystemExit(f"unknown experiment {exp!r}")

        metrics = pd.DataFrame(all_rows)
        first_cols = ["experiment", "test_house", "model"]
        metrics = metrics[first_cols + [c for c in metrics.columns if c not in first_cols]]
        metrics.to_csv(out_dir / f"metrics_{exp}.csv", index=False)
        pd.concat(all_preds).to_parquet(out_dir / f"predictions_{exp}.parquet")
        pd.concat(all_imp).to_csv(out_dir / f"importance_{exp}.csv")
        show = ["mae_w", "mae_on_w", "energy_error", "f1", "cycle_recall", "cycle_precision"]
        print(f"\n=== {exp}: mean over test houses ===")
        print(metrics.groupby("model")[show].mean().round(3).to_string())
        print()


if __name__ == "__main__":
    main()
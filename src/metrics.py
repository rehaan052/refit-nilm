"""Metrics for washing-machine power estimation. The point metrics take plain arrays with NO NaN;
`evaluate` handles unavailable minutes itself (valid mask). Definitions are our own and are written out in each docstring.
"""
from __future__ import annotations

import numpy as np

from src.cycles import find_cycles


def _check(y, p):
    y = np.asarray(y, dtype="float64")
    p = np.asarray(p, dtype="float64")
    if y.shape != p.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    if np.isnan(y).any() or np.isnan(p).any():
        raise ValueError("NaN found: drop invalid minutes before computing metrics")
    return y, p


def mae(y, p) -> float:
    """Mean absolute error over all minutes (W)."""
    y, p = _check(y, p)
    return float(np.mean(np.abs(p - y)))


def mae_on(y, p, on_threshold_w: float) -> float:
    """Mean absolute error over minutes where the TRUE power is above the ON threshold (W). NaN if none."""
    y, p = _check(y, p)
    m = y > on_threshold_w
    return float(np.mean(np.abs(p[m] - y[m]))) if m.any() else float("nan")


def energy_error(y, p) -> float:
    """Signed relative error of total energy: (sum(pred) - sum(true)) / sum(true).
    -1.0 = nothing predicted (always-off), 0 = total energy right, +0.2 = 20 % too much. NaN if true energy is 0."""
    y, p = _check(y, p)
    return float((p.sum() - y.sum()) / y.sum()) if y.sum() > 0 else float("nan")


def on_off_scores(y, p, on_threshold_w: float) -> dict:
    """Precision, recall, F1 of the ON/OFF state, both signals thresholded at the same value."""
    y, p = _check(y, p)
    t, q = y > on_threshold_w, p > on_threshold_w
    tp, fp, fn = int((t & q).sum()), int((~t & q).sum()), int((t & ~q).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1}


def cycle_scores(y, p, cycle_params: dict) -> dict:
    """Cycle-level view on FULL-LENGTH series where unavailable minutes are NaN (in both y and p).
    Cycles are found in the true and in the predicted series with the same rule.
    A true cycle is 'found' if a predicted cycle overlaps it by at least one minute.
      cycle_recall    = found true cycles / true cycles
      cycle_precision = predicted cycles that overlap a true cycle / predicted cycles
      cycle_energy_mae_wh = mean |predicted energy - true energy| inside each true cycle window (Wh)
    Vectorised: cycles of one series are sorted and do not overlap each other, so one binary search
    per cycle finds the overlapping cycle of the other series.
    """
    y = np.asarray(y, dtype="float64")
    p = np.asarray(p, dtype="float64")
    if y.shape != p.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    ct = find_cycles(y, **cycle_params)
    cp = find_cycles(p, **cycle_params)
    ts, te = ct["start"].to_numpy(), ct["end"].to_numpy()
    ps, pe = cp["start"].to_numpy(), cp["end"].to_numpy()

    def n_overlapping(a_s, a_e, b_s, b_e):
        """How many intervals (a_s, a_e) overlap some interval (b_s, b_e)."""
        if len(a_s) == 0 or len(b_s) == 0:
            return 0
        i = np.searchsorted(b_e, a_s, side="right")      # first b that ends after a starts
        ok = i < len(b_s)
        hit = np.zeros(len(a_s), dtype=bool)
        hit[ok] = b_s[i[ok]] < a_e[ok]
        return int(hit.sum())

    found = n_overlapping(ts, te, ps, pe)
    good_pred = n_overlapping(ps, pe, ts, te)
    if len(ct):
        cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(p, nan=0.0))])
        pred_wh = (cs[te] - cs[ts]) / 60.0
        e_err = float(np.mean(np.abs(pred_wh - ct["energy_wh"].to_numpy())))
    else:
        e_err = float("nan")
    return {
        "n_true_cycles": int(len(ct)),
        "n_pred_cycles": int(len(cp)),
        "cycle_recall": found / len(ct) if len(ct) else float("nan"),
        "cycle_precision": good_pred / len(cp) if len(cp) else float("nan"),
        "cycle_energy_mae_wh": e_err,
    }


def evaluate(y, p, on_threshold_w: float, cycle_params: dict | None = None, valid=None) -> dict:
    """All metrics in one dict.
    y, p: full-length arrays on the 1-minute grid. `valid` marks minutes with a usable label and aggregate
    (default: both finite). Point metrics use valid minutes only; cycle metrics run on the full-length series with
    unavailable minutes set to NaN, so an episode is never bridged across a gap."""
    y = np.asarray(y, dtype="float64")
    p = np.asarray(p, dtype="float64")
    if valid is None:
        valid = np.isfinite(y) & np.isfinite(p)
    valid = np.asarray(valid, dtype=bool)
    yv, pv = y[valid], p[valid]
    out = {
        "n_minutes": int(valid.sum()),
        "mean_true_w": float(np.mean(yv)),
        "mae_w": mae(yv, pv),
        "mae_on_w": mae_on(yv, pv, on_threshold_w),
        "energy_error": energy_error(yv, pv),
    }
    out.update(on_off_scores(yv, pv, on_threshold_w))
    if cycle_params is not None:
        out.update(cycle_scores(np.where(valid, y, np.nan), np.where(valid, p, np.nan), cycle_params))
    return out
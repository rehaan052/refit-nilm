import pandas as pd
import yaml

cfg = yaml.safe_load(open("config.yaml"))
chan = cfg["washing_machine_channel"]
on_thr = cfg["model"]["on_threshold_w"]
parts = []

for h in cfg["model"]["houses"]:
    col = chan[h]
    df = pd.read_csv(
        f"data/clean/CLEAN_House{h}.csv",
        usecols=lambda x: x.strip().lower() in ("time", col),
    )
    df.columns = [x.strip().lower() for x in df.columns]
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    s = df.dropna(subset=["time", col]).reset_index(drop=True)
    run_id = (s[col] != s[col].shift()).cumsum()
    g = s.groupby(run_id).agg(
        start=("time", "first"), end=("time", "last"),
        n_readings=(col, "size"), value_w=(col, "first"),
    )
    g["minutes"] = (g["end"] - g["start"]).dt.total_seconds() / 60
    g = g[(g["minutes"] >= 30) & (g["n_readings"] >= 20) & (g["value_w"] != 0)]
    g.insert(0, "house", h)
    parts.append(g)

out = pd.concat(parts)
out.to_csv("outputs/section3_wm_flat_runs.csv", index=False)

print(f"Non-zero constant runs of the WM channel (>= 30 min, >= 20 readings); ON threshold = {on_thr} W")
for h, g in out.groupby("house"):
    print(f"House {h} ({chan[h]}): runs={len(g)}, total minutes={g['minutes'].sum():.0f}, "
          f"runs above {on_thr} W={int((g['value_w'] > on_thr).sum())}, "
          f"value min/median/max = {g['value_w'].min():.1f} / {g['value_w'].median():.1f} / {g['value_w'].max():.1f}")
print()
print(out.sort_values("minutes", ascending=False).head(15).to_string(index=False))
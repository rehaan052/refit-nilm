import sys

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, ".")
from src.stuck import find_stuck_runs

cfg = yaml.safe_load(open("config.yaml"))
c = cfg["cleaning"]
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

for h in cfg["model"]["houses"]:
    ch = cfg["washing_machine_channel"][h]
    df = pd.read_csv(
        f"data/clean/CLEAN_House{h}.csv",
        usecols=lambda x: x.strip().lower() in ("time", "aggregate", ch),
    )
    df.columns = [x.strip().lower() for x in df.columns]
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)

    runs = find_stuck_runs(df, "aggregate", "time", c["stuck_min_minutes"], c["stuck_min_readings"])
    times = df["time"].to_numpy()
    wm_max, wm_const_pos = [], []
    for _, r in runs.iterrows():
        i0 = np.searchsorted(times, np.datetime64(r["start"]), side="left")
        i1 = np.searchsorted(times, np.datetime64(r["end"]), side="right")
        w = df[ch].iloc[i0:i1]
        wm_max.append(float(w.max()))
        wm_const_pos.append(bool(w.nunique() == 1 and w.iloc[0] > 0))
    runs["wm_max_w"] = wm_max
    runs["wm_frozen_above_zero"] = wm_const_pos

    print("=" * 70)
    print(f"House {h} (washing machine = {ch}), rows read: {len(df):,}")
    print("stuck runs:", len(runs), "| total minutes:", round(float(runs["minutes"].sum()), 1) if len(runs) else 0)
    if len(runs):
        print("longest run (minutes):", round(float(runs["minutes"].max()), 1))
        print("runs with aggregate value 0:", int((runs["value"] == 0).sum()))
        print("runs where washing machine reached more than 20 W:", int((runs["wm_max_w"] > 20).sum()))
        print("runs where washing machine is frozen at a value above 0:", int(runs["wm_frozen_above_zero"].sum()))
        print("most common stuck values:")
        print(runs["value"].value_counts().head(5).to_string())
        print("ten longest runs:")
        print(runs.sort_values("minutes", ascending=False).head(10).to_string(index=False))
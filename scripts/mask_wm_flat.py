import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import minute_parquet_path

cfg = yaml.safe_load(open("config.yaml"))
thr = cfg["model"]["on_threshold_w"]
runs = pd.read_csv("outputs/section3_wm_flat_runs.csv", parse_dates=["start", "end"])
runs = runs[runs["value_w"] > thr]          # only runs frozen above the ON threshold

for h, g in runs.groupby("house"):
    path = minute_parquet_path(cfg, int(h))
    df = pd.read_parquet(path)
    before = int(df["wm"].isna().sum())
    for r in g.itertuples():
        df.loc[r.start.floor("min"):r.end.floor("min"), "wm"] = float("nan")
    after = int(df["wm"].isna().sum())
    df.to_parquet(path)
    print(f"House {h}: {len(g)} runs masked, wm NaN {before:,} -> {after:,} (+{after - before:,})")
import pandas as pd
import yaml
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import minute_parquet_path

cfg = yaml.safe_load(open("config.yaml"))
runs = pd.read_csv("outputs/section3_wm_flat_runs.csv", parse_dates=["start", "end"])
runs = runs[runs["value_w"] > cfg["model"]["on_threshold_w"]]

cache = {}
for r in runs.itertuples():
    if r.house not in cache:
        cache[r.house] = pd.read_parquet(minute_parquet_path(cfg, r.house))
    df = cache[r.house]
    w = df.loc[r.start.floor("min"):r.end.floor("min")]
    print(f"House {r.house} | {r.start} -> {r.end} | frozen {r.value_w:.0f} W | "
          f"minutes in window={len(w)}, wm NaN={int(w['wm'].isna().sum())}, "
          f"aggregate NaN={int(w['aggregate'].isna().sum())}, "
          f"wm min/max={w['wm'].min():.0f}/{w['wm'].max():.0f}")
import json
import sys

import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/minute/prepare_log.json"
log = json.load(open(path))
rows = []
for h, d in log.items():
    rows.append({
        "house": h,
        "wm_channel": d["wm_channel"],
        "first": d["first"][:10],
        "last": d["last"][:10],
        "minutes": d["minutes"],
        "aggregate_nan_min": d["minutes_aggregate_nan"],
        "wm_nan_min": d["minutes_wm_nan"],
        "dup_rows_removed": d["duplicate_rows_removed"],
        "stuck_runs": (d.get("stuck") or {}).get("n_runs"),
        "stuck_rows_to_nan": (d.get("stuck") or {}).get("rows_set_to_nan"),
    })
df = pd.DataFrame(rows)
df["aggregate_nan_pct"] = (100 * df["aggregate_nan_min"] / df["minutes"]).round(1)
df["wm_nan_pct"] = (100 * df["wm_nan_min"] / df["minutes"]).round(1)
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
print(df.to_string(index=False))
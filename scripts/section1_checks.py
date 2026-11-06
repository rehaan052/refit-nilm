"""Section 1 checks: (a) what appliance NaN means, (b) aggregate glitches, (c) duplicate-value agreement."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cleaning import nan_run_lengths  # noqa: E402

PROC = ROOT / "data/processed/house1_raw_cleaned_1min.parquet"
RAW = [ROOT / "data/raw/RAW_House1_Part1.csv", ROOT / "data/raw/RAW_House1_Part2.csv"]
APP = [f"appliance{i}" for i in range(1, 10)]

# ---------------------------------------------------------------- (a)
print("=" * 70)
print("(a) Appliance NaN after cleaning (only minutes where aggregate is fine)")
print("=" * 70)
if not PROC.exists():
    print("Missing:", PROC, "-> unzip section1_results.zip or run scripts/run_section1.py")
else:
    clean = pd.read_parquet(PROC)
    idx = clean.index.tz_localize(None) if clean.index.tz is not None else clean.index
    late = idx >= pd.Timestamp("2014-10-01 02:00")   # roughly the Part2-only range
    ok = (~clean["agg_outage"]).values

    table = pd.DataFrame({
        "all": 100 * clean.loc[ok, APP].isna().mean(),
        "before_Oct2014": 100 * clean.loc[ok & ~late, APP].isna().mean(),
        "from_Oct2014": 100 * clean.loc[ok & late, APP].isna().mean(),
    }).round(2)
    print("NaN % per appliance channel:")
    print(table.to_string())

    wm = clean["appliance5"]
    mask = wm.isna() & pd.Series(ok, index=clean.index)
    rl = nan_run_lengths(mask)
    print("\nWashing machine (appliance5) NaN minutes:", int(mask.sum()))
    print("  of which inside NaN runs longer than 10 min:", int((rl > 10).sum()))
    print("  of which inside NaN runs longer than 60 min:", int((rl > 60).sum()))
    prev = wm.ffill()
    print("Last known WM value before those NaN minutes (rounded to 10 W):")
    print(prev[mask].round(-1).value_counts().head(6).to_string())

# ---------------------------------------------------------------- (b)
print("\n" + "=" * 70)
print("(b) Largest raw aggregate readings")
print("=" * 70)
for p in RAW:
    s = pd.read_csv(p, usecols=["Aggregate"])["Aggregate"]
    print(p.name)
    print("  top 15:", s.nlargest(15).tolist())
    print("  readings > 8000 W :", int((s > 8000).sum()))
    print("  readings > 25000 W:", int((s > 25000).sum()))
    print("  99.99th percentile:", float(s.quantile(0.9999)))
    del s

# ---------------------------------------------------------------- (c)
print("\n" + "=" * 70)
print("(c) Part1: do values agree inside duplicate-timestamp groups?")
print("=" * 70)
cols = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
df = pd.read_csv(RAW[0], dtype={c: "float32" for c in cols})
dup = df[df.duplicated("Time", keep=False)]
print("rows in duplicate-time groups:", len(dup), "| groups:", dup["Time"].nunique())
g = dup.groupby("Time")[cols]
spread = g.max() - g.min()
print("\nShare of groups where max != min (values differ):")
print((spread > 0).mean().round(4).to_string())
print("\nLargest max-min difference (W):")
print(spread.max().round(1).to_string())
print("\n99th percentile of max-min difference (W):")
print(spread.quantile(0.99).round(1).to_string())
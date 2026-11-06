"""Section 1 follow-up: aggregate saturation values and large duplicate differences."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = {
    "Part1": ROOT / "data/raw/RAW_House1_Part1.csv",
    "Part2": ROOT / "data/raw/RAW_House1_Part2.csv",
}

# ---------------------------------------------------------------- (b2)
for name, p in RAW.items():
    df = pd.read_csv(p, usecols=["Time", "Aggregate"])
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    s = df["Aggregate"]
    print("=" * 70)
    print(name)
    print("=" * 70)
    print("quantiles:", s.quantile([0.5, 0.9, 0.99, 0.999]).round(0).to_dict())
    print("exactly 24000 W:", int((s == 24000).sum()))
    hi = s > 8000
    print("> 8000 W:", int(hi.sum()), "| share:", round(100 * hi.mean(), 3), "%")
    print("most common values above 8000 W:")
    print(s[hi].value_counts().head(8).to_string())

    grp = hi.ne(hi.shift(fill_value=False)).cumsum()
    run_len = hi.groupby(grp).sum()[hi.groupby(grp).first()]
    bins = pd.cut(run_len, [0, 1, 5, 30, 10**9], labels=["1 reading", "2-5", "6-30", ">30"])
    print("\nruns of consecutive readings > 8000 W:", len(run_len))
    print(bins.value_counts().sort_index().to_string())

    iso = hi & ~hi.shift(1, fill_value=False) & ~hi.shift(-1, fill_value=False)
    print("isolated single readings:", int(iso.sum()))
    print("  median of previous / next reading:",
          float(s.shift(1)[iso].median()), float(s.shift(-1)[iso].median()))
    print("count of readings > 8000 W by month:")
    print(df.loc[hi, "Time"].dt.to_period("M").value_counts().sort_index().to_string())
    del df, s

# ---------------------------------------------------------------- (c2)
print("\n" + "=" * 70)
print("(c2) Part1: size of value differences inside duplicate-time groups")
print("=" * 70)
cols = ["Aggregate", "Appliance5"]
df = pd.read_csv(RAW["Part1"], usecols=["Time"] + cols, dtype={c: "float32" for c in cols})
dup = df[df.duplicated("Time", keep=False)]
g = dup.groupby("Time")[cols]
spread = g.max() - g.min()
for col in cols:
    for thr in (10, 100, 1000):
        print(f"groups with {col} spread > {thr} W:", int((spread[col] > thr).sum()))

# ---------------------------------------------------------------- (d)
print("\n" + "=" * 70)
print("(d) Cleaned 1-minute aggregate: how many minutes are very high?")
print("=" * 70)
clean = pd.read_parquet(ROOT / "data/processed/house1_raw_cleaned_1min.parquet")
for thr in (5000, 8000, 12000, 20000):
    print(f"minutes with aggregate > {thr} W:", int((clean["aggregate"] > thr).sum()))
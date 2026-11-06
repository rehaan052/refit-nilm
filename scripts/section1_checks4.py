"""Section 1 follow-up 3: how long does an identical value last? (stuck-value threshold)"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = {
    "Part1": ROOT / "data/raw/RAW_House1_Part1.csv",
    "Part2": ROOT / "data/raw/RAW_House1_Part2.csv",
}


def runs_of_identical(df, col):
    d = df.dropna(subset=[col]).reset_index(drop=True)
    rid = d[col].ne(d[col].shift()).cumsum()
    r = d.groupby(rid).agg(
        value=(col, "first"), start=("Time", "first"), end=("Time", "last"), n=(col, "size")
    )
    r["minutes"] = (r["end"] - r["start"]).dt.total_seconds() / 60
    return r


for name, p in RAW.items():
    print("=" * 70)
    print(name)
    print("=" * 70)
    df = pd.read_csv(
        p,
        usecols=["Time", "Aggregate", "Appliance5"],
        dtype={"Aggregate": "float32", "Appliance5": "float32"},
    )
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

    r = runs_of_identical(df, "Aggregate")
    print("AGGREGATE: number of runs of an identical value lasting at least ...")
    for m in (5, 10, 30, 60, 120):
        print(f"  {m:>3} min: {int((r['minutes'] >= m).sum())}")
    long_ = r[r["minutes"] >= 30].sort_values("start")
    print(f"\nAll runs >= 30 min: {len(long_)} | total minutes inside them: {int(long_['minutes'].sum())}")
    print(long_.to_string())

    r5 = runs_of_identical(df, "Appliance5")
    busy = r5[(r5["value"] > 20) & (r5["minutes"] >= 10)].sort_values("minutes", ascending=False)
    print(f"\nWASHING MACHINE (Appliance5): runs of an identical value > 20 W lasting >= 10 min: {len(busy)}")
    print(busy.head(15).to_string())

    if name == "Part2":
        w = df[(df["Time"] >= "2015-02-08 13:24:00") & (df["Time"] <= "2015-02-08 16:12:32")]
        print("\nAppliance5 inside the 12505 W window:")
        print(w["Appliance5"].describe().round(1).to_string())
    del df
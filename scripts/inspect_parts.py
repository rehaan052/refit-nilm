"""Facts-only look at the two raw House 1 part files (no cleaning)."""
import numpy as np
import pandas as pd

FILES = ["data/raw/RAW_House1_Part1.csv", "data/raw/RAW_House1_Part2.csv"]
POWER = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
DTYPE = {c: "float32" for c in POWER}
DTYPE["Unix"] = "float64"

parts = []
for f in FILES:
    df = pd.read_csv(f, dtype=DTYPE)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    parts.append(df)

    print("=" * 70)
    print(f)
    print("rows:", len(df), "| unparseable Time (NaT):", int(df["Time"].isna().sum()))
    print("first/last row Time:", df["Time"].iloc[0], "/", df["Time"].iloc[-1])
    print("min/max Time:", df["Time"].min(), "/", df["Time"].max())
    print("time sorted (monotonic increasing):", df["Time"].is_monotonic_increasing)
    d = df["Time"].diff().dt.total_seconds()
    print("steps going backwards in time:", int((d < 0).sum()))
    print("step seconds quantiles (1%, 50%, 99%, max):",
          d.quantile([0.01, 0.5, 0.99]).round(1).tolist(), d.max())
    print("exact duplicate rows:", int(df.duplicated().sum()))
    print("duplicate Time values:", int(df["Time"].duplicated().sum()))

    off = (df["Time"] - pd.to_datetime(df["Unix"], unit="s")).dt.total_seconds()
    print("Time minus Unix(UTC), seconds, top values:")
    print(off.value_counts().head(6).to_string())

    na = df[POWER].isna()
    print("rows with ALL power cols NaN:", int(na.all(axis=1).sum()))
    print("rows with SOME (not all) power cols NaN:",
          int((na.any(axis=1) & ~na.all(axis=1)).sum()))
    print("Aggregate NaN but some appliance present:",
          int((df["Aggregate"].isna() & df[POWER[1:]].notna().any(axis=1)).sum()))
    print("negative values (all power cols):", int((df[POWER] < 0).sum().sum()))
    print("column max:")
    print(df[POWER].max().to_string())

print("=" * 70)
print("OVERLAP BETWEEN PARTS")
a, b = parts
lo = max(a["Time"].min(), b["Time"].min())
hi = min(a["Time"].max(), b["Time"].max())
print("overlap window:", lo, "->", hi)
if lo < hi:
    for name, df in (("Part1", a), ("Part2", b)):
        n = int(((df["Time"] >= lo) & (df["Time"] <= hi)).sum())
        print(f"{name} rows inside window:", n)
    ad = a.drop_duplicates("Time").set_index("Time")
    bd = b.drop_duplicates("Time").set_index("Time")
    idx = ad.index.intersection(bd.index)
    print("timestamps present in BOTH parts:", len(idx))
    if len(idx):
        for c in POWER:
            x, y = ad.loc[idx, c], bd.loc[idx, c]
            same = (x == y) | (x.isna() & y.isna())
            print(f"  {c}: identical in {same.mean():.4f} of common timestamps")
else:
    print("no overlap")
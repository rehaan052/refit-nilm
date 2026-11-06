"""Section 1 follow-up 2: stuck (frozen) aggregate values, e.g. 12505 W in Part2."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = {
    "Part1": ROOT / "data/raw/RAW_House1_Part1.csv",
    "Part2": ROOT / "data/raw/RAW_House1_Part2.csv",
}
APP = [f"Appliance{i}" for i in range(1, 10)]
STUCK = 12505.0

for name, p in RAW.items():
    print("=" * 70)
    print(name)
    print("=" * 70)
    df = pd.read_csv(p, dtype={c: "float32" for c in ["Aggregate"] + APP})
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

    d = df.dropna(subset=["Aggregate"]).reset_index(drop=True)
    rid = d["Aggregate"].ne(d["Aggregate"].shift()).cumsum()
    runs = d.groupby(rid).agg(
        value=("Aggregate", "first"),
        start=("Time", "first"),
        end=("Time", "last"),
        n=("Aggregate", "size"),
    )
    print("Longest runs of an identical aggregate value (consecutive readings):")
    print(runs.sort_values("n", ascending=False).head(12).to_string())
    print("runs with >= 100 identical readings:", int((runs["n"] >= 100).sum()))

    st = runs[runs["value"] == STUCK]
    if len(st) == 0:
        print(f"\nNo runs with value {STUCK}.")
        continue

    print(f"\nRuns with value {STUCK}: {len(st)} | readings in them: {int(st['n'].sum())}")
    print(st.sort_values("n", ascending=False).head(8).to_string())
    top = st.sort_values("n", ascending=False).iloc[0]

    w = df[(df["Time"] >= top["start"]) & (df["Time"] <= top["end"])]
    print("\nAppliance means inside the longest such run (W):")
    print(w[APP].mean().round(1).to_string())

    c = pd.read_csv(ROOT / "data/clean/CLEAN_House1.csv", usecols=["Time", "Aggregate"])
    c["Time"] = pd.to_datetime(c["Time"], errors="coerce")
    cw = c[(c["Time"] >= top["start"]) & (c["Time"] <= top["end"])]
    print("\nOfficial CLEAN aggregate over the same window (top 3 values):")
    print(cw["Aggregate"].value_counts().head(3).to_string())
    del c
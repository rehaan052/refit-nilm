import pandas as pd

files = ["data/raw/RAW_House1_Part1.csv", "data/raw/RAW_House1_Part2.csv"]
parts = []
for i, f in enumerate(files, start=1):
    d = pd.read_csv(f, usecols=lambda c: c.strip().lower() in ("time", "aggregate"))
    d.columns = [c.strip().lower() for c in d.columns]
    d["part"] = i
    parts.append(d)
df = pd.concat(parts, ignore_index=True)
df["time"] = pd.to_datetime(df["time"], errors="coerce")

high = df[df["aggregate"] > 23999].sort_values("time")
print("n readings above 23999:", len(high))
print()
print("value counts:")
print(high["aggregate"].value_counts().sort_index())
print()
print("per part:")
print(high["part"].value_counts().sort_index())
print()
print("per day:")
print(high["time"].dt.date.value_counts().sort_index())
print()
print("first 10 rows:")
print(high.head(10).to_string())
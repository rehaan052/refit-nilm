import pandas as pd

windows = [
    ("2014-08-01 17:12:18", "2014-08-02 12:58:51"),
    ("2014-09-06 22:52:04", "2014-09-07 12:24:09"),
]

raw = pd.read_csv("data/raw/RAW_House1_Part1.csv", usecols=lambda x: x.strip().lower() in ("time", "aggregate"))
raw.columns = [x.strip().lower() for x in raw.columns]
raw["time"] = pd.to_datetime(raw["time"], errors="coerce")

clean = pd.read_csv("data/clean/CLEAN_House1.csv", usecols=lambda x: x.strip().lower() in ("time", "aggregate"))
clean.columns = [x.strip().lower() for x in clean.columns]
clean["time"] = pd.to_datetime(clean["time"], errors="coerce")

for a, b in windows:
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    print("window", a, "to", b)
    for name, d in (("raw Part 1", raw), ("CLEAN", clean)):
        w = d[(d["time"] >= a) & (d["time"] <= b)]
        print(f"  {name}: rows={len(w):,}, unique aggregate values={w['aggregate'].nunique()}, "
              f"min={w['aggregate'].min()}, max={w['aggregate'].max()}")
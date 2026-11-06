"""Facts-only, part 3: lag scan between parts, DST-day behaviour, 3 high Aggregate rows."""
import numpy as np
import pandas as pd

FILES = {"Part1": "data/raw/RAW_House1_Part1.csv", "Part2": "data/raw/RAW_House1_Part2.csv"}
DT = {"Aggregate": "float32"}
d = {}
for k, f in FILES.items():
    df = pd.read_csv(f, usecols=["Time", "Aggregate"], dtype=DT)
    df["Time"] = pd.to_datetime(df["Time"])
    d[k] = df

print("Part2 rows with Aggregate > 25000:")
print(d["Part2"][d["Part2"]["Aggregate"] > 25000].to_string())

print("\nROWS PER HOUR around DST dates (row count per clock hour)")
for k, lo, hi in [("Part1", "2013-10-27 00:00", "2013-10-27 04:00"),
                  ("Part1", "2014-03-30 00:00", "2014-03-30 04:00"),
                  ("Part2", "2014-10-26 00:00", "2014-10-26 04:00"),
                  ("Part2", "2015-03-29 00:00", "2015-03-29 04:00")]:
    s = d[k][(d[k]["Time"] >= lo) & (d[k]["Time"] < hi)]
    print(k, lo, "->", hi)
    print(s.groupby(s["Time"].dt.floor("h")).size().to_string())

print("\nLAG SCAN on overlap (1-min Aggregate mean; positive lag = Part1 shifted later)")


def minute(df):
    m = df.copy()
    m["Time"] = m["Time"].dt.floor("min")
    return m.groupby("Time")["Aggregate"].mean()


a, b = minute(d["Part1"]), minute(d["Part2"])
lo, hi = b.index.min(), a.index.max()
idx = pd.date_range(lo, hi, freq="min")
a, b = a.reindex(idx), b.reindex(idx)
rows = []
for lag in range(-180, 181):
    x = a.shift(lag)
    ok = x.notna() & b.notna()
    diff = (x[ok] - b[ok]).abs()
    rows.append((lag, int(ok.sum()), float(x[ok].corr(b[ok])), float((diff <= 5).mean())))
r = pd.DataFrame(rows, columns=["lag_min", "n", "corr", "share_within_5W"])
print("lag 0:", r[r.lag_min == 0].round(4).to_string(index=False, header=False))
print("top 5 lags by corr:")
print(r.sort_values("corr", ascending=False).head(5).round(4).to_string(index=False))
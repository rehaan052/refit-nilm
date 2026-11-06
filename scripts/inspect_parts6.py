"""Facts-only, part 6: per-day best lag of each RAW part vs the OFFICIAL CLEAN_House1 file
(overlap window only). Lag k: raw series shifted k minutes later. Scan is +-120 min because
we do not know if CLEAN Time uses the same clock convention as RAW Time.
Aggregate > 25000 -> NaN in raw; Aggregate == 0 -> NaN in CLEAN (zero-filled outages)."""
import pandas as pd

RAW = {"Part1": "data/raw/RAW_House1_Part1.csv", "Part2": "data/raw/RAW_House1_Part2.csv"}
CLEAN = "data/clean/CLEAN_House1.csv"


def minute_raw(f):
    df = pd.read_csv(f, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
    df["Time"] = pd.to_datetime(df["Time"]).dt.floor("min")
    df.loc[df["Aggregate"] > 25000, "Aggregate"] = float("nan")
    return df.groupby("Time")["Aggregate"].mean()


c = pd.read_csv(CLEAN, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
print("CLEAN rows:", len(c), "| first/last Time:", c["Time"].iloc[0], "/", c["Time"].iloc[-1])
c["Time"] = pd.to_datetime(c["Time"]).dt.floor("min")
c.loc[c["Aggregate"] == 0, "Aggregate"] = float("nan")
ref = c.groupby("Time")["Aggregate"].mean()

p = {k: minute_raw(f) for k, f in RAW.items()}
lo, hi = p["Part2"].index.min(), p["Part1"].index.max()
idx = pd.date_range(lo, hi, freq="min")
ref = ref.reindex(idx)
p = {k: v.reindex(idx) for k, v in p.items()}
days = idx.normalize()
LAGS = range(-120, 121)

out = {}
for name, s in p.items():
    mad, cnt = {}, {}
    for k in LAGS:
        d = (s.shift(k) - ref).abs()
        g = d.groupby(days)
        mad[k], cnt[k] = g.mean(), g.count()
    mad, cnt = pd.DataFrame(mad), pd.DataFrame(cnt)
    mad = mad.where(cnt >= 600)
    out[name] = pd.DataFrame({
        "best_lag": mad.idxmin(axis=1),
        "mad_best": mad.min(axis=1).round(1),
        "mad_lag0": mad[0].round(1),
    })

r = out["Part1"].join(out["Part2"], lsuffix="_p1", rsuffix="_p2").dropna(how="all")
print(r.to_string())
for name in out:
    print("\n", name, "best_lag value counts (days):")
    print(out[name]["best_lag"].dropna().astype(int).value_counts().sort_index().to_string())
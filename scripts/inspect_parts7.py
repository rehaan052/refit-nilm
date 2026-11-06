"""Facts-only, part 7: per-day best lag of each RAW part vs OFFICIAL CLEAN_House1 over each
part's FULL date range. Lag k: raw series shifted k minutes later. Output on screen is
run-length compressed; per-day table goes to outputs/inspect_parts7_perday.csv.
Raw Aggregate > 25000 -> NaN; CLEAN Aggregate == 0 -> NaN (zero-filled outages)."""
import pandas as pd

RAW = {"Part1": "data/raw/RAW_House1_Part1.csv", "Part2": "data/raw/RAW_House1_Part2.csv"}
CLEAN = "data/clean/CLEAN_House1.csv"
LAGS = range(-125, 11)


def minute_raw(f):
    df = pd.read_csv(f, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
    df["Time"] = pd.to_datetime(df["Time"]).dt.floor("min")
    df.loc[df["Aggregate"] > 25000, "Aggregate"] = float("nan")
    return df.groupby("Time")["Aggregate"].mean()


c = pd.read_csv(CLEAN, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
c["Time"] = pd.to_datetime(c["Time"]).dt.floor("min")
c.loc[c["Aggregate"] == 0, "Aggregate"] = float("nan")
ref_all = c.groupby("Time")["Aggregate"].mean()

frames = []
for name, f in RAW.items():
    s = minute_raw(f)
    idx = pd.date_range(s.index.min(), s.index.max(), freq="min")
    s = s.reindex(idx)
    ref = ref_all.reindex(idx)
    days = idx.normalize()
    mad, cnt = {}, {}
    for k in LAGS:
        g = (s.shift(k) - ref).abs().groupby(days)
        mad[k], cnt[k] = g.mean(), g.count()
    mad, cnt = pd.DataFrame(mad), pd.DataFrame(cnt)
    mad = mad.where(cnt >= 600)
    mad = mad[mad.notna().any(axis=1)]
    res = pd.DataFrame({"part": name, "best_lag": mad.idxmin(axis=1),
                        "mad_best": mad.min(axis=1).round(1)})
    res["mad_lag0"] = mad[0].round(1)
    frames.append(res)

r = pd.concat(frames)
r.index.name = "day"
r.to_csv("outputs/inspect_parts7_perday.csv")

for name in RAW:
    x = r[r["part"] == name].reset_index()
    x["run"] = (x["best_lag"] != x["best_lag"].shift()).cumsum()
    runs = x.groupby("run").agg(start=("day", "min"), end=("day", "max"),
                                lag=("best_lag", "first"), days=("day", "size"),
                                med_mad=("mad_best", "median"))
    print("=" * 60, "\n", name, "| days analysed:", len(x))
    print(runs.to_string(index=False))
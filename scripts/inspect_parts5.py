"""Facts-only, part 5: best lag between the two parts, per day, in the overlap window.
Lag k: Part1 shifted k minutes later (positive = Part1 events happen EARLIER than Part2).
Criterion: mean abs difference of 1-min Aggregate (Aggregate > 25000 set to NaN first)."""
import pandas as pd

F = {"Part1": "data/raw/RAW_House1_Part1.csv", "Part2": "data/raw/RAW_House1_Part2.csv"}


def minute(f):
    df = pd.read_csv(f, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
    df["Time"] = pd.to_datetime(df["Time"]).dt.floor("min")
    df.loc[df["Aggregate"] > 25000, "Aggregate"] = float("nan")
    return df.groupby("Time")["Aggregate"].mean()


a, b = minute(F["Part1"]), minute(F["Part2"])
idx = pd.date_range(b.index.min(), a.index.max(), freq="min")
a, b = a.reindex(idx), b.reindex(idx)
days = idx.normalize()
LAGS = range(-20, 21)
shifted = {k: a.shift(k) for k in LAGS}

rows = []
for day in days.unique():
    m = days == day
    bb = b[m]
    res = {}
    for k in LAGS:
        x = shifted[k][m]
        ok = x.notna() & bb.notna()
        if ok.sum() >= 600:
            res[k] = (float((x[ok] - bb[ok]).abs().mean()), int(ok.sum()))
    if 0 not in res:
        continue
    kb = min(res, key=lambda k: res[k][0])
    rows.append((day.date(), res[0][1], round(res[0][0], 1), kb, round(res[kb][0], 1)))

r = pd.DataFrame(rows, columns=["day", "n_min", "mad_lag0", "best_lag", "mad_best"])
r["improved_20pct"] = r["mad_best"] < 0.8 * r["mad_lag0"]
print(r.to_string(index=False))
print("\ndays analysed:", len(r))
print("best_lag value counts:")
print(r["best_lag"].value_counts().sort_index().to_string())
print("days where best_lag != 0 AND mad improves >20%:", int((r["improved_20pct"] & (r["best_lag"] != 0)).sum()))
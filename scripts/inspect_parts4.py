"""Facts-only, part 4: where do the two parts disagree in the overlap? + 3 high rows."""
import numpy as np
import pandas as pd

F = {"Part1": "data/raw/RAW_House1_Part1.csv", "Part2": "data/raw/RAW_House1_Part2.csv"}
d = {}
for k, f in F.items():
    df = pd.read_csv(f, usecols=["Time", "Aggregate"], dtype={"Aggregate": "float32"})
    df["Time"] = pd.to_datetime(df["Time"])
    d[k] = df

p2 = d["Part2"].reset_index(drop=True)
print("NEIGHBOURS of the 3 Part2 rows with Aggregate > 25000")
for i in p2.index[p2["Aggregate"] > 25000]:
    print(p2.iloc[i - 3:i + 4].to_string(), "\n")


def minute(df):
    m = df.copy()
    m["Time"] = m["Time"].dt.floor("min")
    g = m.groupby("Time")["Aggregate"]
    return pd.DataFrame({"mean": g.mean(), "n": g.count(), "std": g.std()})


a, b = minute(d["Part1"]), minute(d["Part2"])
j = a.join(b, how="inner", lsuffix="_p1", rsuffix="_p2").dropna(subset=["mean_p1", "mean_p2"])
j = j.loc[b.index.min():a.index.max()]
j["absdiff"] = (j["mean_p1"] - j["mean_p2"]).abs()
j["bad"] = j["absdiff"] > 5

print("minutes compared:", len(j), "| share bad (>5 W):", round(j["bad"].mean(), 4))
print("readings per minute (mean)  Part1:", round(j["n_p1"].mean(), 2),
      " Part2:", round(j["n_p2"].mean(), 2))
print("share bad by Part1 readings/min:")
print(j.groupby(j["n_p1"].clip(upper=12))["bad"].agg(["mean", "size"]).round(3).to_string())
print("share bad by Part2 readings/min:")
print(j.groupby(j["n_p2"].clip(upper=12))["bad"].agg(["mean", "size"]).round(3).to_string())
print("share bad by month:")
print(j.groupby(j.index.to_period("M"))["bad"].agg(["mean", "size"]).round(3).to_string())
print("share bad by hour of day:")
print(j.groupby(j.index.hour)["bad"].mean().round(3).to_string())
print("bad minutes: diff quantiles (50/90/99%):",
      j.loc[j["bad"], "absdiff"].quantile([.5, .9, .99]).round(1).tolist())
print("signed diff (Part1 - Part2) on bad minutes: mean",
      round(float((j.loc[j["bad"], "mean_p1"] - j.loc[j["bad"], "mean_p2"]).mean()), 2))
print("20 worst minutes:")
print(j.sort_values("absdiff", ascending=False).head(20).round(1).to_string())
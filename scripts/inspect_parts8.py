"""Facts-only, part 8: how does CLEAN_House1 encode time? (no raw files needed)"""
import pandas as pd

c = pd.read_csv("data/clean/CLEAN_House1.csv", usecols=["Time", "Unix"], dtype={"Unix": "float64"})
c["Time"] = pd.to_datetime(c["Time"])
off = (c["Time"] - pd.to_datetime(c["Unix"], unit="s")).dt.total_seconds()
c["off_h"] = (off / 3600).round(2)

print("Time minus Unix(UTC), hours: value counts")
print(c["off_h"].value_counts().to_string())

x = c.assign(month=c["Time"].dt.to_period("M"))
print("\nTime minus Unix by month (hours): most common value / share")
g = x.groupby("month")["off_h"].agg(lambda s: s.value_counts().index[0])
sh = x.groupby("month")["off_h"].agg(lambda s: s.value_counts(normalize=True).iloc[0].round(3))
print(pd.DataFrame({"mode_off_h": g, "share": sh}).to_string())

print("\nROWS PER CLOCK HOUR around DST dates in CLEAN (by Time)")
for lo, hi in [("2013-10-27 00:00", "2013-10-27 04:00"), ("2014-03-30 00:00", "2014-03-30 04:00"),
               ("2014-10-26 00:00", "2014-10-26 04:00"), ("2015-03-29 00:00", "2015-03-29 04:00")]:
    s = c[(c["Time"] >= lo) & (c["Time"] < hi)]
    print(lo, "->", hi)
    print(s.groupby(s["Time"].dt.floor("h")).size().to_string())
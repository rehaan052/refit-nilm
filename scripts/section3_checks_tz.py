import numpy as np
import pandas as pd
import yaml

cfg = yaml.safe_load(open("config.yaml"))
transition_days = ["2014-03-30", "2014-10-26", "2015-03-29"]

for h in cfg["model"]["houses"]:
    df = pd.read_csv(
        f"data/clean/CLEAN_House{h}.csv",
        usecols=lambda x: x.strip().lower() in ("time", "aggregate"),
    )
    df.columns = [x.strip().lower() for x in df.columns]
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    print("=" * 70)
    print("House", h)
    print("Test 1: rows per clock hour (hours 00 to 05) on the days the UK clocks change")
    print("  local clock time: spring day has NO rows in hour 02; autumn day has a repeated hour 01")
    print("  UTC time: every hour has rows on both days")
    for d in transition_days:
        day = df[df["time"].dt.strftime("%Y-%m-%d") == d]
        counts = day["time"].dt.hour.value_counts().reindex(range(0, 6), fill_value=0).sort_index()
        dup = int(day["time"].duplicated().sum())
        print(f"  {d}: rows={len(day):6d} | rows in hours 0..5 = {counts.tolist()} | duplicated timestamps = {dup}")

    print("Test 2: hour of the morning rise and of the evening peak of the mean aggregate")
    print("  local clock time: summer and winter give (about) the same hours; UTC time: summer is one hour EARLIER")
    hour = df["time"].dt.hour
    month = df["time"].dt.month
    for name, months in (("summer (Jun-Aug)", [6, 7, 8]), ("winter (Dec-Feb)", [12, 1, 2])):
        m = df[month.isin(months)]
        if len(m) == 0:
            print(f"  {name}: no data")
            continue
        prof = m.groupby(m["time"].dt.hour)["aggregate"].mean().reindex(range(24))
        rise = int(prof.diff().loc[4:10].idxmax())
        peak = int(prof.loc[16:23].idxmax())
        print(f"  {name}: morning rise at hour {rise:02d}, evening peak at hour {peak:02d}")
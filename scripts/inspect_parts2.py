"""Facts-only, part 2: gaps, high values, same-Time conflicts, overlap at 1-min."""
import numpy as np
import pandas as pd

FILES = ["data/raw/RAW_House1_Part1.csv", "data/raw/RAW_House1_Part2.csv"]
POWER = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
DTYPE = {c: "float32" for c in POWER}
DTYPE["Unix"] = "float64"


def load(f):
    df = pd.read_csv(f, dtype=DTYPE)
    df["Time"] = pd.to_datetime(df["Time"])
    return df


parts = {"Part1": load(FILES[0]), "Part2": load(FILES[1])}

for name, df in parts.items():
    print("=" * 70)
    print(name)
    t = df["Time"]
    d = t.diff().dt.total_seconds()

    print("backward steps (row, time before -> time after):")
    for i in np.where(d < 0)[0]:
        print("  row", i, t.iloc[i - 1], "->", t.iloc[i])

    s = t.drop_duplicates().sort_values().reset_index(drop=True)
    g = s.diff().dt.total_seconds()
    print("largest gaps (gap start, hours):")
    for i, v in g.nlargest(8).items():
        print("  ", s.iloc[i - 1], round(v / 3600, 1))
    print("number of gaps > 10 min:", int((g > 600).sum()))

    print("values above limits:")
    print("  Aggregate > 25000:", int((df["Aggregate"] > 25000).sum()))
    hi = {}
    for c in POWER[1:]:
        m = df[c] > 4000
        print(f"  {c} > 4000:", int(m.sum()))
        for v, n in df.loc[m, c].value_counts().head(5).items():
            hi[v] = hi.get(v, 0) + int(n)
    print("most frequent values above 4000 (all appliance cols):")
    for v, n in sorted(hi.items(), key=lambda x: -x[1])[:8]:
        print("  ", v, n)

    conf = df[df["Time"].duplicated(keep=False) & ~df.duplicated(keep=False)]
    print("rows sharing Time with a DIFFERENT row:", len(conf))
    print(conf.sort_values("Time").head(8)[["Time"] + POWER[:6]].to_string())

print("=" * 70)
print("OVERLAP AT 1-MIN (appliances > 4000 W masked to NaN; Aggregate unmasked)")
cols = ["Aggregate", "Appliance1", "Appliance5"]


def minute(df):
    m = df[["Time"] + cols].copy()
    for c in cols[1:]:
        m.loc[m[c] > 4000, c] = np.nan
    m["Time"] = m["Time"].dt.floor("min")
    return m.groupby("Time")[cols].mean()


a, b = minute(parts["Part1"]), minute(parts["Part2"])
lo, hi_t = b.index.min(), a.index.max()
a, b = a.loc[lo:hi_t], b.loc[lo:hi_t]
total = int((hi_t - lo).total_seconds() // 60) + 1
print("window:", lo, "->", hi_t, "| minutes in window:", total)
print("minutes with Aggregate data  Part1:", int(a["Aggregate"].notna().sum()),
      " Part2:", int(b["Aggregate"].notna().sum()))
j = a.join(b, how="inner", lsuffix="_p1", rsuffix="_p2")
for c in cols:
    x, y = j[c + "_p1"], j[c + "_p2"]
    ok = x.notna() & y.notna()
    diff = (x[ok] - y[ok]).abs()
    print(c, "| minutes in both:", int(ok.sum()),
          "| mean abs diff:", round(float(diff.mean()), 2),
          "| median abs diff:", round(float(diff.median()), 2),
          "| corr:", round(float(x[ok].corr(y[ok])), 4),
          "| share within 5 W:", round(float((diff <= 5).mean()), 4))
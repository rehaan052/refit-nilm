import numpy as np
import pandas as pd

from src.data import load_clean_house


def write_csv(path, n=2000, header=("Time", "Unix", "Aggregate", "Appliance1", "Appliance2", "Appliance5", "Issues")):
    t = pd.date_range("2014-03-01", periods=n, freq="8s")
    df = pd.DataFrame({
        "Time": t.strftime("%Y-%m-%d %H:%M:%S"),
        "Unix": (t.astype("int64") // 10**9),
        "Aggregate": 300 + np.arange(n) % 7,
        "Appliance1": 50.0, "Appliance2": 0.0, "Appliance5": 0.0, "Issues": 0,
    })
    df.loc[100:110, "Appliance5"] = 700.0
    df[list(header)].to_csv(path, index=False)


def test_loader_returns_minute_frame(tmp_path):
    p = tmp_path / "CLEAN_House9.csv"
    write_csv(p)
    df, log = load_clean_house(p, "appliance5", stuck_min_minutes=None)
    assert list(df.columns) == ["aggregate", "wm"]
    assert (df.index.to_series().diff().dropna() == pd.Timedelta("1min")).all()
    assert df["wm"].max() > 0
    assert log["rows_read"] == 2000


def test_missing_channel_gives_clear_error(tmp_path):
    p = tmp_path / "CLEAN_House9.csv"
    write_csv(p, header=("Time", "Unix", "Aggregate", "Appliance1"))
    try:
        load_clean_house(p, "appliance5", stuck_min_minutes=None)
    except KeyError as e:
        assert "appliance5" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_stuck_aggregate_becomes_nan(tmp_path):
    p = tmp_path / "CLEAN_House9.csv"
    n = 3000
    t = pd.date_range("2014-03-01", periods=n, freq="8s")
    df = pd.DataFrame({"Time": t.strftime("%Y-%m-%d %H:%M:%S"), "Unix": t.astype("int64") // 10**9,
                       "Aggregate": 300 + (np.arange(n) * 7919) % 53, "Appliance5": 0.0})
    df.loc[500:1500, "Aggregate"] = 12505.0       # 1000 readings x 8 s = ~133 min stuck
    df.to_csv(p, index=False)
    out, log = load_clean_house(p, "appliance5", stuck_min_minutes=30, stuck_min_readings=20, max_fill_minutes=3)
    assert out["aggregate"].max() < 1000
    assert out["aggregate"].isna().sum() > 100
import numpy as np
import pandas as pd

from src.stuck import apply_stuck_aggregate, find_stuck_runs


def make_frame(tz=None):
    t = pd.date_range("2014-01-01 00:00:00", periods=600, freq="10s", tz=tz)  # 100 minutes
    rng = np.random.default_rng(0)
    agg = 300 + rng.normal(0, 20, len(t)).round(0)
    df = pd.DataFrame({"time": t, "aggregate": agg, "appliance1": 5.0, "appliance5": 0.0})
    # stuck window: rows 120..300 (30 min = 1800 s)
    df.loc[120:300, "aggregate"] = 12505.0
    df.loc[120:300, "appliance5"] = 2256.0
    # partial rows inside the window: aggregate NaN but other channel present
    df.loc[[150, 200], "aggregate"] = np.nan
    return df


def test_long_identical_run_is_flagged():
    df = make_frame()
    runs = find_stuck_runs(df, min_minutes=30, min_readings=20)
    assert len(runs) == 1
    assert runs.loc[0, "value"] == 12505.0
    assert runs.loc[0, "minutes"] >= 30


def test_apply_sets_all_channels_nan_inside_window_only():
    df = make_frame()
    out, log = apply_stuck_aggregate(df, min_minutes=30, min_readings=20)
    inside = out.loc[120:300]
    assert inside[["aggregate", "appliance1", "appliance5"]].isna().all().all()  # incl. the partial rows
    assert out.loc[:119, "aggregate"].notna().all()
    assert out.loc[301:, "appliance1"].notna().all()
    assert log["n_runs"] == 1 and log["rows_set_to_nan"] == 181


def test_short_identical_run_not_flagged():
    df = make_frame()
    df.loc[400:430, "aggregate"] = 777.0  # 5 minutes
    runs = find_stuck_runs(df, min_minutes=30, min_readings=20)
    assert 777.0 not in runs["value"].tolist()


def test_two_far_apart_identical_readings_not_flagged():
    # Same value twice, 60 minutes apart, nothing in between: a gap, not a stuck sensor
    t = pd.to_datetime(["2014-01-01 00:00:00", "2014-01-01 01:00:00"])
    df = pd.DataFrame({"time": t, "aggregate": [250.0, 250.0], "appliance1": [1.0, 1.0]})
    assert len(find_stuck_runs(df, min_minutes=30, min_readings=20)) == 0


def test_works_with_tz_aware_time():
    df = make_frame(tz="UTC")
    out, log = apply_stuck_aggregate(df)
    assert log["n_runs"] == 1
    assert out.loc[200, "appliance5"] != out.loc[200, "appliance5"]  # NaN


def test_unsorted_input_raises():
    df = make_frame().iloc[::-1]
    try:
        apply_stuck_aggregate(df)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
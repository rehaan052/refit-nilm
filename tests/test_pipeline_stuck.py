import numpy as np
import pandas as pd

from src.cleaning import run_cleaning_pipeline


def make_raw():
    t = pd.date_range("2014-03-10 00:00:00", periods=2 * 3600 // 8, freq="8s")  # 2 hours
    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "time": t,
        "aggregate": 300 + rng.normal(0, 20, len(t)).round(0),
        "appliance1": 5.0,
        "appliance5": 0.0,
    })
    s, e = 3600 // 8, 3600 // 8 + 2400 // 8   # a 40-minute stuck stretch starting at minute 60
    df.loc[s:e, "aggregate"] = 12505.0
    df.loc[s:e, "appliance5"] = 2256.0
    return df


def cfg(stuck=True, agg_max=23999):
    c = {"dedup_keep": "first", "resample_rule": "1min", "resample_agg": "mean",
         "max_fill_minutes": 3, "aggregate_max_w": agg_max, "appliance_max_w": 4000}
    if stuck:
        c.update({"stuck_min_minutes": 30, "stuck_min_readings": 20})
    return {"cleaning": c}


def test_pipeline_turns_stuck_window_into_outage():
    out, log = run_cleaning_pipeline(make_raw(), cfg(stuck=True))
    assert log["stuck_aggregate"]["n_runs"] == 1
    assert out["agg_outage"].sum() >= 38           # roughly the 40 stuck minutes
    assert out["aggregate"].max() < 1000           # 12505 W never reaches the 1-minute data
    assert out["appliance5"].max() < 100           # 2256 W of the frozen WM channel is gone too


def test_without_stuck_rule_old_behaviour_is_kept():
    out, log = run_cleaning_pipeline(make_raw(), cfg(stuck=False))
    assert "stuck_aggregate" not in log
    assert out["aggregate"].max() > 12000


def test_24000_ceiling_value_is_masked():
    df = make_raw()
    df.loc[10, "aggregate"] = 24000.0
    _, log = run_cleaning_pipeline(df, cfg(stuck=False, agg_max=23999))
    assert log["impossible_values_set_to_nan"]["aggregate"]["above_limit"] == 1
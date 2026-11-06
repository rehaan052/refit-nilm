"""Unit tests on small synthetic frames for src/cleaning.py."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cleaning import (  # noqa: E402
    combine_parts_primary_first,
    fill_short_gaps,
    flag_aggregate_outages,
    local_to_utc,
    mask_impossible_values,
    nan_run_lengths,
    outage_table,
    parse_timestamps,
    resample_to_grid,
    run_cleaning_pipeline,
    sort_and_dedup,
    standardise_columns,
)


def test_standardise_columns_maps_names():
    df = pd.DataFrame(columns=["Time", "Unix", "Aggregate", "Appliance1"])
    out = standardise_columns(df)
    assert list(out.columns) == ["time", "unix", "aggregate", "appliance1"]


def test_parse_timestamps_bad_value_becomes_nat():
    df = pd.DataFrame({"time": ["2014-01-01 00:00:00", "not a time"], "aggregate": [1.0, 2.0]})
    out = parse_timestamps(df)
    assert out["time"].isna().tolist() == [False, True]


def test_nan_run_lengths():
    mask = pd.Series([False, True, True, False, True])
    assert nan_run_lengths(mask).tolist() == [0, 2, 2, 0, 1]


def test_sort_and_dedup_keep_first():
    t1, t2 = pd.Timestamp("2014-01-01 00:00:00"), pd.Timestamp("2014-01-01 00:00:08")
    df = pd.DataFrame({"time": [t2, t1, t1], "aggregate": [3.0, 1.0, 2.0]})
    out, log = sort_and_dedup(df, keep="first")
    assert out["time"].tolist() == [t1, t2]
    assert out["aggregate"].tolist() == [1.0, 3.0]
    assert log["duplicate_rows_removed"] == 1


def test_sort_and_dedup_keep_mean():
    t1 = pd.Timestamp("2014-01-01 00:00:00")
    df = pd.DataFrame({"time": [t1, t1], "aggregate": [1.0, 2.0]})
    out, _ = sort_and_dedup(df, keep="mean")
    assert len(out) == 1
    assert out["aggregate"].iloc[0] == 1.5


def test_mask_impossible_values():
    df = pd.DataFrame({
        "time": pd.date_range("2014-01-01", periods=3, freq="min"),
        "aggregate": [100.0, 30000.0, -5.0],
        "appliance1": [10.0, 5000.0, 0.0],
    })
    out, log = mask_impossible_values(df, aggregate_max=25000, appliance_max=4000)
    assert out["aggregate"].isna().tolist() == [False, True, True]
    assert out["appliance1"].isna().tolist() == [False, True, False]
    assert log["aggregate"] == {"negative": 1, "above_limit": 1}


def test_resample_to_grid_counts_readings_and_leaves_empty_minute_nan():
    t = pd.to_datetime(["2014-01-01 00:00:00", "2014-01-01 00:00:30", "2014-01-01 00:02:10"])
    df = pd.DataFrame({"time": t, "aggregate": [10.0, 20.0, 40.0]})
    out = resample_to_grid(df, "1min", "mean")
    assert len(out) == 3
    assert out["aggregate"].iloc[0] == 15.0
    assert np.isnan(out["aggregate"].iloc[1])
    assert out["n_raw_readings"].tolist() == [2, 0, 1]


def test_fill_short_gaps_fills_short_not_long():
    df = pd.DataFrame({"aggregate": [1.0, np.nan, np.nan, np.nan, 7.0, np.nan, 9.0]})
    out, counts = fill_short_gaps(df, max_gap_steps=2)
    assert out["aggregate"].isna().tolist() == [False, True, True, True, False, False, False]
    assert out["aggregate"].iloc[5] == 7.0
    assert counts["aggregate"] == 1


def test_outage_table_lists_each_outage():
    idx = pd.date_range("2014-01-01", periods=5, freq="min")
    df = pd.DataFrame({"aggregate": [1.0, np.nan, np.nan, 4.0, np.nan]}, index=idx)
    flagged = flag_aggregate_outages(df)
    table = outage_table(flagged)
    assert table["minutes"].tolist() == [2.0, 1.0]
    assert table["start"].iloc[0] == idx[1]


def test_combine_parts_keeps_part1_in_overlap():
    t = pd.date_range("2014-07-01", periods=6, freq="min")
    p1 = pd.DataFrame({"time": t[:4], "aggregate": [1.0] * 4, "part": 1})
    p2 = pd.DataFrame({"time": t[2:], "aggregate": [9.0] * 4, "part": 2})
    out, log = combine_parts_primary_first(pd.concat([p1, p2], ignore_index=True))
    assert len(out) == 6
    assert out.sort_values("time")["aggregate"].tolist() == [1, 1, 1, 1, 9, 9]
    assert "part" not in out.columns


def test_local_to_utc_shifts_bst_and_drops_ambiguous_and_nonexistent():
    t = pd.to_datetime([
        "2014-07-01 12:00:00",   # BST -> 11:00 UTC
        "2013-10-27 01:30:00",   # repeated hour -> dropped
        "2013-12-01 12:00:00",   # GMT -> unchanged
        "2014-03-30 01:30:00",   # does not exist -> dropped
    ])
    df = pd.DataFrame({"time": t, "aggregate": [1.0, 2.0, 3.0, 4.0]})
    out, log = local_to_utc(df, "Europe/London")
    assert out["time"].tolist() == [pd.Timestamp("2014-07-01 11:00:00"), pd.Timestamp("2013-12-01 12:00:00")]
    assert log["rows_dropped_ambiguous_or_nonexistent"] == 2


def test_pipeline_fills_short_gap_and_flags_long_outage():
    minutes = pd.date_range("2014-01-01", periods=14, freq="min")
    present = [0, 1, 2, 5, 6, 13]          # gaps: minutes 3-4 (2 min, filled), 7-12 (6 min, outage)
    raw = pd.DataFrame({
        "Time": minutes[present].strftime("%Y-%m-%d %H:%M:%S"),
        "Aggregate": [100.0] * len(present),
    })
    cfg = {"cleaning": {
        "dedup_keep": "first", "resample_rule": "1min", "resample_agg": "mean",
        "max_fill_minutes": 3, "aggregate_max_w": 25000, "appliance_max_w": 4000,
    }}
    out, log = run_cleaning_pipeline(raw, cfg)
    assert log["minutes_total"] == 14
    assert log["minutes_aggregate_filled"] == 2
    assert log["minutes_aggregate_outage"] == 6
    assert log["n_outages"] == 1
    assert out["agg_outage"].sum() == 6
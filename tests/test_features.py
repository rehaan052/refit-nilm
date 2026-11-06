import numpy as np
import pandas as pd
import pytest

from src.features import context_minutes, make_features

M = {"window_minutes": 30, "rolling_windows": [5, 15, 31, 61], "baseload_minutes": 60}


def agg(n=300):
    idx = pd.date_range("2014-03-01", periods=n, freq="1min")
    return pd.Series(np.arange(n, dtype="float64"), index=idx)


def test_shift_features_look_forward_and_backward():
    a = agg()
    X = make_features(a, M)
    t = 100
    assert X["agg_t+5"].iloc[t] == a.iloc[t + 5]
    assert X["agg_t-5"].iloc[t] == a.iloc[t - 5]
    assert np.isnan(X["agg_t+5"].iloc[-1])


def test_baseload_is_a_minimum_not_the_current_value():
    a = agg()
    a.iloc[150] = 5000.0
    X = make_features(a, M)
    assert X["baseload"].iloc[150] < 5000
    assert X["agg_minus_baseload"].iloc[150] > 4000


def test_time_features_only_when_asked():
    a = agg()
    assert "hour_sin" not in make_features(a, M).columns
    assert "hour_sin" in make_features(a, M, use_time=True).columns


def test_irregular_index_is_rejected():
    a = agg()
    a = a.drop(a.index[10])
    with pytest.raises(ValueError):
        make_features(a, M)


def test_context_minutes_covers_largest_window():
    assert context_minutes(M) == 30
    assert context_minutes({**M, "baseload_minutes": 180}) == 90


def test_no_target_in_features():
    X = make_features(agg(), M)
    assert not any("wm" in c for c in X.columns)
"""Features for one house, built from the aggregate only (never from the target).

All windows are CENTERED: a minute's features look at minutes before AND after it. That is fine for offline
analysis (what did the washing machine do during this period) but is not real-time. Features are computed
inside one house at a time, so no information crosses between houses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def context_minutes(model_cfg: dict) -> int:
    """How many minutes on each side of a minute the features can look. Used as the split embargo."""
    w = int(model_cfg.get("window_minutes", 30))
    r = max([int(x) for x in model_cfg.get("rolling_windows", [5, 15, 31, 61])]) // 2
    b = int(model_cfg.get("baseload_minutes", 60)) // 2
    return max(w, r, b)


def make_features(agg: pd.Series, model_cfg: dict, use_time: bool = False) -> pd.DataFrame:
    """agg: aggregate power on a regular 1-minute DatetimeIndex (NaN allowed). Returns a float32 frame."""
    steps = agg.index.to_series().diff().dropna()
    if len(steps) and not (steps == pd.Timedelta("1min")).all():
        raise ValueError("aggregate index must be a regular 1-minute grid")

    w = int(model_cfg.get("window_minutes", 30))
    offsets = [k for k in (-30, -20, -15, -10, -5, -3, -2, -1, 1, 2, 3, 5, 10, 15, 20, 30) if abs(k) <= w]
    rolls = [int(x) for x in model_cfg.get("rolling_windows", [5, 15, 31, 61])]
    base_win = int(model_cfg.get("baseload_minutes", 60))

    f = {"agg": agg}
    for k in offsets:
        f[f"agg_t{k:+d}"] = agg.shift(-k)                 # value k minutes later (k>0) or earlier (k<0)
    for r in rolls:
        roll = agg.rolling(r, center=True, min_periods=r // 2 + 1)
        f[f"roll{r}_mean"] = roll.mean()
        f[f"roll{r}_std"] = roll.std()
        f[f"roll{r}_min"] = roll.min()
        f[f"roll{r}_max"] = roll.max()
    base = agg.rolling(base_win, center=True, min_periods=base_win // 2).min()
    f["baseload"] = base
    f["agg_minus_baseload"] = agg - base
    f["diff1"] = agg - agg.shift(1)

    X = pd.DataFrame(f, index=agg.index)
    if use_time:
        hour = X.index.hour + X.index.minute / 60.0
        dow = X.index.day_of_week
        X["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        X["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        X["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        X["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    return X.astype("float32")
"""Detect 'stuck' aggregate readings: the same value repeated for a long time.

Why this exists: in raw House 1 Part2 the aggregate (and in two checked windows also the washing-machine
channel) repeats one value for hours, e.g. 12505 W for 2h48m on 2015-02-08. Real household load does not
stay identical for that long. The official CLEAN file contains the same artefact.

The thresholds (30 minutes, 20 readings) are OUR choice, picked from House 1: in Part1 no aggregate value
stayed identical for 30 minutes, in Part2 there are 18 such runs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _power_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c == "aggregate" or c.startswith("appliance")]


def find_stuck_runs(
    df: pd.DataFrame,
    col: str = "aggregate",
    time_col: str = "time",
    min_minutes: float = 30.0,
    min_readings: int = 20,
) -> pd.DataFrame:
    """Runs of an identical non-NaN value in `col` lasting >= min_minutes AND having >= min_readings readings.

    NaN rows are skipped when forming runs (partial rows of other channels do not break a run).
    Returns a table with value, start, end, n, minutes.
    """
    d = df[[time_col, col]].dropna(subset=[col])
    cols = ["value", "start", "end", "n", "minutes"]
    if d.empty:
        return pd.DataFrame(columns=cols)
    run_id = d[col].ne(d[col].shift()).cumsum()
    runs = d.groupby(run_id).agg(
        value=(col, "first"), start=(time_col, "first"), end=(time_col, "last"), n=(col, "size")
    )
    runs["minutes"] = (runs["end"] - runs["start"]).dt.total_seconds() / 60
    keep = (runs["minutes"] >= min_minutes) & (runs["n"] >= min_readings)
    return runs.loc[keep, cols].reset_index(drop=True)


def stuck_row_mask(df: pd.DataFrame, runs: pd.DataFrame, time_col: str = "time") -> np.ndarray:
    """Boolean mask over ALL rows of df whose time lies inside any stuck run (start <= time <= end).

    df must be sorted by time.
    """
    t = df[time_col].values  # datetime64[ns]; also correct for tz-aware columns (UTC)
    mask = np.zeros(len(df), dtype=bool)
    for start, end in zip(runs["start"].values, runs["end"].values):
        lo = np.searchsorted(t, start, side="left")
        hi = np.searchsorted(t, end, side="right")
        mask[lo:hi] = True
    return mask


def apply_stuck_aggregate(
    df: pd.DataFrame,
    min_minutes: float = 30.0,
    min_readings: int = 20,
    time_col: str = "time",
) -> tuple[pd.DataFrame, dict]:
    """Set ALL power channels to NaN inside stuck-aggregate windows. Returns (frame, log)."""
    if not df[time_col].is_monotonic_increasing:
        raise ValueError("df must be sorted by time before stuck-value detection")
    runs = find_stuck_runs(df, "aggregate", time_col, min_minutes, min_readings)
    mask = stuck_row_mask(df, runs, time_col)
    out = df.copy()
    out.loc[mask, _power_cols(out)] = np.nan
    log = {
        "rule": f"aggregate identical for >= {min_minutes} min and >= {min_readings} readings",
        "n_runs": int(len(runs)),
        "rows_set_to_nan": int(mask.sum()),
        "minutes_inside_runs": round(float(runs["minutes"].sum()), 1),
        "runs": [
            {"value": float(r.value), "start": str(r.start), "end": str(r.end), "n": int(r.n)}
            for r in runs.itertuples()
        ],
    }
    return out, log
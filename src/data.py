"""Load one official CLEAN REFIT house as a 1-minute frame with columns: aggregate, wm.

The loader reads only the columns it needs (memory friendly) and reuses the Section 1 tools
(`fill_short_gaps`, `apply_stuck_aggregate`) so Sections 1-3 treat gaps and stuck values the same way.
Nothing here decides the time zone: `time_zone=None` keeps the timestamps exactly as they are in the file.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.cleaning import fill_short_gaps, standardise_columns
from src.stuck import apply_stuck_aggregate


def clean_csv_path(cfg: dict, house: int) -> Path:
    return Path(cfg["paths"]["clean_dir"]) / f"CLEAN_House{house}.csv"


def minute_parquet_path(cfg: dict, house: int) -> Path:
    return Path(cfg["paths"]["minute_dir"]) / f"house{house}.parquet"


def load_clean_house(
    csv_path,
    wm_col: str,
    time_zone: str | None = None,
    stuck_min_minutes: float | None = 30,
    stuck_min_readings: int = 20,
    max_fill_minutes: int = 3,
) -> tuple[pd.DataFrame, dict]:
    """Return (frame indexed by 1-minute time, log).

    Steps: read needed columns, parse time, sort, drop duplicate timestamps (keep first),
    optional time-zone conversion to naive UTC, optional stuck-aggregate rule (all channels -> NaN),
    resample to 1 minute (mean), forward-fill gaps of at most `max_fill_minutes`.
    Minutes that are still NaN stay NaN (they are excluded later by the `valid` mask).
    """
    header = pd.read_csv(csv_path, nrows=0).columns
    std = list(standardise_columns(pd.DataFrame(columns=header)).columns)
    wanted = {"time", "aggregate", wm_col}
    missing = wanted - set(std)
    if missing:
        raise KeyError(f"{csv_path}: columns not found after standardising names: {sorted(missing)}. Found: {std}")
    usecols = [orig for orig, s in zip(header, std) if s in wanted]

    df = standardise_columns(pd.read_csv(csv_path, usecols=usecols))
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    log = {"rows_read": int(len(df)), "rows_bad_time": int(df["time"].isna().sum())}
    df = df.dropna(subset=["time"]).sort_values("time", kind="stable")
    n0 = len(df)
    df = df.drop_duplicates(subset="time", keep="first").reset_index(drop=True)
    log["duplicate_rows_removed"] = int(n0 - len(df))

    if time_zone:
        t = df["time"].dt.tz_localize(time_zone, ambiguous="NaT", nonexistent="NaT")
        ok = t.notna()
        log["rows_dropped_ambiguous_or_nonexistent"] = int((~ok).sum())
        df = df[ok].copy()
        df["time"] = t[ok].dt.tz_convert("UTC").dt.tz_localize(None)

    if stuck_min_minutes:
        df, log["stuck"] = apply_stuck_aggregate(
            df, min_minutes=stuck_min_minutes, min_readings=stuck_min_readings
        )

    grid = df.set_index("time")[["aggregate", wm_col]].resample("1min").mean()
    grid, filled = fill_short_gaps(grid, max_gap_steps=max_fill_minutes)
    log["filled_values"] = filled
    grid = grid.rename(columns={wm_col: "wm"}).astype("float32")
    log["minutes"] = int(len(grid))
    log["minutes_aggregate_nan"] = int(grid["aggregate"].isna().sum())
    log["minutes_wm_nan"] = int(grid["wm"].isna().sum())
    return grid, log
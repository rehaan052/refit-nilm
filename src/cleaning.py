"""Reusable cleaning functions for REFIT data (Section 1, reused in Sections 2-3)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.stuck import apply_stuck_aggregate


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def power_columns(df: pd.DataFrame) -> list[str]:
    """Columns that hold power in Watts: aggregate and appliance1..9."""
    return [c for c in df.columns if c == "aggregate" or c.startswith("appliance")]


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case, strip spaces; map the time and unix columns to 'time' and 'unix'."""
    out = df.copy()
    new_cols = []
    for c in out.columns:
        name = str(c).strip().lower().replace(" ", "")
        if name in ("datetime", "date_time", "time"):
            name = "time"
        elif name.startswith("unix"):
            name = "unix"
        new_cols.append(name)
    out.columns = new_cols
    return out


def parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the 'time' column. Unparseable values become NaT."""
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    return out


def nan_run_lengths(mask: pd.Series) -> pd.Series:
    """For a boolean mask (True = missing), return for each row the length of the True-run it belongs to.
    Rows where mask is False get 0."""
    mask = mask.astype(bool)
    group_id = mask.ne(mask.shift(fill_value=False)).cumsum()
    run_len = mask.groupby(group_id).transform("sum")
    return run_len.where(mask, 0).astype(int)


# ----------------------------------------------------------------------------
# Inspection (these only report, they do not change data)
# ----------------------------------------------------------------------------
def timestamp_report(df: pd.DataFrame, gap_thresholds_s=(30, 60, 120, 600, 3600)) -> dict:
    """Summarise timestamp quality of a frame with a parsed 'time' column."""
    t = df["time"]
    valid = t.dropna()
    unique_sorted = pd.Series(np.sort(valid.unique()))
    diffs = unique_sorted.diff().dt.total_seconds().dropna()

    report = {
        "n_rows": int(len(df)),
        "n_unparseable_timestamps": int(t.isna().sum()),
        "first_timestamp": valid.min(),
        "last_timestamp": valid.max(),
        "is_sorted_ascending": bool(valid.is_monotonic_increasing),
        "n_out_of_order_steps": int((valid.diff().dt.total_seconds() < 0).sum()),
        "n_duplicate_timestamps": int(valid.duplicated().sum()),
        "n_fully_duplicated_rows": int(df.duplicated().sum()),
        "step_seconds_quantiles": diffs.quantile([0.01, 0.25, 0.5, 0.75, 0.99]).round(1).to_dict(),
        "step_seconds_max": float(diffs.max()) if len(diffs) else float("nan"),
        "gap_counts": {f">{int(s)}s": int((diffs > s).sum()) for s in gap_thresholds_s},
    }
    return report


def time_vs_unix_offset_hours(df: pd.DataFrame) -> pd.Series:
    """Compare the 'time' column with the Unix timestamp (UTC).
    NOTE: in the REFIT raw and CLEAN files Unix was found to be derived from Time (difference 0 or 1 s),
    so this check does not reveal the time zone. Use DST row counts instead."""
    if "unix" not in df.columns:
        raise KeyError("No unix column in this file.")
    utc = pd.to_datetime(df["unix"], unit="s", errors="coerce")
    offset = (df["time"] - utc).dt.total_seconds() / 3600
    return offset.round(2).value_counts().sort_index()


def value_report(df: pd.DataFrame, aggregate_max: float, appliance_max: float) -> pd.DataFrame:
    """Per power column: missing, negative, above-limit and basic stats."""
    rows = []
    for col in power_columns(df):
        s = df[col]
        limit = aggregate_max if col == "aggregate" else appliance_max
        rows.append(
            {
                "column": col,
                "n_missing": int(s.isna().sum()),
                "pct_missing": round(100 * s.isna().mean(), 2),
                "n_negative": int((s < 0).sum()),
                "n_above_limit": int((s > limit).sum()),
                "limit_w": limit,
                "min": s.min(),
                "median": s.median(),
                "mean": s.mean(),
                "max": s.max(),
                "pct_zero": round(100 * (s == 0).mean(), 2),
            }
        )
    return pd.DataFrame(rows).set_index("column")


# ----------------------------------------------------------------------------
# Cleaning steps
# ----------------------------------------------------------------------------
def combine_parts_primary_first(df: pd.DataFrame, part_col: str = "part") -> tuple[pd.DataFrame, dict]:
    """Merge part files. Part 1 is primary: all its rows are kept. Rows of later parts are kept
    only if their time is AFTER the last Part 1 timestamp, so overlapping stretches (where Part 2's
    clock drifts by up to ~7 min in our check) and gaps inside Part 1 are NOT filled from Part 2.
    Our choice, based on a comparison with the official CLEAN file (reference only).
    If there is no part column (single-file houses) nothing changes."""
    if part_col not in df.columns:
        return df, {}
    first_id = df[part_col].min()
    first = df[df[part_col] == first_id]
    cutoff = first["time"].max()
    kept = [first]
    log = {
        "primary_part": int(first_id),
        "primary_last_time": cutoff,
        f"rows_part{int(first_id)}_kept": int(len(first)),
    }
    for p in sorted(df[part_col].unique()):
        if p == first_id:
            continue
        d = df[df[part_col] == p]
        k = d[d["time"] > cutoff]
        kept.append(k)
        log[f"rows_part{int(p)}_in"] = int(len(d))
        log[f"rows_part{int(p)}_kept"] = int(len(k))
        log[f"rows_part{int(p)}_dropped_overlap_or_bad_time"] = int(len(d) - len(k))
    out = pd.concat(kept, ignore_index=True).drop(columns=[part_col])
    return out, log


def local_to_utc(df: pd.DataFrame, tz: str = "Europe/London") -> tuple[pd.DataFrame, dict]:
    """Treat 'time' as local clock time in `tz`, convert to naive UTC.
    Repeated hour (clocks go back) is ambiguous and nonexistent hours cannot be placed:
    those rows are dropped and counted (our choice; the dropped hour then shows as a gap)."""
    out = df.copy()
    t = out["time"]
    t_utc = (
        t.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
    )
    dropped = t_utc.isna() & t.notna()
    log = {"assumed_time_zone": tz, "rows_dropped_ambiguous_or_nonexistent": int(dropped.sum())}
    out["time"] = t_utc
    out = out[~dropped].reset_index(drop=True)
    return out, log


def sort_and_dedup(df: pd.DataFrame, keep: str = "first") -> tuple[pd.DataFrame, dict]:
    """Drop unparseable timestamps, sort by time, and resolve duplicate timestamps.
    keep = 'first' | 'last' : keep that row
    keep = 'mean'           : average the power columns of rows sharing a timestamp"""
    if keep not in ("first", "last", "mean"):
        raise ValueError("keep must be 'first', 'last' or 'mean'")
    n_in = len(df)
    out = df.dropna(subset=["time"])
    n_bad_time = n_in - len(out)
    out = out.sort_values("time", kind="stable")

    n_before_dedup = len(out)
    if keep == "mean":
        cols = [c for c in out.columns if c != "time"]
        out = out.groupby("time", as_index=False)[cols].mean()
    else:
        out = out.drop_duplicates(subset="time", keep=keep)
    out = out.reset_index(drop=True)

    log = {
        "rows_in": n_in,
        "rows_dropped_bad_timestamp": n_bad_time,
        "duplicate_rows_removed": n_before_dedup - len(out),
        "dedup_rule": keep,
        "rows_out": len(out),
    }
    return out, log


def mask_impossible_values(
    df: pd.DataFrame, aggregate_max: float, appliance_max: float
) -> tuple[pd.DataFrame, dict]:
    """Set negative values and values above the sensor limit to NaN. Counts what was changed."""
    out = df.copy()
    log = {}
    for col in power_columns(out):
        limit = aggregate_max if col == "aggregate" else appliance_max
        bad_neg = out[col] < 0
        bad_high = out[col] > limit
        if bad_neg.any() or bad_high.any():
            log[col] = {"negative": int(bad_neg.sum()), "above_limit": int(bad_high.sum())}
        out.loc[bad_neg | bad_high, col] = np.nan
    return out, log


def resample_to_grid(df: pd.DataFrame, rule: str = "1min", agg: str = "mean") -> pd.DataFrame:
    """Resample to a regular time grid. Minutes with no reading become NaN.
    Adds n_raw_readings = number of non-missing aggregate readings in each minute."""
    d = df.set_index("time")[power_columns(df)]
    out = getattr(d.resample(rule), agg)()
    out["n_raw_readings"] = d["aggregate"].resample(rule).count().astype("int16")
    return out


def fill_short_gaps(
    df: pd.DataFrame, max_gap_steps: int, columns: list[str] | None = None
) -> tuple[pd.DataFrame, dict]:
    """Forward-fill gaps of at most `max_gap_steps` grid steps. Longer gaps stay NaN."""
    out = df.copy()
    columns = columns or power_columns(out)
    filled_counts = {}
    for col in columns:
        s = out[col]
        missing = s.isna()
        run_len = nan_run_lengths(missing)
        ff = s.ffill()
        fill_here = missing & (run_len <= max_gap_steps) & ff.notna()
        out.loc[fill_here, col] = ff[fill_here]
        filled_counts[col] = int(fill_here.sum())
    return out, filled_counts


def flag_aggregate_outages(df: pd.DataFrame, filled_mask: pd.Series | None = None) -> pd.DataFrame:
    """Add boolean flags:
    agg_filled : aggregate value came from short-gap filling
    agg_outage : aggregate still missing after filling (long outage, NOT filled)"""
    out = df.copy()
    out["agg_outage"] = out["aggregate"].isna()
    out["agg_filled"] = filled_mask.reindex(out.index).fillna(False) if filled_mask is not None else False
    return out


def outage_table(df: pd.DataFrame, flag_col: str = "agg_outage", step_minutes: float = 1.0) -> pd.DataFrame:
    """List each continuous outage with start, end and length in minutes."""
    mask = df[flag_col].astype(bool)
    group_id = mask.ne(mask.shift(fill_value=False)).cumsum()
    rows = []
    for _, g in df[mask].groupby(group_id[mask]):
        rows.append({"start": g.index[0], "end": g.index[-1], "minutes": len(g) * step_minutes})
    return pd.DataFrame(rows, columns=["start", "end", "minutes"])


# ----------------------------------------------------------------------------
# End-to-end wrapper
# ----------------------------------------------------------------------------
def run_cleaning_pipeline(df_raw: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Run all steps with settings from config['cleaning']. Returns (1-minute frame, log dict)."""
    c = cfg["cleaning"]
    log: dict = {}

    df = parse_timestamps(standardise_columns(df_raw))
    df, log["combine_parts"] = combine_parts_primary_first(df)
    tz = c.get("raw_time_zone")
    if tz:
        df, log["local_to_utc"] = local_to_utc(df, tz)
    df, log["sort_dedup"] = sort_and_dedup(df, keep=c["dedup_keep"])
    df, log["impossible_values_set_to_nan"] = mask_impossible_values(
        df, c["aggregate_max_w"], c["appliance_max_w"]
    )
    stuck_minutes = c.get("stuck_min_minutes")
    if stuck_minutes:
        df, log["stuck_aggregate"] = apply_stuck_aggregate(
            df, min_minutes=stuck_minutes, min_readings=c.get("stuck_min_readings", 20)
        )

    grid = resample_to_grid(df, rule=c["resample_rule"], agg=c["resample_agg"])
    agg_missing_before_fill = grid["aggregate"].isna()
    log["minutes_total"] = int(len(grid))
    log["minutes_aggregate_missing_before_fill"] = int(agg_missing_before_fill.sum())

    step_min = pd.tseries.frequencies.to_offset(c["resample_rule"]).nanos / 60e9
    max_steps = int(c["max_fill_minutes"] / step_min)
    filled, log["filled_values_per_column"] = fill_short_gaps(grid, max_gap_steps=max_steps)

    agg_filled = agg_missing_before_fill & filled["aggregate"].notna()
    out = flag_aggregate_outages(filled, filled_mask=agg_filled)
    log["minutes_aggregate_filled"] = int(out["agg_filled"].sum())
    log["minutes_aggregate_outage"] = int(out["agg_outage"].sum())
    log["n_outages"] = int(len(outage_table(out, step_minutes=step_min)))
    return out, log
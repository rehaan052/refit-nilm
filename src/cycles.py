"""Washing-machine episode detection on a regular 1-minute power series (same rule as the Section 2 EDA).

  1. A minute is ON when power > on_threshold_w; an observed minute at or below it is OFF.
  2. NaN minutes are UNAVAILABLE: they are neither ON nor OFF. They break an episode and are never merged across.
  3. A run of at most merge_gap_minutes OBSERVED OFF minutes that sits directly between two ON runs is merged.
  4. A merged episode shorter than min_minutes (its full span, including bridged OFF minutes) is dropped,
     and so is one with less energy than min_energy_wh.
These are 'estimated activation episodes', not ground-truth wash programmes.
Settings come from config.yaml (`model:`); the values chosen in the Section 2 EDA are 20 W / 5 min / 27 min.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def find_cycles(
    power,
    on_threshold_w: float,
    merge_gap_minutes: int = 5,
    min_minutes: int = 27,
    min_energy_wh: float = 0.0,
) -> pd.DataFrame:
    """One row per episode: start (position), end (position, exclusive), minutes, active_minutes, energy_wh, peak_w."""
    p = np.asarray(power, dtype="float64")
    valid = np.isfinite(p)
    on = valid & (p > on_threshold_w)
    edges = np.flatnonzero(np.diff(np.concatenate([[0], on.astype(int), [0]])))
    starts, ends = edges[0::2], edges[1::2]          # end is exclusive

    runs: list[list[int]] = []
    for s, e in zip(starts, ends):
        if runs:
            gap_start, gap_end = runs[-1][1], int(s)
            if (gap_end - gap_start) <= merge_gap_minutes and valid[gap_start:gap_end].all():
                runs[-1][1] = int(e)
                continue
        runs.append([int(s), int(e)])

    rows = []
    for s, e in runs:
        seg = p[s:e]
        energy = float(seg.sum() / 60.0)             # W * 1 min -> Wh, includes bridged OFF minutes
        active = int((seg > on_threshold_w).sum())
        if (e - s) >= min_minutes and energy >= min_energy_wh and active > 0:
            rows.append({"start": s, "end": e, "minutes": e - s, "active_minutes": active,
                         "energy_wh": energy, "peak_w": float(seg.max())})
    return pd.DataFrame(rows, columns=["start", "end", "minutes", "active_minutes", "energy_wh", "peak_w"])
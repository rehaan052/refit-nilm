"""Train / validation / test splitting designed to avoid leakage.

Two rules:
  1. House split: a test house never appears in training (leave-one-house-out).
  2. Time split inside a house: the later part is held out and an EMBARGO of `embargo` minutes is removed
     from the earlier part, because window features around a minute look at neighbouring minutes.
"""
from __future__ import annotations

import numpy as np


def leave_one_house_out(houses: list[int]) -> list[dict]:
    """One fold per house: that house is the test house, all others train."""
    return [{"test": h, "train": [x for x in houses if x != h]} for h in houses]


def assert_no_house_overlap(train_houses, test_houses) -> None:
    both = set(train_houses) & set(test_houses)
    if both:
        raise AssertionError(f"houses in both train and test: {sorted(both)}")


def chronological_masks(n_rows: int, last_fraction: float, embargo: int = 0):
    """Boolean masks over n_rows time-ordered rows (regular 1-minute grid, so rows = minutes).
    Returns (first_mask, last_mask): the last `last_fraction` of rows go to `last_mask`;
    `embargo` rows just before them are dropped from `first_mask`."""
    if not 0 < last_fraction < 1:
        raise ValueError("last_fraction must be between 0 and 1")
    cut = int(round(n_rows * (1 - last_fraction)))
    idx = np.arange(n_rows)
    last = idx >= cut
    first = idx < max(cut - embargo, 0)
    return first, last
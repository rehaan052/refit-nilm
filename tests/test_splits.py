import numpy as np
import pytest

from src.splits import assert_no_house_overlap, chronological_masks, leave_one_house_out


def test_loho_never_trains_on_test_house():
    folds = leave_one_house_out([1, 2, 5, 6])
    assert len(folds) == 4
    for f in folds:
        assert f["test"] not in f["train"]
        assert sorted(f["train"] + [f["test"]]) == [1, 2, 5, 6]
        assert_no_house_overlap(f["train"], [f["test"]])


def test_overlap_is_detected():
    with pytest.raises(AssertionError):
        assert_no_house_overlap([1, 2], [2])


def test_chronological_masks_order_and_embargo():
    first, last = chronological_masks(1000, last_fraction=0.3, embargo=60)
    assert last.sum() == 300
    assert not (first & last).any()
    assert np.flatnonzero(first).max() < np.flatnonzero(last).min() - 59   # embargo gap of 60 rows
    assert np.flatnonzero(first).max() == 639                              # cut=700, minus embargo 60 -> rows 0..639


def test_bad_fraction():
    with pytest.raises(ValueError):
        chronological_masks(100, 1.5)
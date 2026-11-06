import numpy as np

from src.cycles import find_cycles


def test_two_cycles_found():
    p = np.zeros(200)
    p[10:40] = 300
    p[100:130] = 500
    c = find_cycles(p, on_threshold_w=20, merge_gap_minutes=5, min_minutes=10)
    assert len(c) == 2
    assert list(c["start"]) == [10, 100] and list(c["end"]) == [40, 130]
    assert c["energy_wh"].iloc[0] == 30 * 300 / 60


def test_small_pause_is_merged_but_long_pause_splits():
    p = np.zeros(200)
    p[10:30] = 300
    p[34:60] = 300          # pause of 4 minutes: merged
    p[100:120] = 300
    p[130:150] = 300        # pause of 10 minutes: split
    c = find_cycles(p, on_threshold_w=20, merge_gap_minutes=5, min_minutes=10)
    assert len(c) == 3


def test_short_blip_is_dropped_and_nan_counts_as_off():
    p = np.zeros(100)
    p[10:13] = 2000
    p[50:70] = np.nan
    assert len(find_cycles(p, on_threshold_w=20, min_minutes=10)) == 0



def test_nan_gap_is_not_bridged_but_observed_off_gap_is():
    a = np.zeros(200)
    a[10:30] = 300
    a[33:60] = 300                      # observed OFF gap of 3 minutes: merged
    b = a.copy()
    b[30:33] = np.nan                   # same gap but unavailable: not merged
    ca = find_cycles(a, on_threshold_w=20, merge_gap_minutes=5, min_minutes=10)
    cb = find_cycles(b, on_threshold_w=20, merge_gap_minutes=5, min_minutes=10)
    assert len(ca) == 1 and ca["minutes"].iloc[0] == 50
    assert len(cb) == 2


def test_minimum_duration_uses_merged_span():
    p = np.zeros(100)
    p[10:20] = 300
    p[23:40] = 300                      # merged span 10..40 = 30 minutes
    assert len(find_cycles(p, on_threshold_w=20, merge_gap_minutes=5, min_minutes=27)) == 1
    assert len(find_cycles(p, on_threshold_w=20, merge_gap_minutes=5, min_minutes=31)) == 0
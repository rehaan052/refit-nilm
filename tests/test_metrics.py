import numpy as np
import pytest

from src.metrics import energy_error, evaluate, mae, mae_on, on_off_scores

CYC = dict(on_threshold_w=20, merge_gap_minutes=5, min_minutes=10, min_energy_wh=0)


def series():
    y = np.zeros(300)
    y[50:80] = 500.0          # one 30-minute cycle
    y[200:230] = 1000.0       # another one
    return y


def test_always_off_sanity():
    y = series()
    r = evaluate(y, np.zeros_like(y), 20, CYC)
    assert r["energy_error"] == pytest.approx(-1.0)     # -100 %: no energy found
    assert r["f1"] == 0.0
    assert r["cycle_recall"] == 0.0
    assert r["mae_w"] == pytest.approx(y.mean())


def test_perfect_prediction():
    y = series()
    r = evaluate(y, y.copy(), 20, CYC)
    assert r["mae_w"] == 0 and r["mae_on_w"] == 0
    assert r["energy_error"] == 0
    assert r["f1"] == 1.0
    assert r["cycle_recall"] == 1.0 and r["cycle_precision"] == 1.0
    assert r["cycle_energy_mae_wh"] == pytest.approx(0)


def test_known_small_example():
    y = np.array([0, 100, 100, 0.0])
    p = np.array([0, 100, 0, 100.0])
    assert mae(y, p) == pytest.approx(50.0)
    assert mae_on(y, p, 20) == pytest.approx(50.0)       # ON minutes: |100-100| and |0-100|
    assert energy_error(y, p) == pytest.approx(0.0)      # same total energy, wrong timing
    s = on_off_scores(y, p, 20)
    assert s["precision"] == pytest.approx(0.5) and s["recall"] == pytest.approx(0.5)


def test_nan_is_rejected():
    with pytest.raises(ValueError):
        mae(np.array([1.0, np.nan]), np.array([1.0, 1.0]))


def test_prediction_shifted_in_time_is_still_found_as_cycle():
    y = series()
    p = np.roll(y, 5)         # same cycles, 5 minutes late
    r = evaluate(y, p, 20, CYC)
    assert r["cycle_recall"] == 1.0
    assert r["energy_error"] == pytest.approx(0.0)
    assert r["mae_w"] > 0



def test_valid_mask_excludes_unavailable_minutes_from_point_metrics():
    y = series()
    p = np.zeros_like(y)
    y_bad = y.copy()
    y_bad[100:150] = np.nan             # unavailable label
    valid = np.isfinite(y_bad)
    p_full = np.where(np.isfinite(y_bad), p, 999.0)   # whatever is predicted there must not matter
    r = evaluate(y_bad, p_full, 20, CYC, valid=valid)
    assert r["n_minutes"] == int(valid.sum())
    assert r["energy_error"] == pytest.approx(-1.0)
    assert r["f1"] == 0.0


def test_cycle_metrics_do_not_bridge_across_unavailable_gap():
    y = np.zeros(300)
    y[50:70] = 500.0
    y[72:95] = 500.0                    # two ON runs, 2 observed OFF minutes between them: one cycle
    valid = np.ones(300, dtype=bool)
    r1 = evaluate(y, y.copy(), 20, CYC, valid=valid)
    assert r1["n_true_cycles"] == 1
    y2 = y.copy(); y2[70:72] = np.nan   # same gap, but unavailable: two cycles (each at least 10 minutes)
    valid2 = np.isfinite(y2)
    r2 = evaluate(y2, np.where(valid2, y, np.nan), 20, CYC, valid=valid2)
    assert r2["n_true_cycles"] == 2
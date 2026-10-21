import numpy as np
import pandas as pd

from tfvalidity.stats import benjamini_hochberg, deflated_sharpe_ratio, pbo_cscv


def test_dsr_decreases_with_more_trials_and_increases_with_sr():
    low = deflated_sharpe_ratio(0.05, 1000, 10, 0.03, 0.0, 3.0)
    high = deflated_sharpe_ratio(0.10, 1000, 10, 0.03, 0.0, 3.0)
    many = deflated_sharpe_ratio(0.05, 1000, 1000, 0.03, 0.0, 3.0)
    assert high > low
    assert many < low


def test_pbo_near_half_for_independent_noise():
    rng = np.random.default_rng(7)
    R = pd.DataFrame(rng.standard_normal((600, 40)) * 0.01)
    out = pbo_cscv(R, slices=6)
    assert 0.25 < out["pbo"] < 0.75
    assert out["n_combinations"] == 20


def test_bh_monotone_and_bounded():
    q = benjamini_hochberg([0.001, 0.02, 0.5, 0.9])
    assert np.all((q >= 0) & (q <= 1))
    assert np.all(np.diff(q[np.argsort([0.001, 0.02, 0.5, 0.9])]) >= 0)

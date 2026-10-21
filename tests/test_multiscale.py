import numpy as np
import pandas as pd

from tfvalidity.capacity import tbmt_select
from tfvalidity.multiscale import dfa_hurst, disagreement_probability


def test_disagreement_formula_endpoints():
    assert disagreement_probability(0.0) == 0.5
    assert abs(disagreement_probability(1.0) - 0.0) < 1e-9


def test_dfa_white_noise_near_half():
    rng = np.random.default_rng(11)
    x = rng.standard_normal(100_000)
    out = dfa_hurst(x)
    assert 0.42 < out["hurst"] < 0.58


def test_tbmt_respects_budget():
    table = pd.DataFrame(
        {
            "timeframe": ["5m", "1h", "4h", "1d"],
            "timeframe_minutes": [5, 60, 240, 1440],
            "sharpe_net": [1.0, 0.9, 0.8, 0.2],
        }
    )
    out = tbmt_select(table, 168)
    assert out["selected_timeframe"] == "1h"
    assert out["unconstrained_timeframe"] == "5m"
    out2 = tbmt_select(table, 21)
    assert out2["selected_timeframe"] == "1d"

import numpy as np
import pandas as pd
import pytest

from tfvalidity.data.resample import infer_base_minutes, pandas_offset, resample_ohlcv, rule_minutes
from tfvalidity.signals import HTF_LADDER, align_htf


def synthetic_1m(n: int = 180) -> pd.DataFrame:
    t = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    close = 100 + np.arange(n) * 0.01
    return pd.DataFrame(
        {
            "open_time": t,
            "open": close,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": np.ones(n),
            "close_time": t + pd.Timedelta(minutes=1) - pd.Timedelta(milliseconds=1),
        }
    )


def test_infer_base_minutes():
    assert infer_base_minutes(synthetic_1m()) == 1


@pytest.mark.parametrize("unit", ["ms", "us", "ns"])
def test_infer_base_minutes_is_unit_independent(unit):
    df = synthetic_1m(30)
    df["open_time"] = df["open_time"].dt.as_unit(unit)
    assert infer_base_minutes(df) == 1
    coarse = synthetic_1m(30).iloc[::5].copy()
    coarse["open_time"] = coarse["open_time"].dt.as_unit(unit)
    assert infer_base_minutes(coarse) == 5


def test_resample_ohlc_and_incomplete_bucket():
    df = synthetic_1m(150)
    out = resample_ohlcv(df, "1h", 1)
    assert len(out) == 2
    first = out.iloc[0]
    assert first["open"] == pytest.approx(df["open"].iloc[0])
    assert first["close"] == pytest.approx(df["close"].iloc[59])
    assert first["high"] == pytest.approx(df["high"].iloc[:60].max())
    assert first["low"] == pytest.approx(df["low"].iloc[:60].min())
    assert first["bars"] == 60
    assert out.iloc[1]["bars"] == 60


def test_htf_alignment_has_no_lookahead():
    base = synthetic_1m(120)
    htf = resample_ohlcv(base, "1h", 1)
    htf_sig = pd.Series([1.0, -1.0], index=htf.index)
    aligned = align_htf(base, htf, htf_sig)
    assert aligned.iloc[50] == 0.0
    assert aligned.iloc[59] == 1.0
    assert aligned.iloc[60] == 1.0
    assert aligned.iloc[119] == -1.0


def test_ladder_is_ordered_and_covers_grid():
    for tf, (h1, h2) in HTF_LADDER.items():
        assert rule_minutes(tf) < rule_minutes(h1) < rule_minutes(h2)


def test_pandas_offset_translates_minutes():
    assert pandas_offset("5m") == "5min"
    assert pandas_offset("1m") == "1min"
    assert pandas_offset("4h") == "4h"
    assert pandas_offset("1d") == "1D"
    assert pandas_offset("1w") == "1W"


def test_partial_calendar_week_needs_relaxed_min_bars():
    t = pd.bdate_range("2024-01-01", periods=5, tz="UTC")
    close = 100 + np.arange(5) * 0.1
    df = pd.DataFrame(
        {
            "open_time": t,
            "open": close,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "volume": np.ones(5),
            "close_time": t + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1),
        }
    )
    assert len(resample_ohlcv(df, "1w", 1440)) == 0
    out = resample_ohlcv(df, "1w", 1440, min_bars=3)
    assert len(out) == 1 and out.iloc[0]["bars"] == 5
    assert rule_minutes("2w") == 20160

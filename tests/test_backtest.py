import numpy as np
import pandas as pd

from tfvalidity.backtest import extract_trades, forward_open_returns, run_backtest


def frame(n=20):
    t = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = 100 * (1.001 ** np.arange(n))
    return pd.DataFrame(
        {
            "open_time": t,
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 1.0,
            "close_time": t + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1),
        }
    )


def test_forward_open_returns_shift_two():
    df = frame()
    fwd = forward_open_returns(df)
    assert fwd[0] == (df["open"].iloc[2] / df["open"].iloc[1] - 1)
    assert np.isnan(fwd[-1]) and np.isnan(fwd[-2])
    assert fwd[1] == (df["open"].iloc[3] / df["open"].iloc[2] - 1)


def test_constant_long_net_matches_gross_minus_costs():
    df = frame()
    pos = pd.Series(1.0, index=df.index)
    cost = 0.001
    res = run_backtest(df, pos, "1h", "ma", "base_only", {}, cost, 8760.0)
    assert res.turnover == 1.0
    assert res.bar_returns.sum() == (res.gross_bar_returns.sum() - cost)


def test_flip_turnover_not_double_counted():
    df = frame(8)
    pos = np.array([1.0, 1.0, -1.0, -1.0, 0.0, 0.0, 1.0, 1.0])
    trades = extract_trades(df, pos, 0.001)
    total = (trades["entry_turnover"] + trades["exit_turnover"]).sum()
    effective = np.abs(np.diff(np.r_[0.0, pos]))[:6]
    assert total == effective.sum() == 4
    assert len(trades) == 2
    assert abs(trades["net_return"] - (trades["gross_return"] - trades["cost"])).max() < 1e-12

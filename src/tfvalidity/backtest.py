from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    name: str
    timeframe: str
    strategy: str
    variant: str
    params: dict
    bar_returns: pd.Series
    gross_bar_returns: pd.Series
    daily_returns: pd.Series
    gross_daily_returns: pd.Series
    trades: pd.DataFrame
    position: pd.Series
    turnover: float
    bars_per_year: float
    meta: dict = field(default_factory=dict)

    @property
    def equity(self) -> pd.Series:
        return (1.0 + self.bar_returns.fillna(0.0)).cumprod()


def forward_open_returns(df: pd.DataFrame) -> np.ndarray:
    o = df["open"].to_numpy(dtype=float)
    fwd = np.full(len(o), np.nan)
    if len(o) > 2:
        fwd[:-2] = o[2:] / o[1:-1] - 1.0
    return fwd


def forward_close_returns(df: pd.DataFrame) -> np.ndarray:
    c = df["close"].to_numpy(dtype=float)
    fwd = np.full(len(c), np.nan)
    if len(c) > 2:
        fwd[:-2] = c[2:] / c[1:-1] - 1.0
    return fwd


def daily_aggregate(bar_returns: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    frame = pd.DataFrame({"r": bar_returns.to_numpy()}, index=index)
    frame = frame.dropna()
    daily = (1.0 + frame["r"]).groupby(frame.index.floor("D")).prod() - 1.0
    return daily


def extract_trades(df: pd.DataFrame, position: np.ndarray, cost_rate: float) -> pd.DataFrame:
    o = df["open"].to_numpy(dtype=float)
    ts = df["open_time"].to_numpy()
    p = np.asarray(position, dtype=float)
    n = len(p)
    trades: list[dict] = []
    i = 0
    while i < n:
        if p[i] == 0 or not np.isfinite(p[i]):
            i += 1
            continue
        direction = p[i]
        j = i + 1
        while j < n and p[j] == direction:
            j += 1
        entry_idx = min(i + 1, n - 1)
        exit_idx = min(j + 1, n - 1)
        if exit_idx <= entry_idx:
            i = j
            continue
        gross = direction * (o[exit_idx] / o[entry_idx] - 1.0)
        prev = p[i - 1] if i > 0 else 0.0
        nxt = p[j] if j < n else 0.0
        size = abs(direction)
        prev_size = abs(prev)
        next_size = abs(nxt)
        same_prev = np.sign(prev) == np.sign(direction)
        same_next = np.sign(nxt) == np.sign(direction)
        entry_turn = max(0.0, size - prev_size) if same_prev else size
        exit_turn = max(0.0, size - next_size) if same_next else size
        cost = (entry_turn + exit_turn) * cost_rate
        trades.append(
            {
                "entry_time": pd.Timestamp(ts[entry_idx]),
                "exit_time": pd.Timestamp(ts[exit_idx]),
                "direction": float(np.sign(direction)),
                "size": float(abs(direction)),
                "bars": int(exit_idx - entry_idx),
                "gross_return": float(gross),
                "net_return": float(gross - cost),
                "cost": float(cost),
                "entry_turnover": float(entry_turn),
                "exit_turnover": float(exit_turn),
            }
        )
        i = j
    return pd.DataFrame(trades)


def run_backtest(
    df: pd.DataFrame,
    position: pd.Series,
    timeframe: str,
    strategy: str,
    variant: str,
    params: dict,
    cost_rate: float,
    bars_per_year: float,
    execution: str = "next_open",
    vol_target: float | None = None,
    vol_lookback: int = 30,
    max_leverage: float = 3.0,
    name: str = "",
) -> BacktestResult:
    pos = position.reindex(df.index).fillna(0.0).to_numpy(dtype=float)
    if vol_target is not None:
        if execution == "next_open":
            ret = pd.Series(df["open"]).pct_change()
        else:
            ret = df["close"].pct_change()
        realized = ret.rolling(vol_lookback, min_periods=vol_lookback).std().shift(1)
        bars_per_day = bars_per_year / 365.0
        scale = (vol_target / (realized * np.sqrt(bars_per_day))).clip(0.0, max_leverage)
        pos = pos * scale.fillna(0.0).to_numpy()
    if execution == "next_open":
        fwd = forward_open_returns(df)
    elif execution == "next_close":
        fwd = forward_close_returns(df)
    else:
        raise KeyError(execution)
    turnover = np.abs(np.diff(np.r_[0.0, pos]))
    turnover = np.where(np.isfinite(fwd), turnover, 0.0)
    gross = pos * fwd
    net = gross - turnover * cost_rate
    bar_returns = pd.Series(net, index=df["open_time"])
    gross_bar_returns = pd.Series(gross, index=df["open_time"])
    daily = daily_aggregate(bar_returns, pd.DatetimeIndex(df["open_time"]))
    gross_daily = daily_aggregate(gross_bar_returns, pd.DatetimeIndex(df["open_time"]))
    trades = extract_trades(df, pos, cost_rate)
    return BacktestResult(
        name=name or f"{strategy}:{variant}:{timeframe}",
        timeframe=timeframe,
        strategy=strategy,
        variant=variant,
        params=params,
        bar_returns=bar_returns,
        gross_bar_returns=gross_bar_returns,
        daily_returns=daily,
        gross_daily_returns=gross_daily,
        trades=trades,
        position=pd.Series(pos, index=df["open_time"]),
        turnover=float(np.nansum(turnover)),
        bars_per_year=bars_per_year,
        meta={
            "gross_expectancy_per_bar": float(np.nanmean(gross)),
            "net_expectancy_per_bar": float(np.nanmean(net)),
            "n_bars": int(len(df)),
            "cost_rate": float(cost_rate),
            "execution": execution,
        },
    )

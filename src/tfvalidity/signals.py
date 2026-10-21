from __future__ import annotations

import numpy as np
import pandas as pd

HTF_LADDER = {
    "1m": ("5m", "15m"),
    "5m": ("15m", "1h"),
    "15m": ("1h", "4h"),
    "30m": ("2h", "8h"),
    "1h": ("4h", "1d"),
    "4h": ("1d", "1w"),
    "1d": ("2d", "4d"),
}


def ma_crossover(close: pd.Series, fast: int, slow: int) -> pd.Series:
    if fast >= slow:
        raise ValueError("fast must be smaller than slow")
    f = close.rolling(fast, min_periods=fast).mean()
    s = close.rolling(slow, min_periods=slow).mean()
    sig = np.sign(f - s)
    return pd.Series(sig, index=close.index, dtype=float).fillna(0.0)


def donchian(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int) -> pd.Series:
    upper = high.shift(1).rolling(lookback, min_periods=lookback).max()
    lower = low.shift(1).rolling(lookback, min_periods=lookback).min()
    raw = np.where(close > upper, 1.0, np.where(close < lower, -1.0, np.nan))
    return pd.Series(raw, index=close.index).ffill().fillna(0.0)


def tsmom(close: pd.Series, lookback: int) -> pd.Series:
    past = close / close.shift(lookback) - 1.0
    return pd.Series(np.sign(past), index=close.index, dtype=float).fillna(0.0)


def build_signal(df: pd.DataFrame, strategy: str, params: dict) -> pd.Series:
    close = df["close"]
    if strategy == "ma":
        return ma_crossover(close, int(params["fast"]), int(params["slow"]))
    if strategy == "donchian":
        return donchian(df["high"], df["low"], close, int(params["lookback"]))
    if strategy == "tsmom":
        return tsmom(close, int(params["lookback"]))
    raise KeyError(strategy)


def _epoch_ns(values) -> np.ndarray:
    return pd.to_datetime(pd.Series(values), utc=True).dt.as_unit("ns").astype("int64").to_numpy()


def align_htf(base: pd.DataFrame, htf: pd.DataFrame, htf_signal: pd.Series) -> pd.Series:
    right = pd.DataFrame(
        {
            "htf_close_time": _epoch_ns(htf["close_time"]),
            "htf_signal": htf_signal.to_numpy(),
        }
    ).sort_values("htf_close_time")
    left = pd.DataFrame(
        {
            "base_close_time": _epoch_ns(base["close_time"]),
            "base_pos": np.arange(len(base)),
        }
    ).sort_values("base_close_time")
    merged = pd.merge_asof(
        left,
        right,
        left_on="base_close_time",
        right_on="htf_close_time",
        direction="backward",
    )
    merged = merged.sort_values("base_pos")
    return pd.Series(merged["htf_signal"].fillna(0.0).to_numpy(), index=base.index, dtype=float)


def apply_variant(base_signal: pd.Series, htf_signal: pd.Series, htf2_signal: pd.Series, variant: str) -> pd.Series:
    b = base_signal.to_numpy(dtype=float)
    h = htf_signal.to_numpy(dtype=float)
    h2 = htf2_signal.to_numpy(dtype=float)
    if variant == "base_only":
        return pd.Series(b, index=base_signal.index)
    if variant == "htf_filter":
        return pd.Series(np.where(b == h, b, 0.0), index=base_signal.index)
    if variant == "htf_trigger":
        run_id = pd.Series((np.diff(np.r_[0.0, h]) != 0).cumsum(), index=base_signal.index)
        agree = pd.Series((b == h) & (h != 0), index=base_signal.index).astype(float)
        seen = agree.groupby(run_id).cummax()
        return pd.Series(h * seen.to_numpy(), index=base_signal.index)
    if variant == "confluence3":
        return pd.Series((b + h + h2) / 3.0, index=base_signal.index)
    raise KeyError(variant)


def parameter_grid(strategy: str, grid: dict) -> list[dict]:
    if strategy == "ma":
        out = []
        for fast in grid["fast"]:
            for slow in grid["slow"]:
                if fast < slow:
                    out.append({"fast": int(fast), "slow": int(slow)})
        return out
    if strategy in ("donchian", "tsmom"):
        return [{"lookback": int(n)} for n in grid["lookback"]]
    raise KeyError(strategy)

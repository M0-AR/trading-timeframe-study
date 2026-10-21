from __future__ import annotations

import numpy as np
import pandas as pd

AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
    "quote_volume": "sum",
    "trades": "sum",
    "taker_buy_base": "sum",
    "taker_buy_quote": "sum",
}

RULE_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "8h": 480,
    "6h": 360,
    "12h": 720,
    "1d": 1440,
    "2d": 2880,
    "4d": 5760,
    "1w": 10080,
    "2w": 20160,
}


def pandas_offset(rule: str) -> str:
    if rule.endswith("min"):
        return rule
    if rule.endswith("m"):
        return rule[:-1] + "min"
    if rule.endswith("d"):
        return rule[:-1] + "D"
    if rule.endswith("w"):
        return rule[:-1] + "W"
    return rule


def rule_minutes(rule: str) -> int:
    if rule in RULE_MINUTES:
        return RULE_MINUTES[rule]
    raise KeyError(f"unknown rule {rule}")


def resample_ohlcv(
    df: pd.DataFrame,
    rule: str,
    base_minutes: int | None = None,
    min_bars: int | None = None,
) -> pd.DataFrame:
    if base_minutes is None:
        base_minutes = infer_base_minutes(df)
    target = rule_minutes(rule)
    if target % base_minutes != 0:
        raise ValueError(f"{rule} is not a multiple of base interval {base_minutes}m")
    expected = target // base_minutes
    if min_bars is None:
        min_bars = expected
    idx = df.set_index("open_time").sort_index()
    agg = {k: v for k, v in AGG.items() if k in idx.columns}
    offset = pandas_offset(rule)
    out = idx.resample(offset, label="left", closed="left").agg(agg)
    counts = idx["close"].resample(offset, label="left", closed="left").count()
    out = out.loc[counts >= max(1, int(min_bars))].copy()
    out["bars"] = counts.loc[out.index].astype(int)
    out["close_time"] = out.index + pd.Timedelta(minutes=target) - pd.Timedelta(milliseconds=1)
    return out.reset_index()


def infer_base_minutes(df: pd.DataFrame) -> int:
    diffs = df["open_time"].sort_values().diff().dt.total_seconds().dropna()
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return 1
    return int(round(float(diffs.median()) / 60.0)) or 1


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close).diff()


def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    return resample_ohlcv(df, "1w", infer_base_minutes(df))

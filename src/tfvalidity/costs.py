from __future__ import annotations

import numpy as np
import pandas as pd


def corwin_schultz_spread(high: pd.Series, low: pd.Series) -> pd.Series:
    h = high.to_numpy(dtype=float)
    lo = low.to_numpy(dtype=float)
    n = len(h)
    out = np.full(n, np.nan)
    if n < 2:
        return pd.Series(out, index=high.index)
    beta = np.log(h / lo) ** 2
    gamma = np.log(np.maximum(h[:-1], h[1:]) / np.minimum(lo[:-1], lo[1:])) ** 2
    beta_pair = beta[:-1] + beta[1:]
    alpha = (np.sqrt(2.0 * beta_pair) - np.sqrt(beta_pair)) / (3.0 - 2.0 * np.sqrt(2.0)) - np.sqrt(
        np.clip(gamma / (3.0 - 2.0 * np.sqrt(2.0)), 0.0, None)
    )
    spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    out[1:] = np.clip(spread, 0.0, 0.2)
    return pd.Series(out, index=high.index)


def corwin_schultz_summary(df: pd.DataFrame) -> dict:
    s = corwin_schultz_spread(df["high"], df["low"]).dropna()
    if s.empty:
        return {"median_bps": float("nan"), "mean_bps": float("nan"), "n": 0}
    return {
        "median_bps": float(s.median() * 1e4),
        "mean_bps": float(s.mean() * 1e4),
        "p90_bps": float(s.quantile(0.9) * 1e4),
        "n": int(len(s)),
    }


def sqrt_impact_cost(participation: float, sigma_daily: float, k: float = 0.10) -> float:
    return float(k * sigma_daily * np.sqrt(max(participation, 0.0)))


def capacity_notional(adv_quote: float, edge: float, sigma_daily: float, k: float = 0.10) -> float:
    if sigma_daily <= 0 or edge <= 0:
        return 0.0
    participation = (edge / (k * sigma_daily)) ** 2
    return float(min(participation, 1.0) * adv_quote)


def break_even_cost(gross_returns: np.ndarray, turnovers: np.ndarray) -> float:
    g = np.asarray(gross_returns, dtype=float)
    t = np.asarray(turnovers, dtype=float)
    if t.sum() <= 0:
        return float("nan")
    return float(g.sum() / t.sum())

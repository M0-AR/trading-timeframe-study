from __future__ import annotations

import numpy as np
import pandas as pd


def optimal_horizon_days(edge_per_unit_vol: float, sigma_daily: float, cost: float) -> float:
    if edge_per_unit_vol <= 0 or sigma_daily <= 0:
        return float("inf")
    return float((2.0 * cost / (edge_per_unit_vol * sigma_daily)) ** 2)


def horizon_curve(edge_per_unit_vol: float, sigma_daily: float, cost: float, horizons: np.ndarray) -> pd.DataFrame:
    h = np.asarray(horizons, dtype=float)
    gross = edge_per_unit_vol * sigma_daily * np.sqrt(h)
    net = gross - cost
    per_year = 365.0 / h
    ann = per_year * net
    return pd.DataFrame({"horizon_days": h, "gross_edge": gross, "net_edge": net, "trades_per_year": per_year, "ann_net": ann})


def estimate_edge_per_unit_vol(trades: pd.DataFrame, sigma_daily: float, timeframe_days: float) -> float:
    if trades.empty or sigma_daily <= 0 or timeframe_days <= 0:
        return float("nan")
    gross = trades["gross_return"].to_numpy(dtype=float)
    return float(np.mean(gross) / (sigma_daily * np.sqrt(timeframe_days)))


def capacity_table(results: pd.DataFrame, adv_quote: float, sigma_daily: float, k: float = 0.10) -> pd.DataFrame:
    out = results.copy()
    out["edge_per_trade"] = out["avg_trade_return"]
    out["capacity_usd"] = [
        (edge / (k * sigma_daily)) ** 2 * adv_quote if edge > 0 and sigma_daily > 0 else 0.0
        for edge in out["edge_per_trade"]
    ]
    out["capacity_usd"] = out["capacity_usd"].clip(upper=adv_quote)
    return out


def tbmt_select(table: pd.DataFrame, decisions_per_week: float, horizon_col: str = "timeframe_minutes") -> dict:
    if table.empty:
        return {"selected": None, "reason": "empty"}
    t = table.copy()
    t["decisions_per_week"] = 7.0 * 24.0 * 60.0 / t[horizon_col]
    feasible = t[t["decisions_per_week"] <= decisions_per_week]
    if feasible.empty:
        feasible = t.nsmallest(1, "decisions_per_week")
    best_feasible = feasible.loc[feasible["sharpe_net"].idxmax()]
    best_overall = t.loc[t["sharpe_net"].idxmax()]
    return {
        "budget_per_week": float(decisions_per_week),
        "selected_timeframe": str(best_feasible["timeframe"]),
        "selected_sharpe_net": float(best_feasible["sharpe_net"]),
        "unconstrained_timeframe": str(best_overall["timeframe"]),
        "unconstrained_sharpe_net": float(best_overall["sharpe_net"]),
        "regret": float(best_overall["sharpe_net"] - best_feasible["sharpe_net"]),
        "n_feasible": int(len(feasible)),
    }

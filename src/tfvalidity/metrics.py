from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import BacktestResult


def ann_sharpe(returns: pd.Series | np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return float("nan")
    sd = x.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(x.mean() / sd * np.sqrt(periods_per_year))


def ann_sortino(returns: pd.Series | np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return float("nan")
    downside = x[x < 0]
    if downside.size == 0:
        return float("nan")
    dd = np.sqrt(np.mean(downside**2))
    return float(x.mean() / dd * np.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    x = np.asarray(returns, dtype=float)
    x = np.where(np.isfinite(x), x, 0.0)
    equity = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(equity)
    return float(np.min(equity / peak - 1.0)) if equity.size else float("nan")


def calmar(returns: pd.Series | np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    ann = (1.0 + x).prod() ** (periods_per_year / len(x)) - 1.0
    mdd = max_drawdown(x)
    return float(ann / abs(mdd)) if mdd < 0 else float("nan")


def ann_return(returns: pd.Series | np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    return float((1.0 + x).prod() ** (periods_per_year / len(x)) - 1.0)


def ann_vol(returns: pd.Series | np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return float("nan")
    return float(x.std(ddof=1) * np.sqrt(periods_per_year))


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "n_trades": 0,
            "win_rate": float("nan"),
            "avg_win": float("nan"),
            "avg_loss": float("nan"),
            "payoff": float("nan"),
            "profit_factor": float("nan"),
            "expectancy": float("nan"),
            "avg_bars": float("nan"),
            "net_sum": float("nan"),
            "gross_sum": float("nan"),
            "turnover_per_trade": float("nan"),
            "break_even_cost": float("nan"),
            "avg_trade_return": float("nan"),
        }
    net = trades["net_return"].to_numpy(dtype=float)
    gross = trades["gross_return"].to_numpy(dtype=float)
    turnover = (trades["entry_turnover"] + trades["exit_turnover"]).to_numpy(dtype=float)
    wins = net[net > 0]
    losses = net[net < 0]
    gross_wins = gross[gross > 0].sum()
    gross_losses = -gross[gross < 0].sum()
    return {
        "n_trades": int(len(trades)),
        "win_rate": float((net > 0).mean()),
        "avg_win": float(wins.mean()) if wins.size else 0.0,
        "avg_loss": float(losses.mean()) if losses.size else 0.0,
        "payoff": float(wins.mean() / abs(losses.mean())) if wins.size and losses.size else float("nan"),
        "profit_factor": float(gross_wins / gross_losses) if gross_losses > 0 else float("inf"),
        "expectancy": float(net.mean()),
        "avg_bars": float(trades["bars"].mean()),
        "net_sum": float(net.sum()),
        "gross_sum": float(gross.sum()),
        "turnover_per_trade": float(turnover.mean()),
        "break_even_cost": float(gross.sum() / turnover.sum()) if turnover.sum() > 0 else float("nan"),
        "avg_trade_return": float(gross.mean()),
    }


def summarize(result: BacktestResult, periods_per_year: float = 365.0) -> dict:
    dr = result.daily_returns
    ts = trade_stats(result.trades)
    exposure = float((result.position != 0).mean())
    years = max(len(dr) / periods_per_year, 1e-9)
    return {
        "name": result.name,
        "timeframe": result.timeframe,
        "strategy": result.strategy,
        "variant": result.variant,
        "params": result.params,
        "n_bars": result.meta.get("n_bars", 0),
        "n_days": int(dr.size),
        "n_trades": ts["n_trades"],
        "trades_per_year": ts["n_trades"] / years,
        "win_rate": ts["win_rate"],
        "payoff": ts["payoff"],
        "profit_factor": ts["profit_factor"],
        "expectancy": ts["expectancy"],
        "avg_trade_return": ts["avg_trade_return"],
        "break_even_cost": ts["break_even_cost"],
        "turnover_per_trade": ts["turnover_per_trade"],
        "turnover_per_year": result.turnover / years,
        "exposure": exposure,
        "ann_return_net": ann_return(dr, periods_per_year),
        "ann_vol_net": ann_vol(dr, periods_per_year),
        "sharpe_net": ann_sharpe(dr, periods_per_year),
        "sortino_net": ann_sortino(dr, periods_per_year),
        "max_drawdown": max_drawdown(dr),
        "calmar": calmar(dr, periods_per_year),
        "sharpe_gross": ann_sharpe(result.gross_daily_returns, periods_per_year),
        "ann_return_gross": ann_return(result.gross_daily_returns, periods_per_year),
        "cost_drag_ann": ann_return(result.gross_daily_returns, periods_per_year) - ann_return(dr, periods_per_year),
        "t_stat_net": float(dr.mean() / dr.std(ddof=1) * np.sqrt(len(dr))) if len(dr) > 2 and dr.std(ddof=1) > 0 else float("nan"),
        "start": str(dr.index.min().date()) if len(dr) else "",
        "end": str(dr.index.max().date()) if len(dr) else "",
    }

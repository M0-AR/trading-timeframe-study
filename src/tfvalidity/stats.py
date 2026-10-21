from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def period_metrics(x: pd.Series, periods_per_year: float = 365.0) -> dict:
    x = pd.Series(x).dropna()
    n = int(len(x))
    if n < 2 or x.std(ddof=1) == 0:
        return {
            "n_days": n,
            "ann_return": float("nan"),
            "ann_vol": float("nan"),
            "sharpe": float("nan"),
            "max_drawdown": float("nan"),
        }
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    eq = (1.0 + x).cumprod()
    return {
        "n_days": n,
        "ann_return": float(eq.iloc[-1] ** (periods_per_year / n) - 1.0) if eq.iloc[-1] > 0 else float("nan"),
        "ann_vol": float(sd * np.sqrt(periods_per_year)),
        "sharpe": float(mean / sd * np.sqrt(periods_per_year)),
        "max_drawdown": float((eq / eq.cummax() - 1.0).min()),
    }


def _col_sr(block: np.ndarray) -> np.ndarray:
    mean = block.mean(axis=0)
    var = block.var(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sr = mean / np.sqrt(var)
    return np.nan_to_num(sr, nan=-np.inf, posinf=np.inf, neginf=-np.inf)


def _col_sr_from_sums(total: np.ndarray, total_sq: np.ndarray, n: int) -> np.ndarray:
    mean = total / n
    var = (total_sq - n * mean**2) / (n - 1)
    var = np.clip(var, 0.0, None)
    with np.errstate(divide="ignore", invalid="ignore"):
        sr = mean / np.sqrt(var)
    return np.nan_to_num(sr, nan=-np.inf, posinf=np.inf, neginf=-np.inf)


def pbo_cscv(returns: pd.DataFrame, slices: int = 12) -> dict:
    R = returns.to_numpy(dtype=float)
    mask = np.isfinite(R).all(axis=1)
    R = R[mask]
    T, N = R.shape
    if T < slices * 10:
        raise ValueError(f"not enough observations for CSCV: T={T}")
    usable = (T // slices) * slices
    R = R[:usable]
    parts = np.array_split(R, slices, axis=0)
    part_sum = np.vstack([p.sum(axis=0) for p in parts])
    part_sq = np.vstack([(p**2).sum(axis=0) for p in parts])
    part_n = np.array([len(p) for p in parts], dtype=float)
    half = slices // 2
    combos = list(combinations(range(slices), half))
    logits = np.empty(len(combos))
    is_sr_list = np.empty(len(combos))
    oos_sr_list = np.empty(len(combos))
    for k, combo in enumerate(combos):
        inside = np.zeros(slices, dtype=bool)
        inside[list(combo)] = True
        tr_sum = part_sum[inside].sum(axis=0)
        tr_sq = part_sq[inside].sum(axis=0)
        tr_n = part_n[inside].sum()
        te_sum = part_sum[~inside].sum(axis=0)
        te_sq = part_sq[~inside].sum(axis=0)
        te_n = part_n[~inside].sum()
        sr_tr = _col_sr_from_sums(tr_sum, tr_sq, int(tr_n))
        sr_te = _col_sr_from_sums(te_sum, te_sq, int(te_n))
        best = int(np.argmax(sr_tr))
        rank = stats.rankdata(sr_te, method="average")[best]
        omega = rank / (N + 1.0)
        omega = min(max(omega, 1e-9), 1.0 - 1e-9)
        logits[k] = np.log(omega / (1.0 - omega))
        is_sr_list[k] = sr_tr[best]
        oos_sr_list[k] = sr_te[best]
    slope = np.polyfit(is_sr_list, oos_sr_list, 1)[0] if len(is_sr_list) > 2 else np.nan
    return {
        "pbo": float((logits < 0).mean()),
        "n_combinations": int(len(combos)),
        "n_trials": int(N),
        "n_observations": int(usable),
        "slices": int(slices),
        "logit_mean": float(np.mean(logits)),
        "logit_std": float(np.std(logits, ddof=1)),
        "degradation_slope": float(slope),
        "prob_oos_loss": float((oos_sr_list < 0).mean()),
        "oos_sr_median": float(np.median(oos_sr_list)),
        "logits": logits,
    }


def deflated_sharpe_ratio(
    sr: float,
    n_obs: int,
    n_trials: int,
    sr_std: float,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    if n_trials < 2 or not np.isfinite(sr_std) or sr_std <= 0:
        return float("nan")
    gamma = 0.5772156649015329
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    sr0 = sr_std * ((1.0 - gamma) * z1 + gamma * z2)
    denom = np.sqrt(max(1e-12, 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr**2))
    return float(stats.norm.cdf((sr - sr0) * np.sqrt(max(n_obs - 1, 1)) / denom))


def probabilistic_sharpe_ratio(sr: float, n_obs: int, skew: float = 0.0, kurtosis: float = 3.0, sr_star: float = 0.0) -> float:
    denom = np.sqrt(max(1e-12, 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr**2))
    return float(stats.norm.cdf((sr - sr_star) * np.sqrt(max(n_obs - 1, 1)) / denom))


def stationary_bootstrap_indices(n: int, block: float, rng: np.random.Generator) -> np.ndarray:
    idx = np.empty(n, dtype=np.int64)
    i = 0
    p = 1.0 / max(block, 1.0)
    while i < n:
        start = int(rng.integers(0, n))
        length = int(rng.geometric(p))
        for k in range(length):
            if i >= n:
                break
            idx[i] = (start + k) % n
            i += 1
    return idx


def block_bootstrap_ci(
    x: np.ndarray,
    stat_fn,
    reps: int = 500,
    block: float = 20.0,
    seed: int = 20261021,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    rng = np.random.default_rng(seed)
    point = float(stat_fn(x))
    draws = np.empty(reps)
    for b in range(reps):
        idx = stationary_bootstrap_indices(len(x), block, rng)
        draws[b] = stat_fn(x[idx])
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)


def white_reality_check(returns: pd.DataFrame, reps: int = 500, block: float = 20.0, seed: int = 20261021) -> dict:
    R = returns.to_numpy(dtype=float)
    R = R[np.isfinite(R).all(axis=1)]
    T, N = R.shape
    means = R.mean(axis=0)
    v = np.sqrt(T) * means.max()
    rng = np.random.default_rng(seed)
    centered = R - means
    boot = np.empty(reps)
    for b in range(reps):
        idx = stationary_bootstrap_indices(T, block, rng)
        boot[b] = np.sqrt(T) * centered[idx].mean(axis=0).max()
    p = float((1.0 + np.sum(boot >= v)) / (reps + 1.0))
    return {"stat": float(v), "p_value": p, "best_index": int(np.argmax(means)), "n_trials": int(N), "n_obs": int(T)}


def spa_test(returns: pd.DataFrame, reps: int = 500, block: float = 20.0, seed: int = 20261021) -> dict:
    R = returns.to_numpy(dtype=float)
    R = R[np.isfinite(R).all(axis=1)]
    T, N = R.shape
    means = R.mean(axis=0)
    sds = R.std(axis=0, ddof=1)
    sds = np.where(sds > 0, sds, np.inf)
    tstats = np.sqrt(T) * means / sds
    v = max(0.0, float(np.max(tstats)))
    centered = R - means
    rng = np.random.default_rng(seed)
    boot = np.empty(reps)
    for b in range(reps):
        idx = stationary_bootstrap_indices(T, block, rng)
        tb = np.sqrt(T) * centered[idx].mean(axis=0) / sds
        boot[b] = max(0.0, float(np.max(tb)))
    p = float((1.0 + np.sum(boot >= v)) / (reps + 1.0))
    return {
        "stat": v,
        "p_value": p,
        "best_index": int(np.argmax(tstats)),
        "n_trials": int(N),
        "n_obs": int(T),
        "n_positive": int((tstats > 0).sum()),
    }


def benjamini_hochberg(pvals: np.ndarray | list[float]) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(q, 0.0, 1.0)
    return out


def newey_west_tstat(x: np.ndarray, lags: int | None = None) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"mean": float("nan"), "t_stat": float("nan"), "lags": 0, "se": float("nan")}
    if lags is None:
        lags = int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    mu = x.mean()
    e = x - mu
    gamma0 = np.dot(e, e) / n
    var = gamma0
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        cov = np.dot(e[k:], e[:-k]) / n
        var += 2.0 * w * cov
    se = np.sqrt(max(var, 1e-18) / n)
    return {"mean": float(mu), "t_stat": float(mu / se), "lags": int(lags), "se": float(se)}


def hac_regression(y: np.ndarray, X: np.ndarray, lags: int | None = None) -> dict:
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    if lags is None:
        lags = int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    resid = y - X @ beta
    omega = np.zeros((k, k))
    for t in range(n):
        omega += np.outer(X[t], X[t]) * resid[t] ** 2
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1.0)
        gamma = np.zeros((k, k))
        for t in range(lag, n):
            gamma += np.outer(X[t], X[t - lag]) * resid[t] * resid[t - lag]
        omega += w * (gamma + gamma.T)
    cov = xtx_inv @ omega @ xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    return {"beta": beta, "se": se, "t": beta / np.where(se > 0, se, np.inf), "lags": int(lags), "n": int(n)}

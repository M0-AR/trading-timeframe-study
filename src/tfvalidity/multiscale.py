from __future__ import annotations

import numpy as np
import pandas as pd

from .data.resample import infer_base_minutes, resample_ohlcv, rule_minutes


def scale_table(df: pd.DataFrame, timeframes: list[str]) -> pd.DataFrame:
    base = infer_base_minutes(df)
    rows = []
    for tf in timeframes:
        r = resample_ohlcv(df, tf, base)
        lr = np.log(r["close"]).diff().dropna()
        minutes = rule_minutes(tf)
        rows.append(
            {
                "timeframe": tf,
                "minutes": minutes,
                "n_bars": int(len(lr)),
                "sigma_bar": float(lr.std(ddof=1)),
                "mean_bar": float(lr.mean()),
                "sigma_annual": float(lr.std(ddof=1) * np.sqrt(365 * 24 * 60 / minutes)),
            }
        )
    out = pd.DataFrame(rows)
    out["log_minutes"] = np.log(out["minutes"])
    out["log_sigma_bar"] = np.log(out["sigma_bar"])
    out["log_sigma_annual"] = np.log(out["sigma_annual"])
    return out


def scaling_exponent(table: pd.DataFrame, y_col: str = "log_sigma_bar") -> dict:
    x = table["log_minutes"].to_numpy()
    y = table[y_col].to_numpy()
    X = np.column_stack([np.ones_like(x), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    n = len(y)
    lag = 1
    xtx_inv = np.linalg.inv(X.T @ X)
    scores = X * resid[:, None]
    omega = scores.T @ scores
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        gamma = scores[k:].T @ scores[:-k]
        omega += w * (gamma + gamma.T)
    cov = xtx_inv @ omega @ xtx_inv
    se = float(np.sqrt(max(cov[1, 1], 0.0)))
    return {
        "slope": float(beta[1]),
        "intercept": float(beta[0]),
        "se": se,
        "t_stat": float(beta[1] / se) if se > 0 else float("nan"),
        "r2": float(1 - np.sum(resid**2) / np.sum((y - y.mean()) ** 2)),
        "n": int(n),
    }


def dfa_hurst(x: np.ndarray, scales: list[int] | None = None) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if scales is None:
        scales = [8, 16, 32, 64, 128, 256, 512, 1024]
    profile = np.cumsum(x - x.mean())
    valid_scales = []
    fluct = []
    for s in scales:
        n_seg = len(profile) // s
        if n_seg < 4:
            continue
        seg = profile[: n_seg * s].reshape(n_seg, s)
        t = np.arange(s, dtype=float)
        tc = t - t.mean()
        denom = float(tc @ tc)
        slope = seg @ tc / denom
        intercept = seg.mean(axis=1)
        fit = intercept[:, None] + slope[:, None] * tc[None, :]
        rms = np.sqrt(np.mean((seg - fit) ** 2, axis=1))
        fluct.append(float(np.mean(rms)))
        valid_scales.append(s)
    if len(valid_scales) < 3:
        return {"hurst": float("nan"), "scales": valid_scales, "fluct": fluct}
    slope = np.polyfit(np.log(valid_scales), np.log(fluct), 1)[0]
    return {
        "hurst": float(slope),
        "scales": valid_scales,
        "fluct": [float(v) for v in fluct],
        "log_scales": [float(np.log(v)) for v in valid_scales],
        "log_fluct": [float(np.log(v)) for v in fluct],
    }


def sign_disagreement(close: pd.Series, h1: int, h2: int) -> dict:
    c = close.to_numpy(dtype=float)
    r1 = np.full(len(c), np.nan)
    r2 = np.full(len(c), np.nan)
    r1[h1:] = c[h1:] / c[:-h1] - 1.0
    r2[h2:] = c[h2:] / c[:-h2] - 1.0
    s1 = np.sign(r1)
    s2 = np.sign(r2)
    mask = np.isfinite(s1) & np.isfinite(s2) & (s1 != 0) & (s2 != 0)
    if mask.sum() < 10:
        return {"n": int(mask.sum()), "disagreement": float("nan"), "rho_theory": float("nan")}
    return {
        "n": int(mask.sum()),
        "disagreement": float((s1[mask] != s2[mask]).mean()),
        "rho_theory": float(np.sqrt(h1 / h2)),
        "disagreement_theory": float(0.5 - np.arcsin(np.sqrt(h1 / h2)) / np.pi),
    }


def disagreement_probability(rho: float) -> float:
    return float(0.5 - np.arcsin(rho) / np.pi)


def simulate_disagreement(n: int, rho: float, seed: int = 1, reps: int = 200) -> dict:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(reps):
        z1 = rng.standard_normal(n)
        z2 = rho * z1 + np.sqrt(max(1 - rho**2, 0)) * rng.standard_normal(n)
        vals.append(float((np.sign(z1) != np.sign(z2)).mean()))
    return {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1)), "theory": disagreement_probability(rho)}


def conditional_forward_returns(close: pd.Series, fast: int, slow: int, horizon: int) -> dict:
    c = close.to_numpy(dtype=float)
    r_fast = np.full(len(c), np.nan)
    r_slow = np.full(len(c), np.nan)
    fwd = np.full(len(c), np.nan)
    r_fast[fast:] = c[fast:] / c[:-fast] - 1.0
    r_slow[slow:] = c[slow:] / c[:-slow] - 1.0
    fwd[:-horizon] = c[horizon:] / c[:-horizon] - 1.0
    sf = np.sign(r_fast)
    ss = np.sign(r_slow)
    mask = np.isfinite(sf) & np.isfinite(ss) & np.isfinite(fwd) & (sf != 0) & (ss != 0)
    agree = mask & (sf == ss)
    disagree = mask & (sf != ss)
    return {
        "n": int(mask.sum()),
        "disagreement": float(disagree.sum() / mask.sum()),
        "fwd_mean_agree": float(fwd[agree].mean()),
        "fwd_mean_disagree": float(fwd[disagree].mean()),
        "fwd_mean_fast_long": float(fwd[mask & (sf > 0)].mean()),
        "fwd_mean_slow_long": float(fwd[mask & (ss > 0)].mean()),
        "fwd_mean_fast_short": float(fwd[mask & (sf < 0)].mean()),
        "fwd_mean_slow_short": float(fwd[mask & (ss < 0)].mean()),
    }


def _codes(values: np.ndarray, bins: int) -> np.ndarray:
    edges = np.quantile(values, np.linspace(0, 1, bins + 1)[1:-1])
    return np.digitize(values, edges).astype(np.int64)


def _mi_from_codes(bx: np.ndarray, by: np.ndarray, bins: int) -> float:
    joint = np.bincount(bx * bins + by, minlength=bins * bins).reshape(bins, bins)
    pxy = joint / joint.sum()
    px = pxy.sum(axis=1, keepdims=True)
    py = pxy.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        contrib = pxy * np.log(pxy / (px * py))
    return float(np.nansum(contrib))


def mutual_information(x: np.ndarray, y: np.ndarray, bins: int = 8) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < bins * 10:
        return float("nan")
    return _mi_from_codes(_codes(x, bins), _codes(y, bins), bins)


def surrogate_mi_pvalue(x: np.ndarray, y: np.ndarray, reps: int = 200, bins: int = 8, seed: int = 20261021) -> dict:
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(y)
    if n < bins * 10:
        return {"mi": float("nan"), "p_value": float("nan"), "null_mean": float("nan"), "null_sd": float("nan"), "n": int(n), "reps": int(reps)}
    bx = _codes(x, bins)
    by = _codes(y, bins)
    observed = _mi_from_codes(bx, by, bins)
    null = np.empty(reps)
    for b in range(reps):
        shift = int(rng.integers(1, max(2, n)))
        null[b] = _mi_from_codes(bx, np.roll(by, shift), bins)
    p = float((1.0 + np.sum(null >= observed)) / (reps + 1.0))
    return {
        "mi": observed,
        "p_value": p,
        "null_mean": float(np.nanmean(null)),
        "null_sd": float(np.nanstd(null, ddof=1)),
        "n": int(n),
        "reps": int(reps),
    }

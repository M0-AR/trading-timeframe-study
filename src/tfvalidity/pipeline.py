from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .capacity import (
    capacity_table,
    estimate_edge_per_unit_vol,
    optimal_horizon_days,
    tbmt_select,
)
from .config import RESULTS_DIR, StudyConfig
from .costs import corwin_schultz_summary
from .data.binance import build_symbol, dependency_versions, gap_audit
from .data.equities import fetch_daily, fetch_hourly, fred_csv
from .data.resample import resample_ohlcv, rule_minutes
from .metrics import summarize
from .multiscale import (
    conditional_forward_returns,
    dfa_hurst,
    scale_table,
    scaling_exponent,
    sign_disagreement,
    simulate_disagreement,
    surrogate_mi_pvalue,
)
from .signals import HTF_LADDER, align_htf, apply_variant, build_signal, parameter_grid
from .stats import (
    benjamini_hochberg,
    block_bootstrap_ci,
    deflated_sharpe_ratio,
    newey_west_tstat,
    pbo_cscv,
    period_metrics,
    spa_test,
    white_reality_check,
)
from .utils import read_json, seed_everything, write_json

EXTRA_FRAMES = ["2h", "8h", "2d", "4d", "1w"]


def _log(msg: str) -> None:
    print(msg, flush=True)


def stage_fetch(cfg: StudyConfig, force: bool = False) -> dict:
    b = cfg.raw["data"]["binance"]
    manifests = {}
    for symbol in cfg.crypto_symbols:
        _log(f"[fetch] binance {symbol} {b['interval']} {b['start']}..{b['end']}")
        _, man = build_symbol(symbol, b["interval"], b["start"], b["end"], cfg.cache_dir, force=force)
        manifests[f"{symbol}:{b['interval']}"] = man
    fine_symbol = b["finest_symbol"]
    _log(f"[fetch] binance {fine_symbol} {b['finest_interval']}")
    _, man = build_symbol(fine_symbol, b["finest_interval"], b["start"], b["end"], cfg.cache_dir, force=force)
    manifests[f"{fine_symbol}:{b['finest_interval']}"] = man
    for symbol in cfg.equity_symbols:
        _log(f"[fetch] eodhd {symbol} daily")
        df = fetch_daily(symbol, cfg.cache_dir, cfg.raw["data"]["equities"]["start"], force=force)
        manifests[f"{symbol}:daily"] = {"rows": len(df), "start": str(df["open_time"].min()), "end": str(df["open_time"].max())}
        try:
            h = fetch_hourly(symbol, cfg.cache_dir, force=force)
            manifests[f"{symbol}:1h"] = {"rows": len(h), "start": str(h["open_time"].min()), "end": str(h["open_time"].max())}
        except Exception as exc:
            _log(f"[fetch] hourly unavailable for {symbol}: {exc}")
            manifests[f"{symbol}:1h"] = {"error": str(exc)}
    macro = cfg.raw["data"]["macro"]
    try:
        rf = fred_csv(macro["risk_free_series"], cfg.cache_dir, force=force)
        manifests["FRED:" + macro["risk_free_series"]] = {
            "rows": len(rf),
            "start": str(rf["open_time"].min()),
            "end": str(rf["open_time"].max()),
        }
    except Exception as exc:
        _log(f"[fetch] FRED unavailable: {exc}")
        manifests["FRED:" + macro["risk_free_series"]] = {"error": str(exc)}
    payload = {"versions": dependency_versions(), "manifests": manifests}
    write_json(RESULTS_DIR / "data_manifest.json", payload)
    return payload


def _load_5m(cfg: StudyConfig, symbol: str) -> pd.DataFrame:
    b = cfg.raw["data"]["binance"]
    df = pd.read_parquet(cfg.cache_dir / "binance" / b["interval"] / f"{symbol}.parquet")
    return df.sort_values("open_time").reset_index(drop=True)


def _build_frames(df: pd.DataFrame, base_minutes: int, timeframes: list[str]) -> dict[str, pd.DataFrame]:
    frames = {}
    for tf in timeframes:
        frames[tf] = df if rule_minutes(tf) == base_minutes else resample_ohlcv(df, tf, base_minutes)
    for tf in EXTRA_FRAMES:
        if tf not in frames:
            frames[tf] = resample_ohlcv(df, tf, base_minutes)
    return frames


def stage_audit(cfg: StudyConfig) -> dict:
    out = {"crypto": {}, "equities": {}}
    for symbol in cfg.crypto_symbols:
        df = _load_5m(cfg, symbol)
        out["crypto"][symbol] = gap_audit(df, 5)
        out["crypto"][symbol]["median_quote_volume_daily"] = float(
            df.set_index("open_time")["quote_volume"].resample("1D").sum().median()
        )
    fine = cfg.raw["data"]["binance"]["finest_symbol"]
    try:
        df1 = pd.read_parquet(cfg.cache_dir / "binance" / "1m" / f"{fine}.parquet")
        out["crypto"][fine + ":1m"] = gap_audit(df1, 1)
    except FileNotFoundError:
        out["crypto"][fine + ":1m"] = {"error": "1m cache not fetched"}
    for symbol in cfg.equity_symbols:
        try:
            df = fetch_daily(symbol, cfg.cache_dir)
            out["equities"][symbol] = gap_audit(df.rename(columns={}), 1440, business_days=True)
            out["equities"][symbol]["corwin_schultz"] = corwin_schultz_summary(df)
            out["equities"][symbol]["start"] = str(df["open_time"].min().date())
            out["equities"][symbol]["end"] = str(df["open_time"].max().date())
        except Exception as exc:
            out["equities"][symbol] = {"error": str(exc)}
    write_json(RESULTS_DIR / "data_audit.json", out)
    return out


def stage_multiscale(cfg: StudyConfig) -> dict:
    tfs = cfg.timeframes
    out: dict = {"scaling": {}, "hurst": {}, "disagreement": {}, "theory": {}, "conditional": {}}
    for symbol in cfg.crypto_symbols:
        df = _load_5m(cfg, symbol)
        table = scale_table(df, tfs)
        table.to_csv(RESULTS_DIR / f"scaling_{symbol}.csv", index=False)
        out["scaling"][symbol] = {
            "per_bar": scaling_exponent(table, "log_sigma_bar"),
            "annualized": scaling_exponent(table, "log_sigma_annual"),
            "table": table.to_dict(orient="records"),
        }
        lr = np.log(df["close"]).diff().dropna().to_numpy()
        out["hurst"][symbol] = dfa_hurst(lr)
        close = df["close"]
        pairs = []
        for h1, h2, label in [
            (1, 12, "5m_vs_1h"),
            (12, 48, "1h_vs_4h"),
            (12, 288, "1h_vs_1d"),
            (48, 288, "4h_vs_1d"),
        ]:
            d = sign_disagreement(close, h1, h2)
            d.update({"pair": label, "h1_bars": h1, "h2_bars": h2})
            pairs.append(d)
        out["disagreement"][symbol] = pairs
        out["conditional"][symbol] = conditional_forward_returns(close, 12, 288, 288)
    rng = np.random.default_rng(cfg.seed)
    sims = []
    for rho in [0.0, 0.25, 0.5, 0.7071, 0.866, 0.95]:
        res = simulate_disagreement(20000, rho, seed=int(rng.integers(1 << 30)), reps=50)
        res["rho"] = rho
        sims.append(res)
    out["theory"]["monte_carlo"] = sims
    out["theory"]["formula"] = "P(sign(X) != sign(Y)) = 1/2 - arcsin(rho)/pi"
    write_json(RESULTS_DIR / "multiscale.json", out)
    return out


def _trial_id(symbol: str, tf: str, strategy: str, variant: str, params: dict) -> str:
    p = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    return f"{symbol}|{tf}|{strategy}|{variant}|{p}"


def run_trial(
    frames: dict[str, pd.DataFrame],
    symbol: str,
    tf: str,
    strategy: str,
    params: dict,
    variant: str,
    cost_bps: float,
    execution: str = "next_open",
) -> object:
    base = frames[tf]
    base_sig = build_signal(base, strategy, params)
    if variant == "base_only":
        htf_al = pd.Series(0.0, index=base.index)
        htf2_al = pd.Series(0.0, index=base.index)
    else:
        htf_name, htf2_name = HTF_LADDER[tf]
        htf_sig = build_signal(frames[htf_name], strategy, params)
        htf2_sig = build_signal(frames[htf2_name], strategy, params)
        htf_al = align_htf(base, frames[htf_name], htf_sig)
        htf2_al = align_htf(base, frames[htf2_name], htf2_sig)
    pos = apply_variant(base_sig, htf_al, htf2_al, variant)
    minutes = rule_minutes(tf)
    bars_per_year = 365.0 * 24.0 * 60.0 / minutes
    return run_backtest(
        base,
        pos,
        timeframe=tf,
        strategy=strategy,
        variant=variant,
        params=params,
        cost_rate=cost_bps / 1e4,
        bars_per_year=bars_per_year,
        execution=execution,
        name=_trial_id(symbol, tf, strategy, variant, params),
    )


def stage_backtest(cfg: StudyConfig) -> dict:
    seed_everything(cfg.seed)
    strategies = cfg.raw["strategies"]
    variants = cfg.raw["variants"]
    cost_bps = float(cfg.raw["costs"]["crypto_bps"])
    sens = [float(x) for x in cfg.raw["costs"]["sensitivity_bps"]]
    all_rows: list[dict] = []
    daily_series: dict[str, pd.Series] = {}
    cost_rows: list[dict] = []
    for symbol in cfg.crypto_symbols:
        _log(f"[backtest] {symbol}")
        df = _load_5m(cfg, symbol)
        frames = _build_frames(df, 5, cfg.timeframes)
        local: list[dict] = []
        for tf in cfg.timeframes:
            for strategy in ("ma", "donchian", "tsmom"):
                for params in parameter_grid(strategy, strategies[strategy]):
                    for variant in variants:
                        try:
                            res = run_trial(frames, symbol, tf, strategy, params, variant, cost_bps)
                        except Exception as exc:
                            _log(f"[backtest] skip {symbol} {tf} {strategy} {params} {variant}: {exc}")
                            continue
                        row = summarize(res, periods_per_year=365.0)
                        row.update(
                            {
                                "symbol": symbol,
                                "params_json": json.dumps(params, sort_keys=True),
                                "trial_id": res.name,
                                "cost_bps": cost_bps,
                                "start": str(res.daily_returns.index.min().date()),
                                "end": str(res.daily_returns.index.max().date()),
                            }
                        )
                        local.append(row)
                        all_rows.append(row)
                        daily_series[res.name] = res.daily_returns
            _log(f"[backtest] {symbol} {tf} done ({len(local)} trials)")
        top = pd.DataFrame(local).sort_values("sharpe_net", ascending=False).head(6)
        for _, row in top.iterrows():
            params = json.loads(row["params_json"])
            for cb in sens:
                res = run_trial(frames, symbol, row["timeframe"], row["strategy"], params, row["variant"], cb)
                s = summarize(res, periods_per_year=365.0)
                s.update({"symbol": symbol, "params_json": row["params_json"], "cost_bps": cb})
                cost_rows.append(s)
        del frames
    trials = pd.DataFrame(all_rows)
    trials.to_parquet(RESULTS_DIR / "trials.parquet", index=False)
    daily = pd.concat(daily_series, axis=1).sort_index()
    daily = daily.loc[:, ~daily.columns.duplicated()]
    daily.to_parquet(RESULTS_DIR / "daily_returns.parquet")
    pd.DataFrame(cost_rows).to_csv(RESULTS_DIR / "cost_sensitivity.csv", index=False)
    _log(f"[backtest] {len(trials)} trials, {daily.shape[0]} days x {daily.shape[1]} series")
    return {"n_trials": int(len(trials)), "n_days": int(daily.shape[0])}


def stage_finest(cfg: StudyConfig) -> dict:
    symbol = cfg.raw["data"]["binance"]["finest_symbol"]
    df = pd.read_parquet(cfg.cache_dir / "binance" / "1m" / f"{symbol}.parquet")
    tfs = ["1m", "5m", "15m", "1h", "4h", "1d"]
    frames = _build_frames(df, 1, tfs)
    cost_bps = float(cfg.raw["costs"]["crypto_bps"])
    rows = []
    for tf in tfs:
        for strategy, params in (("ma", {"fast": 20, "slow": 100}), ("tsmom", {"lookback": 50}), ("donchian", {"lookback": 50})):
            for variant in ("base_only", "htf_filter"):
                res = run_trial(frames, symbol, tf, strategy, params, variant, cost_bps)
                s = summarize(res, periods_per_year=365.0)
                s.update({"symbol": symbol, "trial_id": res.name})
                rows.append(s)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS_DIR / "finest_scale.csv", index=False)
    return {"rows": int(len(out))}


def stage_stats(cfg: StudyConfig) -> dict:
    trials = pd.read_parquet(RESULTS_DIR / "trials.parquet")
    daily = pd.read_parquet(RESULTS_DIR / "daily_returns.parquet")
    is_end = pd.Timestamp(cfg.raw.get("sample", {}).get("is_end", "2024-12-31"), tz="UTC")
    oos_start = pd.Timestamp(cfg.raw.get("sample", {}).get("oos_start", "2025-01-01"), tz="UTC")
    is_daily = daily.loc[daily.index <= is_end]
    oos_daily = daily.loc[daily.index >= oos_start]
    keep = (is_daily.notna().sum() > 20) & (is_daily.std(ddof=1) > 0)
    cols = list(is_daily.columns[keep])
    is_daily = is_daily.loc[:, cols]
    oos_daily = oos_daily.loc[:, cols]
    n_trials = len(cols)
    sr_is_all = is_daily.mean() / is_daily.std(ddof=1)
    sr_std = float(sr_is_all.std(ddof=1))
    rows = []
    for col in cols:
        xi = is_daily[col].dropna()
        xo = oos_daily[col].dropna()
        mi = period_metrics(xi)
        mo = period_metrics(xo)
        sr_daily = float(xi.mean() / xi.std(ddof=1))
        skew = float(xi.skew())
        kurt = float(xi.kurtosis() + 3.0)
        dsr = deflated_sharpe_ratio(sr_daily, len(xi), n_trials, sr_std, skew, kurt)
        rows.append(
            {
                "trial_id": col,
                "is_sr_daily": sr_daily,
                "is_dsr": dsr,
                "is_skew": skew,
                "is_kurtosis": kurt,
                "is_sharpe_net": mi["sharpe"],
                "is_ann_return_net": mi["ann_return"],
                "is_ann_vol_net": mi["ann_vol"],
                "is_max_drawdown": mi["max_drawdown"],
                "is_n_days": mi["n_days"],
                "oos_sharpe_net": mo["sharpe"],
                "oos_ann_return_net": mo["ann_return"],
                "oos_ann_vol_net": mo["ann_vol"],
                "oos_max_drawdown": mo["max_drawdown"],
                "oos_n_days": mo["n_days"],
            }
        )
    stats_df = pd.DataFrame(rows)
    merged = trials.merge(stats_df, on="trial_id", how="left")
    merged.to_csv(RESULTS_DIR / "trials_with_dsr.csv", index=False)
    pbo = pbo_cscv(is_daily, slices=int(cfg.raw["stats"]["cscv_slices"]))
    logits = pbo.pop("logits")
    np.save(RESULTS_DIR / "pbo_logits.npy", logits)
    rc = white_reality_check(is_daily, reps=int(cfg.raw["stats"]["bootstrap_reps"]), block=float(cfg.raw["stats"]["block_days"]), seed=cfg.seed)
    spa = spa_test(is_daily, reps=int(cfg.raw["stats"]["bootstrap_reps"]), block=float(cfg.raw["stats"]["block_days"]), seed=cfg.seed)
    top = merged.sort_values("is_sharpe_net", ascending=False).head(10)
    cis = []
    for _, row in top.iterrows():
        x = oos_daily[row["trial_id"]].dropna().to_numpy()
        if len(x) < 30:
            continue
        point, lo, hi = block_bootstrap_ci(x, lambda a: float(a.mean() / a.std(ddof=1) * np.sqrt(365.0)), reps=500, block=20.0, seed=cfg.seed)
        cis.append(
            {
                "trial_id": row["trial_id"],
                "is_sharpe_net": float(row["is_sharpe_net"]),
                "oos_sharpe_net": float(row["oos_sharpe_net"]),
                "oos_ci_lo": lo,
                "oos_ci_hi": hi,
            }
        )
    cis_df = pd.DataFrame(cis)
    cis_df.to_csv(RESULTS_DIR / "top_bootstrap_ci.csv", index=False)
    pvals = []
    oos_pvals = []
    from scipy import stats as st

    for col in cols:
        xi = is_daily[col].dropna().to_numpy()
        xo = oos_daily[col].dropna().to_numpy()
        nw = newey_west_tstat(xi, lags=10)
        p = 2 * (1 - st.norm.cdf(abs(nw["t_stat"]))) if np.isfinite(nw["t_stat"]) else 1.0
        nw_oos = newey_west_tstat(xo, lags=10) if len(xo) > 30 else {"t_stat": float("nan")}
        p_oos = 2 * (1 - st.norm.cdf(abs(nw_oos["t_stat"]))) if np.isfinite(nw_oos["t_stat"]) else 1.0
        pvals.append({"trial_id": col, "t_stat_nw": nw["t_stat"], "p_value": p})
        oos_pvals.append({"trial_id": col, "t_stat_nw_oos": nw_oos["t_stat"], "p_value_oos": p_oos})
    pv = pd.DataFrame(pvals)
    pv["q_value"] = benjamini_hochberg(pv["p_value"].to_numpy())
    pv_oos = pd.DataFrame(oos_pvals)
    pv_oos["q_value_oos"] = benjamini_hochberg(pv_oos["p_value_oos"].to_numpy())
    pv = pv.merge(pv_oos, on="trial_id", how="left")
    pv.to_csv(RESULTS_DIR / "trial_pvalues.csv", index=False)
    fam = merged.groupby(["symbol", "timeframe"]).agg(
        best_net_sharpe=("is_sharpe_net", "max"),
        median_net_sharpe=("is_sharpe_net", "median"),
        best_gross_sharpe=("sharpe_gross", "max"),
        n=("is_sharpe_net", "size"),
    ).reset_index()
    best_idx = merged.groupby(["symbol", "timeframe"])["is_sharpe_net"].idxmax()
    best_rows = merged.loc[best_idx, ["symbol", "timeframe", "oos_sharpe_net", "oos_ann_return_net"]].rename(
        columns={"oos_sharpe_net": "best_oos_sharpe", "oos_ann_return_net": "best_oos_ann_return"}
    )
    fam = fam.merge(best_rows, on=["symbol", "timeframe"], how="left")
    fam.to_csv(RESULTS_DIR / "timeframe_family.csv", index=False)
    key = ["symbol", "timeframe", "strategy", "params_json"]
    base = merged[merged["variant"] == "base_only"].set_index(key)
    effects = {}
    for variant in ("htf_filter", "htf_trigger", "confluence3"):
        alt = merged[merged["variant"] == variant].set_index(key)
        diff = (alt["is_sharpe_net"] - base["is_sharpe_net"]).dropna()
        oos_diff = (alt["oos_sharpe_net"] - base["oos_sharpe_net"]).dropna()
        gross = (alt["sharpe_gross"] - base["sharpe_gross"]).dropna()
        vol_ratio = (alt["is_ann_vol_net"] / base["is_ann_vol_net"]).replace([np.inf, -np.inf], np.nan).dropna()
        turn_ratio = (alt["turnover_per_year"] / base["turnover_per_year"]).replace([np.inf, -np.inf], np.nan).dropna()
        tstat = float(st.ttest_1samp(diff, 0.0).statistic) if len(diff) > 2 and diff.std(ddof=1) > 0 else float("nan")
        effects[variant] = {
            "n_pairs": int(len(diff)),
            "mean_net_sharpe_diff": float(diff.mean()),
            "median_net_sharpe_diff": float(diff.median()),
            "frac_positive": float((diff > 0).mean()),
            "t_stat": tstat,
            "mean_gross_sharpe_diff": float(gross.mean()),
            "median_vol_ratio": float(vol_ratio.median()),
            "median_turnover_ratio": float(turn_ratio.median()),
            "oos_mean_net_sharpe_diff": float(oos_diff.mean()),
            "oos_median_net_sharpe_diff": float(oos_diff.median()),
            "oos_frac_positive": float((oos_diff > 0).mean()),
        }
    tf_effect = merged.groupby("timeframe").agg(
        n=("is_sharpe_net", "size"),
        mean_is_sharpe=("is_sharpe_net", "mean"),
        median_is_sharpe=("is_sharpe_net", "median"),
        median_gross_sharpe=("sharpe_gross", "median"),
        median_cost_drag_ann=("cost_drag_ann", "median"),
        median_turnover=("turnover_per_year", "median"),
    ).reset_index()
    tf_effect["_order"] = tf_effect["timeframe"].map({t: i for i, t in enumerate(["5m", "15m", "30m", "1h", "4h", "1d"])})
    tf_effect = tf_effect.sort_values("_order").drop(columns="_order")
    best = merged.sort_values("is_sharpe_net", ascending=False).head(1).to_dict(orient="records")[0]
    finite = merged.dropna(subset=["is_sharpe_net", "oos_sharpe_net"])
    rho = float(st.spearmanr(finite["is_sharpe_net"], finite["oos_sharpe_net"]).statistic) if len(finite) > 2 else float("nan")
    pos = finite[finite["is_sharpe_net"] > 0]
    rho_pos = float(st.spearmanr(pos["is_sharpe_net"], pos["oos_sharpe_net"]).statistic) if len(pos) > 2 else float("nan")
    decile = merged.sort_values("is_sharpe_net", ascending=False).head(max(1, int(np.ceil(0.1 * len(merged)))))
    top_oos_mean = float(decile["oos_sharpe_net"].mean())
    top_oos_pos = float((decile["oos_sharpe_net"] > 0).mean())
    sig = merged.merge(pv[["trial_id", "q_value", "q_value_oos"]], on="trial_id", how="left")
    n_fdr_pos = int(((sig["q_value"] < 0.05) & (sig["is_sharpe_net"] > 0)).sum())
    n_fdr_neg = int(((sig["q_value"] < 0.05) & (sig["is_sharpe_net"] < 0)).sum())
    n_fdr_oos_pos = int(((sig["q_value_oos"] < 0.05) & (sig["oos_sharpe_net"] > 0)).sum())
    n_fdr_oos_neg = int(((sig["q_value_oos"] < 0.05) & (sig["oos_sharpe_net"] < 0)).sum())
    top_oos_desc = merged.sort_values("oos_sharpe_net", ascending=False).head(10)[
        ["trial_id", "is_sharpe_net", "oos_sharpe_net", "oos_ann_return_net", "n_trades"]
    ].to_dict(orient="records")
    out = {
        "n_trials": int(n_trials),
        "n_days_is": int(len(is_daily)),
        "n_days_oos": int(len(oos_daily)),
        "is_end": str(is_end.date()),
        "oos_start": str(oos_start.date()),
        "sr_across_trials_mean_daily_is": float(sr_is_all.mean()),
        "sr_across_trials_std_daily_is": sr_std,
        "pbo": pbo,
        "reality_check": rc,
        "spa": spa,
        "dsr_best": float(merged["is_dsr"].max()),
        "dsr_median": float(merged["is_dsr"].median()),
        "n_dsr_above_095": int((merged["is_dsr"] > 0.95).sum()),
        "n_fdr_significant": int((pv["q_value"] < 0.05).sum()),
        "n_fdr_significant_oos": int((pv["q_value_oos"] < 0.05).sum()),
        "n_fdr_significant_positive": n_fdr_pos,
        "n_fdr_significant_negative": n_fdr_neg,
        "n_fdr_significant_oos_positive": n_fdr_oos_pos,
        "n_fdr_significant_oos_negative": n_fdr_oos_neg,
        "is_oos_spearman": rho,
        "is_oos_spearman_positive_is": rho_pos,
        "n_positive_is": int(len(pos)),
        "n_positive_oos": int((merged["oos_sharpe_net"] > 0).sum()),
        "top_decile_oos_mean_sharpe": top_oos_mean,
        "top_decile_oos_positive_frac": top_oos_pos,
        "best_is_trial": best,
        "variant_effects": effects,
        "timeframe_effects": tf_effect.to_dict(orient="records"),
        "top_is_with_oos_ci": cis,
        "top_oos_descriptive": top_oos_desc,
        "family": fam.to_dict(orient="records"),
    }
    write_json(RESULTS_DIR / "stats.json", out)
    return out


def stage_capacity(cfg: StudyConfig) -> dict:
    trials = pd.read_csv(RESULTS_DIR / "trials_with_dsr.csv")
    audit = read_json(RESULTS_DIR / "data_audit.json")
    rows = []
    for symbol in cfg.crypto_symbols:
        df = _load_5m(cfg, symbol)
        sigma_daily = float(np.log(df["close"]).diff().dropna().std() * np.sqrt(288))
        adv = float(audit["crypto"][symbol]["median_quote_volume_daily"])
        sort_col = "is_sharpe_net" if "is_sharpe_net" in trials.columns else "sharpe_net"
        best = trials[trials["symbol"] == symbol].sort_values(sort_col, ascending=False).head(8)
        for _, row in best.iterrows():
            h_days = rule_minutes(row["timeframe"]) / 1440.0
            edge = float(row["avg_trade_return"])
            q = estimate_edge_per_unit_vol(
                pd.DataFrame({"gross_return": [edge]}), sigma_daily, h_days
            )
            h_star = optimal_horizon_days(q, sigma_daily, float(row["break_even_cost"]) if np.isfinite(row["break_even_cost"]) else 1e-4)
            cap = capacity_table(pd.DataFrame([row]), adv, sigma_daily, k=float(cfg.raw["costs"]["impact_k"]))
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": row["timeframe"],
                    "strategy": row["strategy"],
                    "variant": row["variant"],
                    "sharpe_net": row["sharpe_net"],
                    "is_sharpe_net": row.get("is_sharpe_net", row["sharpe_net"]),
                    "avg_trade_return": edge,
                    "sigma_daily": sigma_daily,
                    "adv_quote_usd": adv,
                    "edge_per_unit_vol": q,
                    "h_star_days": h_star,
                    "capacity_usd": float(cap["capacity_usd"].iloc[0]),
                    "n_trades": row["n_trades"],
                }
            )
    cap_df = pd.DataFrame(rows)
    cap_df.to_csv(RESULTS_DIR / "capacity.csv", index=False)
    budgets = [float(x) for x in cfg.raw["protocol"]["decision_budgets_per_week"]]
    tb = []
    for symbol in cfg.crypto_symbols:
        sub = trials[trials["symbol"] == symbol].copy()
        sub["timeframe_minutes"] = sub["timeframe"].map(rule_minutes)
        sub["sharpe_net"] = sub[("is_sharpe_net" if "is_sharpe_net" in sub.columns else "sharpe_net")].astype(float)
        for b in budgets:
            sel = tbmt_select(sub, b)
            sel["symbol"] = symbol
            tb.append(sel)
    pd.DataFrame(tb).to_csv(RESULTS_DIR / "tbmt.csv", index=False)
    out = {"capacity": cap_df.to_dict(orient="records"), "tbmt": tb}
    write_json(RESULTS_DIR / "capacity.json", out)
    return out


def stage_equities(cfg: StudyConfig) -> dict:
    cost_bps = float(cfg.raw["costs"]["equity_bps"])
    rows_daily = []
    for symbol in cfg.equity_symbols:
        df = fetch_daily(symbol, cfg.cache_dir)
        frames = {
            "1d": df,
            "1w": resample_ohlcv(df, "1w", 1440, min_bars=3),
            "2w": resample_ohlcv(df, "2w", 1440, min_bars=8),
        }
        for tf in ("1d", "1w"):
            for strategy, params in (("ma", {"fast": 20, "slow": 100}), ("ma", {"fast": 50, "slow": 200}), ("tsmom", {"lookback": 100}), ("donchian", {"lookback": 55})):
                variants = ["base_only"] if tf == "1w" else ["base_only", "htf_filter", "htf_trigger", "confluence3"]
                for variant in variants:
                    base = frames[tf]
                    b = build_signal(base, strategy, params)
                    if variant == "base_only":
                        h = pd.Series(0.0, index=base.index)
                        h2 = pd.Series(0.0, index=base.index)
                    else:
                        hs1 = build_signal(frames["1w"], strategy, params)
                        h = align_htf(base, frames["1w"], hs1)
                        hs2 = build_signal(frames["2w"], strategy, params)
                        h2 = align_htf(base, frames["2w"], hs2)
                    pos = apply_variant(b, h, h2, variant)
                    res = run_backtest(base, pos, tf, strategy, variant, params, cost_bps / 1e4, 252.0, name=f"{symbol}|{tf}|{strategy}|{variant}")
                    ppy = 252.0 if tf == "1d" else 52.0
                    s = summarize(res, periods_per_year=ppy)
                    s.update({"symbol": symbol, "market": "equity", "trial_id": res.name})
                    rows_daily.append(s)
    daily = pd.DataFrame(rows_daily)
    daily["params_json"] = daily["params"].map(lambda p: json.dumps(p, sort_keys=True))
    daily.to_csv(RESULTS_DIR / "equities_daily.csv", index=False)
    key = ["symbol", "timeframe", "strategy", "params_json"]
    base = daily[daily["variant"] == "base_only"].set_index(key)
    eq_effects = {}
    for variant in ("htf_filter", "htf_trigger", "confluence3"):
        alt = daily[daily["variant"] == variant].set_index(key)
        diff = (alt["sharpe_net"] - base["sharpe_net"]).dropna()
        gross = (alt["sharpe_gross"] - base["sharpe_gross"]).dropna()
        vol_ratio = (alt["ann_vol_net"] / base["ann_vol_net"]).replace([np.inf, -np.inf], np.nan).dropna()
        turn_ratio = (alt["turnover_per_year"] / base["turnover_per_year"]).replace([np.inf, -np.inf], np.nan).dropna()
        eq_effects[variant] = {
            "n_pairs": int(len(diff)),
            "mean_net_sharpe_diff": float(diff.mean()),
            "median_net_sharpe_diff": float(diff.median()),
            "frac_positive": float((diff > 0).mean()),
            "mean_gross_sharpe_diff": float(gross.mean()),
            "median_vol_ratio": float(vol_ratio.median()),
            "median_turnover_ratio": float(turn_ratio.median()),
        }
    write_json(RESULTS_DIR / "equity_effects.json", eq_effects)
    rows_intraday = []
    for symbol in cfg.equity_symbols:
        try:
            h = fetch_hourly(symbol, cfg.cache_dir)
        except Exception:
            continue
        if len(h) < 300:
            continue
        frames = {
            "1h": h,
            "4h": resample_ohlcv(h, "4h", 60, min_bars=3),
            "1d": resample_ohlcv(h, "1d", 60, min_bars=5),
        }
        for tf in ("1h", "4h"):
            bars_per_day = float(frames[tf].groupby(frames[tf]["open_time"].dt.date).size().median())
            periods_per_year = 252.0 * max(bars_per_day, 1.0)
            for strategy, params in (("ma", {"fast": 20, "slow": 100}), ("tsmom", {"lookback": 50}), ("donchian", {"lookback": 50})):
                res = run_backtest(frames[tf], build_signal(frames[tf], strategy, params), tf, strategy, "base_only", params, cost_bps / 1e4, periods_per_year, name=f"{symbol}|{tf}|{strategy}|base_only")
                s = summarize(res, periods_per_year=periods_per_year)
                s.update({"symbol": symbol, "market": "equity", "trial_id": res.name})
                rows_intraday.append(s)
    pd.DataFrame(rows_intraday).to_csv(RESULTS_DIR / "equities_intraday.csv", index=False)
    return {"daily_rows": len(rows_daily), "intraday_rows": len(rows_intraday)}


def stage_surrogates(cfg: StudyConfig) -> dict:
    out = {}
    for symbol in cfg.crypto_symbols:
        df = _load_5m(cfg, symbol)
        idx = df.set_index("open_time")
        r1h = np.log(idx["close"]).diff().rolling(12).sum()
        fwd1h = np.log(idx["close"]).shift(-12) - np.log(idx["close"])
        df4 = resample_ohlcv(df, "4h", 5)
        s4 = pd.Series(np.sign(np.log(df4["close"]).diff(12)).to_numpy(), index=df4["close_time"])
        s4_1h = s4.reindex(idx.index, method="ffill")
        df1d = resample_ohlcv(df, "1d", 5)
        s1d = pd.Series(np.sign(np.log(df1d["close"]).diff(48)).to_numpy(), index=df1d["close_time"])
        s1d_1h = s1d.reindex(idx.index, method="ffill")
        fast = np.sign(r1h)
        disagree = (fast != s1d_1h).astype(float)
        fwd1d = np.log(idx["close"]).shift(-288) - np.log(idx["close"])
        tests = {
            "own_tf": surrogate_mi_pvalue(fast.to_numpy(), fwd1h.to_numpy(), reps=200, bins=8, seed=cfg.seed),
            "htf_to_ltf": surrogate_mi_pvalue(s4_1h.to_numpy(), fwd1h.to_numpy(), reps=200, bins=8, seed=cfg.seed + 1),
            "disagreement_to_future": surrogate_mi_pvalue(disagree.to_numpy(), fwd1d.to_numpy(), reps=200, bins=6, seed=cfg.seed + 2),
        }
        out[symbol] = tests
    write_json(RESULTS_DIR / "surrogates.json", out)
    return out


def stage_live(cfg: StudyConfig, loop: bool = False, interval_seconds: int = 3600) -> dict:
    from .live import cross_venue_snapshot, fetch_kraken, shadow_signals
    from .protocol import TimeframeLock

    log_path = cfg.root / cfg.raw["live"]["log_path"]
    lock = TimeframeLock(log_path)
    snap = cross_venue_snapshot()
    bars = {
        "1h": fetch_kraken("XBTUSD", 60, 720),
        "4h": fetch_kraken("XBTUSD", 240, 720),
        "1d": fetch_kraken("XBTUSD", 1440, 720),
    }
    sig = shadow_signals(bars)
    payload = {
        "venues": snap,
        "signal": sig,
        "tolerance_bps": float(cfg.raw["live"]["tolerance_bps"]),
        "within_tolerance": bool(snap.get("max_deviation_bps", 0) <= float(cfg.raw["live"]["tolerance_bps"])),
    }
    lock.record("shadow_snapshot", payload)
    verify = lock.verify()
    write_json(RESULTS_DIR / "live_snapshot.json", {"snapshot": payload, "log_verification": verify, "log_path": str(log_path)})
    return {"snapshot": payload, "verification": verify}


def stage_report(cfg: StudyConfig) -> dict:
    files = {
        "manifest": RESULTS_DIR / "data_manifest.json",
        "audit": RESULTS_DIR / "data_audit.json",
        "multiscale": RESULTS_DIR / "multiscale.json",
        "stats": RESULTS_DIR / "stats.json",
        "capacity": RESULTS_DIR / "capacity.json",
        "surrogates": RESULTS_DIR / "surrogates.json",
    }
    out = {}
    for k, p in files.items():
        if p.exists():
            out[k] = read_json(p)
    for name in ("equities_daily", "equities_intraday", "finest_scale", "timeframe_family", "tbmt"):
        p = RESULTS_DIR / f"{name}.csv"
        if p.exists():
            out[name] = pd.read_csv(p).to_dict(orient="records")
    out["environment"] = dependency_versions()
    write_json(RESULTS_DIR / "report.json", out)
    return out

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import FIGURES_DIR, RESULTS_DIR
from .utils import read_json


def _save(fig, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def fig_sharpe_by_timeframe() -> Path:
    df = pd.read_csv(RESULTS_DIR / "trials_with_dsr.csv")
    order = ["5m", "15m", "30m", "1h", "4h", "1d"]
    symbols = sorted(df["symbol"].unique())
    fig, axes = plt.subplots(1, len(symbols), figsize=(4.2 * len(symbols), 4.2), sharey=True)
    if len(symbols) == 1:
        axes = [axes]
    for ax, sym in zip(axes, symbols, strict=False):
        sub = df[df["symbol"] == sym]
        col = "is_sharpe_net" if "is_sharpe_net" in sub.columns else "sharpe_net"
        data = [sub.loc[sub["timeframe"] == tf, col].dropna().to_numpy() for tf in order]
        ax.boxplot(data, tick_labels=order, showfliers=False)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(sym)
        ax.set_xlabel("timeframe")
        ax.tick_params(axis="x", rotation=45)
    axes[0].set_ylabel("annualized net Sharpe")
    fig.suptitle("In-sample net Sharpe by timeframe and symbol (12 bp costs)")
    return _save(fig, "fig1_sharpe_by_timeframe.png")


def fig_cost_sensitivity() -> Path:
    df = pd.read_csv(RESULTS_DIR / "cost_sensitivity.csv")
    symbols = sorted(df["symbol"].unique())
    fig, axes = plt.subplots(1, len(symbols), figsize=(4.4 * len(symbols), 4.2), sharey=True)
    if len(symbols) == 1:
        axes = [axes]
    for ax, sym in zip(axes, symbols, strict=False):
        sub = df[df["symbol"] == sym]
        keys = sub.groupby(["timeframe", "strategy", "variant", "params_json"])["sharpe_net"].max().sort_values(ascending=False).head(4)
        for (tf, strategy, variant, params), _ in keys.items():
            curve = sub[(sub["timeframe"] == tf) & (sub["strategy"] == strategy) & (sub["variant"] == variant) & (sub["params_json"] == params)].sort_values("cost_bps")
            ax.plot(curve["cost_bps"], curve["sharpe_net"], marker="o", label=f"{tf} {strategy} {variant}")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(f"{sym}")
        ax.set_xlabel("cost (bp per unit turnover)")
        ax.legend(fontsize=6)
    axes[0].set_ylabel("annualized net Sharpe")
    fig.suptitle("Full-sample net Sharpe versus cost (top full-sample trials)")
    return _save(fig, "fig2_cost_sensitivity.png")


def fig_vol_scaling() -> Path:
    ms = read_json(RESULTS_DIR / "multiscale.json")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    for sym, payload in ms["scaling"].items():
        table = pd.DataFrame(payload["table"])
        axes[0].plot(table["log_minutes"], table["log_sigma_bar"], marker="o", label=sym)
        axes[1].plot(table["log_minutes"], table["log_sigma_annual"], marker="o", label=sym)
        s1 = payload["per_bar"]["slope"]
        s2 = payload["annualized"]["slope"]
        axes[0].annotate(f"{s1:.3f}", (table["log_minutes"].iloc[2], table["log_sigma_bar"].iloc[2]), fontsize=8, xytext=(4, 4), textcoords="offset points")
        axes[1].annotate(f"{s2:.3f}", (table["log_minutes"].iloc[2], table["log_sigma_annual"].iloc[2]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axes[0].set_title("per-bar volatility vs horizon")
    axes[0].set_ylabel("log sigma per bar")
    axes[1].set_title("annualized volatility vs horizon")
    axes[1].set_ylabel("log annualized sigma")
    for ax in axes:
        ax.set_xlabel("log minutes per bar")
        ax.legend(fontsize=8)
    return _save(fig, "fig3_vol_scaling.png")


def fig_disagreement() -> Path:
    ms = read_json(RESULTS_DIR / "multiscale.json")
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    rho = np.linspace(0, 1, 300)
    ax.plot(rho, 0.5 - np.arcsin(rho) / np.pi, color="black", lw=1.5, label="0.5 - arcsin(rho)/pi")
    markers = {"BTCUSDT": "o", "ETHUSDT": "s", "SOLUSDT": "^"}
    colors = {"5m_vs_1h": "#4c72b0", "1h_vs_4h": "#dd8452", "1h_vs_1d": "#55a868", "4h_vs_1d": "#c44e52"}
    for sym, pairs in ms["disagreement"].items():
        for p in pairs:
            ax.scatter(
                p["rho_theory"],
                p["disagreement"],
                marker=markers.get(sym, "o"),
                color=colors.get(p["pair"], "black"),
                s=40,
                label=f"{sym} {p['pair']}",
            )
    ax.set_xlabel("rho = sqrt(h1/h2)")
    ax.set_ylabel("P(sign disagreement)")
    ax.set_title("Empirical sign disagreement vs Gaussian benchmark")
    ax.legend(fontsize=6, ncol=2, frameon=False)
    return _save(fig, "fig4_disagreement.png")


def fig_pbo() -> Path:
    logits = np.load(RESULTS_DIR / "pbo_logits.npy")
    stats = read_json(RESULTS_DIR / "stats.json")
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.hist(logits, bins=40, color="#4c72b0", alpha=0.85)
    ax.axvline(0, color="black", lw=1.0)
    ax.set_xlabel("logit of OOS rank of IS-best strategy")
    ax.set_ylabel("combinations")
    ax.set_title(f"CSCV distribution: PBO = {stats['pbo']['pbo']:.3f}")
    return _save(fig, "fig5_pbo.png")


def fig_equity() -> Path:
    daily = pd.read_parquet(RESULTS_DIR / "daily_returns.parquet")
    trials = pd.read_csv(RESULTS_DIR / "trials_with_dsr.csv").sort_values("is_sharpe_net", ascending=False).head(5)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for _, row in trials.iterrows():
        col = row["trial_id"]
        if col not in daily.columns:
            continue
        eq = (1.0 + daily[col].fillna(0.0)).cumprod()
        ax.plot(eq.index, eq.values, lw=1.1, label=col.split("|")[1] + " " + row["strategy"] + " " + row["variant"])
    ax.axvline(pd.Timestamp("2025-01-01", tz="UTC"), color="grey", ls="--", lw=0.9, label="holdout start")
    ax.set_yscale("log")
    ax.set_title("Top-5 in-sample net equity curves, with holdout (daily, log scale)")
    ax.set_ylabel("growth of 1")
    ax.legend(fontsize=6)
    return _save(fig, "fig6_equity.png")


def fig_capacity() -> Path:
    df = pd.read_csv(RESULTS_DIR / "capacity.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for sym, sub in df.groupby("symbol"):
        ax.scatter(sub["timeframe"], sub["capacity_usd"], label=sym, s=40)
    ax.set_yscale("log")
    ax.set_ylabel("capacity (USD, log)")
    ax.set_xlabel("timeframe")
    ax.set_title("Estimated capacity (capped at ADV) vs decision timeframe")
    ax.legend(fontsize=8)
    return _save(fig, "fig7_capacity.png")


def fig_finest() -> Path:
    df = pd.read_csv(RESULTS_DIR / "finest_scale.csv")
    order = ["1m", "5m", "15m", "1h", "4h", "1d"]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for (strategy, variant), sub in df.groupby(["strategy", "variant"]):
        sub = sub.set_index("timeframe").reindex(order).dropna(subset=["sharpe_net"])
        ax.plot(sub.index, sub["sharpe_net"], marker="o", label=f"{strategy} {variant}")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("timeframe")
    ax.set_ylabel("annualized net Sharpe")
    ax.set_title("Finest available data (BTCUSDT 1m): net Sharpe by timeframe")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=7)
    return _save(fig, "fig8_finest_scale.png")


def make_all() -> list[Path]:
    paths = []
    for fn in (fig_sharpe_by_timeframe, fig_cost_sensitivity, fig_vol_scaling, fig_disagreement, fig_pbo, fig_equity, fig_capacity, fig_finest):
        try:
            paths.append(fn())
        except Exception as exc:
            print(f"[figures] skip {fn.__name__}: {exc}")
    return paths

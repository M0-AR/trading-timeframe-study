# Pre-registration: Timeframe Validity

**Version:** 1.0
**Frozen:** 2026-10-21, before any return series was computed.
**Authors:** Timeframe Validity Project.

This document fixes the hypotheses, data, estimators, and decision rules of the
study. Any change after the first backtest is recorded in
`docs/DEVIATIONS.md` with a timestamp and a reason. Results are reported for
every pre-registered cell, including cells that fail.

## 1. Question

Trading education routinely asserts that (i) higher timeframes are more
"reliable", (ii) a higher-timeframe filter improves a lower-timeframe system,
and (iii) very short timeframes are unusable because "noise" and costs
dominate. We ask which of these statements survive when the same signal
family is evaluated across a fixed timeframe ladder on identical data, with
execution lags, realistic costs, and a correction for the number of trials.

The study is descriptive and inferential, not a search for a profitable
strategy. A negative result for a claim is a result.

## 2. Hypotheses

- **H1 (sampling).** Per-bar log-return volatility scales as the square root
  of the bar length, so annualized volatility is approximately flat across
  the ladder. Departures at 5m/15m are attributable to microstructure.
- **H2 (cost).** For a fixed signal family, net Sharpe is non-increasing in
  decision frequency once costs are charged; the gross-to-net gap is largest
  at 5m and smallest at 1d.
- **H3 (multi-timeframe).** On average across the pre-registered grid, an HTF
  filter does not increase net Sharpe relative to the same base signal. Any
  improvement is family- and regime-specific and does not survive PBO/DSR.
- **H4 (confluence).** Averaging base and HTF signs reduces turnover and
  volatility but does not reliably raise net Sharpe.
- **H5 (selection).** The best in-sample trial out of 1,008 has a deflated
  Sharpe ratio below 0.95 and a probability of backtest overfitting above
  0.25, i.e. the winner is not credible as an out-of-sample edge.
- **H6 (budget).** When a trader can act at most `kappa` times per week, the
  best feasible timeframe differs from the unconstrained best, and regret
  increases as `kappa` falls.
- **H7 (equities).** The direction of H1-H3 transfers to daily US equity
  data, with smaller cost effects because equity costs per turnover are
  lower and the sampling grid is coarser.
- **H8 (live).** Independent venues produce last prices within 50 bp and
  shadow 1h/4h/1d signals that agree in sign more often than chance; the
  hash-chained live log verifies.

## 3. Data

- **Crypto primary.** Binance Vision spot monthly klines, `BTCUSDT`,
  `ETHUSDT`, `SOLUSDT`, interval `5m`, 2021-01 to 2026-09, each file checked
  against its published SHA-256. The 5m series is built by resampling a
  single 1m path per symbol; 1m files cover `BTCUSDT` only.
- **Equities.** EODHD demo end-of-day series for `AAPL.US`, `TSLA.US`,
  `AMZN.US`, `VTI.US`, and the available 1h window. Adjusted prices are
  used for signals and returns.
- **Rates.** FRED `DTB3` for a risk-free reference; no Sharpe is excess-return
  adjusted in the primary endpoint (documented limitation).
- **Live verification.** Kraken, Coinbase and OKX public endpoints, read-only,
  no keys.

All timestamps are UTC. Incomplete resampled buckets are dropped. No forward
fill of prices across gaps is performed for signal construction.

## 4. Sample split

- Development/in-sample: 2021-01-01 to 2024-12-31.
- Holdout/out-of-sample: 2025-01-01 to 2026-09-30.

The holdout is not used for parameter selection. Because the trial grid is
fixed and exhaustive (Section 5), the holdout is a genuine unseen period for
the selected configurations.

## 5. Design

- Ladder: 5m, 15m, 30m, 1h, 4h, 1d.
- HTF map: 5m→(15m,1h), 15m→(1h,4h), 30m→(2h,8h), 1h→(4h,1d),
  4h→(1d,1w), 1d→(2d,4d).
- Signal families:
  - MA crossover, `(fast, slow)` in `{10,20,50} x {50,100,200}`, fast<slow.
  - Donchian breakout, lookback in `{20,50,100}`.
  - Time-series momentum, lookback in `{20,50,100}`.
- Variants: `base_only`, `htf_filter` (trade base only when signs agree),
  `htf_trigger` (enter on first agreement in an HTF run, stay until HTF
  flips), `confluence3` (average of base and two HTF signs).
- Trials: 3 symbols x 6 timeframes x 14 configurations x 4 variants = 1,008.
- Execution: signal at bar close `t`, position effective at open `t+1`, return
  measured to open `t+2`. Positions are unit exposure; no leverage, no
  volatility targeting in the primary run.
- Costs: 12 bp per unit turnover for crypto (10 bp taker + 1 bp half-spread +
  1 bp slippage). Sensitivity at 0, 5, 12, 25, 50 bp. Equity base case 4 bp.
- Shorting is allowed. No funding is charged (spot data).

## 6. Endpoints

**Primary:** annualized net Sharpe ratio of daily returns at the base cost.

**Secondary:** annualized net return, annualized volatility, maximum
drawdown, Calmar, turnover per year, trades per year, win rate, payoff,
profit factor, break-even cost, deflated Sharpe ratio, probability of
backtest overfitting.

**Capacity:** estimated deployable notional from average trade edge, daily
volatility, and a square-root impact coefficient `k = 0.10`.

## 7. Inference

- CSCV with `S=12` slices (924 combinations) for PBO.
- Deflated Sharpe ratio with the trial count and the cross-trial dispersion
  of Sharpe ratios.
- White Reality Check and a studentized SPA-style bootstrap (stationary
  bootstrap, mean block 20 days, 500 replications).
- Benjamini-Hochberg FDR at 5% over all trial t-statistics, Newey-West with
  10 lags.
- Stationary-bootstrap 95% confidence intervals for the top ten trials.

## 8. Decision rules

A claim is reported as **supported** only if the pre-specified direction is
observed and (a) the bootstrap 95% interval excludes zero, (b) the FDR
q-value is below 0.05, and (c) DSR exceeds 0.95. If (a) holds but (b) or (c)
fails, the claim is **inconclusive**. If the sign is opposite, the claim is
**rejected**. H1 and H6 are assessed descriptively with the same thresholds
where applicable.

No symbol may be dropped. No timeframe may be added after seeing results.
The 2025-2026 holdout is evaluated once, after the in-sample analysis is
complete.

## 9. Stopping and deviations

The data window is fixed. There is no optional stopping. Any deviation
(additional trial, changed cost, dropped file) is logged in
`docs/DEVIATIONS.md` before the affected result is interpreted.

## 10. Outputs

`results/trials.parquet`, `results/trials_with_dsr.csv`,
`results/stats.json`, `results/capacity.csv`, `results/tbmt.csv`,
`results/equities_daily.csv`, `results/surrogates.json`,
`results/live_snapshot.json`, and `figures/fig1..fig8`.

# Deviations from pre-registration

Append-only. Each entry states the date, the change, and the reason.

The pre-registration was frozen on 2026-10-21, before the first return series
was computed. The entries below record post-freeze data-availability and
implementation corrections. They do not change the hypotheses, the 1,008-trial
grid, the in-sample/out-of-sample dates, the cost model, or the one-time
holdout rule.

## 2026-10-21 — Data availability and implementation corrections

1. **FRED `DTB3` unavailable.** The fetch stage now treats FRED as optional,
   records the timeout in the fetch manifest, and continues. The risk-free
   series is not used in any reported result. Reason: `fred.stlouisfed.org`
   timed out repeatedly from the research host.

2. **Equity intraday history is much shorter than the crypto history.** EODHD
   returned 1-hour bars only from 2026-06-24 through 2026-10-20 (664 bars, 83
   trading days). Intraday equity results are therefore labelled exploratory,
   are not used for annualized claims, and do not enter the confirmatory
   hypothesis tests. Reason: vendor intraday retention limit.

3. **Equity weekly timeframe added.** H7 was specified for daily equity data;
   the implementation also evaluates weekly bars (16 additional rows) to test
   whether the horizon result survives a slower sampling frequency. Weekly
   equity rows use `base_only` to keep the reduced grid interpretable. Reason:
   direct test of the paper's horizon mechanism.

4. **Native 5-minute bars used instead of resampling all assets from 1-minute
   data.** Binance Vision 1-minute history was downloaded only for BTCUSDT;
   ETHUSDT and SOLUSDT use native 5-minute bars. BTCUSDT native 5-minute bars
   were cross-checked against 1-minute resampling: 604,299 versus 604,297
   overlapping bars, identical opens/closes, and only a handful of high/low
   and volume boundary differences. Reason: 1-minute files for ETH/SOL would
   have exceeded the available memory and added little to the main tests.

5. **Live venue endpoints use ticker quotes rather than the OHLC endpoint named
   in the pre-registration.** Kraken, Coinbase, and OKX public ticker endpoints
   are used to obtain contemporaneous last prices. The three-venue tolerance
   test is unchanged. Reason: the documented OHLC endpoints were unavailable
   or rate-limited during implementation.

6. **Timestamp-unit bug in gap auditing fixed.** The audit originally converted
   tz-aware parquet timestamps with `.astype("int64")`, whose unit depends on
   the parquet dtype (milliseconds versus microseconds). Gap and spacing
   calculations now use `.diff().dt.total_seconds()` and explicit unit
   conversion. Reason: pandas 3 preserves different timestamp resolutions and
   the original conversion produced false gaps.

7. **Corwin–Schultz spread estimator corrected.** The two-day beta term now uses
   the correct two-day high/low covariance expression rather than a one-day
   proxy. Reason: implementation error found during audit review.

8. **Equity business-day audit corrected.** Equity gap checks now use a
   business-day calendar and align timezone/unit before differencing. Missing
   bars are exchange holidays, not data defects. Reason: the original
   calendar-day audit reported holiday closures as gaps.

9. **In-sample/out-of-sample statistics implemented as frozen.** `stage_stats`
   selects trials and computes DSR, PBO/CSCV, Reality Check, SPA, and BH on the
   in-sample period only; out-of-sample returns are used only for evaluation
   and descriptive checks. The holdout is evaluated once for the selected
   trial. Reason: the original stage computed full-sample statistics, which
   would have leaked the holdout.

10. **Equity weekly annualization uses 52 periods per year.** Daily equity rows
    use 252; weekly rows use 52. Reason: calendar-consistent annualization.

11. **Equity intraday annualization uses the empirical bars-per-year from the
    observed calendar.** The short 83-day sample cannot support a fixed 252-day
    annualization. Reason: avoid inflating annualized statistics.

12. **Intraday daily timeframe dropped.** The 1-hour equity history is shorter
    than one year, so a 1-day intraday row would have very few observations.
    Only 15m, 30m, 1h, and 4h intraday rows are reported. Reason: insufficient
    sample length.

13. **Live shadow layers use native interval bars.** The 1h, 4h, and 1d shadow
    layers are computed from bars at those native intervals rather than by
    resampling a single base series. Reason: match the signal definitions and
    avoid resampling artifacts. Early log records had shorter warm-up windows
    (31 and 181 daily bars); the final record uses 720 bars.

14. **Matplotlib pinned below 4.0.** The environment uses matplotlib 3.11.2;
    `pyproject.toml` and `requirements.txt` constrain `matplotlib>=3.9,<4`.
    Reason: reproducible figure rendering and compatibility with the plotting
    code.

15. **`n_days` added to metrics.** `metrics.summarize` now reports the number of
    daily observations alongside `n_bars`. The top-level `n_days` field in
    `stats.json` is null; use `n_days_is` and `n_days_oos`. Reason: bars and
    days are not interchangeable across timeframes.

16. **Capacity and figures select on in-sample Sharpe.** Capacity, the equity
    curve figure, and the cost-sensitivity figure select trials using
    in-sample Sharpe and show out-of-sample performance only for evaluation.
    Reason: prevent holdout leakage in plots and capacity estimates.

17. **Surrogate mutual-information test uses 200 replications.** The
    permutation test was reduced from a larger default to 200 replications to
    keep the pipeline tractable. Reason: runtime on ~604k observations.

18. **Finest-scale diagnostic uses the 12 bp base cost.** The 1-minute
    diagnostic is evaluated at the same 12 bp crypto cost as the main grid.
    Reason: comparability with the pre-registered cost model.

19. **Reduced equity grid.** The equity daily grid uses four configurations
    (MA 20/100, MA 50/200, TSMOM 100, Donchian 55); the weekly grid uses
    `base_only`. Reason: keep the equity extension within the compute budget
    while preserving the main strategy families.

20. **Figure labeling corrections.** Figure 2 is explicitly labelled
    full-sample cost sensitivity; Figure 6 marks the 2025-01-01 holdout
    boundary; Figure 4 labels all 12 symbol/pair combinations; Figure 7 is
    titled "Estimated capacity (capped at ADV) vs decision timeframe"; Figure 8
    is titled for the 1-minute net Sharpe diagnostic. Reason: accuracy and
    readability.

21. **Artifact key renamed.** `stats.json` previously stored the top-IS trials
    with OOS confidence intervals under the misleading key `top_oos`. The key
    is now `top_is_with_oos_ci`, and a separate descriptive `top_oos_descriptive`
    list is provided. Reason: avoid confusing selection ranking with
    out-of-sample ranking.

22. **BH significance counts split by sign.** `stats.json` now reports positive
    and negative BH-significant counts separately. The 237 in-sample and 214
    out-of-sample BH-significant trials are overwhelmingly negative; only 5
    in-sample and 0 out-of-sample positive trials are BH-significant. Reason:
    the aggregate count alone is easy to misread as evidence of profitable
    strategies.

No other deviations are recorded. All results in `results/` were regenerated
after these corrections.

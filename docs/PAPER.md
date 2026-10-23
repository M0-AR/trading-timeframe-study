# Timeframe Is a Parameter, Not a Truth

## A Pre-Registered, Cost-Aware Evaluation of Trading Signals

**Timeframe Validity Project**<br>
**Version 1.0 — 21 October 2026**

> **Technical paper edition.** This is the full pre-registered research paper. For the business-friendly guide, start with the repository [README](../README.md).

---

## Abstract

Trading education commonly treats the choice of chart timeframe as a statement
about signal quality: higher timeframes are said to be more reliable, a
higher-timeframe (HTF) filter is said to improve a lower-timeframe system, and
very short timeframes are said to be unusable because of noise and costs. This
paper tests those claims on a fixed, pre-registered grid of 1,008 strategies
using Binance spot data for BTCUSDT, ETHUSDT, and SOLUSDT from January 2021 to
September 2026, with a genuine 2025–2026 holdout, next-open execution, 12 bp
crypto costs, and a battery of selection-bias corrections. The same signal
families are evaluated at 5m, 15m, 30m, 1h, 4h, and 1d, with four
multi-timeframe variants.

Three results stand out. First, the sampling identity is real but does not
make higher timeframes “less noisy” in annualized terms: per-bar volatility
scales with an exponent of 0.484–0.494, while annualized volatility is
approximately flat (BTC 0.620 at 5m versus 0.571 at 1d). Second, costs, not
sampling noise, dominate the timeframe decision. Median in-sample net Sharpe
is −3.21 at 5m, −0.60 at 15m, −0.11 at 30m, 0.18 at 1h, 0.39 at 4h, and 0.35
at 1d; median annual cost drag falls from 80.1% at 5m to 0.8% at 1d. The
cost-optimal region is 4h–1d, not the shortest timeframe. Third, the
pre-registered negative claims about HTF filters and confluence are rejected
in their stated form: on average, an HTF filter raises net Sharpe by 0.53
(80.6% of pairs positive), and a three-way confluence raises it by 0.94 (83.7%
positive). The improvement is mostly a risk/turnover effect, not new gross
alpha: median volatility falls to 0.80 and turnover to 0.62 of the base
levels for the filter variant.

Selection remains the binding constraint. The best in-sample trial
(`SOLUSDT|4h|ma|confluence3|fast10_slow50`) has an in-sample Sharpe of 1.542
and an out-of-sample Sharpe of −0.498; its 95% out-of-sample bootstrap
interval is [−2.094, 0.727]. The maximum deflated Sharpe probability across all trials is
effectively zero (1.36 × 10⁻⁹¹), and the best trial’s own DSR is 8.16 × 10⁻⁹⁶. PBO is 0.156, and the Reality Check and
SPA p-values are 0.246 and 0.210. Only 5 of the 237 in-sample BH-significant
trials are positive; all 214 out-of-sample BH-significant trials are negative.
Overall in-sample/out-of-sample rank correlation is 0.709, but among trials
with positive in-sample Sharpe it is −0.030. The apparent persistence is
driven by extreme 5m losers, not by winners.

Equity and live results are partial. The direction of the HTF-filter effect
transfers to daily US equities, but the top equity rows are buy-and-hold-like
and the intraday equity window is only 83 days. The live three-venue check
passes its 50 bp tolerance test and the hash-chained log verifies, but the
1h/4h/1d shadow signals disagree and the sample is too small for a chance
test. The paper’s practical conclusion is narrow and robust: timeframe is a
cost, exposure, and decision-budget parameter, not a truth about signal
quality; HTF filters are useful risk-control overlays, not alpha generators;
and the winner of a large backtest grid should not be trusted without
deflation and an untouched holdout.

**Keywords:** timeframe analysis; multiple timeframes; transaction costs;
backtest overfitting; market microstructure; pre-registration.

---

## 1. Introduction

A chart timeframe is a sampling choice. It determines how often a trader makes
a decision, how much turnover the strategy generates, how much data is
available, and how much microstructure noise enters the signal. It does not,
by itself, determine whether a signal has an edge. Yet trading education
routinely conflates the two. A typical claim is that a higher timeframe is
“more reliable,” that a lower-timeframe entry should be filtered by a
higher-timeframe trend, or that 5-minute charts are “too noisy” to trade. These
claims are testable, but they are rarely tested on the same signal family,
the same data, the same execution assumptions, and with a correction for the
number of trials.

This paper is a pre-registered attempt to do that. The design fixes the
timeframe ladder, the signal families, the variants, the sample split, the
cost model, and the inference before any return series is computed. The
primary object is not a single profitable strategy. It is the *mapping* from
timeframe to net performance, gross performance, turnover, cost drag, and
out-of-sample persistence. A negative result for a popular claim is a result.

The paper makes five contributions.

1. **A fixed-ladder, cost-aware comparison.** The same 14 signal
   configurations are evaluated at six timeframes and under four
   multi-timeframe variants, for three crypto assets, producing 1,008 trials.
   Execution is next-open with a one-bar lag, costs are charged on position
   changes, and the holdout is untouched until the in-sample analysis is
   complete.

2. **A separation of sampling from costs.** Per-bar volatility scales almost
   exactly as the square root of bar length, but annualized volatility is
   approximately flat. The apparent “calm” of higher timeframes is a
   denominator effect, not a reduction in annual risk. Once costs are charged,
   the net Sharpe ranking is dominated by turnover and cost drag.

3. **A direct test of HTF filters and confluence.** The pre-registered
   hypotheses expected these variants not to help. They do help on average,
   but mostly by reducing volatility and turnover, not by improving gross
   alpha. The paper therefore separates “does the overlay improve risk-adjusted
   net performance?” from “does the overlay create a credible standalone
   edge?”

4. **A selection-bias audit.** DSR, PBO/CSCV, White’s Reality Check, a
   studentized SPA-style bootstrap, BH FDR, and a one-time holdout are applied
   to the full grid. The best in-sample trial collapses out of sample. The
   overall rank correlation is high only because extreme losers remain losers;
   among winners, rank persistence is absent.

5. **External validity checks.** The design is extended to daily US equities,
   a short intraday equity window, and a live three-venue shadow snapshot.
   These extensions are deliberately labelled partial: they test whether the
   direction of the crypto results survives a different asset class and a
   live-data setting, not whether a deployable strategy exists.

The rest of the paper is organized as follows. Section 2 relates the design to
prior work. Section 3 describes the data and audit. Section 4 lays out the
design and estimators. Section 5 reports the results. Section 6 discusses the
implications, Section 7 lists limitations, Section 8 gives the reproducibility
instructions, and Section 9 concludes.

---

## 2. Related Work

### 2.1 Timeframe claims in trading practice

Trading-education material often presents timeframe selection as a hierarchy:
higher timeframes are said to reveal the “real” trend, while lower timeframes
are said to contain noise. Multi-timeframe analysis then combines a
higher-timeframe trend filter with a lower-timeframe entry. These claims mix
three distinct ideas: sampling frequency, signal horizon, and execution cost.
The present paper keeps the signal family fixed and varies only the sampling
frequency and the HTF overlay, which makes the claims falsifiable.

The specific motivation for this study is the recent trading-education
literature on “confirmation horizons” and multi-timeframe confirmation,
including Kang and Ryu’s (2026) analysis of market-specific confirmation
horizons and the MQL5 article 22290 (2026) on timeframe-based confirmation.
Those sources motivate the hypotheses; they do not provide the identification
strategy used here.

### 2.2 Time-series momentum and trend following

Time-series momentum is a natural fixed signal family for a timeframe study.
Moskowitz, Ooi, and Pedersen (2012) document time-series momentum across
futures markets, and Georgopoulou and Wang (2017) extend the evidence to
equity and commodity markets. The present paper does not attempt to replicate
those return premia. It uses MA crossover, Donchian breakout, and TSMOM as
three economically interpretable signal families, then asks how their net
performance changes with sampling frequency and HTF overlays.

### 2.3 Optimal sampling and microstructure

The variance-time relation implies that per-bar volatility grows with the
square root of the bar length. At very high frequency, microstructure noise
drifts the realized variance estimator away from the quadratic variation, which
is the classic optimal-sampling problem analyzed by Bandi and Russell (2008).
The paper’s H1 is a deliberately simple version of this identity: estimate the
per-bar and annualized volatility slopes across the ladder and ask whether the
annualized series is approximately flat. Departures at 5m and 15m are
interpreted as microstructure and execution effects, not as evidence that
higher timeframes are intrinsically safer.

Corwin and Schultz (2012) provide a daily high-low spread estimator, which is
used here as an external check on the equity cost assumption. The estimator is
not a substitute for quoted spreads, but it is useful for asking whether a
4 bp equity cost is plausible for the assets in the sample.

### 2.4 Data snooping and backtest overfitting

A grid of 1,008 trials creates a large selection problem. White’s (2000)
Reality Check and Hansen’s (2005) Superior Predictive Ability test provide
bootstrap-based control of the maximum statistic. Bailey and López de Prado
(2014) provide the Deflated Sharpe Ratio, which adjusts for the number of
trials, non-normality, and the dispersion of trial Sharpe ratios. Bailey,
Borwein, López de Prado, and Zhu (2016) provide the Probability of Backtest
Overfitting via combinatorially symmetric cross-validation (CSCV). The present
paper applies all of these, and adds a genuine holdout that is evaluated once.

The REFORMS recommendations (2024) motivate the pre-registration, the explicit
decision rules, and the artifact trail. The paper is deliberately conservative:
a trial is not called credible merely because its in-sample Sharpe is large.

---

## 3. Data

### 3.1 Crypto data

The primary crypto sample is Binance Vision spot monthly klines for BTCUSDT,
ETHUSDT, and SOLUSDT, from 2021-01-01 through 2026-09-30. The 5-minute series
are native exchange bars. BTCUSDT 1-minute data were also downloaded to
construct the finest-scale diagnostic and to cross-check the 5-minute series.
All timestamps are UTC. Incomplete resampled buckets are dropped; prices are
not forward-filled across gaps for signal construction.

| Asset | Frequency | Rows | Start | End | Gaps | Missing bars (est.) |
|---|---:|---:|---|---|---:|---:|
| BTCUSDT | 5m | 604,299 | 2021-01-01 | 2026-09-30 23:55 | 7 | 213 |
| ETHUSDT | 5m | 604,299 | 2021-01-01 | 2026-09-30 23:55 | 7 | 213 |
| SOLUSDT | 5m | 604,299 | 2021-01-01 | 2026-09-30 23:55 | 7 | 213 |
| BTCUSDT | 1m | 3,021,487 | 2021-01-01 | 2026-09-30 23:59 | 7 | 1,073 |

The largest crypto gap is 17,100 seconds (4h45m). All series are monotonic,
with zero duplicate timestamps, zero non-positive prices, and zero high-low
violations. Median daily quote volume is $1.927bn for BTCUSDT, $1.088bn for
ETHUSDT, and $0.281bn for SOLUSDT.

The 5-minute series are native exchange bars, not a resample of the 1-minute
BTC series. The BTC cross-check is close: 604,299 native bars versus 604,297
overlapping 1-minute-resampled bars, identical opens and closes, four high
prices differing by at most $129.72, two low prices differing by at most
$85.87, 38 volume bars differing by at most 755.96 BTC, and two boundary bars.
This is recorded in `docs/DEVIATIONS.md`.

### 3.2 Equity data

EODHD adjusted daily data cover AAPL.US, TSLA.US, AMZN.US, and VTI.US from
their available starts through 2026-10-20. EODHD 1-hour data are available
only from 2026-06-24 through 2026-10-20 (664 bars, 83 trading days). The
intraday equity results are therefore exploratory and are not used for
annualized claims.

| Asset | Rows | Start | End | Missing (est.) | Max business-day gap | Corwin–Schultz median |
|---|---:|---|---|---:|---:|---:|
| AAPL.US | 6,740 | 2000-01-03 | 2026-10-20 | 252 | 4 | 10.15 bp |
| TSLA.US | 4,103 | 2010-06-29 | 2026-10-20 | 153 | 2 | 4.12 bp |
| AMZN.US | 6,740 | 2000-01-03 | 2026-10-20 | 252 | 4 | 13.51 bp |
| VTI.US | 6,385 | 2001-05-31 | 2026-10-20 | 239 | 4 | 0.00 bp |

The missing counts are exchange holidays, not data defects. The Corwin–Schultz
medians are 10.15 bp for AAPL, 4.12 bp for TSLA, 13.51 bp for AMZN, and 0.00
bp for VTI. The equity base cost of 4 bp is therefore below the median
high-low spread estimate for AAPL and AMZN; equity results may be optimistic.

### 3.3 Rates and live data

FRED `DTB3` was requested for a risk-free reference, but the endpoint timed
out from the research host. The series is optional, is recorded as unavailable
in the fetch manifest, and is not used in any reported result. No Sharpe ratio
in this paper is excess-return adjusted; this is a documented limitation.

The live check reads public last-price endpoints from Kraken, Coinbase, and
OKX. No API keys are used. The snapshot analyzed below was taken on
2026-10-21 at 10:36:04 UTC. The signal timestamp is 10:00 UTC, so the snapshot
is a 36-minute-lagged check of venue agreement and shadow-signal state, not a
synchronized tick test.

---

## 4. Design and Estimators

### 4.1 Pre-registered hypotheses

The hypotheses were frozen on 2026-10-21 before the first return series was
computed. The full text is in `PREREGISTRATION.md`; the short forms are:

| ID | Pre-registered prediction |
|---|---|
| H1 | Per-bar volatility scales as the square root of bar length; annualized volatility is approximately flat. |
| H2 | Net Sharpe is non-increasing in decision frequency once costs are charged; the gross-to-net gap is largest at 5m and smallest at 1d. |
| H3 | On average, an HTF filter does not increase net Sharpe; any improvement is family/regime-specific and does not survive PBO/DSR. |
| H4 | Confluence reduces turnover and volatility but does not reliably raise net Sharpe. |
| H5 | The best in-sample trial has DSR below 0.95 and PBO above 0.25; the winner is not credible out of sample. |
| H6 | A binding decision budget changes the best feasible timeframe, and regret rises as the budget falls. |
| H7 | The direction of H1–H3 transfers to daily US equities, with smaller cost effects. |
| H8 | Independent venues agree within 50 bp and shadow signals agree more often than chance; the hash-chained log verifies. |

The decision rule is strict: a claim is “supported” only if the pre-specified
direction is observed and (a) the bootstrap 95% interval excludes zero, (b)
the FDR q-value is below 0.05, and (c) DSR exceeds 0.95. H1 and H6 are
assessed descriptively with the same thresholds where applicable. If the sign
is opposite, the claim is rejected. If the direction holds but (b) or (c)
fails, the claim is inconclusive. The 2025–2026 holdout is evaluated once.

### 4.2 Sample split

The in-sample period is 2021-01-01 through 2024-12-31 (1,461 daily
observations). The out-of-sample period is 2025-01-01 through 2026-09-30 (638
daily observations). The holdout is not used for parameter selection. The
trial grid is fixed and exhaustive, so the holdout is genuinely unseen for the
selected configurations.

### 4.3 Trial grid

The ladder is 5m, 15m, 30m, 1h, 4h, and 1d. The HTF map is:

- 1m → (5m, 15m)
- 5m → (15m, 1h)
- 15m → (1h, 4h)
- 30m → (2h, 8h)
- 1h → (4h, 1d)
- 4h → (1d, 1w)
- 1d → (2d, 4d)

The signal families are:

- **MA crossover:** `(fast, slow)` in `{10,20,50} × {50,100,200}`, fast < slow.
- **Donchian breakout:** lookback in `{20,50,100}`.
- **Time-series momentum:** lookback in `{20,50,100}`.

The variants are:

- **`base_only`:** trade the base signal only.
- **`htf_filter`:** trade the base signal only when its sign agrees with the
  first HTF signal.
- **`htf_trigger`:** enter on the first agreement in an HTF run and stay until
  the HTF flips.
- **`confluence3`:** average the base sign with the two HTF signs, with
  fractional position sizes when the average is not ±1.

The grid is 3 symbols × 6 timeframes × 14 configurations × 4 variants =
1,008 trials. Every cell is reported, including failures.

### 4.4 Execution and costs

Let `O_t` be the open of bar `t` and `p_t` the position decided at the close of
bar `t`. The position is effective from `O_{t+1}` to `O_{t+2}`:

```
r_t = p_t * (O_{t+2} / O_{t+1} - 1) - |p_t - p_{t-1}| * c
```

where `c` is the round-trip cost per unit turnover. Costs are charged at the
decision bar, which is conservative relative to charging at execution. A flip
from +1 to −1 costs `2c`, not `4c`. Positions are unit exposure; there is no
leverage and no volatility targeting in the primary run. Shorting is allowed.
No funding is charged because the data are spot.

Crypto costs are 12 bp per unit turnover (10 bp taker + 1 bp half-spread + 1
bp slippage), with sensitivity at 0, 5, 12, 25, and 50 bp. Equity costs are
4 bp in the base case. The finest-scale 1-minute diagnostic uses the same 12
bp crypto cost.

### 4.5 Estimators

**Volatility scaling.** For a random walk, `sigma_bar(h) = sigma_1 sqrt(h)`, so
`log sigma_bar = const + 0.5 log h`. Annualized volatility is
`sigma_bar(h) sqrt(T/h)` and is therefore flat in `h`. The empirical slope of
`log sigma_bar` on `log h` is estimated across the six timeframes; the
annualized slope is the same regression on `log sigma_annual`, with a theory
value of zero.

**Disagreement.** If two zero-mean Gaussian returns have correlation `rho`,
then `P(sign(X) != sign(Y)) = arccos(rho)/pi = 1/2 - arcsin(rho)/pi`. For a
Brownian price, the `h1`- and `h2`-period returns have `rho = sqrt(h1/h2)`.
This gives a parameter-free benchmark for how often a fast and a slow
timeframe should disagree.

**Break-even and optimal horizon.** A trade with per-trade edge
`q sigma sqrt(h)` and cost `c` has net edge `q sigma sqrt(h) - c`. It breaks
even at `h_be = (c/(q sigma))^2`. Annualized net edge per unit time is
`(q sigma sqrt(h) - c)/h`; maximizing over `h` gives `h* = 4 h_be`. The
cost-optimal horizon is four times the break-even horizon.

**Decision budget.** A trader who can act at most `kappa` times per week cannot
use a timeframe shorter than `10080/kappa` minutes. The budget-constrained
choice is the best net-Sharpe trial among timeframes with `10080/h <= kappa`.
Regret is the Sharpe difference from the unconstrained best.

**Deflated Sharpe.** With `N` trials, cross-trial Sharpe standard deviation
`sigma_SR`, skewness `gamma_3`, and kurtosis `gamma_4`, the expected maximum
Sharpe under the null is
`SR_0 = sigma_SR ((1 - gamma) z_{1-1/N} + gamma z_{1-1/(Ne)})` with
`gamma = 0.5772`. The deflated Sharpe is
`Phi((SR - SR_0) sqrt(T-1) / sqrt(1 - gamma_3 SR + (gamma_4-1) SR^2/4))`.
`DSR > 0.95` is the credibility threshold.

**PBO/CSCV.** Split the `T × N` return matrix into `S = 12` contiguous blocks.
For each of the 924 choices of in-sample blocks, select the trial with the
highest in-sample Sharpe and record its out-of-sample rank. PBO is the fraction
of splits with negative logit rank.

**Reality Check and SPA.** White’s statistic is `sqrt(T) max_i mean(r_i)`,
compared with a stationary bootstrap of centered returns. The SPA-style
statistic studentizes each column and truncates negative values at zero. The
implementation recenters every column, the conservative “all-hypotheses”
variant.

**Bootstrap.** Blocks have geometric length with mean 20 trading days, 500
replications, percentile intervals. This preserves volatility clustering and
cross-sectional dependence better than i.i.d. resampling.

**Capacity.** If per-trade edge is `e` and impact is `k sigma_d
sqrt(participation)`, the largest participation with non-negative net edge is
`p* = (e/(k sigma_d))^2`, and capacity is `p* ADV`, capped at ADV, with
`k = 0.10`. This is an upper bound; it ignores competition, information decay,
and borrow constraints.

---

## 5. Results

### 5.1 H1: Sampling is real; annualized risk is approximately flat

The per-bar volatility slope is 0.486 for BTCUSDT (t = 208.5, R² = 0.9999),
0.494 for ETHUSDT (t = 131.7, R² = 0.9997), and 0.484 for SOLUSDT (t = 731.0,
R² = 0.99999). These are close to the random-walk value of 0.5. The annualized
slope is −0.0142 for BTC (t = −6.07), −0.0063 for ETH (t = −1.68), and −0.0162
for SOL (t = −24.5). The economic magnitude is small relative to the per-bar
effect.

| Asset | Annualized vol 5m | 1h | 4h | 1d | Per-bar slope | Annualized slope |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 0.620 | 0.581 | 0.576 | 0.571 | 0.486 | −0.0142 |
| ETHUSDT | 0.802 | 0.761 | 0.755 | 0.775 | 0.494 | −0.0063 |
| SOLUSDT | 1.190 | 1.135 | 1.110 | 1.087 | 0.484 | −0.0162 |

H1 is supported descriptively: higher timeframes are not “less noisy” in
annualized terms. A 5m bar has smaller variance than a 1d bar, but that is the
square-root sampling identity, not a reduction in annual risk. The slight
negative annualized slopes for BTC and SOL are consistent with microstructure
noise at high frequency; the ETH slope is not statistically distinguishable
from zero at conventional levels.

![Figure 3: Volatility scaling](figures/fig3_vol_scaling.png)

**Figure 3.** Per-bar and annualized volatility scaling across the timeframe
ladder. The per-bar slope is close to 0.5; the annualized series is
approximately flat.

### 5.2 H2: Costs, not sampling noise, dominate the timeframe decision

The cross-timeframe pattern is large and monotone over most of the ladder. The
5m median net Sharpe is −3.21; the 4h median is +0.39. Median annual cost drag
falls from 80.1% at 5m to 0.8% at 1d, while median turnover falls from 1,991
to 7.2 turns per year.

| Timeframe | n | Mean IS net SR | Median IS net SR | Median gross SR | Median cost drag | Median turnover/yr |
|---|---:|---:|---:|---:|---:|---:|
| 5m | 168 | −5.375 | −3.207 | 0.244 | 0.801 | 1,991.5 |
| 15m | 168 | −1.363 | −0.596 | 0.326 | 0.511 | 603.2 |
| 30m | 168 | −0.392 | −0.111 | 0.384 | 0.312 | 291.8 |
| 1h | 168 | 0.101 | 0.175 | 0.431 | 0.168 | 143.8 |
| 4h | 168 | 0.414 | 0.387 | 0.447 | 0.039 | 27.8 |
| 1d | 168 | 0.385 | 0.347 | 0.273 | 0.008 | 7.2 |

The strict “non-increasing in frequency” form is not exact: 4h has a higher
median net Sharpe than 1d (0.387 versus 0.347), and the 4h gross Sharpe is
also higher (0.447 versus 0.273). The 4h hump is a gross-signal effect, not a
cost effect. The broad direction is nonetheless clear: 5m and 15m are
dominated by costs; 1h is marginal; 4h and 1d are the only timeframes with
positive median in-sample net Sharpe. The gross-to-net gap is largest at 5m
and smallest at 1d, as predicted.

Out of sample, every timeframe has a negative median net Sharpe: −3.843 at
5m, −1.095 at 15m, −0.638 at 30m, −0.382 at 1h, −0.028 at 4h, and −0.180 at
1d. The 4h row is the least negative, not a profitable one. H2 is therefore
supported descriptively in its broad cost direction, but not as a claim that
any timeframe is a reliable out-of-sample winner. Under the strict decision
rule, the cross-timeframe median is not a selected-trial claim, so it is
reported as descriptive support rather than a confirmatory edge.

![Figure 1: Net Sharpe by timeframe](figures/fig1_sharpe_by_timeframe.png)

**Figure 1.** In-sample net Sharpe by timeframe, all 168 trials per timeframe.
The 5m and 15m distributions are shifted far below zero; 4h and 1d are the
only medians above zero.

![Figure 2: Cost sensitivity](figures/fig2_cost_sensitivity.png)

**Figure 2.** Full-sample cost sensitivity for the top trials. This figure is
explicitly full-sample and is not used for the holdout claim. The vertical
line marks the 12 bp base cost.

### 5.3 H3 and H4: HTF filters and confluence help on average, but not by creating alpha

The pre-registered H3 and H4 predicted that HTF filters and confluence would
not improve net Sharpe. The paired evidence rejects the negative form of both
claims. Across 252 matched pairs, the HTF filter raises net Sharpe by 0.527 on
average (median 0.287; 80.6% of pairs positive; t = 9.61). The three-way
confluence raises it by 0.936 (median 0.458; 83.7% positive; t = 9.80). The
HTF-trigger variant raises it even more (mean 1.633; median 0.526; 80.2%
positive; t = 8.04), but with a different exposure profile.

| Variant | Pairs | Mean Δnet IS | Median Δnet IS | % positive | t | Mean Δgross | Median vol ratio | Median turnover ratio | OOS mean Δnet | OOS median Δnet | OOS % positive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `htf_filter` | 252 | 0.527 | 0.287 | 80.6% | 9.61 | 0.066 | 0.803 | 0.620 | 0.487 | 0.260 | 68.3% |
| `htf_trigger` | 252 | 1.633 | 0.526 | 80.2% | 8.04 | 0.027 | 0.959 | 0.235 | 1.782 | 0.778 | 73.0% |
| `confluence3` | 252 | 0.936 | 0.458 | 83.7% | 9.80 | 0.127 | 0.680 | 0.432 | 0.812 | 0.432 | 69.0% |

The mechanism is visible in the decomposition. The HTF filter’s mean gross
Sharpe improvement is only 0.066, while its median volatility ratio is 0.803
and its median turnover ratio is 0.620. The confluence variant’s gross
improvement is larger (0.127), but its volatility ratio is 0.680 and turnover
ratio 0.432. In other words, the overlays are primarily risk-control devices:
they cut exposure, volatility, and trading, and the net Sharpe improvement is
largely a denominator effect. They are not strong standalone alpha generators.

The effect is strongly timeframe-dependent. For `htf_filter`, the mean Δnet is
+1.66 at 5m, +0.72 at 15m, +0.45 at 30m, +0.26 at 1h, +0.11 at 4h, and −0.027
at 1d. For `confluence3`, the corresponding values are +2.95, +1.26, +0.78,
+0.42, +0.18, and +0.022. The overlays help most where the base signal is
noisiest and most expensive to trade. At 1d, where turnover is already low,
the benefit is negligible or slightly negative.

H3 is therefore **rejected in its negative-average form**, but its secondary
claim—that any improvement does not survive PBO/DSR—is supported. H4 is
**rejected**: confluence does reliably raise net Sharpe on average, but the
improvement does not make the selected winner credible out of sample.

![Figure 4: Timeframe disagreement](figures/fig4_disagreement.png)

**Figure 4.** Observed sign disagreement versus the Brownian benchmark for the
12 symbol/pair combinations. The observed values sit close to the theoretical
curve; disagreement is not a standalone edge.

### 5.4 H5: The winner is not credible out of sample

The best in-sample trial is
`SOLUSDT|4h|ma|confluence3|fast10_slow50`. Its in-sample Sharpe is 1.542, its
in-sample annual return is 139.4%, and its in-sample max drawdown is −60.1%.
Out of sample, the Sharpe is −0.498, the annual return is −29.0%, and the max
drawdown is −52.9%. The trial has 356 trades, 44.1 turns per year, a 44.7% win
rate, and a break-even cost of 217.4 bp. The 12 bp base cost is not the reason
it fails out of sample.

| Metric | In-sample | Out-of-sample |
|---|---:|---:|
| Sharpe (net) | 1.542 | −0.498 |
| Annual return (net) | 139.4% | −29.0% |
| Annual volatility | 73.8% | 46.9% |
| Max drawdown | −60.1% | −52.9% |
| Days | 1,461 | 638 |
| Trades | 356 | — |
| Turnover/yr | 44.1 | — |
| Break-even cost | 217.4 bp | — |
| DSR | 8.16 × 10⁻⁹⁶ | — |

The full-sample row for the same trial has a Sharpe of 1.078 and an annual
return of 65.4%. That row is not the in-sample result and should not be used
as one; it is reported here only to prevent confusion with
`results/report.json["stats"]["best_is_trial"]`.

The top-ten in-sample trials tell the same story. Only 3 of the 10 have a
positive out-of-sample Sharpe, and none has an out-of-sample confidence
interval that excludes zero.

| Rank | Trial | IS SR | OOS SR | OOS 95% CI |
|---:|---|---:|---:|---|
| 1 | `SOLUSDT\|4h\|ma\|confluence3\|fast10_slow50` | 1.542 | −0.498 | [−2.094, 0.727] |
| 2 | `SOLUSDT\|1h\|ma\|confluence3\|fast50_slow200` | 1.485 | 0.092 | [−1.132, 1.149] |
| 3 | `SOLUSDT\|1h\|ma\|htf_filter\|fast50_slow200` | 1.382 | 0.403 | [−0.805, 1.456] |
| 4 | `SOLUSDT\|1h\|donchian\|confluence3\|lookback100` | 1.376 | −0.663 | [−1.974, 0.402] |
| 5 | `SOLUSDT\|1d\|donchian\|confluence3\|lookback20` | 1.374 | −0.441 | [−1.634, 0.702] |
| 6 | `SOLUSDT\|1h\|ma\|confluence3\|fast10_slow50` | 1.341 | −0.375 | [−1.826, 0.942] |
| 7 | `SOLUSDT\|15m\|ma\|confluence3\|fast50_slow200` | 1.307 | −0.078 | [−1.441, 1.143] |
| 8 | `SOLUSDT\|4h\|ma\|confluence3\|fast50_slow200` | 1.290 | −0.316 | [−1.587, 1.118] |
| 9 | `SOLUSDT\|4h\|ma\|htf_filter\|fast10_slow50` | 1.286 | 0.035 | [−1.362, 1.207] |
| 10 | `SOLUSDT\|4h\|donchian\|confluence3\|lookback100` | 1.279 | −0.817 | [−2.080, 0.292] |

The selection-bias diagnostics are unambiguous:

| Diagnostic | Value | Interpretation |
|---|---:|---|
| Maximum trial DSR | 1.36 × 10⁻⁹¹ | Essentially zero credibility under the null. |
| Best-trial DSR | 8.16 × 10⁻⁹⁶ | The winner itself is even further from credibility. |
| Median-trial DSR | 3.07 × 10⁻¹¹⁶ | The typical trial is not credible either. |
| Trials with DSR > 0.95 | 0 / 1,008 | None clears the pre-registered threshold. |
| PBO | 0.156 | 15.6% probability of backtest overfitting; below 0.25. |
| PBO logit mean | 1.050 | OOS rank is positive on average across CSCV splits. |
| PBO degradation slope | −0.531 | Performance degrades as IS rank improves. |
| PBO prob. OOS loss | 0.253 | About one in four splits selects a loser. |
| PBO OOS Sharpe median | 0.024 | The selected trial is near zero in the median split. |
| Reality Check p | 0.246 | Cannot reject no predictability. |
| SPA p | 0.210 | Cannot reject no predictability. |
| IS BH significant | 237 | But only 5 are positive; 232 are negative. |
| OOS BH significant | 214 | All 214 are negative; 0 are positive. |
| IS–OOS Spearman | 0.709 | High overall, driven by extreme losers. |
| IS–OOS Spearman, IS > 0 | −0.030 | No persistence among winners. |
| Top-decile OOS mean | −0.191 | The top 10% by IS loses out of sample. |
| Top-decile OOS positive | 30.7% | Fewer than one in three are positive. |

H5 is **not supported as a conjunction**. The DSR clause passes (the winner is
not credible), but the PBO clause fails (0.156 is below the 0.25 threshold).
The correct conclusion is not “PBO certifies the winner.” It is “the winner is
not credible, and PBO alone would not have caught it.” The holdout and the DSR
do the heavy lifting.

The aggregate BH count is easy to misread. The 237 in-sample significant
trials are mostly significant *losers*: 232 negative, 5 positive. The 214
out-of-sample significant trials are all negative. A large count of
“significant” trials is therefore not evidence of a profitable family; it is
evidence that the grid contains many reliably bad configurations, especially
at 5m.

![Figure 5: Probability of backtest overfitting](figures/fig5_pbo.png)

**Figure 5.** CSCV distribution of out-of-sample ranks for the 1,008 trials.

![Figure 6: Top in-sample equity curves](figures/fig6_equity.png)

**Figure 6.** Top-five in-sample equity curves. The vertical line marks the
2025-01-01 holdout boundary. The curves are selected on in-sample performance
and are shown out of sample only for evaluation.

### 5.5 H6: Decision budgets change the feasible optimum

The decision-budget analysis asks what happens when a trader can act only
`kappa` times per week. BTCUSDT is robust: 1d is the unconstrained best at
every budget, with zero regret. ETHUSDT and SOLUSDT are budget-sensitive. At
21 actions per week, ETHUSDT must use 1d instead of 30m and gives up 0.095
Sharpe; at 42–168 actions it uses 4h and gives up 0.039; at 336 or more it can
use 30m with zero regret. SOLUSDT must use 1d at 21 actions and gives up 0.167;
at 42 or more it can use 4h with zero regret.

| Symbol | κ/week | Selected TF | Selected net SR | Unconstrained TF | Unconstrained net SR | Regret |
|---|---:|---|---:|---|---:|---:|
| BTCUSDT | 21 | 1d | 0.907 | 1d | 0.907 | 0.000 |
| BTCUSDT | 42–1,008 | 1d | 0.907 | 1d | 0.907 | 0.000 |
| ETHUSDT | 21 | 1d | 0.493 | 30m | 0.588 | 0.095 |
| ETHUSDT | 42–168 | 4h | 0.549 | 30m | 0.588 | 0.039 |
| ETHUSDT | 336–1,008 | 30m | 0.588 | 30m | 0.588 | 0.000 |
| SOLUSDT | 21 | 1d | 1.374 | 4h | 1.542 | 0.167 |
| SOLUSDT | 42–1,008 | 4h | 1.542 | 4h | 1.542 | 0.000 |

H6 is **partially supported descriptively**. Budget constraints matter for
ETH and SOL, and regret is largest at the tightest budget. BTC is already at
1d, so the constraint is not binding. The result is a useful bridge between
the statistical timeframe ranking and the practical question of how often a
trader can act.

### 5.6 H7: Equity evidence is directionally consistent but not confirmatory

The equity extension uses 80 daily rows (64 at 1d, 16 at 1w). Median net
Sharpe is 0.367 at 1d and 0.401 at 1w; median gross Sharpe is 0.369 and 0.404;
median annual cost drag is 0.00094 and 0.00033. Costs are negligible relative
to the crypto sample, as expected.

| Asset | 1d rows | 1d median net SR | 1w rows | 1w median net SR | 1d median cost drag | 1w median cost drag |
|---|---:|---:|---:|---:|---:|---:|
| AAPL.US | 16 | 0.676 | 4 | 0.692 | 0.00089 | 0.00036 |
| TSLA.US | 16 | 0.287 | 4 | 0.410 | 0.00117 | 0.00046 |
| AMZN.US | 16 | 0.264 | 4 | 0.327 | 0.00094 | 0.00032 |
| VTI.US | 16 | 0.369 | 4 | 0.368 | 0.00088 | 0.00032 |

The equity variant effects point in the same direction as the crypto results:
`htf_filter` mean Δnet +0.248 (median +0.273; 93.8% positive), `htf_trigger`
+0.295 (+0.343; 81.3%), and `confluence3` +0.335 (+0.360; 100%). Gross
improvements are almost the same as net improvements, confirming that equity
costs are small. Volatility ratios are 0.709, 0.903, and 0.672; turnover
ratios are 0.520, 0.127, and 0.392.

The top equity rows are not timing evidence. The best AAPL 1d row has one
trade and a Sharpe of 0.972; the best AAPL 1w row has two trades and a Sharpe
of 0.957. These are buy-and-hold-like exposures with a trend filter, not
high-frequency signals. The top TSLA intraday rows are even more fragile: the
1h Donchian row has five trades and an annualized return of 30.27 over 83
days.

H7 is **mixed/partial**. The H2 cost direction and the H3 filter direction
transfer to equities, but H1 is not separately estimated on equities, the
sample is only four assets, the weekly timeframe was added beyond the daily
H7 grid, and the top rows are dominated by long-equity drift. The result is
consistent with the crypto mechanism, not a confirmation of a deployable
equity strategy.

### 5.7 H8: Venue tolerance passes; shadow signals disagree; sample too small

The live snapshot passes the venue-tolerance check. Kraken prints 83,253.0,
Coinbase 83,249.47, and OKX 83,349.4, for a maximum deviation of 12.00 bp,
well inside the 50 bp tolerance. The signal snapshot is as of 10:00 UTC; the
quote snapshot is 36 minutes later. The 1h layer has MA +1 and TSMOM +1; the
4h layer has MA −1 and TSMOM +1; the 1d layer has MA +1 and TSMOM +1. The
layers are not aligned: there are two distinct signs and an agreement count of
two. The payload hash is
`d2d081702d1d9f64249bd8ccace883ff669ce1fcaaf7d9d568ed96921e0c5a70`. The
hash-chained log verifies three records; the head hash is
`0550ef2fa6c69870f713a66549c3dc0dd3c90c007fbc6477a9818473dfbb6657`.

| Check | Result |
|---|---|
| Venues | Kraken 83,253.0; Coinbase 83,249.47; OKX 83,349.4 |
| Max deviation | 12.00 bp |
| Tolerance | 50 bp |
| Within tolerance | Yes |
| Signal timestamp | 2026-10-21 10:00 UTC |
| 1h layer | MA +1, TSMOM +1 |
| 4h layer | MA −1, TSMOM +1 |
| 1d layer | MA +1, TSMOM +1 |
| Aligned | No |
| Distinct signs | 2 |
| Agreement count | 2 |
| Log records | 3 |
| Log valid | Yes |

H8 is **partial**. The venue-agreement and hash-chain components pass. The
“agree more often than chance” component cannot be tested with three records;
the observed snapshot actually disagrees across 1h and 4h. Early log records
had shorter warm-up windows (31 and 181 daily bars); the final record uses 720
bars. The live result is a plumbing and data-integrity check, not a
statistical test of signal agreement.

### 5.8 Auxiliary diagnostics: disagreement, mutual information, finest scale, and capacity

**Disagreement.** Observed sign disagreement is close to the Brownian
benchmark. For BTC, the 5m-vs-1h pair disagrees 0.425 of the time versus a
theory value of 0.407; 1h-vs-4h is 0.356 versus 0.333; 1h-vs-1d is 0.455
versus 0.435; 4h-vs-1d is 0.394 versus 0.366. ETH and SOL are similar. The
conditional forward returns do not show an economically large agreement
premium: BTC agree 0.000941 versus disagree 0.000910; ETH 0.001467 versus
0.001312; SOL 0.003661 versus 0.003697. Disagreement is a description of
sampling, not a standalone signal.

**Mutual information.** The permutation tests use 200 replications. The
own-timeframe MI is significant for all three assets (p ≈ 0.005), and the
HTF-to-LTF MI is significant for BTC and ETH (p ≈ 0.005) but not SOL
(p = 0.134). The disagreement-to-future MI is not significant at the 5% level
for BTC (p = 0.080), ETH (p = 0.134), or SOL (p = 0.129). This is consistent
with the conditional-return result: multi-timeframe disagreement contains
little predictive information beyond the marginal distributions.

**Finest scale.** The 1-minute diagnostic is a cost-drag illustration, not a
viable strategy. At 12 bp, 1m TSMOM has a net Sharpe of −85.76, an annual net
return of −100%, a cost drag of 98.8%, a break-even cost of 0.28 bp, and
70,764 turns per year. The 1m MA has a net Sharpe of −29.45 and a 52.2% cost
drag. Even the best 1m row is deeply negative. At 4h and 1d, the same signal
families are near zero to modestly positive, which is the cost-horizon result
in its starkest form.

| Strategy | Net SR | Annual net | Cost drag | Break-even | Turnover/yr |
|---|---:|---:|---:|---:|---:|
| 1m TSMOM `base_only` | −85.76 | −100% | 98.8% | 0.28 bp | 70,764 |
| 1m MA `base_only` | −29.45 | −100% | 52.2% | −0.29 bp | 15,002 |
| 1m Donchian `base_only` | −24.65 | −100% | 22.1% | −1.10 bp | 11,753 |
| 5m TSMOM `base_only` | −24.37 | −100% | 51.1% | −0.29 bp | 15,554 |
| 4h MA `base_only` | 0.505 | 13.6% | 7.6% | 79.8 bp | 53.7 |
| 1d TSMOM `base_only` | 0.512 | 13.9% | 5.7% | 87.1 bp | 40.7 |

**Capacity.** The capacity estimates are upper bounds and are mostly clipped
at ADV. Of 24 rows, 20 are at the ADV cap. The top BTC 1d rows are all
$1.927bn capacity, the ETH 30m row is $1.088bn, and the 4h/1h rows are also
clipped. The median capacity by timeframe is not monotone: 15m $98.7m, 1h
$447.7m, 30m $704.4m, 4h $1.088bn, 1d $1.927bn. This is a warning about the
capacity model, not evidence that 30m is more deployable than 1h. The model
ignores competition, information decay, and borrow constraints, and the ADV
cap binds for most of the selected trials.

![Figure 7: Capacity](figures/fig7_capacity.png)

**Figure 7.** Estimated capacity (capped at ADV) versus decision timeframe.
Most points are at the ADV cap, so the figure is an upper-bound diagnostic,
not a precise deployable-notional estimate.

![Figure 8: Finest-scale diagnostic](figures/fig8_finest_scale.png)

**Figure 8.** One-minute net Sharpe diagnostic. The 1m strategies are
dominated by costs; the figure is included to make the cost-horizon mechanism
visible, not to propose a 1m strategy.

---

## 6. Discussion

### 6.1 Timeframe is a parameter, not a truth

The most important result is negative: there is no timeframe that is
“more reliable” in the sense implied by trading education. Annualized
volatility is approximately flat across the ladder, and the per-bar scaling
exponent is close to 0.5. A higher timeframe gives fewer, larger bars; it does
not give a lower annual risk. The apparent smoothness of a 4h or 1d chart is a
display artifact of sampling, not a property of the return process.

What does change with the timeframe is the cost-to-signal ratio. At 5m, the
median strategy turns over 1,991 times per year and loses 80.1% of annual
return to costs. At 1d, turnover is 7.2 turns per year and cost drag is 0.8%.
The cost-optimal region is 4h–1d. This is the paper’s main prescriptive result:
choose the slowest timeframe that preserves the signal’s decision budget, not
the fastest timeframe that feels informative.

### 6.2 HTF filters are risk control, not alpha

The pre-registered H3/H4 expected HTF filters and confluence to fail. They do
not fail on average: the filter improves net Sharpe in 80.6% of pairs, and
confluence in 83.7%. But the decomposition shows why. The filter’s gross
Sharpe improvement is only 0.066, while its volatility and turnover ratios are
0.803 and 0.620. The overlay is mostly a position-sizing and trade-reduction
device. It helps most at 5m, where the base signal is noisy and expensive, and
barely helps at 1d, where turnover is already low.

This distinction matters for practice. An HTF filter can be a sensible risk
overlay even if it does not create alpha. It can reduce drawdowns, smooth
equity curves, and lower transaction costs. It should not be sold as a
standalone edge, and it should not be evaluated only on gross returns. The
paper’s evidence supports “use the higher timeframe to control risk and
turnover,” not “the higher timeframe knows the truth.”

### 6.3 Selection is the binding constraint

The grid produces a spectacular in-sample winner: a 1.542 Sharpe on SOL 4h
with a 139% annual return. Out of sample it loses 29% annualized and has a
−0.498 Sharpe. The DSR is essentially zero, the Reality Check and SPA p-values
are 0.246 and 0.210, and only 3 of the top 10 IS trials have positive OOS
Sharpe. The winner is not credible.

The aggregate rank correlation is a trap. The overall IS–OOS Spearman is
0.709, which sounds like persistence. But among trials with positive IS
Sharpe, the correlation is −0.030. The overall number is driven by the extreme
5m losers: a strategy that loses 80% a year in sample tends to lose out of
sample too. That is persistence of failure, not persistence of edge. The top
decile by IS Sharpe has a negative OOS mean (−0.191) and only a 30.7% positive
rate. A researcher who reports only the overall rank correlation would tell
the wrong story.

The BH counts reinforce the point. There are 237 in-sample BH-significant
trials, but only 5 are positive; 232 are negative. Out of sample, all 214
BH-significant trials are negative. A large number of significant trials is
not a portfolio of edges. It is a reminder that the grid contains many
reliably bad high-frequency configurations.

### 6.4 Decision budgets and the practical optimum

The decision-budget analysis turns the statistical ranking into a practical
rule. BTC is already at 1d, so a budget constraint does not bind. ETH and SOL
would prefer 30m or 4h in the unconstrained ranking, but at 21 actions per
week they must use 1d and give up 0.095 and 0.167 Sharpe, respectively. At 42
actions per week, ETH can use 4h and SOL can use 4h with zero regret. The
practical message is that the “best” timeframe depends on how often the trader
can actually act, not just on the backtest Sharpe.

### 6.5 External validity

The equity extension is directionally consistent: HTF filters and confluence
improve net Sharpe, and costs are negligible. But the top equity rows are
buy-and-hold-like, the sample is four assets, and the weekly timeframe was
added beyond the pre-registered daily H7 grid. The intraday equity window is
only 83 days. The equity evidence should be read as a robustness check on the
mechanism, not as a confirmation of a deployable equity strategy.

The live check is a plumbing check. The three venues agree within 12 bp, the
hash chain verifies, and the shadow layers produce a non-aligned state. That
is useful operationally, but three records cannot test “agree more often than
chance.” The live result is partial by design.

---

## 7. Limitations

1. **Survivorship and asset selection.** The crypto sample is three large USDT
   pairs that survived to 2026. The results do not generalize to delisted or
   small-cap tokens.

2. **Spot only, no funding.** The data are spot, and no funding or borrow cost
   is charged. Perpetual futures could change the short-side economics.

3. **No risk-free adjustment.** Sharpe ratios are not excess-return adjusted
   because FRED `DTB3` was unavailable. The effect is small relative to the
   spread of trial Sharpe ratios, but it is a documented limitation.

4. **One crypto regime.** The sample covers 2021–2026, including a severe bear
   market, a recovery, and a strong 2025–2026 ETH trend. The OOS winner is an
   ETH trend strategy; that is a regime observation, not a structural edge.

5. **Native 5m versus 1m resampling.** ETH and SOL use native 5m bars because
   1m data were downloaded only for BTC. The BTC cross-check is close, but the
   ETH/SOL microstructure may differ.

6. **Equity intraday sample is short.** The 1h equity window is 83 trading
   days and 664 bars. Annualized intraday equity numbers are exploratory and
   should not be interpreted as stable performance.

7. **Reduced equity grid.** The equity daily grid uses four configurations and
   the weekly grid uses `base_only`. This is a compute-budget compromise, not
   the full crypto grid.

8. **Equity costs may be optimistic.** The 4 bp base cost is below the
   Corwin–Schultz median for AAPL and AMZN. The equity results are therefore
   more optimistic than the crypto results.

9. **Capacity is an upper bound.** The capacity model ignores competition,
   information decay, and borrow constraints. Twenty of 24 rows are clipped at
   ADV, so the capacity ranking is not informative across timeframes.

10. **Live sample is tiny.** Three records cannot test signal agreement. The
    live check is an operational validation, not a statistical one.

11. **DSR and PBO are approximations.** DSR uses a normal approximation and
    cross-trial dispersion; PBO/CSCV assumes exchangeability of the return
    matrix. Both are useful, but neither is a proof of absence of edge.

12. **No transaction-level latency model.** Execution is next-open with a
    one-bar lag. Real latency, queue position, and partial fills are not
    modeled.

---

## 8. Reproducibility

### 8.1 Environment

The reference environment is Python 3.12 with the versions pinned in
`requirements.txt` and `pyproject.toml`. The random seed is `20261021`. All
figures use the non-interactive `Agg` backend.

### 8.2 Commands

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
tfv all
```

or, equivalently:

```bash
make install
make all
```

The pipeline order is:

```
fetch -> audit -> multiscale -> backtest -> finest -> stats ->
capacity -> equities -> surrogates -> live -> figures -> report
```

`make all` runs every stage, including the live check once. The live stage
requires network access to Kraken, Coinbase, and OKX. For an offline
reproduction, run the earlier stages individually and skip `live`; the
confirmatory results do not depend on the live snapshot.

Docker:

```bash
make docker
# or
docker compose run --rm research
```

The `live-shadow` service is available under the `live` profile for continuous
shadow logging:

```bash
docker compose --profile live up live-shadow
```

### 8.3 Artifacts

The machine-readable report is `results/report.json`. It contains the audit,
multiscale diagnostics, statistics, capacity, surrogate tests, equity results,
finest-scale results, timeframe-family summaries, TBMT, and environment
metadata. If a hand-written sentence and an artifact disagree, the artifact is
authoritative.

| Artifact | Contents |
|---|---|
| `results/report.json` | Top-level machine-readable report. |
| `results/stats.json` | DSR, PBO, RC, SPA, BH, variant effects, timeframe effects, top-IS CIs, descriptive top-OOS list. |
| `results/trials_with_dsr.csv` | All 1,008 trials with IS/OOS metrics and DSR. |
| `results/trials.parquet` | Raw trial return matrix. |
| `results/top_bootstrap_ci.csv` | Top-10 IS trials with OOS bootstrap intervals. |
| `results/timeframe_family.csv` | Per-symbol/timeframe best and median performance. |
| `results/capacity.csv` | Capacity estimates and ADV caps. |
| `results/tbmt.csv` | Decision-budget results. |
| `results/equities_daily.csv` | Daily and weekly equity results. |
| `results/equities_intraday.csv` | Exploratory intraday equity results. |
| `results/equity_effects.json` | Equity variant effects. |
| `results/live_snapshot.json` | Live venue and shadow-signal snapshot. |
| `results/live_shadow.jsonl` | Hash-chained live log (not committed). |
| `figures/fig1..fig8` | Publication figures. |

### 8.4 Deviations

`docs/DEVIATIONS.md` is the append-only log. The main deviations are the
optional FRED series, the short equity intraday window, the native 5m data,
the live ticker endpoints, the timestamp-unit and Corwin–Schultz fixes, the
IS/OOS statistics implementation, the reduced equity grid, and the artifact
key rename. None of these changes the hypotheses, the 1,008-trial grid, the
sample dates, the cost model, or the one-time holdout rule.

---

## 9. Conclusion

Timeframe is a parameter, not a truth. The square-root sampling identity is
real, but it does not make higher timeframes less risky in annualized terms.
Costs dominate the timeframe decision: 5m and 15m are structurally difficult,
1h is marginal, and 4h–1d is the cost-optimal region. HTF filters and
confluence improve average net Sharpe, but mainly by reducing volatility and
turnover, not by creating gross alpha. The best in-sample trial collapses out
of sample, the deflated Sharpe is essentially zero, and the top decile by
in-sample Sharpe loses money out of sample. The practical prescription is to
choose the slowest timeframe that preserves the decision budget, use HTF
filters as risk controls, and treat any large-grid winner as a hypothesis to
be tested on an untouched holdout—not as a discovery.

---

## Appendix A: Hypothesis Verdicts

| ID | Verdict | Evidence |
|---|---|---|
| H1 | Supported descriptively | Per-bar slope 0.484–0.494; annualized vol approximately flat; BTC/SOL slight negative slopes. |
| H2 | Supported descriptively, strict monotonic form not exact | Net Sharpe rises from 5m to 4h; 4h exceeds 1d; cost drag falls monotonically with timeframe; all OOS medians negative. |
| H3 | Rejected in negative-average form; secondary PBO/DSR clause supported | HTF filter mean Δnet +0.527, 80.6% positive; gross Δ only +0.066; winner fails DSR/PBO. |
| H4 | Rejected | Confluence mean Δnet +0.936, 83.7% positive; improvement is risk/turnover-driven. |
| H5 | Not supported as conjunction | DSR < 0.95 passes; PBO 0.156 < 0.25 fails; winner collapses OOS. |
| H6 | Partially supported descriptively | Budget matters for ETH/SOL; BTC always 1d; regret largest at 21/week. |
| H7 | Mixed/partial | Filter direction transfers; costs small; top rows buy-and-hold-like; intraday window 83 days; H1 not separately estimated. |
| H8 | Partial | Venue tolerance and hash chain pass; shadow signals disagree; 3 records cannot test chance agreement. |

## Appendix B: Pre-Registered Decision Rule

A claim is reported as supported only if the pre-specified direction is
observed and (a) the bootstrap 95% interval excludes zero, (b) the FDR q-value
is below 0.05, and (c) DSR exceeds 0.95. If (a) holds but (b) or (c) fails,
the claim is inconclusive. If the sign is opposite, the claim is rejected. H1
and H6 are assessed descriptively with the same thresholds where applicable.
No symbol is dropped. No timeframe is added after seeing results. The
2025–2026 holdout is evaluated once.

## Appendix C: Data and Code Availability

The code, configuration, pre-registration, methods note, deviations log, and
result artifacts are in this repository. The raw data are cached under
`data/cache/` and are not committed. The Binance Vision files are public;
EODHD data are subject to the vendor’s terms. The live endpoints are public and
read-only.

---

## References

1. Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio:
   Correcting for selection bias, backtest overfitting, and non-normality.
   *The Journal of Portfolio Management*, 40(5), 94–107.
   https://doi.org/10.3905/jpm.2014.40.5.094

2. Bailey, D., Borwein, J., López de Prado, M., & Zhu, Q. J. (2016). The
   probability of backtest overfitting. *The Journal of Computational
   Finance*. https://doi.org/10.21314/JCF.2016.322

3. Bandi, F. M., & Russell, J. R. (2008). Microstructure noise, realized
   variance, and optimal sampling. *The Review of Economic Studies*, 75(2),
   339–369. https://doi.org/10.1111/j.1467-937X.2008.00474.x

4. Corwin, S. A., & Schultz, P. (2012). A simple way to estimate bid-ask
   spreads from daily high and low prices. *The Journal of Finance*, 67(2),
   719–760. https://doi.org/10.1111/j.1540-6261.2012.01729.x

5. Georgopoulou, A., & Wang, J. (2017). The trend is your friend: Time-series
   momentum strategies across equity and commodity markets. *Review of
   Finance*. https://doi.org/10.1093/rof/rfw048

6. Hansen, P. R. (2005). A test for superior predictive ability. *Journal of
   Business & Economic Statistics*, 23(4), 365–380.
   https://doi.org/10.1198/073500105000000063

7. Kang, Y., & Ryu, D. (2026). Market-specific confirmation horizons in
   momentum turning-point strategies. *Applied Economics*.
   https://doi.org/10.1080/00036846.2026.2737829

8. Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series
   momentum. *Journal of Financial Economics*, 104(2), 228–250.
   https://doi.org/10.1016/j.jfineco.2011.11.003

9. REFORMS. (2024). Consensus-based recommendations for machine-learning-based
   science. https://reforms.cs.princeton.edu/

10. White, H. (2000). A reality check for data snooping. *Econometrica*,
    68(5), 1097–1126. https://doi.org/10.1111/1468-0262.00152

11. MQL5. (2026). Article 22290: Timeframe-based confirmation in trading
    systems. MQL5.com.

12. Binance Vision. Spot monthly klines.
    https://data.binance.vision/data/spot/monthly/klines/

13. EODHD. End-of-day and intraday market data. https://eodhd.com/

---

*All results in this paper are generated from the artifacts in `results/`.
The machine-readable report is authoritative. See `docs/DEVIATIONS.md` for the
append-only deviation log.*

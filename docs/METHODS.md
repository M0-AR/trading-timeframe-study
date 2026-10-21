# Methods

## Returns, timing, and costs

Let `O_t` be the open of bar `t` and `p_t` the position decided at the close
of bar `t`. The position is effective from `O_{t+1}` to `O_{t+2}`:

```
r_t = p_t * (O_{t+2} / O_{t+1} - 1) - |p_t - p_{t-1}| * c
```

where `c` is the round-trip cost per unit turnover. Costs are charged at the
decision bar, which is conservative relative to charging at execution. A trade
run from bar `i` to `j-1` earns `O_{j+1}/O_{i+1} - 1` before costs; its entry
and exit turnover are separated so that a flip from +1 to -1 costs `2c`, not
`4c`.

## Volatility scaling

For a random walk, `sigma_bar(h) = sigma_1 * sqrt(h)`, so
`log sigma_bar = const + 0.5 log h`. Annualized volatility is
`sigma_bar(h) * sqrt(T/h)` and is therefore flat in `h`. The empirical slope
of `log sigma_bar` on `log h` is estimated with Newey-West standard errors;
the annualized slope is the same regression on `log sigma_annual`, and the
theory value is zero. This separates the sampling identity from the claim
that higher timeframes are "less noisy".

## Sign disagreement

If two zero-mean Gaussian returns have correlation `rho`, then

```
P(sign(X) != sign(Y)) = arccos(rho)/pi = 1/2 - arcsin(rho)/pi.
```

For a Brownian price, the `h1`- and `h2`-period returns have
`rho = sqrt(h1/h2)`. This gives a parameter-free benchmark for how often a
fast and a slow timeframe should disagree. Deviations indicate trending or
mean-reverting microstructure, not a trading edge by themselves.

## Break-even and optimal horizon

A trade with per-trade edge `q * sigma * sqrt(h)` and cost `c` has net edge
`q sigma sqrt(h) - c`. It breaks even at

```
h_be = (c / (q sigma))^2.
```

Annualized net edge per unit time is `(q sigma sqrt(h) - c)/h`. Maximizing
over `h` gives

```
h* = (2c / (q sigma))^2 = 4 h_be.
```

Thus the cost-optimal horizon is four times the break-even horizon, a factor
that is independent of the signal's quality. This is the paper's main
prescriptive result.

## Decision budget

A trader who can act at most `kappa` times per week cannot use a timeframe
shorter than `10080/kappa` minutes. The budget-constrained choice is the
best net-Sharpe trial among timeframes with
`10080/h <= kappa`. Regret is the Sharpe difference from the unconstrained
best.

## Deflated Sharpe ratio

With `N` trials, cross-trial Sharpe standard deviation `sigma_SR`, skewness
`gamma_3`, and kurtosis `gamma_4`, the expected maximum Sharpe under the null
is

```
SR_0 = sigma_SR * ((1 - gamma) * z_{1 - 1/N} + gamma * z_{1 - 1/(N e)})
```

with `gamma = 0.5772`. The deflated Sharpe is

```
DSR = Phi( (SR - SR_0) * sqrt(T - 1) /
          sqrt(1 - gamma_3 SR + (gamma_4 - 1) SR^2 / 4) ).
```

`DSR > 0.95` is the pre-registered credibility threshold.

## Probability of backtest overfitting (CSCV)

Split the `T x N` return matrix into `S` contiguous blocks. For each of the
`C(S, S/2)` choices of in-sample blocks, select the trial with the highest
in-sample Sharpe and record its out-of-sample rank `omega`. The logit
`log(omega/(1-omega))` is computed per split; PBO is the fraction of splits
with negative logit. `S = 12` gives 924 splits.

## Reality Check and SPA

White's statistic is `sqrt(T) * max_i mean(r_i)`, compared with a stationary
bootstrap of the centered returns. The SPA-style statistic studentizes each
column by its standard deviation and truncates negative values at zero. The
implementation recenters every column, which is the conservative
"all-hypotheses" variant; it is documented here because Hansen's SPA uses a
different recentering for the null.

## Stationary bootstrap

Blocks have geometric length with mean 20 trading days. This preserves
volatility clustering and cross-sectional dependence better than i.i.d.
resampling. Confidence intervals use 500 replications and the percentile
method.

## Capacity

If the per-trade edge is `e` and market impact is `k sigma_d sqrt(participation)`,
the largest participation with non-negative net edge is

```
p* = (e / (k sigma_d))^2,
```

and capacity is `p* * ADV`, capped at ADV. This is an upper bound: it ignores
competition, information decay, and borrow constraints.

## Reproducibility

All randomness derives from seed 20261021. The pipeline is idempotent, writes
manifests with SHA-256 hashes, and runs under Docker Compose. Figures are
regenerated from `results/` only. Every number in the paper is traceable to
`results/report.json` or a CSV/JSON artifact in `results/`; the machine-readable
report is authoritative if a hand-written sentence and an artifact disagree.

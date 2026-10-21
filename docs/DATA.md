# Data sources

## Primary: Binance Vision

- URL: `https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{YYYY-MM}.zip`
- Companion checksum: same URL with `.CHECKSUM`, format `<sha256>  <filename>`.
- Symbols: BTCUSDT, ETHUSDT, SOLUSDT. Intervals: 5m (primary), 1m (BTCUSDT
  finest-scale experiment).
- Span: 2021-01 to 2026-09. Each archive is verified before parsing.
- Schema: 12 headerless columns
  `open_time, open, high, low, close, volume, close_time, quote_volume,
  trades, taker_buy_base, taker_buy_quote, ignore`.
- Timestamps are milliseconds through 2024-12 and microseconds from
  2025-01. The loader detects the magnitude and normalizes to milliseconds.
- Integrity: row counts, monotonicity, duplicate timestamps, gaps, non-positive
  prices, and high-low violations are written to `results/data_audit.json`.

## Equities: EODHD demo

- `https://eodhd.com/api/eod/{symbol}?api_token=demo&fmt=json&period=d`
- `https://eodhd.com/api/intraday/{symbol}?api_token=demo&fmt=json&interval=1h`
- Symbols: AAPL.US, TSLA.US, AMZN.US, VTI.US.
- Daily history is long; the demo intraday window is short (~4 months). The
  intraday equity results are therefore labelled exploratory.
- Adjusted close is used to rescale OHLC, removing split and dividend jumps.

## Rates: FRED

- `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3` (3-month T-bill,
  secondary market, annualized percentage).

## Live shadow verification

- Kraken: `https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60`
- Coinbase: `https://api.exchange.coinbase.com/products/BTC-USD/candles`
- OKX: `https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H`

These are public, read-only endpoints. The live stage records a snapshot, a
cross-venue price deviation, shadow 1h/4h/1d signals, and a hash-chained log
entry. No orders are placed and no API keys are used.

## Sources checked and unusable

| Source | Failure |
|---|---|
| `api.binance.com` | HTTP 451 from the host location |
| stooq.com | JavaScript proof-of-work challenge |
| Yahoo Finance chart API | HTTP 429 |
| Bybit v5 | CloudFront block |
| Dukascopy | HTTP 429 |
| EODHD demo, EUR-USD / BTC-USD intraday | no intraday entitlement |
| Nasdaq API | empty record set |
| ScienceDirect full text | captcha |

## Limitations

- USDT pairs only; no delisted symbols, so crypto results are survivorship-biased
  toward majors. This is stated in the paper and does not affect the
  within-sample comparison across timeframes.
- Spot only: no funding, borrow, or liquidation dynamics.
- Equity intraday conclusions are exploratory because of the short window.
- Timestamps are exchange-reported; no attempt is made to model latency beyond
  the one-bar execution lag.

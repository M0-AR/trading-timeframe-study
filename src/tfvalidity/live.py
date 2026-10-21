from __future__ import annotations

import time
from datetime import UTC, datetime

import pandas as pd
import requests

from .signals import ma_crossover, tsmom
from .utils import stable_hash


def _get_json(url: str, params: dict | None = None, retries: int = 4) -> dict | list:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30, headers={"User-Agent": "tfvalidity/1.0"})
            if resp.status_code == 200:
                return resp.json()
            last = RuntimeError(f"HTTP {resp.status_code}")
        except Exception as exc:
            last = exc
        time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"request failed: {last}")


def fetch_kraken(pair: str = "XBTUSD", interval: int = 60, n_bars: int = 6000) -> pd.DataFrame:
    rows: list[list] = []
    since: int | None = None
    collected = 0
    for _ in range(30):
        params: dict = {"pair": pair, "interval": interval}
        if since is not None:
            params["since"] = since
        payload = _get_json("https://api.kraken.com/0/public/OHLC", params)
        if not isinstance(payload, dict) or payload.get("error"):
            raise RuntimeError(f"kraken error: {payload}")
        result = payload["result"]
        key = next(k for k in result if k != "last")
        batch = result[key]
        if not batch:
            break
        rows.extend(batch)
        collected += len(batch)
        earliest = int(batch[0][0])
        since = earliest - len(batch) * interval * 60
        if collected >= n_bars:
            break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["open_time"] = pd.to_datetime(df["ts"].astype(float), unit="s", utc=True)
    for col in ("open", "high", "low", "close", "vwap", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    df["close_time"] = df["open_time"] + pd.Timedelta(minutes=interval) - pd.Timedelta(milliseconds=1)
    return df.tail(n_bars).reset_index(drop=True)


def fetch_coinbase(product: str = "BTC-USD", granularity: int = 3600, n_bars: int = 300) -> pd.DataFrame:
    frames = []
    end = datetime.now(UTC)
    remaining = n_bars
    while remaining > 0:
        start = end - pd.Timedelta(seconds=granularity * 300)
        payload = _get_json(
            f"https://api.exchange.coinbase.com/products/{product}/candles",
            {"granularity": granularity, "start": start.isoformat(), "end": end.isoformat()},
        )
        if not isinstance(payload, list) or not payload:
            break
        frames.append(pd.DataFrame(payload, columns=["ts", "low", "high", "open", "close", "volume"]))
        remaining -= len(payload)
        end = start
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["open_time"] = pd.to_datetime(df["ts"].astype(float), unit="s", utc=True)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    df["close_time"] = df["open_time"] + pd.Timedelta(seconds=granularity) - pd.Timedelta(milliseconds=1)
    return df.tail(n_bars).reset_index(drop=True)


def fetch_okx(inst: str = "BTC-USDT", bar: str = "1H", n_bars: int = 300) -> pd.DataFrame:
    payload = _get_json("https://www.okx.com/api/v5/market/candles", {"instId": inst, "bar": bar, "limit": min(n_bars, 300)})
    if not isinstance(payload, dict) or payload.get("code") != "0":
        raise RuntimeError(f"okx error: {payload}")
    df = pd.DataFrame(payload["data"], columns=["ts", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"])
    df["open_time"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "vol"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    df["close_time"] = df["open_time"] + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)
    return df.rename(columns={"vol": "volume"})


def cross_venue_snapshot() -> dict:
    out: dict = {"timestamp": datetime.now(UTC).isoformat(), "venues": {}}
    try:
        k = _get_json("https://api.kraken.com/0/public/Ticker", {"pair": "XBTUSD"})
        key = next(k for k in k["result"] if k != "last")
        out["venues"]["kraken"] = {"last": float(k["result"][key]["c"][0]), "source": "ticker"}
    except Exception as exc:
        try:
            k = fetch_kraken("XBTUSD", 60, 5)
            out["venues"]["kraken"] = {"last": float(k["close"].iloc[-1]), "source": "last_bar", "bar_time": k["open_time"].iloc[-1].isoformat()}
        except Exception as inner:
            out["venues"]["kraken"] = {"error": f"{exc}; {inner}"}
    try:
        c = _get_json("https://api.exchange.coinbase.com/products/BTC-USD/ticker")
        out["venues"]["coinbase"] = {"last": float(c["price"]), "source": "ticker"}
    except Exception as exc:
        try:
            c = fetch_coinbase("BTC-USD", 3600, 5)
            out["venues"]["coinbase"] = {"last": float(c["close"].iloc[-1]), "source": "last_bar", "bar_time": c["open_time"].iloc[-1].isoformat()}
        except Exception as inner:
            out["venues"]["coinbase"] = {"error": f"{exc}; {inner}"}
    try:
        o = _get_json("https://www.okx.com/api/v5/market/ticker", {"instId": "BTC-USDT"})
        out["venues"]["okx"] = {"last": float(o["data"][0]["last"]), "source": "ticker"}
    except Exception as exc:
        try:
            o = fetch_okx("BTC-USDT", "1H", 5)
            out["venues"]["okx"] = {"last": float(o["close"].iloc[-1]), "source": "last_bar", "bar_time": o["open_time"].iloc[-1].isoformat()}
        except Exception as inner:
            out["venues"]["okx"] = {"error": f"{exc}; {inner}"}
    prices = [v["last"] for v in out["venues"].values() if "last" in v]
    out["max_deviation_bps"] = float((max(prices) / min(prices) - 1.0) * 1e4) if len(prices) > 1 else float("nan")
    out["n_venues"] = len(prices)
    return out


def shadow_signals(bars: dict[str, pd.DataFrame]) -> dict:
    out = {"as_of": None, "layers": {}}
    for label in ("1h", "4h", "1d"):
        df = bars[label].reset_index(drop=True)
        ma = ma_crossover(df["close"], 20, 100).iloc[-1]
        ts = tsmom(df["close"], 50).iloc[-1]
        out["layers"][label] = {
            "ma_20_100": float(ma),
            "tsmom_50": float(ts),
            "close": float(df["close"].iloc[-1]),
            "n_bars": int(len(df)),
            "last_bar": df["open_time"].iloc[-1].isoformat(),
        }
    out["as_of"] = out["layers"]["1h"]["last_bar"]
    signs = [v["ma_20_100"] for v in out["layers"].values()]
    out["aligned"] = bool(len(set(signs)) == 1 and signs[0] != 0.0)
    out["n_distinct_signs"] = int(len(set(signs)))
    out["agreement_count"] = int(sum(s == signs[0] for s in signs))
    out["payload_hash"] = stable_hash(out)
    return out

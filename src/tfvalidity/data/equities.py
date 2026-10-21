from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from ..utils import sha256_file, write_json

EODHD = "https://eodhd.com/api"
DEMO_TOKEN = "demo"


def _get(url: str, params: dict, retries: int = 5) -> list | dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=60, headers={"User-Agent": "tfvalidity/1.0"})
            if resp.status_code == 200:
                return resp.json()
            last = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            last = exc
        time.sleep(min(2**attempt, 15))
    raise RuntimeError(f"EODHD request failed: {last}")


def fetch_daily(symbol: str, cache_dir: Path, start: str = "2000-01-01", force: bool = False) -> pd.DataFrame:
    cache = cache_dir / "eodhd" / f"{symbol.replace('.', '_')}_daily.parquet"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and not force:
        return pd.read_parquet(cache)
    payload = _get(
        f"{EODHD}/eod/{symbol}",
        {"api_token": DEMO_TOKEN, "fmt": "json", "period": "d", "from": start},
    )
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"no daily data for {symbol}: {str(payload)[:300]}")
    df = pd.DataFrame(payload)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.rename(columns={"date": "open_time"}).sort_values("open_time").reset_index(drop=True)
    for col in ("open", "high", "low", "close", "adjusted_close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df["close_time"] = df["open_time"] + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    if "adjusted_close" in df.columns and df["adjusted_close"].notna().all():
        ratio = df["adjusted_close"] / df["close"]
        for col in ("open", "high", "low", "close"):
            df[col] = df[col] * ratio
    df.to_parquet(cache, index=False)
    write_json(cache.with_suffix(".manifest.json"), {"symbol": symbol, "rows": len(df), "sha256": sha256_file(cache), "start": df["open_time"].min().isoformat(), "end": df["open_time"].max().isoformat()})
    return df


def fetch_hourly(symbol: str, cache_dir: Path, force: bool = False) -> pd.DataFrame:
    cache = cache_dir / "eodhd" / f"{symbol.replace('.', '_')}_1h.parquet"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and not force:
        return pd.read_parquet(cache)
    payload = _get(
        f"{EODHD}/intraday/{symbol}",
        {"api_token": DEMO_TOKEN, "fmt": "json", "interval": "1h"},
    )
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"no hourly data for {symbol}: {str(payload)[:300]}")
    df = pd.DataFrame(payload)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.rename(columns={"datetime": "open_time"}).sort_values("open_time").reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df["close_time"] = df["open_time"] + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)
    df.to_parquet(cache, index=False)
    write_json(cache.with_suffix(".manifest.json"), {"symbol": symbol, "rows": len(df), "sha256": sha256_file(cache), "start": df["open_time"].min().isoformat(), "end": df["open_time"].max().isoformat()})
    return df


def fred_csv(series: str, cache_dir: Path, force: bool = False) -> pd.DataFrame:
    cache = cache_dir / "fred" / f"{series}.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists() or force:
        resp = requests.get(
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}",
            timeout=60,
            headers={"User-Agent": "tfvalidity/1.0"},
        )
        resp.raise_for_status()
        cache.write_bytes(resp.content)
    df = pd.read_csv(cache)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.rename(columns={"date": "open_time"}).dropna()

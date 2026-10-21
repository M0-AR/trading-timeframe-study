from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from ..utils import read_json, sha256_file, write_json
from .resample import rule_minutes

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]
NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
]


def month_range(start: str, end: str) -> list[str]:
    start_ts = pd.Period(start, freq="M")
    end_ts = pd.Period(end, freq="M")
    if end_ts < start_ts:
        raise ValueError("end month precedes start month")
    return [str(p) for p in pd.period_range(start_ts, end_ts, freq="M")]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "tfvalidity/1.0 (research; reproducible pipeline)"})
    return s


def _download(url: str, dest: Path, retries: int = 6) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with _session() as s:
                resp = s.get(url, timeout=60)
            if resp.status_code == 200 and resp.content:
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.write_bytes(resp.content)
                tmp.replace(dest)
                return
            if resp.status_code in (403, 404):
                raise FileNotFoundError(f"{url} returned {resp.status_code}")
            last_error = RuntimeError(f"{url} returned {resp.status_code}")
        except FileNotFoundError:
            raise
        except Exception as exc:
            last_error = exc
        time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"download failed for {url}: {last_error}")


def download_month(
    symbol: str,
    interval: str,
    month: str,
    cache_dir: Path,
    verify: bool = True,
) -> Path:
    name = f"{symbol}-{interval}-{month}.zip"
    url = f"{BASE_URL}/{symbol}/{interval}/{name}"
    dest = cache_dir / "binance" / interval / symbol / name
    _download(url, dest)
    if verify:
        checksum_path = dest.with_suffix(dest.suffix + ".CHECKSUM")
        _download(url + ".CHECKSUM", checksum_path)
        expected = checksum_path.read_text(encoding="utf-8").split()[0].strip()
        actual = sha256_file(dest)
        if actual != expected:
            dest.unlink(missing_ok=True)
            raise ValueError(f"checksum mismatch for {name}: {actual} != {expected}")
    return dest


def _normalize_timestamp(values: np.ndarray) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return values
    peak = float(np.nanmax(finite))
    if peak > 1e17:
        return values / 1e6
    if peak > 1e14:
        return values / 1e3
    return values


def window_bounds(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC") + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    return start_ts, end_ts


def load_month(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        member = zf.namelist()[0]
        raw = zf.read(member)
    first_line = raw.split(b"\n", 1)[0]
    header = 0 if not first_line[:1].isdigit() else None
    df = pd.read_csv(io.BytesIO(raw), header=header, names=KLINE_COLUMNS if header is None else None)
    if header == 0:
        df.columns = KLINE_COLUMNS[: len(df.columns)]
    for col in NUMERIC_COLUMNS + ["open_time", "close_time"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open_time", "open", "high", "low", "close"])
    ms = _normalize_timestamp(df["open_time"].to_numpy(dtype=float))
    cms = _normalize_timestamp(df["close_time"].to_numpy(dtype=float))
    df["open_time"] = pd.to_datetime(ms, unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(cms, unit="ms", utc=True)
    df = df.drop(columns=["ignore"], errors="ignore")
    return df


def build_symbol(
    symbol: str,
    interval: str,
    start: str,
    end: str,
    cache_dir: Path,
    verify: bool = True,
    force: bool = False,
) -> tuple[pd.DataFrame, dict]:
    out_dir = cache_dir / "binance" / interval
    parquet = out_dir / f"{symbol}.parquet"
    manifest_path = out_dir / f"{symbol}.manifest.json"
    if parquet.exists() and manifest_path.exists() and not force:
        man = read_json(manifest_path)
        req_start, req_end = window_bounds(start, end)
        tolerance = pd.Timedelta(minutes=rule_minutes(interval))
        try:
            covered = (
                man.get("symbol") == symbol
                and man.get("interval") == interval
                and pd.Timestamp(man["start"]) <= req_start
                and pd.Timestamp(man["end"]) >= req_end - tolerance
            )
        except Exception:
            covered = False
        if covered:
            return pd.read_parquet(parquet), man

    frames = []
    files: list[dict] = []
    for month in month_range(start, end):
        path = download_month(symbol, interval, month, cache_dir, verify=verify)
        frame = load_month(path)
        frames.append(frame)
        files.append(
            {
                "file": path.name,
                "sha256": sha256_file(path),
                "rows": int(len(frame)),
                "start": frame["open_time"].min().isoformat(),
                "end": frame["open_time"].max().isoformat(),
            }
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("open_time").drop_duplicates("open_time", keep="last").reset_index(drop=True)
    start_ts, end_ts = window_bounds(start, end)
    df = df[(df["open_time"] >= start_ts) & (df["open_time"] <= end_ts)]
    df.to_parquet(parquet, index=False)
    manifest = {
        "symbol": symbol,
        "interval": interval,
        "rows": int(len(df)),
        "start": df["open_time"].min().isoformat(),
        "end": df["open_time"].max().isoformat(),
        "files": files,
        "parquet_sha256": sha256_file(parquet),
        "verified_checksums": bool(verify),
    }
    write_json(manifest_path, manifest)
    return df, manifest


def gap_audit(df: pd.DataFrame, interval_minutes: int, business_days: bool = False) -> dict:
    diffs = df["open_time"].sort_values().diff().dt.total_seconds().dropna().to_numpy()
    expected = interval_minutes * 60
    gaps = diffs[diffs != expected]
    out = {
        "rows": int(len(df)),
        "start": df["open_time"].min().isoformat(),
        "end": df["open_time"].max().isoformat(),
        "expected_spacing_seconds": expected,
        "n_gaps": int(len(gaps)),
        "max_gap_seconds": int(gaps.max()) if len(gaps) else 0,
        "missing_bars_estimate": int(((gaps - expected) // expected).clip(min=0).sum()) if len(gaps) else 0,
        "monotonic": bool(df["open_time"].is_monotonic_increasing),
        "duplicates": int(df["open_time"].duplicated().sum()),
        "nonpositive_prices": int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        "high_low_violations": int((df["high"] < df["low"]).sum()),
    }
    if business_days:
        sessions = pd.bdate_range(df["open_time"].min().date(), df["open_time"].max().date())
        if df["open_time"].dt.tz is not None:
            sessions = sessions.tz_localize(df["open_time"].dt.tz)
        sessions = sessions.as_unit("ns")
        present = pd.DatetimeIndex(df["open_time"].dt.normalize().unique()).as_unit("ns")
        missing = sessions.difference(present)
        if len(missing):
            runs = np.split(missing, np.where(np.diff(missing.asi8 // 86_400_000_000_000) > 1)[0] + 1)
            max_run = max(len(r) for r in runs)
        else:
            runs, max_run = [], 0
        out.update(
            {
                "calendar": "business_days",
                "n_gaps": int(len(runs)),
                "missing_bars_estimate": int(len(missing)),
                "max_gap_business_days": int(max_run),
                "note": "business-day calendar includes exchange holidays",
            }
        )
    return out


def dependency_versions() -> dict[str, str]:
    import platform

    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }

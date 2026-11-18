"""Fetch and cache daily prices and quote data from Yahoo Finance via yfinance.

yfinance is unofficial and can break or rate limit. Every failure raises PriceError;
nothing here guesses or fills gaps. Calculations live in src/technicals.py.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "prices"
CACHE_MAX_AGE_HOURS = 12
HISTORY_PERIOD = "2y"  # a year of chart plus a year to warm up the 200-day average


class PriceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float  # split-adjusted, not dividend-adjusted
    volume: float
    split: float = 0.0  # split ratio on this day, 0 when none


def _fresh(path: Path, refresh: bool) -> bool:
    return not refresh and path.exists() and (time.time() - path.stat().st_mtime) / 3600 < CACHE_MAX_AGE_HOURS


def _read_bars(path: Path) -> list[Bar]:
    with open(path, newline="", encoding="utf-8") as f:
        return [
            Bar(date.fromisoformat(r["day"]), float(r["open"]), float(r["high"]), float(r["low"]),
                float(r["close"]), float(r["volume"]), float(r["split"]))
            for r in csv.DictReader(f)
        ]


def price_history(ticker: str, refresh: bool = False) -> list[Bar]:
    """Daily bars, oldest first. The last bar can be a session still in progress."""
    path = CACHE_DIR / f"{ticker.upper()}.csv"
    if _fresh(path, refresh):
        return _read_bars(path)

    import yfinance as yf  # imported here so tests and EDGAR-only scripts don't need it

    try:
        frame = yf.Ticker(ticker).history(period=HISTORY_PERIOD, auto_adjust=False, actions=True)
    except Exception as error:  # yfinance raises many exception types
        raise PriceError(f"{ticker}: yfinance price download failed: {error}") from error
    if frame is None or frame.empty:
        raise PriceError(f"{ticker}: yfinance returned no price history")

    bars = []
    for stamp, row in frame.iterrows():
        values = [row["Open"], row["High"], row["Low"], row["Close"], row["Volume"]]
        if any(v != v for v in values):  # NaN: skip the row rather than invent a value
            continue
        split = float(row.get("Stock Splits", 0) or 0)
        bars.append(Bar(stamp.date(), *(float(v) for v in values), split=split))
    if not bars:
        raise PriceError(f"{ticker}: yfinance price history had no complete rows")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["day", "open", "high", "low", "close", "volume", "split"])
        for b in bars:
            writer.writerow([b.day, b.open, b.high, b.low, b.close, b.volume, b.split])
    return bars


ESTIMATE_COLUMNS = ("avg", "low", "high", "numberOfAnalysts", "yearAgoRevenue", "growth", "currency")


def revenue_estimates(ticker: str, refresh: bool = False) -> dict:
    """Yahoo's analyst revenue consensus: {"_fetched": epoch seconds, "rows": [...]}, one row per
    period (0q, +1q, 0y, +1y) with the ESTIMATE_COLUMNS. Missing values are None. A company no
    analyst covers comes back with zeros; src/estimates.py treats those as missing."""
    path = CACHE_DIR / f"{ticker.upper()}_estimates.json"
    if _fresh(path, refresh):
        return json.loads(path.read_text(encoding="utf-8"))

    import yfinance as yf

    try:
        frame = yf.Ticker(ticker).revenue_estimate
    except Exception as error:
        raise PriceError(f"{ticker}: yfinance revenue estimate download failed: {error}") from error
    if frame is None or frame.empty:
        raise PriceError(f"{ticker}: yfinance returned no revenue estimates")

    rows = []
    for period, row in frame.iterrows():
        out = {"period": str(period)}
        for column in ESTIMATE_COLUMNS:
            value = row.get(column)
            if value is None or (isinstance(value, float) and value != value):  # NaN
                out[column] = None
            else:
                out[column] = value if isinstance(value, str) else float(value)
        rows.append(out)
    data = {"_fetched": time.time(), "rows": rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def quote_info(ticker: str, refresh: bool = False) -> dict:
    """Yahoo's quote summary: short interest, float, holders, next earnings date and more."""
    path = CACHE_DIR / f"{ticker.upper()}_info.json"
    if _fresh(path, refresh):
        return json.loads(path.read_text(encoding="utf-8"))

    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info
    except Exception as error:
        raise PriceError(f"{ticker}: yfinance quote download failed: {error}") from error
    if not info or "symbol" not in info:
        raise PriceError(f"{ticker}: yfinance returned no quote data")
    info["_fetched"] = time.time()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    return info

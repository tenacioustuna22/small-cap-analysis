"""Trend, momentum, volume and short interest from daily bars and quote data. Pure functions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from src.charts import add_months
from src.prices import Bar

RETURN_PERIODS = [("1 month", 1), ("3 months", 3), ("6 months", 6), ("12 months", 12)]
BIG_MOVE = 0.5  # a one-day move of 50% or more gets a note
LIVE_STATES = {"REGULAR", "PRE", "PREPRE"}


@dataclass(frozen=True)
class ShortInterest:
    shares: float
    pct_float: float | None  # percent
    days_to_cover: float | None
    as_of: date | None
    prior_shares: float | None = None
    prior_as_of: date | None = None

    @property
    def change_pct(self) -> float | None:
        if not self.prior_shares:
            return None
        return (self.shares - self.prior_shares) / self.prior_shares * 100


@dataclass
class Technicals:
    bars: list[Bar] = field(default_factory=list)  # completed sessions, oldest first
    dropped_live: bool = False  # a session in progress was left out
    sma50: float | None = None
    sma200: float | None = None
    sma50_series: list[tuple[date, float]] = field(default_factory=list)
    sma200_series: list[tuple[date, float]] = field(default_factory=list)
    high52: tuple[date, float] | None = None
    low52: tuple[date, float] | None = None
    returns: dict[str, float | None] = field(default_factory=dict)
    volume20: float | None = None
    volume63: float | None = None
    rsi14: float | None = None
    short: ShortInterest | None = None
    institutions_pct: float | None = None
    insiders_pct: float | None = None
    sessions_below_1: int = 0  # consecutive closes under $1.00, up to the latest
    notes: list[str] = field(default_factory=list)

    @property
    def last(self) -> Bar | None:
        return self.bars[-1] if self.bars else None

    def _vs(self, level: float | None) -> float | None:
        return (self.last.close / level - 1) * 100 if self.last and level else None

    @property
    def vs_sma50(self) -> float | None:
        return self._vs(self.sma50)

    @property
    def vs_sma200(self) -> float | None:
        return self._vs(self.sma200)

    @property
    def from_high(self) -> float | None:
        return self._vs(self.high52[1] if self.high52 else None)

    @property
    def volume_ratio(self) -> float | None:
        return self.volume20 / self.volume63 if self.volume20 and self.volume63 else None

    @property
    def trend(self) -> str:
        """Plain description of where price sits against its moving averages."""
        if self.sma50 is None or self.sma200 is None or not self.last:
            return "not enough history"
        price = self.last.close
        above50, above200 = price > self.sma50, price > self.sma200
        if above50 and above200:
            return "above both averages" + (", with the 50-day above the 200-day" if self.sma50 > self.sma200 else "")
        if not above50 and not above200:
            return "below both averages" + (", with the 50-day below the 200-day" if self.sma50 < self.sma200 else "")
        if above200:
            return "above the 200-day average, below the 50-day"
        return "above the 50-day average, below the 200-day"


def _market_date(info: dict) -> date | None:
    stamp = info.get("regularMarketTime")
    if not isinstance(stamp, (int, float)):
        return None
    offset = (info.get("gmtOffSetMilliseconds") or 0) / 1000
    return datetime.fromtimestamp(stamp + offset, tz=timezone.utc).date()


def completed_bars(bars: list[Bar], info: dict) -> tuple[list[Bar], bool]:
    """Drop today's bar while that session is still trading. Returns (bars, dropped)."""
    if bars and info.get("marketState") in LIVE_STATES and bars[-1].day == _market_date(info):
        return bars[:-1], True
    return bars, False


def sma(closes: list[float], length: int) -> float | None:
    return sum(closes[-length:]) / length if len(closes) >= length else None


def rolling_sma(bars: list[Bar], length: int) -> list[tuple[date, float]]:
    out, total = [], 0.0
    for i, bar in enumerate(bars):
        total += bar.close
        if i >= length:
            total -= bars[i - length].close
        if i >= length - 1:
            out.append((bar.day, total / length))
    return out


def rsi(closes: list[float], length: int = 14) -> float | None:
    """Wilder's relative strength index."""
    if len(closes) <= length:
        return None
    changes = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(c, 0) for c in changes[:length]) / length
    loss = sum(max(-c, 0) for c in changes[:length]) / length
    for c in changes[length:]:
        gain = (gain * (length - 1) + max(c, 0)) / length
        loss = (loss * (length - 1) + max(-c, 0)) / length
    if loss == 0:
        return 100.0
    return 100 - 100 / (1 + gain / loss)


def sessions_below(closes: list[float], level: float) -> int:
    """Consecutive sessions, counting back from the latest, that closed below `level`."""
    count = 0
    for close in reversed(closes):
        if close >= level:
            break
        count += 1
    return count


def close_on_or_before(bars: list[Bar], day: date) -> Bar | None:
    earlier = [b for b in bars if b.day <= day]
    return earlier[-1] if earlier else None


def _stamp_date(value) -> date | None:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, tz=timezone.utc).date()
    return None


def short_interest(info: dict) -> ShortInterest | None:
    shares = info.get("sharesShort")
    if not isinstance(shares, (int, float)):
        return None
    pct = info.get("shortPercentOfFloat")
    return ShortInterest(
        shares=float(shares),
        pct_float=float(pct) * 100 if isinstance(pct, (int, float)) else None,
        days_to_cover=info.get("shortRatio") if isinstance(info.get("shortRatio"), (int, float)) else None,
        as_of=_stamp_date(info.get("dateShortInterest")),
        prior_shares=info.get("sharesShortPriorMonth") if isinstance(info.get("sharesShortPriorMonth"), (int, float)) else None,
        prior_as_of=_stamp_date(info.get("sharesShortPreviousMonthDate")),
    )


def _pct(info: dict, key: str) -> float | None:
    value = info.get(key)
    return float(value) * 100 if isinstance(value, (int, float)) else None


def compute_technicals(bars: list[Bar], info: dict | None = None) -> Technicals:
    info = info or {}
    result = Technicals()
    result.bars, result.dropped_live = completed_bars(bars, info)
    if not result.bars:
        result.notes.append("no completed trading sessions in the price history")
        return result

    closes = [b.close for b in result.bars]
    last = result.bars[-1]
    result.sma50, result.sma200 = sma(closes, 50), sma(closes, 200)
    result.sma50_series = rolling_sma(result.bars, 50)
    result.sma200_series = rolling_sma(result.bars, 200)
    year = [b for b in result.bars if b.day > last.day - timedelta(days=365)]
    top, bottom = max(year, key=lambda b: b.high), min(year, key=lambda b: b.low)
    result.high52, result.low52 = (top.day, top.high), (bottom.day, bottom.low)
    for label, months in RETURN_PERIODS:
        then = close_on_or_before(result.bars, add_months(last.day, -months))
        result.returns[label] = (last.close / then.close - 1) * 100 if then else None
    volumes = [b.volume for b in result.bars]
    result.volume20, result.volume63 = sma(volumes, 20), sma(volumes, 63)
    result.rsi14 = rsi(closes)

    result.short = short_interest(info)
    result.institutions_pct = _pct(info, "heldPercentInstitutions")
    result.insiders_pct = _pct(info, "heldPercentInsiders")

    result.sessions_below_1 = sessions_below(closes, 1.0)
    if result.sessions_below_1:
        result.notes.append(
            f"closed below $1.00 for the last {result.sessions_below_1} sessions. Exchange minimum bid rules "
            f"(on Nasdaq, 30 consecutive business days) lead to a deficiency notice and often a reverse split; "
            "check recent 8-Ks for item 3.01"
        )
    if len(closes) < 200:
        result.notes.append(f"only {len(closes)} sessions of history, so the 200-day average is missing")
    for a, b in zip(result.bars, result.bars[1:]):
        if b.split:
            result.notes.append(
                f"stock split ({b.split:g} for 1) on {b.day}: prices are adjusted for it, "
                "EDGAR share counts from before that date are not"
            )
        elif a.close and abs(b.close / a.close - 1) >= BIG_MOVE:
            result.notes.append(
                f"price moved {(b.close / a.close - 1) * 100:+.0f}% on {b.day}; "
                "confirm it was news and not an unadjusted split"
            )
    return result

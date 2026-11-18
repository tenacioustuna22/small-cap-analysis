"""Analyst revenue consensus for next year, chosen so periods line up across companies.

The figures are Yahoo's consensus via yfinance (unofficial). Pure functions on the cached data
from prices.revenue_estimates; nothing here fetches.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

YEAR_ROWS = {"0y": 0, "+1y": 1}  # current fiscal year, next fiscal year
WIDE_RANGE = 1.5  # high more than this many times low gets a note
SOURCE = "Yahoo analyst consensus via yfinance (unofficial)"


@dataclass
class ForwardEstimate:
    label: str  # "FY2027", or "FY ending 2027-06-30" when the year does not end in December
    period_end: date
    average: float
    low: float | None
    high: float | None
    analysts: int
    year_ago: float | None  # Yahoo's figure for the fiscal year before (itself an estimate if not reported)
    as_of: date
    notes: list[str] = field(default_factory=list)

    @property
    def growth(self) -> float | None:
        """Expected growth over the year before, in percent."""
        if not self.year_ago:
            return None
        return (self.average - self.year_ago) / self.year_ago * 100


def _add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 February
        return day.replace(year=day.year + years, day=28)


def choose_forward(data: dict, current_fiscal_year_end: date | None, latest_quarter_end: date | None) -> ForwardEstimate | None:
    """The fiscal year (current or next) whose end is closest to twelve months after the latest
    reported quarter. In November 2026 that is FY2027 for December-year companies and the year
    ending June 2027 for a June-year company. None when there is no usable estimate."""
    if current_fiscal_year_end is None or latest_quarter_end is None:
        return None
    rows = {r.get("period"): r for r in data.get("rows", [])}
    target = latest_quarter_end + timedelta(days=365)
    candidates = []
    for period, offset in YEAR_ROWS.items():
        row = rows.get(period)
        if not row or not row.get("avg") or not row.get("numberOfAnalysts"):
            continue  # zeros mean no coverage
        if row.get("currency") not in (None, "USD"):
            continue  # EV is in dollars; a multiple on another currency would be wrong
        end = _add_years(current_fiscal_year_end, offset)
        candidates.append((abs((end - target).days), end, row))
    if not candidates:
        return None
    _, end, row = min(candidates, key=lambda c: c[0])
    label = f"FY{end.year}" if (end.month, end.day) == (12, 31) else f"FY ending {end}"
    fetched = data.get("_fetched")
    as_of = datetime.fromtimestamp(fetched).date() if fetched else date.today()  # local date of the fetch
    estimate = ForwardEstimate(
        label=label,
        period_end=end,
        average=row["avg"],
        low=row.get("low") or None,
        high=row.get("high") or None,
        analysts=int(row["numberOfAnalysts"]),
        year_ago=row.get("yearAgoRevenue") or None,
        as_of=as_of,
    )
    if estimate.analysts == 1:
        estimate.notes.append(f"{label} revenue consensus is a single analyst's estimate")
    if estimate.low and estimate.high and estimate.high > WIDE_RANGE * estimate.low:
        estimate.notes.append(f"{label} revenue estimates range widely, from ${estimate.low / 1e6:.1f}M "
                              f"to ${estimate.high / 1e6:.1f}M")
    return estimate


def fiscal_year_end(info: dict) -> date | None:
    """End of the current fiscal year from Yahoo's quote data (`nextFiscalYearEnd`, epoch seconds)."""
    stamp = info.get("nextFiscalYearEnd")
    if not stamp:
        return None
    return datetime.fromtimestamp(int(stamp), tz=timezone.utc).date()

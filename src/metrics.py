"""Calculations on reported facts. Pure functions, no network access."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Fact:
    """One reported XBRL value. `start` is None for balance sheet (point in time) values."""

    tag: str
    start: date | None
    end: date
    val: float
    form: str
    filed: date


@dataclass(frozen=True)
class QuarterFlow:
    """A cash flow or income value for a single quarter."""

    end: date
    val: float
    source: Fact  # the filing fact the value came from


def _is_one_quarter(days: int) -> bool:
    return 80 <= days <= 100


def latest_instant(facts: list[Fact]) -> Fact | None:
    """Most recent balance sheet value. For a restated date, the latest filing wins."""
    instants = [f for f in facts if f.start is None]
    return max(instants, key=lambda f: (f.end, f.filed), default=None)


def instant_at(facts: list[Fact], end: date) -> Fact | None:
    """Balance sheet value at an exact date, taking the latest filing."""
    matches = [f for f in facts if f.start is None and f.end == end]
    return max(matches, key=lambda f: f.filed, default=None)


def quarterly_flows(facts: list[Fact]) -> list[QuarterFlow]:
    """Turn reported flow values into single-quarter values, oldest first.

    Cash flow statements report year-to-date totals (3, 6, 9, 12 months), so a
    quarter is the difference between two totals that share a fiscal year start.
    """
    periods: dict[tuple[date, date], Fact] = {}
    for f in facts:
        if f.start is None:
            continue
        key = (f.start, f.end)
        if key not in periods or f.filed > periods[key].filed:
            periods[key] = f

    quarters: dict[date, QuarterFlow] = {}

    # Values that already cover one quarter.
    for (start, end), f in periods.items():
        if _is_one_quarter((end - start).days):
            quarters[end] = QuarterFlow(end, f.val, f)

    # Year-to-date values: subtract the previous total from the same fiscal year.
    for (start, end), f in periods.items():
        if end in quarters:
            continue
        priors = [p for (s, e), p in periods.items() if s == start and e < end]
        if not priors:
            continue
        prev = max(priors, key=lambda p: p.end)
        if _is_one_quarter((end - prev.end).days):
            quarters[end] = QuarterFlow(end, f.val - prev.val, f)

    return sorted(quarters.values(), key=lambda q: q.end)


def single_quarter_values(facts: list[Fact]) -> list[Fact]:
    """Facts that cover exactly one quarter, one per period, oldest first.

    For values that cannot be derived by subtraction, such as weighted average
    share counts. Fourth quarters are usually missing because 10-Ks report the year.
    """
    periods: dict[tuple[date, date], Fact] = {}
    for f in facts:
        if f.start is None or not _is_one_quarter((f.end - f.start).days):
            continue
        key = (f.start, f.end)
        if key not in periods or f.filed > periods[key].filed:
            periods[key] = f
    return sorted(periods.values(), key=lambda f: f.end)


def year_to_date(facts: list[Fact], end: date) -> tuple[Fact | None, Fact | None]:
    """The filed year-to-date total (longer than a quarter, shorter than a year) ending on
    `end`, and the same span a year earlier. The latest filing wins for each."""
    def span(f: Fact) -> int:
        return (f.end - f.start).days if f.start else 0

    now = max((f for f in facts if f.end == end and 100 < span(f) < 300), key=lambda f: f.filed, default=None)
    if now is None:
        return None, None
    prior = max(
        (f for f in facts if f.start and abs((f.end - end).days + 365) <= 20 and abs(span(f) - span(now)) <= 10),
        key=lambda f: f.filed,
        default=None,
    )
    return now, prior


def start_values(latest: QuarterFlow | None, ttm: float | None, ytd: Fact | None) -> dict[str, float]:
    """Annual revenue starting points for a scenario, in dollars. ttm: the last four
    quarters; run_rate: the latest quarter times four; ytd_annualized: the year-to-date
    total scaled to twelve months. Missing ones are left out."""
    out = {}
    if ttm is not None:
        out["ttm"] = ttm
    if latest is not None:
        out["run_rate"] = latest.val * 4
    if ytd is not None and ytd.start:
        months = round((ytd.end - ytd.start).days / 30.44)
        out["ytd_annualized"] = ytd.val * 12 / months
    return out


def value_near(facts: list[Fact], target: date, tolerance_days: int = 20) -> Fact | None:
    """The fact whose period ends closest to `target`, if within the tolerance."""
    closest = min(facts, key=lambda f: abs((f.end - target).days), default=None)
    if closest is None or abs((closest.end - target).days) > tolerance_days:
        return None
    return closest


def pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return (new - old) / old * 100


def trailing_four_quarters(quarters: list[QuarterFlow]) -> list[QuarterFlow] | None:
    """The last four quarters, or None if they are not four consecutive quarters."""
    if len(quarters) < 4:
        return None
    last4 = quarters[-4:]
    for a, b in zip(last4, last4[1:]):
        if not _is_one_quarter((b.end - a.end).days):
            return None
    return last4


def runway_months(liquidity: float, quarterly_burn: float) -> float | None:
    """Months of cash left at the given quarterly burn. None if not burning cash."""
    if quarterly_burn <= 0:
        return None
    return liquidity / quarterly_burn * 3

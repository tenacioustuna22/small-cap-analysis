"""Cash runway from a company's EDGAR facts: liquidity divided by operating cash burn."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.edgar import facts_for_tag
from src.metrics import (
    Fact,
    QuarterFlow,
    instant_at,
    latest_instant,
    quarterly_flows,
    runway_months,
    trailing_four_quarters,
)

# Companies pick different XBRL tags for the same line item. Within each list the
# first tag with data wins, so nothing is counted twice.
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",  # includes restricted cash
]
SHORT_TERM_INVESTMENT_TAGS = [
    "ShortTermInvestments",
    "MarketableSecuritiesCurrent",
    "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
    "HeldToMaturitySecuritiesCurrent",
]
OPERATING_CASH_FLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]

STALE_AFTER_DAYS = 135  # a quarter plus the 45-day 10-Q filing window


@dataclass
class Runway:
    cash: Fact | None = None
    investments: Fact | None = None
    latest_quarter: QuarterFlow | None = None
    trailing: list[QuarterFlow] | None = None
    quarters: list[QuarterFlow] = field(default_factory=list)  # full history, oldest first
    notes: list[str] = field(default_factory=list)

    @property
    def liquidity(self) -> float | None:
        if self.cash is None:
            return None
        return self.cash.val + (self.investments.val if self.investments else 0.0)

    @property
    def burn_latest(self) -> float | None:
        """Operating cash used in the latest quarter. Negative means cash was generated."""
        return -self.latest_quarter.val if self.latest_quarter else None

    @property
    def burn_average(self) -> float | None:
        """Average quarterly operating cash used over the trailing four quarters."""
        if not self.trailing:
            return None
        return -sum(q.val for q in self.trailing) / len(self.trailing)

    def months(self, burn: float | None) -> float | None:
        if self.liquidity is None or burn is None:
            return None
        return runway_months(self.liquidity, burn)


def compute_runway(company: dict, today: date | None = None) -> Runway:
    today = today or date.today()
    result = Runway()

    # Cash: the tag with the most recent balance sheet date.
    cash_candidates = [latest_instant(facts_for_tag(company, tag)) for tag in CASH_TAGS]
    cash_candidates = [c for c in cash_candidates if c is not None]
    if not cash_candidates:
        result.notes.append("no cash balance found under the known tags")
        return result
    newest = max(c.end for c in cash_candidates)
    result.cash = next(c for c in cash_candidates if c.end == newest)
    if result.cash.tag != CASH_TAGS[0]:
        result.notes.append("cash figure includes restricted cash")

    # Short-term investments on the same balance sheet date.
    for tag in SHORT_TERM_INVESTMENT_TAGS:
        found = instant_at(facts_for_tag(company, tag), result.cash.end)
        if found is not None:
            result.investments = found
            break

    age_days = (today - result.cash.end).days
    if age_days > STALE_AFTER_DAYS:
        result.notes.append(f"balance sheet is {age_days} days old")

    # Operating cash flow: the tag with the most recent quarter.
    best: list[QuarterFlow] = []
    for tag in OPERATING_CASH_FLOW_TAGS:
        quarters = quarterly_flows(facts_for_tag(company, tag))
        if quarters and (not best or quarters[-1].end > best[-1].end):
            best = quarters
    if not best:
        result.notes.append("no operating cash flow found under the known tags")
        return result

    result.quarters = best
    result.latest_quarter = best[-1]
    result.trailing = trailing_four_quarters(best)
    if result.trailing is None:
        result.notes.append("fewer than four consecutive quarters of cash flow")
    if result.latest_quarter.end != result.cash.end:
        result.notes.append(
            f"latest cash flow quarter ends {result.latest_quarter.end}, "
            f"balance sheet is {result.cash.end}"
        )
    return result

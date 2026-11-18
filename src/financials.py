"""Revenue, margins, operating expenses and debt from a company's EDGAR facts.

Income statement values arrive the same way as cash flows (three-month and year-to-date
figures in 10-Qs, the full year in 10-Ks), so `metrics.quarterly_flows` turns them into
single quarters, deriving the fourth quarter from the 10-K.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from src.edgar import facts_for_tag
from src.metrics import (
    Fact,
    QuarterFlow,
    instant_at,
    latest_instant,
    pct_change,
    quarterly_flows,
    start_values,
    year_to_date,
)

ROOT = Path(__file__).resolve().parents[1]
FILING_NOTES_PATH = ROOT / "filing_notes.csv"

# Within each list the first tag with data for the latest quarter wins.
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
COST_OF_REVENUE_TAGS = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
]
GROSS_PROFIT_TAG = "GrossProfit"
OPERATING_EXPENSE_TAGS = ["OperatingExpenses", "CostsAndExpenses"]
RESEARCH_TAG = "ResearchAndDevelopmentExpense"
NET_INCOME_TAG = "NetIncomeLoss"
EQUITY_TAG = "StockholdersEquity"

# Debt at carrying value. Each entry is a set of tags added together; the first set
# with a value on the balance sheet date wins. Operating leases are left out.
DEBT_TAG_SETS = [
    ["LongTermDebt"],  # total, current portion included
    ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
    ["ConvertibleNotesPayable", "ConvertibleNotesPayableCurrent"],
    ["NotesPayable", "NotesPayableCurrent"],
    ["LoansPayable", "LoansPayableCurrent"],
    ["DebtCurrent"],
]
DEBT_TAGS = sorted({tag for tags in DEBT_TAG_SETS for tag in tags})


@dataclass
class Financials:
    revenue: list[QuarterFlow] = field(default_factory=list)  # oldest first
    gross_profit: list[QuarterFlow] = field(default_factory=list)
    gross_profit_derived: bool = False  # True when revenue minus cost of revenue
    opex: list[QuarterFlow] = field(default_factory=list)
    research: list[QuarterFlow] = field(default_factory=list)
    net_income: list[QuarterFlow] = field(default_factory=list)
    debt: float | None = None  # None means no debt tag on the balance sheet date
    debt_facts: list[Fact] = field(default_factory=list)
    debt_date: date | None = None
    equity: Fact | None = None
    notes: list[str] = field(default_factory=list)
    debt_notes: list[str] = field(default_factory=list)  # shown next to the debt figure
    # (quarter end, gross margin, usual margin) for recent quarters far from the usual level
    margin_outliers: list[tuple[date, float, float]] = field(default_factory=list)
    revenue_ytd: Fact | None = None  # year-to-date revenue ending with the latest quarter, as filed

    @property
    def latest(self) -> QuarterFlow | None:
        return self.revenue[-1] if self.revenue else None

    def start_values(self) -> dict[str, float]:
        """Whole-company annual revenue starting points for scenarios (see metrics.start_values)."""
        return start_values(self.latest, self.revenue_ttm, self.revenue_ytd)

    def ttm(self, series: list[QuarterFlow], end: date | None = None) -> float | None:
        """Sum of the four quarters ending at `end` (default: the latest revenue quarter)."""
        return trailing_sum(series, end or (self.latest.end if self.latest else None))

    @property
    def revenue_ttm(self) -> float | None:
        return self.ttm(self.revenue)

    @property
    def revenue_ttm_prior(self) -> float | None:
        if not self.latest:
            return None
        year_ago = quarter_near(self.revenue, self.latest.end - timedelta(days=365))
        return self.ttm(self.revenue, year_ago.end) if year_ago else None

    @property
    def growth_ttm(self) -> float | None:
        return pct_change(self.revenue_ttm, self.revenue_ttm_prior)

    @property
    def growth_quarter(self) -> float | None:
        """Latest quarter against the same quarter a year earlier."""
        if not self.latest:
            return None
        year_ago = quarter_near(self.revenue, self.latest.end - timedelta(days=365))
        return pct_change(self.latest.val, year_ago.val if year_ago else None)

    @property
    def gross_margin_quarter(self) -> float | None:
        return margin_at(self.gross_profit, self.revenue, self.latest.end) if self.latest else None

    @property
    def gross_margin_ttm(self) -> float | None:
        gp, rev = self.ttm(self.gross_profit), self.revenue_ttm
        return gp / rev * 100 if gp is not None and rev else None

    @property
    def gross_profit_ttm(self) -> float | None:
        return self.ttm(self.gross_profit)

    @property
    def margins(self) -> list[tuple[date, float]]:
        """Gross margin per quarter, in percent, oldest first."""
        out = []
        for q in self.revenue:
            m = margin_at(self.gross_profit, self.revenue, q.end)
            if m is not None:
                out.append((q.end, m))
        return out

    @property
    def opex_latest(self) -> QuarterFlow | None:
        return self.opex[-1] if self.opex else None

    @property
    def opex_change(self) -> float | None:
        """Latest quarter's operating expenses against the same quarter a year earlier."""
        if not self.opex:
            return None
        year_ago = quarter_near(self.opex, self.opex[-1].end - timedelta(days=365))
        return pct_change(self.opex[-1].val, year_ago.val if year_ago else None)


def quarter_near(quarters: list[QuarterFlow], target: date, tolerance_days: int = 20) -> QuarterFlow | None:
    closest = min(quarters, key=lambda q: abs((q.end - target).days), default=None)
    if closest is None or abs((closest.end - target).days) > tolerance_days:
        return None
    return closest


def trailing_sum(quarters: list[QuarterFlow], end: date | None) -> float | None:
    """Sum of four consecutive quarters ending at `end`, or None if any is missing."""
    if end is None:
        return None
    picked = []
    target = end
    for _ in range(4):
        q = quarter_near(quarters, target)
        if q is None:
            return None
        picked.append(q)
        target = q.end - timedelta(days=91)
    return sum(q.val for q in picked)


def margin_at(numerator: list[QuarterFlow], revenue: list[QuarterFlow], end: date) -> float | None:
    num = next((q for q in numerator if q.end == end), None)
    rev = next((q for q in revenue if q.end == end), None)
    if num is None or rev is None or rev.val == 0:
        return None
    return num.val / rev.val * 100


OUTLIER_POINTS = 20  # percentage points from the median margin
OUTLIER_WINDOW = 8  # quarters checked: the ones the report charts


def margin_outliers(margins: list[tuple[date, float]]) -> list[tuple[date, float, float]]:
    """Quarters whose margin sits far from the median of the series: (end, margin, median)."""
    if len(margins) < 4:
        return []
    values = sorted(m for _, m in margins)
    mid = len(values) // 2
    median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
    return [(end, m, median) for end, m in margins if abs(m - median) > OUTLIER_POINTS]


def _best_series(company: dict, tags: list[str]) -> list[QuarterFlow]:
    """The tag whose quarters reach furthest; earlier tags win ties."""
    best: list[QuarterFlow] = []
    for tag in tags:
        quarters = quarterly_flows(facts_for_tag(company, tag))
        if quarters and (not best or quarters[-1].end > best[-1].end):
            best = quarters
    return best


DERIVED_REVENUE_TAG = "GrossProfit + cost of revenue"


def revenue_gap_facts(revenue: list[Fact], gross_profit: list[Fact], cost: list[Fact]) -> list[Fact]:
    """Revenue for periods a filing tagged gross profit and cost of revenue but no revenue
    total (CEVA's 2025 10-K, for example). Revenue is their sum, so nothing is estimated."""
    have = {(f.start, f.end) for f in revenue if f.start is not None}
    costs = {(f.start, f.end): f for f in cost if f.start is not None}
    out = []
    for g in gross_profit:
        key = (g.start, g.end)
        if g.start is None or key in have or key not in costs:
            continue
        c = costs[key]
        out.append(Fact(DERIVED_REVENUE_TAG, g.start, g.end, g.val + c.val, g.form, max(g.filed, c.filed)))
        have.add(key)
    return out


def _subtract(a: list[QuarterFlow], b: list[QuarterFlow]) -> list[QuarterFlow]:
    by_end = {q.end: q for q in b}
    return [QuarterFlow(q.end, q.val - by_end[q.end].val, q.source) for q in a if q.end in by_end]


def debt_at(company: dict, when: date) -> tuple[float | None, list[Fact]]:
    """Carrying value of debt on a balance sheet date, and the facts it was added from."""
    for tags in DEBT_TAG_SETS:
        found = [instant_at(facts_for_tag(company, tag), when) for tag in tags]
        found = [f for f in found if f is not None]
        if found:
            return sum(f.val for f in found), found
    return None, []


@dataclass(frozen=True)
class FilingNote:
    """What a filing says about one quarter, written by hand after reading it."""
    period_end: date
    note: str
    source_url: str
    cost_charge: float | None = None  # one-off charge inside cost of revenue, in dollars


def load_filing_notes(ticker: str, path: Path = FILING_NOTES_PATH) -> list[FilingNote]:
    """Rows of filing_notes.csv for one ticker. A row without a source is rejected."""
    if not path.exists():
        return []
    out = []
    with path.open(newline="", encoding="utf-8") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            if (row.get("ticker") or "").strip().upper() != ticker.upper():
                continue
            if not (row.get("source_url") or "").strip():
                raise ValueError(f"{path.name} line {line}: every note needs a source_url")
            charge = (row.get("cost_of_revenue_charge") or "").strip()
            out.append(FilingNote(
                period_end=date.fromisoformat(row["period_end"].strip()),
                note=row["note"].strip(),
                source_url=row["source_url"].strip(),
                cost_charge=float(charge) if charge else None,
            ))
    return out


def margin_excluding(f: Financials, note: FilingNote) -> float | None:
    """Gross margin for the note's quarter with its one-off cost of revenue charge added back."""
    if note.cost_charge is None:
        return None
    revenue = next((q for q in f.revenue if q.end == note.period_end), None)
    gross = next((q for q in f.gross_profit if q.end == note.period_end), None)
    if not revenue or not gross or not revenue.val:
        return None
    return (gross.val + note.cost_charge) / revenue.val * 100


def compute_financials(company: dict, balance_date: date | None = None) -> Financials:
    """`balance_date` is the date debt is read at; it defaults to the latest equity figure."""
    result = Financials()
    result.revenue = _best_series(company, REVENUE_TAGS)
    if not result.revenue:
        result.notes.append("no revenue found under the known tags")
    else:
        revenue_facts = facts_for_tag(company, result.revenue[-1].source.tag)
        cost_facts = next((fs for fs in (facts_for_tag(company, t) for t in COST_OF_REVENUE_TAGS) if fs), [])
        gaps = revenue_gap_facts(revenue_facts, facts_for_tag(company, GROSS_PROFIT_TAG), cost_facts)
        filled = quarterly_flows(revenue_facts + gaps)
        derived = sorted({q.end for q in filled if q.source.tag == DERIVED_REVENUE_TAG})
        if derived and len(filled) > len(result.revenue):
            result.revenue, revenue_facts = filled, revenue_facts + gaps
            result.notes.append(
                "revenue for the periods ending " + ", ".join(str(d) for d in derived)
                + " is gross profit plus cost of revenue (the filing tagged no revenue total)"
            )
        result.revenue_ytd, _ = year_to_date(revenue_facts, result.revenue[-1].end)

    result.gross_profit = quarterly_flows(facts_for_tag(company, GROSS_PROFIT_TAG))
    if result.revenue and (not result.gross_profit or result.gross_profit[-1].end < result.revenue[-1].end):
        cost = _best_series(company, COST_OF_REVENUE_TAGS)
        derived = _subtract(result.revenue, cost)
        if derived and (not result.gross_profit or derived[-1].end > result.gross_profit[-1].end):
            result.gross_profit = derived
            result.gross_profit_derived = True
            result.notes.append("gross profit is revenue minus cost of revenue (not tagged directly)")

    result.margin_outliers = margin_outliers(result.margins[-OUTLIER_WINDOW:])

    result.opex = _best_series(company, OPERATING_EXPENSE_TAGS)
    result.research = quarterly_flows(facts_for_tag(company, RESEARCH_TAG))
    result.net_income = quarterly_flows(facts_for_tag(company, NET_INCOME_TAG))
    result.equity = latest_instant(facts_for_tag(company, EQUITY_TAG))

    result.debt_date = balance_date or (result.equity.end if result.equity else None)
    if result.debt_date:
        result.debt, result.debt_facts = debt_at(company, result.debt_date)
    if result.debt is None and any(facts_for_tag(company, tag) for tag in DEBT_TAGS):
        result.debt_notes.append(
            f"debt was tagged in earlier filings but not on {result.debt_date}; "
            "check the balance sheet to confirm it was repaid"
        )
    return result

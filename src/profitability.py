"""Path to profitability from a company's EDGAR facts. Pure calculations on parsed facts.

Every measure is over the last four quarters, compared with the four quarters a year earlier:
operating margin and its change, operating income before stock pay, free cash flow, stock pay as
a share of revenue, operating leverage, share count growth and the Rule of 40. The breakeven date
is a straight-line extrapolation of the last year's change, not a forecast.

"Before stock pay" is used instead of each company's own "adjusted EBITDA", which every company
defines differently. Depreciation stays in, because several companies stopped tagging it in the
summary data (BFLY since 2023). For these companies it is small.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from src.edgar import facts_for_tag
from src.financials import FilingNote, Financials, _best_series, _subtract, quarter_near, trailing_sum
from src.metrics import QuarterFlow, pct_change
from src.runway import OPERATING_CASH_FLOW_TAGS

# Within each list the tag whose quarters reach furthest wins (earlier tags win ties).
OPERATING_INCOME_TAGS = ["OperatingIncomeLoss"]
STOCK_PAY_TAGS = ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]

BREAKEVEN_CAP_YEARS = 10.0  # beyond this the straight line says nothing useful


@dataclass
class Profitability:
    end: date | None = None  # latest quarter end
    revenue_ttm: float | None = None
    revenue_ttm_prior: float | None = None
    gross_profit_ttm: float | None = None
    gross_profit_ttm_prior: float | None = None
    opex_ttm: float | None = None
    opex_ttm_prior: float | None = None
    operating_income: list[QuarterFlow] = field(default_factory=list)
    operating_income_derived: bool = False  # gross profit minus opex, not tagged
    stock_pay: list[QuarterFlow] = field(default_factory=list)
    free_cash: list[QuarterFlow] = field(default_factory=list)  # operating cash flow minus capex
    share_growth_pct: float | None = None  # weighted average shares, latest quarter vs a year earlier
    charges_added_back: list[FilingNote] = field(default_factory=list)  # one-offs left out of operating income
    notes: list[str] = field(default_factory=list)

    def _ttm(self, series: list[QuarterFlow], prior: bool = False) -> float | None:
        if self.end is None:
            return None
        end = self.end
        if prior:
            year_ago = quarter_near(series, end - timedelta(days=365))
            if year_ago is None:
                return None
            end = year_ago.end
        return trailing_sum(series, end)

    # --- operating income -------------------------------------------------------------
    @property
    def operating_income_ttm(self) -> float | None:
        return self._ttm(self.operating_income)

    @property
    def operating_income_ttm_prior(self) -> float | None:
        return self._ttm(self.operating_income, prior=True)

    @property
    def operating_margin(self) -> float | None:
        return _pct(self.operating_income_ttm, self.revenue_ttm)

    @property
    def operating_margin_prior(self) -> float | None:
        return _pct(self.operating_income_ttm_prior, self.revenue_ttm_prior)

    @property
    def operating_margin_change(self) -> float | None:
        """Percentage points."""
        if self.operating_margin is None or self.operating_margin_prior is None:
            return None
        return self.operating_margin - self.operating_margin_prior

    # --- before stock pay ---------------------------------------------------------------
    @property
    def stock_pay_ttm(self) -> float | None:
        return self._ttm(self.stock_pay)

    @property
    def stock_pay_pct(self) -> float | None:
        return _pct(self.stock_pay_ttm, self.revenue_ttm)

    @property
    def before_stock_pay_ttm(self) -> float | None:
        return _add(self.operating_income_ttm, self.stock_pay_ttm)

    @property
    def before_stock_pay_ttm_prior(self) -> float | None:
        return _add(self.operating_income_ttm_prior, self._ttm(self.stock_pay, prior=True))

    @property
    def before_stock_pay_margin(self) -> float | None:
        return _pct(self.before_stock_pay_ttm, self.revenue_ttm)

    # --- free cash flow -----------------------------------------------------------------
    @property
    def free_cash_ttm(self) -> float | None:
        return self._ttm(self.free_cash)

    @property
    def free_cash_ttm_prior(self) -> float | None:
        return self._ttm(self.free_cash, prior=True)

    @property
    def free_cash_margin(self) -> float | None:
        return _pct(self.free_cash_ttm, self.revenue_ttm)

    # --- growth and leverage ------------------------------------------------------------
    @property
    def revenue_growth(self) -> float | None:
        return pct_change(self.revenue_ttm, self.revenue_ttm_prior)

    @property
    def gross_profit_growth(self) -> float | None:
        return pct_change(self.gross_profit_ttm, self.gross_profit_ttm_prior)

    @property
    def opex_growth(self) -> float | None:
        return pct_change(self.opex_ttm, self.opex_ttm_prior)

    @property
    def incremental_margin(self) -> float | None:
        """Share of the year's extra revenue that reached operating income, in percent.
        None when revenue did not grow (the ratio would mislead)."""
        oi, oi0 = self.operating_income_ttm, self.operating_income_ttm_prior
        rev, rev0 = self.revenue_ttm, self.revenue_ttm_prior
        if None in (oi, oi0, rev, rev0) or rev - rev0 <= 0:
            return None
        return (oi - oi0) / (rev - rev0) * 100

    @property
    def rule_of_40(self) -> float | None:
        if self.revenue_growth is None or self.free_cash_margin is None:
            return None
        return self.revenue_growth + self.free_cash_margin

    # --- straight-line breakeven --------------------------------------------------------
    @property
    def operating_breakeven_years(self) -> float | None:
        return straight_line_years(self.operating_income_ttm, self.operating_income_ttm_prior)

    @property
    def before_stock_pay_breakeven_years(self) -> float | None:
        return straight_line_years(self.before_stock_pay_ttm, self.before_stock_pay_ttm_prior)

    @property
    def free_cash_breakeven_years(self) -> float | None:
        return straight_line_years(self.free_cash_ttm, self.free_cash_ttm_prior)


def straight_line_years(now: float | None, year_ago: float | None) -> float | None:
    """Years until `now` reaches zero if it keeps changing by the same amount a year.

    0 when already at or above zero, infinity when it is not improving, None without data.
    """
    if now is None or year_ago is None:
        return None
    if now >= 0:
        return 0.0
    improvement = now - year_ago
    if improvement <= 0:
        return math.inf
    return -now / improvement


def add_back_charges(series: list[QuarterFlow], notes: list[FilingNote]) -> tuple[list[QuarterFlow], list[FilingNote]]:
    """Operating income with each noted one-off charge added back to its quarter, and the
    notes that applied."""
    charges = {n.period_end: n for n in notes if n.cost_charge}
    used = [charges[q.end] for q in series if q.end in charges]
    adjusted = [QuarterFlow(q.end, q.val + charges[q.end].cost_charge, q.source) if q.end in charges else q
                for q in series]
    return adjusted, used


def _pct(top: float | None, bottom: float | None) -> float | None:
    if top is None or bottom is None or bottom <= 0:
        return None
    return top / bottom * 100


def _add(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a + b


def compute_profitability(
    company: dict,
    financials: Financials,
    share_growth_pct: float | None = None,
    filing_notes: list[FilingNote] | None = None,
) -> Profitability:
    """`financials` supplies revenue, gross profit and opex (already chosen and checked there);
    `share_growth_pct` comes from dilution.compute_dilution (change_1y_pct).

    One-off cost of revenue charges recorded in filing_notes.csv are added back to operating
    income, so a write-down does not pass for a trend. Free cash flow needs no adjustment: the
    write-downs were non-cash."""
    p = Profitability(share_growth_pct=share_growth_pct)
    latest = financials.latest
    if latest is None:
        p.notes.append("no revenue, so no margins")
        return p
    p.end = latest.end
    p.revenue_ttm = financials.revenue_ttm
    p.revenue_ttm_prior = financials.revenue_ttm_prior
    gross, _ = add_back_charges(financials.gross_profit, filing_notes or [])
    p.gross_profit_ttm = p._ttm(gross)
    p.gross_profit_ttm_prior = p._ttm(gross, prior=True)
    p.opex_ttm = p._ttm(financials.opex)
    p.opex_ttm_prior = p._ttm(financials.opex, prior=True)

    p.operating_income = _best_series(company, OPERATING_INCOME_TAGS)
    if not p.operating_income or p.operating_income[-1].end < latest.end:
        derived = _subtract(financials.gross_profit, financials.opex)
        if derived and (not p.operating_income or derived[-1].end > p.operating_income[-1].end):
            p.operating_income = derived
            p.operating_income_derived = True
            p.notes.append("operating income is gross profit minus operating expenses (not tagged directly)")
    if not p.operating_income:
        p.notes.append("no operating income found")
    p.operating_income, p.charges_added_back = add_back_charges(p.operating_income, filing_notes or [])
    for note in p.charges_added_back:
        p.notes.append(f"gross profit and operating income exclude the one-off ${note.cost_charge / 1e6:.1f}M cost "
                       f"of revenue charge in the quarter ended {note.period_end} (filing_notes.csv)")

    p.stock_pay = _best_series(company, STOCK_PAY_TAGS)
    if not p.stock_pay:
        p.notes.append("no stock pay tagged, so 'before stock pay' figures are missing")

    cash = _best_series(company, OPERATING_CASH_FLOW_TAGS)
    capex = _best_series(company, CAPEX_TAGS)
    capex_by_end = {q.end: q for q in capex}
    p.free_cash = [QuarterFlow(q.end, q.val - capex_by_end[q.end].val, q.source)
                   for q in cash if q.end in capex_by_end]
    if cash and not capex:
        p.notes.append("no capex tagged, so free cash flow is missing")

    for label, series in (("operating income", p.operating_income), ("free cash flow", p.free_cash)):
        if series and series[-1].end < latest.end:
            p.notes.append(f"latest {label} quarter ends {series[-1].end}, revenue {latest.end}")
    return p

import math
from datetime import date

import pytest

from src.financials import FilingNote, compute_financials
from src.profitability import compute_profitability, straight_line_years
from tests.test_runway import company, flow

# Eight quarters, 2024-10-01 to 2026-09-30, all as three-month figures ($M).
ENDS = [("2024-10-01", "2024-12-31"), ("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"),
        ("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31"), ("2026-01-01", "2026-03-31"),
        ("2026-04-01", "2026-06-30"), ("2026-07-01", "2026-09-30")]


def quarters(*values: float) -> list[dict]:
    return [flow(s, e, v * 1e6) for (s, e), v in zip(ENDS, values)]


REVENUE = quarters(10, 10, 10, 10, 15, 15, 15, 15)  # 40 -> 60
GROSS = quarters(6, 6, 6, 6, 9, 9, 9, 9)  # 24 -> 36
OPEX = quarters(10, 10, 10, 10, 11, 11, 11, 11)  # 40 -> 44
OPERATING = quarters(-4, -4, -4, -4, -2, -2, -2, -2)  # -16 -> -8
STOCK_PAY = quarters(1, 1, 1, 1, 1.5, 1.5, 1.5, 1.5)  # 4 -> 6
CASH = quarters(-5, -5, -5, -5, -3, -3, -3, -3)  # -20 -> -12
CAPEX = quarters(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)  # 2 a year


def build(**overrides):
    tags = dict(Revenues=REVENUE, GrossProfit=GROSS, OperatingExpenses=OPEX, OperatingIncomeLoss=OPERATING,
                ShareBasedCompensation=STOCK_PAY, NetCashProvidedByUsedInOperatingActivities=CASH,
                PaymentsToAcquirePropertyPlantAndEquipment=CAPEX)
    tags.update(overrides)
    tags = {k: v for k, v in tags.items() if v is not None}
    c = company(**tags)
    return compute_profitability(c, compute_financials(c), share_growth_pct=12.0)


def test_margins_and_change():
    p = build()
    assert p.operating_income_ttm == -8e6
    assert p.operating_income_ttm_prior == -16e6
    assert p.operating_margin == pytest.approx(-13.333, abs=0.001)
    assert p.operating_margin_prior == -40
    assert p.operating_margin_change == pytest.approx(26.667, abs=0.001)
    assert not p.operating_income_derived


def test_before_stock_pay_free_cash_and_rule_of_40():
    p = build()
    assert p.stock_pay_pct == 10  # 6 / 60
    assert p.before_stock_pay_ttm == -2e6
    assert p.before_stock_pay_margin == pytest.approx(-3.333, abs=0.001)
    assert p.free_cash_ttm == -14e6  # -12 - 2
    assert p.free_cash_margin == pytest.approx(-23.333, abs=0.001)
    assert p.revenue_growth == 50
    assert p.rule_of_40 == pytest.approx(26.667, abs=0.001)
    assert p.share_growth_pct == 12.0


def test_operating_leverage():
    p = build()
    assert p.incremental_margin == 40  # (-8 - -16) / (60 - 40)
    assert p.gross_profit_growth == 50
    assert p.opex_growth == 10


def test_straight_line_breakeven():
    p = build()
    assert p.operating_breakeven_years == 1.0  # -8 improving by 8 a year
    assert p.before_stock_pay_breakeven_years == pytest.approx(0.2)  # -2, was -12 (-16 + 4)
    assert p.free_cash_breakeven_years == pytest.approx(14 / 8)  # -14, was -22
    assert straight_line_years(5, -3) == 0
    assert straight_line_years(-5, -3) == math.inf  # getting worse
    assert straight_line_years(-5, -5) == math.inf  # not improving
    assert straight_line_years(None, -5) is None


def test_operating_income_derived_when_not_tagged():
    p = build(OperatingIncomeLoss=None)
    assert p.operating_income_derived
    assert p.operating_income_ttm == -8e6  # 36 - 44
    assert any("gross profit minus" in n for n in p.notes)


def test_missing_tags_leave_gaps_with_notes():
    p = build(ShareBasedCompensation=None, PaymentsToAcquirePropertyPlantAndEquipment=None)
    assert p.before_stock_pay_ttm is None
    assert p.free_cash_ttm is None
    assert p.rule_of_40 is None
    assert any("stock pay" in n for n in p.notes)
    assert any("capex" in n for n in p.notes)


def test_noted_one_off_charge_is_added_back():
    c = company(Revenues=REVENUE, GrossProfit=GROSS, OperatingExpenses=OPEX, OperatingIncomeLoss=OPERATING)
    note = FilingNote(date(2025, 9, 30), "write-down", "https://www.sec.gov/x", cost_charge=4e6)
    p = compute_profitability(c, compute_financials(c), filing_notes=[note])
    assert p.operating_income_ttm_prior == -12e6  # -16 + 4
    assert p.operating_income_ttm == -8e6
    assert p.gross_profit_ttm_prior == 28e6  # 24 + 4
    assert p.charges_added_back == [note]
    assert any("one-off" in n for n in p.notes)


def test_no_incremental_margin_when_revenue_shrinks():
    p = build(Revenues=quarters(15, 15, 15, 15, 10, 10, 10, 10))
    assert p.incremental_margin is None

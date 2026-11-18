from datetime import date

import pytest

from src.financials import (
    FilingNote,
    compute_financials,
    load_filing_notes,
    margin_excluding,
    margin_outliers,
    trailing_sum,
)
from tests.test_runway import company, flow, instant

# Quarterly revenue ($M): 2024 Q4 9 | 2025 10, 11, 12, 13 | 2026 14, 15, 16.
# Q4s exist only as full-year 10-K totals, as in real filings.
REVENUE = [
    flow("2024-01-01", "2024-09-30", 27e6),
    flow("2024-01-01", "2024-12-31", 36e6, form="10-K"),
    flow("2025-01-01", "2025-03-31", 10e6),
    flow("2025-04-01", "2025-06-30", 11e6),
    flow("2025-07-01", "2025-09-30", 12e6),
    flow("2025-01-01", "2025-09-30", 33e6),
    flow("2025-01-01", "2025-12-31", 46e6, form="10-K"),
    flow("2026-01-01", "2026-03-31", 14e6),
    flow("2026-04-01", "2026-06-30", 15e6),
    flow("2026-07-01", "2026-09-30", 16e6),
]
GROSS_PROFIT = [
    flow("2025-10-01", "2025-12-31", 6.5e6, form="10-K"),
    flow("2026-01-01", "2026-03-31", 7e6),
    flow("2026-04-01", "2026-06-30", 7.5e6),
    flow("2026-07-01", "2026-09-30", 8e6),
]
Q3 = date(2026, 9, 30)


def test_revenue_growth_and_gross_margin():
    result = compute_financials(
        company(RevenueFromContractWithCustomerExcludingAssessedTax=REVENUE, GrossProfit=GROSS_PROFIT,
                LongTermDebt=[instant("2026-09-30", 13.352e6)]),
        balance_date=Q3,
    )
    assert [q.val for q in result.revenue][-5:] == [12e6, 13e6, 14e6, 15e6, 16e6]
    assert result.revenue_ttm == 58e6
    assert result.revenue_ttm_prior == 42e6  # 9 + 10 + 11 + 12
    assert result.growth_ttm == pytest.approx(38.095, abs=0.001)
    assert result.growth_quarter == pytest.approx(33.333, abs=0.001)
    assert result.gross_margin_quarter == 50
    assert result.gross_margin_ttm == 50  # 29 / 58
    assert result.margins[-1] == (Q3, 50)
    assert result.debt == 13.352e6
    assert not result.gross_profit_derived


def test_gross_profit_is_derived_when_not_tagged():
    result = compute_financials(
        company(Revenues=REVENUE, CostOfRevenue=[flow("2026-07-01", "2026-09-30", 6e6)]), balance_date=Q3
    )
    assert result.gross_profit_derived
    assert result.gross_margin_quarter == 62.5
    assert result.gross_margin_ttm is None  # only one quarter of cost data
    assert any("revenue minus cost of revenue" in n for n in result.notes)


def test_missing_full_year_revenue_is_gross_profit_plus_cost():
    # The 2025 10-K tags gross profit and cost of revenue but no revenue total (as CEVA's does).
    revenue = [r for r in REVENUE if not (r["end"] == "2025-12-31")]
    result = compute_financials(company(
        RevenueFromContractWithCustomerExcludingAssessedTax=revenue,
        GrossProfit=[flow("2025-01-01", "2025-12-31", 30e6, form="10-K")],
        CostOfRevenue=[flow("2025-01-01", "2025-12-31", 16e6, form="10-K")],
    ), balance_date=Q3)
    assert [q.val for q in result.revenue][-5:] == [12e6, 13e6, 14e6, 15e6, 16e6]  # Q4 2025 = 46 - 33
    assert result.growth_ttm == pytest.approx(38.095, abs=0.001)
    assert any("2025-12-31 is gross profit plus cost of revenue" in n for n in result.notes)


def test_revenue_is_left_alone_when_nothing_is_missing():
    result = compute_financials(company(
        RevenueFromContractWithCustomerExcludingAssessedTax=REVENUE,
        GrossProfit=[flow("2025-01-01", "2025-12-31", 30e6, form="10-K")],
        CostOfRevenue=[flow("2025-01-01", "2025-12-31", 99e6, form="10-K")],  # disagrees; must not be used
    ), balance_date=Q3)
    assert result.revenue[-4].val == 13e6
    assert not any("gross profit plus cost" in n for n in result.notes)


def test_debt_adds_current_and_noncurrent_and_flags_missing_debt():
    split = compute_financials(
        company(LongTermDebtNoncurrent=[instant("2026-09-30", 10e6)],
                LongTermDebtCurrent=[instant("2026-09-30", 2e6)]),
        balance_date=Q3,
    )
    assert split.debt == 12e6 and len(split.debt_facts) == 2

    old = compute_financials(company(LongTermDebt=[instant("2025-12-31", 5e6)]), balance_date=Q3)
    assert old.debt is None
    assert any("not on 2026-09-30" in n for n in old.debt_notes)

    none = compute_financials(company(), balance_date=Q3)
    assert none.debt is None and none.debt_notes == []  # the report says "None tagged"
    assert any("no revenue" in n for n in none.notes)


def test_one_off_margin_quarters_are_flagged():
    quarters = [(date(2025, 3, 31), 63.0), (date(2025, 6, 30), 64.0), (date(2025, 9, 30), -17.5),
                (date(2025, 12, 31), 67.0), (date(2026, 3, 31), 69.0)]
    assert margin_outliers(quarters) == [(date(2025, 9, 30), -17.5, 64.0)]
    assert margin_outliers(quarters[:3]) == []  # too short to call anything unusual


def test_filing_notes_load_per_ticker_and_need_a_source(tmp_path):
    path = tmp_path / "filing_notes.csv"
    path.write_text(
        "ticker,period_end,note,cost_of_revenue_charge,source_url\n"
        "bfly,2025-09-30,Inventory write-down.,4000000,https://sec.gov/q\n"
        "HYPR,2026-06-30,Other.,,https://sec.gov/h\n",
        encoding="utf-8",
    )
    notes = load_filing_notes("BFLY", path)
    assert notes == [FilingNote(date(2025, 9, 30), "Inventory write-down.", "https://sec.gov/q", 4e6)]
    assert load_filing_notes("HYPR", path)[0].cost_charge is None
    assert load_filing_notes("BFLY", tmp_path / "missing.csv") == []

    path.write_text("ticker,period_end,note,cost_of_revenue_charge,source_url\nBFLY,2025-09-30,x,,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source_url"):
        load_filing_notes("BFLY", path)


def test_margin_excluding_a_one_off_charge():
    result = compute_financials(company(Revenues=REVENUE, GrossProfit=GROSS_PROFIT), balance_date=Q3)
    note = FilingNote(Q3, "", "u", cost_charge=4e6)
    assert margin_excluding(result, note) == 75  # (8 + 4) / 16
    assert margin_excluding(result, FilingNote(Q3, "", "u")) is None
    assert margin_excluding(result, FilingNote(date(2020, 3, 31), "", "u", 1e6)) is None


def test_trailing_sum_needs_four_consecutive_quarters():
    result = compute_financials(company(Revenues=REVENUE[2:5]))  # three 2025 quarters only
    assert trailing_sum(result.revenue, result.revenue[-1].end) is None
    assert result.growth_ttm is None

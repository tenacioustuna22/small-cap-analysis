from datetime import date

from src.metrics import (
    Fact,
    instant_at,
    latest_instant,
    quarterly_flows,
    runway_months,
    trailing_four_quarters,
)


def flow(start: str, end: str, val: float, filed: str = "2026-01-01", form: str = "10-Q") -> Fact:
    return Fact("OCF", date.fromisoformat(start), date.fromisoformat(end), val, form, date.fromisoformat(filed))


def instant(end: str, val: float, filed: str) -> Fact:
    return Fact("Cash", None, date.fromisoformat(end), val, "10-Q", date.fromisoformat(filed))


# A fiscal year reported the way cash flow statements do: year-to-date totals.
YEAR_2025 = [
    flow("2025-01-01", "2025-03-31", -10),
    flow("2025-01-01", "2025-06-30", -25),
    flow("2025-01-01", "2025-09-30", -45),
    flow("2025-01-01", "2025-12-31", -70, form="10-K"),
]


def test_year_to_date_totals_become_single_quarters():
    quarters = quarterly_flows(YEAR_2025)
    assert [q.val for q in quarters] == [-10, -15, -20, -25]
    assert [q.end for q in quarters] == [
        date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31)
    ]


def test_quarters_continue_across_fiscal_years():
    facts = YEAR_2025 + [flow("2026-01-01", "2026-03-31", -30)]
    quarters = quarterly_flows(facts)
    assert [q.val for q in quarters][-2:] == [-25, -30]


def test_restated_value_from_later_filing_wins():
    facts = YEAR_2025 + [flow("2025-01-01", "2025-03-31", -12, filed="2026-05-01")]
    quarters = quarterly_flows(facts)
    assert quarters[0].val == -12
    assert quarters[1].val == -13  # 6-month total of -25 minus restated -12


def test_quarter_skipped_when_previous_total_is_missing():
    # Without the 6-month total, Q3 cannot be isolated from the 9-month total.
    facts = [YEAR_2025[0], YEAR_2025[2]]
    quarters = quarterly_flows(facts)
    assert [q.end for q in quarters] == [date(2025, 3, 31)]


def test_trailing_four_quarters_requires_consecutive_quarters():
    quarters = quarterly_flows(YEAR_2025)
    assert [q.val for q in trailing_four_quarters(quarters)] == [-10, -15, -20, -25]
    assert trailing_four_quarters(quarters[:3]) is None
    gap = quarterly_flows(YEAR_2025 + [flow("2026-04-01", "2026-06-30", -30)])
    assert trailing_four_quarters(gap) is None


def test_latest_instant_prefers_latest_date_then_latest_filing():
    facts = [
        instant("2025-06-30", 100, "2025-08-01"),
        instant("2025-09-30", 80, "2025-11-01"),
        instant("2025-09-30", 82, "2026-02-01"),
    ]
    assert latest_instant(facts).val == 82
    assert instant_at(facts, date(2025, 6, 30)).val == 100
    assert instant_at(facts, date(2024, 12, 31)) is None
    assert latest_instant([]) is None


def test_runway_months():
    assert runway_months(120, 30) == 12
    assert runway_months(120, 0) is None
    assert runway_months(120, -5) is None  # cash flow positive

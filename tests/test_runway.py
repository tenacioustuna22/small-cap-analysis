from datetime import date

from src.runway import compute_runway


def company(**tags: list[dict]) -> dict:
    """Build a dict shaped like the data.sec.gov companyfacts response."""
    return {"facts": {"us-gaap": {tag: {"units": {"USD": entries}} for tag, entries in tags.items()}}}


def instant(end: str, val: float, filed: str = "2026-11-05", form: str = "10-Q") -> dict:
    return {"end": end, "val": val, "form": form, "filed": filed}


def flow(start: str, end: str, val: float, filed: str = "2026-11-05", form: str = "10-Q") -> dict:
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


OCF = [
    flow("2025-01-01", "2025-09-30", -60e6),
    flow("2025-01-01", "2025-12-31", -90e6, form="10-K"),
    flow("2026-01-01", "2026-03-31", -20e6),
    flow("2026-01-01", "2026-06-30", -45e6),
    flow("2026-01-01", "2026-09-30", -75e6),
]
TODAY = date(2026, 11, 12)


def test_runway_from_cash_investments_and_burn():
    facts = company(
        CashAndCashEquivalentsAtCarryingValue=[instant("2026-06-30", 150e6), instant("2026-09-30", 100e6)],
        ShortTermInvestments=[instant("2026-09-30", 20e6)],
        NetCashProvidedByUsedInOperatingActivities=OCF,
    )
    result = compute_runway(facts, today=TODAY)

    assert result.cash.end == date(2026, 9, 30)
    assert result.liquidity == 120e6
    assert result.burn_latest == 30e6  # 75 - 45
    assert result.burn_average == (30e6 + 20e6 + 25e6 + 30e6) / 4
    assert result.months(result.burn_latest) == 12
    assert result.notes == []


def test_investments_from_another_date_are_not_added():
    facts = company(
        CashAndCashEquivalentsAtCarryingValue=[instant("2026-09-30", 100e6)],
        ShortTermInvestments=[instant("2025-12-31", 50e6)],
        NetCashProvidedByUsedInOperatingActivities=OCF,
    )
    result = compute_runway(facts, today=TODAY)
    assert result.investments is None
    assert result.liquidity == 100e6


def test_only_first_matching_investment_tag_is_counted():
    facts = company(
        CashAndCashEquivalentsAtCarryingValue=[instant("2026-09-30", 100e6)],
        ShortTermInvestments=[instant("2026-09-30", 20e6)],
        MarketableSecuritiesCurrent=[instant("2026-09-30", 20e6)],
        NetCashProvidedByUsedInOperatingActivities=OCF,
    )
    assert compute_runway(facts, today=TODAY).liquidity == 120e6


def test_cash_generating_company_has_no_runway_limit():
    facts = company(
        CashAndCashEquivalentsAtCarryingValue=[instant("2026-09-30", 100e6)],
        NetCashProvidedByUsedInOperatingActivities=[flow("2026-07-01", "2026-09-30", 5e6)],
    )
    result = compute_runway(facts, today=TODAY)
    assert result.burn_latest == -5e6
    assert result.months(result.burn_latest) is None


def test_notes_flag_stale_and_mismatched_data():
    facts = company(
        CashAndCashEquivalentsAtCarryingValue=[instant("2026-03-31", 100e6)],
        NetCashProvidedByUsedInOperatingActivities=OCF,
    )
    notes = compute_runway(facts, today=TODAY).notes
    assert any("days old" in n for n in notes)
    assert any("latest cash flow quarter ends 2026-09-30" in n for n in notes)


def test_missing_data_is_reported_not_guessed():
    result = compute_runway(company(), today=TODAY)
    assert result.liquidity is None
    assert result.notes == ["no cash balance found under the known tags"]

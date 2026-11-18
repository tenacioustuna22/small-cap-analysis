from datetime import date

from src.dilution import (
    compute_dilution,
    latest_periodic_report,
    offering_filings,
    use_cover_shares,
)
from src.edgar import Filing

TODAY = date(2026, 11, 12)


def company(**taxonomies: dict[str, tuple[str, list[dict]]]) -> dict:
    """Build companyfacts: taxonomy={tag: (unit, entries)}."""
    return {
        "facts": {
            taxonomy.replace("_", "-"): {
                tag: {"units": {unit: entries}} for tag, (unit, entries) in tags.items()
            }
            for taxonomy, tags in taxonomies.items()
        }
    }


def instant(end: str, val: float, filed: str = "2026-11-05", form: str = "10-Q") -> dict:
    return {"end": end, "val": val, "form": form, "filed": filed}


def period(start: str, end: str, val: float, filed: str = "2026-11-05", form: str = "10-Q") -> dict:
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


WEIGHTED = ("shares", [
    period("2023-07-01", "2023-09-30", 50e6),
    period("2025-07-01", "2025-09-30", 80e6),
    period("2026-01-01", "2026-09-30", 95e6),  # year-to-date average, must be ignored
    period("2026-07-01", "2026-09-30", 100e6),
])
FINANCING = ("USD", [
    period("2025-01-01", "2025-09-30", 10e6),
    period("2025-01-01", "2025-12-31", 30e6, form="10-K"),
    period("2026-01-01", "2026-03-31", 5e6),
    period("2026-01-01", "2026-06-30", 5e6),
    period("2026-01-01", "2026-09-30", 45e6),
])


def test_single_class_company_uses_cover_page_count():
    facts = company(
        dei={"EntityCommonStockSharesOutstanding": ("shares", [instant("2026-11-01", 110e6)])},
        us_gaap={
            "CommonStockSharesOutstanding": ("shares", [instant("2026-09-30", 105e6)]),
            "WeightedAverageNumberOfSharesOutstandingBasic": WEIGHTED,
            "AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShareAmount": (
                "shares",
                [period("2026-01-01", "2026-09-30", 22e6), period("2026-07-01", "2026-09-30", 22e6)],
            ),
            "NetCashProvidedByUsedInFinancingActivities": FINANCING,
        },
    )
    result = compute_dilution(facts, today=TODAY)

    assert result.shares.val == 110e6
    assert result.shares_basis == "cover page"
    assert result.quarter_avg.val == 100e6
    assert result.change_1y_pct == 25
    assert result.change_3y_pct == 100
    assert result.potential_shares == 22e6
    assert not result.potential_is_partial
    assert result.overhang_pct == 20
    assert result.financing_ttm == 20e6 + 5e6 + 0 + 40e6
    assert result.notes == []


def test_multi_class_company_falls_back_to_quarter_average():
    facts = company(
        # A stale count from before the company had several share classes.
        dei={"EntityCommonStockSharesOutstanding": ("shares", [instant("2020-12-31", 10e6)])},
        us_gaap={"WeightedAverageNumberOfSharesOutstandingBasic": WEIGHTED},
    )
    result = compute_dilution(facts, today=TODAY)

    assert result.shares.val == 100e6
    assert result.shares_basis == "quarter average"
    assert any("no point-in-time share count" in n for n in result.notes)

    # The filing's own cover page has the per-class counts that company facts leave out.
    q = Filing("10-Q", date(2026, 11, 5), "", "https://x/q.htm")
    classes = [("us-gaap:CommonClassAMember", 91e6), ("us-gaap:CommonClassBMember", 15e6)]
    assert use_cover_shares(result, 106e6, date(2026, 11, 4), classes, q)
    assert result.shares.val == 106e6 and result.shares.end == date(2026, 11, 4) and result.shares.form == "10-Q"
    assert result.shares_basis == "cover page" and result.share_classes == classes
    assert not any("no point-in-time share count" in n for n in result.notes)
    assert result.overhang_pct is None or result.overhang_pct >= 0
    assert not use_cover_shares(result, 1e6, date(2026, 8, 1), [], q)  # older than what it has


def test_potential_shares_fall_back_to_warrants_plus_options():
    facts = company(
        us_gaap={
            "WeightedAverageNumberOfSharesOutstandingBasic": WEIGHTED,
            "ClassOfWarrantOrRightOutstanding": ("shares", [instant("2026-09-30", 30e6)]),
            "ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsOutstandingNumber": (
                "shares",
                [instant("2025-12-31", 99e6), instant("2026-09-30", 10e6)],
            ),
        },
    )
    result = compute_dilution(facts, today=TODAY)

    assert result.potential_shares == 40e6
    assert result.potential_is_partial
    assert any("warrants and options only" in n for n in result.notes)


def test_sharp_drop_in_shares_is_flagged_as_possible_reverse_split():
    weighted = ("shares", [
        period("2025-07-01", "2025-09-30", 200e6),
        period("2026-07-01", "2026-09-30", 20e6),
    ])
    facts = company(us_gaap={"WeightedAverageNumberOfSharesOutstandingBasic": weighted})
    notes = compute_dilution(facts, today=TODAY).notes
    assert any("reverse split" in n for n in notes)


def test_missing_data_is_reported_not_guessed():
    result = compute_dilution(company(), today=TODAY)
    assert result.shares is None
    assert result.change_1y_pct is None
    assert result.overhang_pct is None
    assert result.financing_ttm is None
    assert any("no weighted average share count" in n for n in result.notes)


def filing(form: str, filed: str) -> Filing:
    return Filing(form, date.fromisoformat(filed), form, f"https://www.sec.gov/Archives/edgar/data/1/{form}")


def test_offering_filings_are_filtered_labelled_and_matched_to_fee_data():
    filings = [
        filing("10-Q", "2026-11-05"),
        filing("S-3", "2026-10-01"),
        filing("S-3/A", "2026-10-15"),
        filing("424B5", "2026-06-01"),
        filing("8-K", "2026-05-01"),
        filing("S-3", "2023-01-01"),  # before the window
    ]
    facts = company(ffd={"TtlOfferingAmt": ("USD", [
        {"end": "2026-09-30", "val": 150e6, "form": "S-3", "filed": "2026-10-01"},
        {"end": "2026-05-14", "val": 3.8e6, "form": "S-8", "filed": "2026-05-14"},
    ])})
    found = offering_filings(filings, facts, since=date(2025, 1, 1))

    assert [(o.filing.form, o.amount) for o in found] == [
        ("S-3/A", None), ("S-3", 150e6), ("424B5", None)
    ]
    assert found[0].label == "shelf registration (amendment)"
    assert latest_periodic_report(filings).form == "10-Q"
    assert latest_periodic_report([]) is None

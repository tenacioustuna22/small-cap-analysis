from datetime import date

from src.catalysts import (
    earnings_from_quote,
    load_catalysts,
    next_filing_deadline,
    parse_when,
    recent_8ks,
    upcoming,
)
from src.edgar import Filing

TODAY = date(2026, 11, 13)


def periodic(form: str, period: date) -> Filing:
    return Filing(form, period, form, "u", report_date=period)


def test_dates_can_be_a_day_month_or_quarter():
    assert parse_when("2027-03-15") == (date(2027, 3, 15), "2027-03-15")
    assert parse_when("2027-02") == (date(2027, 2, 28), "Feb 2027")
    assert parse_when("2027-q2") == (date(2027, 6, 30), "Q2 2027")


def test_catalyst_file_rows_for_one_ticker(tmp_path):
    path = tmp_path / "catalysts.csv"
    path.write_text(
        "ticker,date,type,event,source_url\n"
        "AAA,2027-Q1,FDA,Clearance decision,https://example.com/pr\n"
        "BBB,2027-01-10,earnings,Q4 results,\n"
        "AAA,2026-01-05,launch,Old launch,\n",
        encoding="utf-8",
    )
    rows = load_catalysts("aaa", path)
    assert [c.event for c in rows] == ["Clearance decision", "Old launch"]
    assert [c.event for c in upcoming(rows, TODAY)] == ["Clearance decision"]


def test_next_filing_deadline_by_filer_status_and_year_end():
    filings = [periodic("10-Q", date(2026, 9, 30)), periodic("10-Q", date(2026, 6, 30))]
    small = next_filing_deadline(filings, "Non-accelerated filer<br>Smaller reporting company", "1231", TODAY)
    assert small.day == date(2027, 3, 31)  # 90 days after 2026-12-31: a 10-K
    assert "10-K due for the period ended 2026-12-31" in small.event and small.estimate

    large = next_filing_deadline(filings, "Large accelerated filer", "1231", TODAY)
    assert large.day == date(2027, 3, 1)  # 60 days
    early = next_filing_deadline([periodic("10-Q", date(2026, 6, 30))], "Accelerated filer", "1231", date(2026, 7, 1))
    assert early.day == date(2026, 11, 9) and "10-Q" in early.event  # 40 days after Sep 30
    assert next_filing_deadline([], "", "1231", TODAY) is None


def test_earnings_date_only_when_ahead():
    future = earnings_from_quote({"earningsTimestampStart": 1802000000, "isEarningsDateEstimate": True}, TODAY)
    assert future.day > TODAY and future.estimate and "not confirmed" in future.event
    assert earnings_from_quote({"earningsTimestamp": 1793277000}, TODAY) is None  # 2026-10-29, past
    assert earnings_from_quote({}, TODAY) is None


def test_8k_items_are_named_and_flagged():
    filings = [
        Filing("8-K", date(2026, 9, 18), "", "a", items="3.01"),
        Filing("8-K", date(2026, 11, 9), "", "b", items="2.02,9.01"),
        Filing("8-K", date(2026, 1, 2), "", "c", items="9.01"),
        Filing("10-Q", date(2026, 11, 9), "", "d"),
    ]
    events = recent_8ks(filings, since=date(2026, 1, 1))
    assert [k.filing.url for k in events] == ["b", "a"]  # exhibits-only filing dropped
    assert events[1].items == [("3.01", "Listing rule deficiency or delisting notice", True)]
    assert events[1].flagged and not events[0].flagged

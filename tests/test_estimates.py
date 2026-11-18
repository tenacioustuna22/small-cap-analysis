from datetime import date, datetime

from src.estimates import choose_forward, fiscal_year_end
from src.valuation import compute_valuation

FETCHED = datetime(2026, 11, 16, 22, 0).timestamp()  # 10 pm local on 2026-11-16


def rows(current: tuple, nxt: tuple | None, currency: str = "USD") -> dict:
    """(avg, low, high, analysts, year_ago) for the current and next fiscal year."""
    out = []
    for period, values in (("0y", current), ("+1y", nxt)):
        if values is None:
            continue
        avg, low, high, analysts, year_ago = values
        out.append({"period": period, "avg": avg, "low": low, "high": high, "numberOfAnalysts": analysts,
                    "yearAgoRevenue": year_ago, "growth": None, "currency": currency})
    return {"_fetched": FETCHED, "rows": out}


DEC_2026 = date(2026, 12, 31)
Q3 = date(2026, 9, 30)


def test_december_year_takes_next_fiscal_year():
    f = choose_forward(rows((125e6, 123e6, 126e6, 7, 97.6e6), (150e6, 145e6, 160e6, 7, 125e6)), DEC_2026, Q3)
    assert f.label == "FY2027" and f.period_end == date(2027, 12, 31)
    assert f.average == 150e6 and f.analysts == 7
    assert f.growth == 20
    assert f.as_of == date(2026, 11, 16)
    assert f.notes == []


def test_june_year_takes_the_current_fiscal_year():
    f = choose_forward(rows((100e6, 95e6, 105e6, 3, 90e6), (110e6, 100e6, 120e6, 3, 100e6)), date(2027, 6, 30), Q3)
    assert f.label == "FY ending 2027-06-30" and f.average == 100e6


def test_missing_next_year_falls_back_to_the_current_one():
    f = choose_forward(rows((125e6, 123e6, 126e6, 2, 97.6e6), None), DEC_2026, Q3)
    assert f.label == "FY2026"


def test_no_coverage_zeros_and_other_currencies_give_none():
    assert choose_forward(rows((0, 0, 0, 0, None), (0, 0, 0, 0, None)), DEC_2026, Q3) is None
    assert choose_forward(rows((1e6, 1e6, 1e6, 2, None), (2e6, 2e6, 2e6, 2, None), currency="EUR"), DEC_2026, Q3) is None
    assert choose_forward({"rows": []}, DEC_2026, Q3) is None
    assert choose_forward(rows((1, 1, 1, 1, None), None), None, Q3) is None


def test_single_analyst_and_wide_range_notes():
    f = choose_forward(rows((10e6, 5e6, 9e6, 1, 8e6), (20e6, 10e6, 30e6, 1, 10e6)), DEC_2026, Q3)
    assert any("single analyst" in n for n in f.notes)
    assert any("range widely, from $10.0M to $30.0M" in n for n in f.notes)


def test_fiscal_year_end_from_quote_info():
    assert fiscal_year_end({"nextFiscalYearEnd": 1798675200}) == DEC_2026
    assert fiscal_year_end({}) is None


def test_forward_multiple_on_the_valuation():
    f = choose_forward(rows((125e6, 123e6, 126e6, 7, 97.6e6), (150e6, 145e6, 160e6, 1, 125e6)), DEC_2026, Q3)
    v = compute_valuation(2.0, Q3, None, "", None, 120e6, None, 40e6, 20e6, None, forward=f)
    assert v.ev_forward_sales is None  # no share count, so no EV
    from src.metrics import Fact
    shares = Fact("dei:EntityCommonStockSharesOutstanding", None, Q3, 100e6, "10-Q", Q3)
    v = compute_valuation(2.0, Q3, shares, "cover page", None, 50e6, None, 40e6, 20e6, None, forward=f)
    assert v.ev_forward_sales == 1.0  # (200 - 50) / 150
    assert any("single analyst" in n for n in v.notes)
    assert compute_valuation(2.0, Q3, shares, "cover page", None, 50e6, None, 40e6, 20e6, None).ev_forward_sales is None

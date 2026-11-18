from datetime import date

from src.metrics import Fact
from src.valuation import compute_valuation

Q = date(2026, 9, 30)


def shares(val: float) -> Fact:
    return Fact("Shares", None, Q, val, "10-Q", date(2026, 11, 5))


def make(price=2.0, liquidity=40e6, debt=10e6, revenue=20e6, basis="cover page"):
    return compute_valuation(price, date(2026, 11, 12), shares(100e6), basis, 25e6, liquidity, debt,
                             revenue, 10e6, Fact("Equity", None, Q, 50e6, "10-Q", date(2026, 11, 5)))


def test_market_value_enterprise_value_and_multiples():
    v = make()
    assert v.market_cap == 200e6
    assert v.diluted_market_cap == 250e6
    assert v.enterprise_value == 170e6  # 200 + 10 debt - 40 cash
    assert v.ev_sales == 8.5
    assert v.ev_gross_profit == 17
    assert v.price_book == 4
    assert any("out of the money" in n for n in v.notes)


def test_notes_for_weighted_shares_missing_debt_and_negative_ev():
    v = make(price=0.2, debt=None, basis="quarterly weighted average")
    assert v.enterprise_value == -20e6
    notes = " ".join(v.notes)
    assert "weighted average share count" in notes
    assert "assumes none" in notes
    assert "below its net cash" in notes
    assert make(revenue=0).ev_sales is None

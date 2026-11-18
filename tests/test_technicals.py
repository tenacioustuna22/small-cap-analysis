from datetime import date, timedelta

import pytest

from src.prices import Bar
from src.technicals import completed_bars, compute_technicals, rolling_sma, rsi, short_interest

START = date(2025, 1, 1)


def bars(closes: list[float], volume: float = 1000) -> list[Bar]:
    return [Bar(START + timedelta(days=i), c, c * 1.01, c * 0.99, c, volume) for i, c in enumerate(closes)]


def test_moving_averages_high_low_and_returns():
    series = bars([10 + i * 0.01 for i in range(400)])  # a steady climb
    t = compute_technicals(series)

    assert t.last.close == pytest.approx(13.99)
    assert t.sma50 == pytest.approx(sum(10 + i * 0.01 for i in range(350, 400)) / 50)
    assert t.sma200 == pytest.approx(sum(10 + i * 0.01 for i in range(200, 400)) / 200)
    assert t.vs_sma50 > 0 and t.vs_sma200 > 0
    assert t.trend == "above both averages, with the 50-day above the 200-day"
    assert t.high52 == (series[-1].day, pytest.approx(13.99 * 1.01))
    assert t.from_high == pytest.approx((1 / 1.01 - 1) * 100)
    # 12 months back from 2026-02-04 is 2025-02-04, day 34 of the series.
    assert t.returns["12 months"] == pytest.approx((13.99 / 10.34 - 1) * 100)
    assert len(t.sma200_series) == 201 and len(t.sma50_series) == 351
    assert t.sma50_series[-1] == (series[-1].day, pytest.approx(t.sma50))
    assert t.rsi14 == 100.0  # no down days
    assert t.notes == []


def test_short_history_and_big_moves_are_noted():
    t = compute_technicals(bars([10, 10, 16, 16]))
    assert t.sma50 is None and t.trend == "not enough history"
    assert any("+60% on" in n for n in t.notes)
    assert any("only 4 sessions" in n for n in t.notes)

    split = [Bar(START, 10, 10, 10, 10, 1), Bar(START + timedelta(days=1), 2, 2, 2, 2, 1, split=0.2)]
    assert any("stock split" in n for n in compute_technicals(split).notes)


def test_sessions_below_a_dollar_are_counted_and_noted():
    t = compute_technicals(bars([1.2, 0.9, 1.1, 0.95, 0.8, 0.7]))
    assert t.sessions_below_1 == 3
    assert any("below $1.00 for the last 3 sessions" in n for n in t.notes)
    assert compute_technicals(bars([0.9, 1.0])).sessions_below_1 == 0


def test_rsi_and_rolling_average():
    assert rsi([1, 2] * 10) == pytest.approx(50, abs=5)
    assert rsi([5.0] * 5) is None
    assert rolling_sma(bars([1, 2, 3, 4]), 2) == [(START + timedelta(days=1), 1.5),
                                                 (START + timedelta(days=2), 2.5),
                                                 (START + timedelta(days=3), 3.5)]


def test_live_session_is_left_out():
    series = bars([10, 11, 12])
    last_day = series[-1].day
    stamp = (last_day - date(1970, 1, 1)).days * 86400 + 15 * 3600  # 15:00 UTC that day
    live = {"marketState": "REGULAR", "regularMarketTime": stamp, "gmtOffSetMilliseconds": -18000000}
    kept, dropped = completed_bars(series, live)
    assert dropped and kept[-1].close == 11
    assert completed_bars(series, {**live, "marketState": "POST"}) == (series, False)


def test_short_interest_from_quote_data():
    info = {"sharesShort": 34272659, "shortPercentOfFloat": 0.1593, "shortRatio": 6.72,
            "dateShortInterest": 1793318400, "sharesShortPriorMonth": 31641985}
    s = short_interest(info)
    assert s.pct_float == pytest.approx(15.93)
    assert s.as_of == date(2026, 10, 30)
    assert s.change_pct == pytest.approx(8.31, abs=0.01)
    assert short_interest({}) is None

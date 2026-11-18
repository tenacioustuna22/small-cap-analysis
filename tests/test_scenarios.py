import math
import tomllib
from datetime import date

import pytest

from src.metrics import Fact, QuarterFlow, start_values
from src.scenarios import (
    WHOLE,
    AssumptionError,
    CaseAssumption,
    StreamAssumption,
    TickerAssumptions,
    check_streams,
    cumulative_burn,
    load_assumptions,
    parse_assumptions,
    placeholder_assumptions,
    resolve_start,
    run_all,
    run_case,
)
from tests.test_valuation import make

SPLIT = """
[AAA]
horizons = [5, 3]
split = "By business line"

[AAA.bear]
breakeven_years = "never"
raise_discount_pct = 30
note = "contracts end"
sources = ["https://www.sec.gov/a"]
[AAA.bear.streams.Core]
start = ["ttm", "ytd_annualized"]
growth_pct = 0
ev_sales = 1
[AAA.bear.streams.Embedded]
revenue_by_year = [10, 5, 0, 0, 0]
ev_sales = 0

[AAA.base]
breakeven_years = 4
[AAA.base.streams.Core]
start = "run_rate"
growth_pct = 10
late_growth_pct = 5
ev_sales = 3
[AAA.base.streams.Embedded]
revenue_by_year = [20, 20, 20, 20, 20]
ev_sales = 1

[AAA.bull]
breakeven_years = 2
[AAA.bull.streams.Core]
start = 30
growth_pct = 20
ev_sales = 4
[AAA.bull.streams.Embedded]
revenue_by_year = [30, 40, 50, 60, 70]
ev_sales = 5
"""

WHOLE_COMPANY = """
[BBB.bear]
growth_pct = 0
ev_sales = 1
[BBB.base]
breakeven_years = 3
growth_pct = 20
ev_sales = 2
[BBB.bull]
breakeven_years = 2
growth_pct = 40
ev_sales = 3
note = "share gains"
"""


def parsed(text: str, ticker: str) -> TickerAssumptions:
    return parse_assumptions(ticker, tomllib.loads(text))


def test_split_assumptions_load_with_defaults_and_sorted_horizons():
    a = parsed(SPLIT, "aaa")
    assert a.ticker == "AAA" and a.horizons == (3, 5) and a.split == "By business line"
    bear, base, bull = a.cases
    assert math.isinf(bear.breakeven_years) and bear.raise_discount_pct == 30 and bear.sources == ("https://www.sec.gov/a",)
    core, embedded = bear.streams
    assert core.start == ("ttm", "ytd_annualized") and embedded.revenue_by_year[0] == 10e6
    assert base.streams[0].start == ("run_rate",) and base.raise_discount_pct == 0
    assert bull.streams[0].start == (30e6,)
    assert not a.placeholder
    assert parsed(SPLIT, "ZZZ") is None


def test_whole_company_assumptions_use_one_stream():
    a = parsed(WHOLE_COMPANY, "BBB")
    assert [s.name for c in a.cases for s in c.streams] == [WHOLE] * 3
    assert a.cases[0].streams[0].start == ("ttm",) and a.horizons == (3, 5)
    assert a.cases[2].note == "share gains"
    assert a.caveats == ()


def test_caveats_load_and_are_checked():
    with_caveats = '[BBB]\ncaveats = ["  Raises only at zero cash. ", "No cost cuts."]\n' + WHOLE_COMPANY
    assert parsed(with_caveats, "BBB").caveats == ("Raises only at zero cash.", "No cost cuts.")
    for bad in ('caveats = "one string"', "caveats = [1]", 'caveats = [""]'):
        text = "[BBB]\n" + bad + "\n" + WHOLE_COMPANY
        with pytest.raises(AssumptionError, match="caveats must be a list of sentences"):
            parsed(text, "BBB")


@pytest.mark.parametrize("change, message", [
    (("growth_pct = 0\nev_sales = 1\n", "grwth_pct = 0\nev_sales = 1\n"), "unknown key grwth_pct"),
    (("[BBB.bear]\n", "[BBB.worst]\n"), "unknown case worst"),
    (("ev_sales = 2\n", "\n"), "ev_sales is required"),
    (("breakeven_years = 3\n", 'breakeven_years = "soon"\n'), 'or "never"'),
    (("growth_pct = 40\n", 'growth_pct = "40"\n'), "growth_pct must be a number"),
    (("ev_sales = 3\n", "ev_sales = -1\n"), "ev_sales must be at least 0"),
])
def test_whole_company_mistakes_are_named(change, message):
    with pytest.raises(AssumptionError, match=message):
        parsed(WHOLE_COMPANY.replace(*change, 1), "BBB")


@pytest.mark.parametrize("change, message", [
    (("revenue_by_year = [10, 5, 0, 0, 0]", "revenue_by_year = [10, 5, 0]"), "has 3 years but the longest horizon is 5"),
    (("revenue_by_year = [10, 5, 0, 0, 0]", "revenue_by_year = []"), "non-empty list"),
    (("start = 30\n", 'start = "thirty"\n'), "start 'thirty' is not one of"),
    (("[AAA.bull.streams.Embedded]", "[AAA.bull.streams.Licensing]"), "every case must name the same streams"),
    (("horizons = [5, 3]", "horizons = [2.5]"), "whole years"),
    (('raise_discount_pct = 30', 'raise_discount_pct = 100'), "below 100"),
    (("[AAA.base]\nbreakeven_years = 4\n", "[AAA.base]\nbreakeven_years = 4\ngrowth_pct = 3\n"), "unknown key growth_pct"),
])
def test_split_mistakes_are_named(change, message):
    with pytest.raises(AssumptionError, match=message):
        parsed(SPLIT.replace(*change, 1), "AAA")


def test_missing_case_and_file_errors(tmp_path):
    with pytest.raises(AssumptionError, match="missing case bull"):
        parsed(WHOLE_COMPANY.split("[BBB.bull]")[0], "BBB")
    path = tmp_path / "assumptions.toml"
    path.write_text("[AAA\n", encoding="utf-8")
    with pytest.raises(AssumptionError, match="assumptions.toml"):
        load_assumptions("AAA", path)
    assert load_assumptions("AAA", tmp_path / "none.toml") is None
    path.write_text(WHOLE_COMPANY, encoding="utf-8")
    assert load_assumptions("bbb", path).cases[1].streams[0].growth_pct == 20


def test_streams_must_match_the_split():
    a = parsed(SPLIT, "AAA")
    check_streams(a, ["Core", "Embedded"])
    with pytest.raises(AssumptionError, match="no assumptions for Other"):
        check_streams(a, ["Core", "Embedded", "Other"])
    with pytest.raises(AssumptionError, match="Embedded is not a stream"):
        check_streams(a, ["Core"])


def test_start_values_and_fallbacks():
    latest = QuarterFlow(date(2026, 9, 30), 11e6, Fact("x", date(2026, 7, 1), date(2026, 9, 30), 11e6, "10-Q", date(2026, 10, 29)))
    ytd = Fact("x", date(2026, 1, 1), date(2026, 9, 30), 27.6e6, "10-Q", date(2026, 10, 29))
    values = start_values(latest, None, ytd)
    assert values == {"run_rate": 44e6, "ytd_annualized": pytest.approx(36.8e6)}
    s = StreamAssumption("Core", 1, ("ttm", "ytd_annualized"), 5)
    assert resolve_start(s, values) == ("ytd_annualized", pytest.approx(36.8e6))
    assert resolve_start(s, {"ttm": 50e6, **values}) == ("ttm", 50e6)
    with pytest.raises(AssumptionError, match="no starting revenue for ttm"):
        resolve_start(StreamAssumption("Core", 1, ("ttm",), 5), values)


def test_growth_switches_rate_after_year_three():
    s = StreamAssumption("Core", 2, ("ttm",), growth_pct=10, late_growth_pct=0)
    assert s.revenue_in(3, 100) == pytest.approx(133.1)
    assert s.revenue_in(5, 100) == pytest.approx(133.1)
    assert StreamAssumption("Core", 2, ("ttm",), growth_pct=10).revenue_in(5, 100) == pytest.approx(161.051)


def test_cumulative_burn_falls_in_a_straight_line():
    assert cumulative_burn(40e6, 3, math.inf) == 120e6
    assert cumulative_burn(40e6, 3, 2) == 40e6  # half of 2 years at full burn
    assert cumulative_burn(40e6, 3, 6) == pytest.approx(40e6 * (3 - 9 / 12))
    assert cumulative_burn(-5e6, 3, math.inf) == 0


def test_case_raises_equity_at_a_discount_and_reports_annual_return():
    v = make()  # $40M cash, $10M debt, 100M shares at $2
    case = CaseAssumption("base", math.inf, (StreamAssumption(WHOLE, 4, ("ttm",), 50),), raise_discount_pct=20)
    s = run_case(case, 2, v, 30e6, {WHOLE: {"ttm": 20e6}})
    assert s.revenue == pytest.approx(45e6)  # 20 x 1.5^2
    assert s.enterprise_value == pytest.approx(180e6) and s.implied_ev_sales == pytest.approx(4)
    assert s.cash_burned == 60e6 and s.raised == 20e6
    assert s.raise_price == pytest.approx(1.6) and s.new_shares == pytest.approx(12.5e6)
    assert s.net_cash == pytest.approx(-10e6)  # 40 + 20 - 60 - 10 debt
    assert s.per_share == pytest.approx(170e6 / 112.5e6)
    assert s.annual_return_pct == pytest.approx(((170 / 112.5 / 2) ** 0.5 - 1) * 100)
    assert s.streams[0].start_label == "last four quarters"


def test_streams_with_paths_and_zero_multiples_and_a_floor_at_zero():
    a = parsed(SPLIT, "AAA")
    v = make()
    starts = {"Core": {"ttm": 20e6, "run_rate": 24e6}, "Embedded": {}}
    results = run_all(a, v, 10e6, starts)
    assert [(s.case.case, s.years) for s in results] == [("bear", 3), ("bear", 5), ("base", 3), ("base", 5),
                                                          ("bull", 3), ("bull", 5)]
    bear3 = results[0]
    core, embedded = bear3.streams
    assert core.revenue == 20e6 and core.enterprise_value == 20e6
    assert embedded.revenue == 0 and embedded.enterprise_value == 0 and embedded.start_label == "yearly path"
    base5 = results[3]
    assert base5.streams[0].revenue == pytest.approx(24e6 * 1.1**3 * 1.05**2)
    assert base5.streams[1].revenue == 20e6
    assert results[4].streams[0].start_label == "set in assumptions.toml"

    broke = CaseAssumption("bear", math.inf, (StreamAssumption(WHOLE, 0, ("ttm",), -50),))
    s = run_case(broke, 5, make(liquidity=0, debt=500e6), 0, {WHOLE: {"ttm": 1e6}})
    assert s.per_share == 0 and s.annual_return_pct == -100


def test_a_case_can_set_its_own_starting_burn():
    a = parsed(SPLIT.replace("[AAA.base]\nbreakeven_years = 4\n", "[AAA.base]\nbreakeven_years = 4\nannual_burn = 25\n"), "AAA")
    assert a.cases[1].annual_burn == 25e6 and a.cases[0].annual_burn is None
    results = run_all(a, make(), 10e6, {"Core": {"ttm": 20e6, "run_rate": 24e6}, "Embedded": {}})
    assert results[0].annual_burn == 10e6 and results[0].cash_burned == 30e6  # bear: default, never stops
    base3 = results[2]
    assert base3.annual_burn == 25e6 and base3.cash_burned == pytest.approx(25e6 * (3 - 9 / 8))
    with pytest.raises(AssumptionError, match="annual_burn must be at least 0"):
        parsed(SPLIT.replace("breakeven_years = 4\n", "breakeven_years = 4\nannual_burn = -1\n"), "AAA")


def test_placeholders_cover_three_cases():
    a = placeholder_assumptions(make(), growth_ttm=80)
    assert [c.case for c in a.cases] == ["bear", "base", "bull"] and a.placeholder
    growth = [c.streams[0].growth_pct for c in a.cases]
    assert growth == [25, 50, 75]  # capped at 50, bull 1.5x
    assert [c.streams[0].ev_sales for c in a.cases] == [4.25, 8.5, 8.5]
    assert placeholder_assumptions(make(revenue=None), 30) is None

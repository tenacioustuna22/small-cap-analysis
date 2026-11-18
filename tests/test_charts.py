import math
from datetime import date, timedelta

import pytest

from src.charts import (
    Column,
    Point,
    RangeMark,
    Reference,
    Stack,
    StripRow,
    add_months,
    column_chart,
    fit_horizon,
    line_chart,
    month_year,
    nice_ticks,
    range_chart,
    runway_strip,
    stacked_column_chart,
)

START = date(2026, 9, 30)
TODAY = date(2026, 11, 12)


def test_nice_ticks_cover_the_range_with_round_steps():
    assert nice_ticks(-30.7, 0) == [-40, -30, -20, -10, 0]
    assert nice_ticks(0, 333) == [0, 100, 200, 300, 400]
    assert nice_ticks(-16, 9) == [-20, -10, 0, 10]
    assert nice_ticks(0, 0) == [0, 0.25, 0.5, 0.75, 1]


def test_month_arithmetic():
    assert month_year(add_months(START, 12)) == "Sep 2027"
    assert add_months(START, 9) == date(2027, 6, 30)
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)  # clamps to the month's end
    assert add_months(START, 0.5) == date(2026, 10, 15)


def test_strip_draws_solid_then_pale_and_marks_today():
    html = runway_strip([StripRow("HUMA", "HUMA/x.html", START, 9, 18, "9 to 18 months")], TODAY)

    # 273 of the 1,096 days shown, then another 274.
    assert 'class="fill solid" style="left:0.00%;width:24.91%"' in html
    assert 'class="fill pale end" style="left:calc(24.91% + 2px);width:calc(25.00% - 2px)"' in html
    assert '<a href="HUMA/x.html">HUMA</a>' in html
    assert "to Jun 2027" in html and "to Mar 2028" in html
    assert 'class="today"' in html
    assert "<span>9 to 18 months</span>" in html
    assert ">2027<" in html and ">2029<" in html


def test_strip_clips_long_runways_and_handles_no_burn_and_no_data():
    long_runway = runway_strip([StripRow("", "", START, 63, 162, "")], TODAY)
    assert 'class="fill solid" style="left:0.00%;width:100.00%"' in long_runway  # square end, no pale part
    assert "fill pale" not in long_runway
    assert "strip-body named" not in long_runway

    no_burn = runway_strip([StripRow("A", "", START, 12, math.inf, "")], TODAY)
    assert "beyond the chart" in no_burn

    unknown = runway_strip([StripRow("A", "", START, None, None, "")], TODAY)
    assert 'class="track"></div>' in unknown
    assert runway_strip([], TODAY) == ""


def test_legend_lists_only_the_fills_drawn():
    clipped = runway_strip([StripRow("", "", START, 63, 162, "")], TODAY)
    assert "Only at the lower burn rate</span>" not in clipped
    assert "continues past it" in clipped

    both = runway_strip([StripRow("", "", START, 9, 18, "")], TODAY)
    assert "Only at the lower burn rate</span>" in both
    assert "continues past it" not in both


def test_fit_horizon_stretches_to_show_long_runways():
    long_row = StripRow("", "", START, 63, 162, "")
    assert fit_horizon([long_row]) == 168  # 13.5 years shown on a 14-year timeline
    assert fit_horizon([StripRow("", "", START, 9, 13, "")]) == 36  # never shorter than 3 years
    assert fit_horizon([StripRow("", "", START, 12, math.inf, "")]) == 36
    assert fit_horizon([StripRow("", "", START, 400, 900, "")]) == 180  # capped at 15 years

    html = runway_strip([long_row], TODAY, fit_horizon([long_row]))
    assert 'class="fill pale end"' in html
    assert ">2028<" in html and ">2027<" not in html  # every other year once past 8 years


def column(value: float, label: str = "") -> Column:
    return Column("Sep", "2026", value, "Quarter ended 2026-09-30", f"{value}", "10-Q", label)


def test_columns_hang_below_zero_for_negative_values():
    html = column_chart("Cash flow", "sub", [column(-20), column(10, "$10.0M"), column(0)])

    # Ticks run -30..20, so zero sits 40% from the top.
    assert 'class="bar neg" style="top:40.00%;height:40.00%"' in html
    assert 'class="bar pos" style="top:20.00%;height:20.00%"' in html
    assert html.count('class="bar') == 2  # a zero value draws nothing
    assert html.count('class="val"') == 1  # only the labelled bar prints its value
    assert '<i class="gridline zero" style="top:40.00%">' in html
    assert ">-$30M<" in html
    assert 'data-tip="Quarter ended 2026-09-30|-20|10-Q"' in html
    assert column_chart("t", "", []) == ""


def test_line_chart_positions_points_by_date_and_labels_the_ends():
    points = [
        Point(date(2024, 9, 30), 50, "Quarter ended 2024-09-30", "50.0M", "10-Q"),
        Point(date(2026, 9, 30), 100, "Quarter ended 2026-09-30", "100.0M", "10-Q"),
        Point(date(2025, 9, 30), 80, "Quarter ended 2025-09-30", "80.0M", "10-Q"),
    ]
    html = line_chart("Shares", "sub", points)

    # Axis runs 0..150: 50 sits two thirds down, 100 one third down.
    assert 'points="0.00,66.67 50.00,46.67 100.00,33.33"' in html
    assert html.count('class="dot"') == 3
    assert '<span class="pt-label last" style="top:calc(33.33% - 10px)">100.0M</span>' in html
    assert '<span class="pt-label first" style="top:calc(66.67% - 10px)">50.0M</span>' in html
    assert ">2025<" in html and ">2026<" in html
    assert line_chart("t", "", []) == ""


def test_line_chart_handles_negative_values_and_fitted_axes():
    dips = [Point(date(2025, 3, 31), 60, "", "60%", ""), Point(date(2025, 9, 30), -20, "", "-20%", "")]
    html = line_chart("Margin", "", dips, suffix="%")
    assert ">-25%<" in html and 'class="gridline zero"' in html  # axis reaches below zero
    assert "line-wash" not in html  # no fill when the baseline is not the bottom

    prices = [Point(date(2026, 1, 1), 10, "", "$10", ""), Point(date(2026, 6, 1), 12, "", "$12", "")]
    fitted = line_chart("Price", "", prices, prefix="$", suffix="", zero_based=False)
    assert ">$0<" not in fitted and ">$12<" in fitted
    assert ">Apr<" in fitted  # short spans get month labels


def test_stacked_columns_keep_series_colours_and_mark_empty_quarters():
    stacks = [
        Stack("Mar", "2026", [20.8, 5.7], "Q1", "$26.5M in total", "Core $20.8M · Embedded $5.7M", "$26.5M"),
        Stack("Jun", "2026", [0.0, 0.0], "Q2", "Not reported by stream", "", "n/a"),
        Stack("Sep", "2026", [21.5, 11.1], "Q3", "$32.6M in total", "", "$32.6M"),
    ]
    html = stacked_column_chart("Revenue", "", ["Core", "Embedded"], stacks)
    assert html.count('class="col"') == 3
    assert html.count("bar seg c1") == 2 and html.count("bar seg c2") == 2  # nothing drawn for the empty quarter
    assert 'class="bar seg c2 topmost"' in html and 'class="bar seg c1 lowest"' in html
    assert html.index("seg c2") < html.index("seg c1")  # top segment first, for the readout anchor
    assert '<i class="sw c1"></i>Core' in html and ">n/a</span>" in html
    with pytest.raises(ValueError):
        stacked_column_chart("x", "", ["a", "b", "c", "d"], [])
    with pytest.raises(ValueError):
        stacked_column_chart("x", "", ["a", "b"], [Stack("a", "b", [1.0], "", "", "")])


def test_range_chart_marks_cases_by_shape_against_a_reference():
    rows = [("Bear", [RangeMark(1.0, 0, "Bear, 3 years", "$1.00", ""), RangeMark(0.5, 1, "Bear, 5 years", "$0.50", "")]),
            ("Bull", [RangeMark(9.0, 0, "Bull, 3 years", "$9.00", ""), RangeMark(14.0, 1, "Bull, 5 years", "$14.00", "")])]
    html = range_chart("Value", "", rows, ["3 years", "5 years"], ("Today $6.67", 6.67))
    assert html.count('class="track"') == 2
    assert html.count('class="mark ring"') == 2 and html.count('class="mark disc"') == 2
    assert html.count('class="range-ref"') == 2  # one per track
    assert "Today $6.67</span>" in html and ">$15<" in html  # axis reaches past the largest mark
    with pytest.raises(ValueError):
        range_chart("x", "", rows, ["a", "b", "c"], ("t", 1))


def test_dense_lines_use_hover_slices_and_reference_line():
    start = date(2026, 1, 1)
    daily = [Point(start + timedelta(days=i), 10 + i / 10, f"d{i}", "", "") for i in range(100)]
    slow = Reference("Slow average", [(p.when, 11) for p in daily], "dashed")
    fast = Reference("Fast average", [(p.when, 12) for p in daily[20:]], "solid")
    html = line_chart("Price", "", daily, prefix="$", suffix="", references=[fast, slow],
                      series_label="Close", zero_based=False)
    assert html.count('class="slice"') == 100 and 'class="dot"' not in html
    assert 'class="line-ref solid"' in html and 'class="line-ref dashed"' in html
    assert "Close</span>" in html and "Fast average</span>" in html and "Slow average</span>" in html
    assert 'class="legend"' not in line_chart("Price", "", daily, suffix="")
    with pytest.raises(ValueError):
        line_chart("Price", "", daily, references=[Reference("x", [(daily[0].when, 1)], "dotted")])

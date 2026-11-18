import math
from datetime import date, timedelta

from src.catalysts import Catalyst, EightK
from src.dilution import Dilution, OfferingFiling
from src.edgar import Filing
from src.financials import FilingNote, Financials
from src.ownership import InsiderSummary
from src.prices import Bar
from src.technicals import compute_technicals
from src.scenarios import WHOLE, CaseAssumption, StreamAssumption, TickerAssumptions, run_all
from src.valuation import compute_valuation
from src.metrics import Fact, QuarterFlow
from src.report import (
    TickerReport,
    dilution_headline,
    duration_range,
    render_summary,
    render_ticker_report,
    run_out,
    runway_headline,
    runway_range,
    usd,
)
from src.runway import Runway
from src.streams import compute_split
from tests.test_streams import CHOICE, TAGGED

TODAY = date(2026, 11, 12)
FILED = date(2026, 11, 5)
Q_END = date(2026, 9, 30)


def fact(tag: str, val: float, start: date | None = None) -> Fact:
    return Fact(tag, start, Q_END, val, "10-Q", FILED)


def make_runway(cash: float = 120e6, latest: float = -30e6, average: float = -40e6) -> Runway:
    quarter = QuarterFlow(Q_END, latest, fact("OCF", latest, start=date(2026, 7, 1)))
    older = QuarterFlow(date(2026, 6, 30), average, fact("OCF", average, start=date(2026, 4, 1)))
    trailing = [QuarterFlow(Q_END, average, quarter.source)] * 4
    return Runway(cash=fact("Cash", cash), latest_quarter=quarter, trailing=trailing, quarters=[older, quarter])


def make_report(ticker: str = "TEST", **runway_args: float) -> TickerReport:
    runway = make_runway(**runway_args)
    runway.notes = ["cash figure includes restricted cash"]
    year_ago = Fact("Avg", date(2025, 7, 1), date(2025, 9, 30), 80e6, "10-Q", FILED)
    latest_avg = fact("Avg", 100e6, start=date(2026, 7, 1))
    dilution = Dilution(
        shares=fact("Shares", 100e6),
        shares_basis="cover page",
        quarter_avg=latest_avg,
        quarter_avg_1y=year_ago,
        history=[year_ago, latest_avg],
        potential_shares=25e6,
        potential_as_of=Q_END,
        financing_ttm=40e6,
    )
    shelf = Filing("S-3", date(2026, 10, 1), "S-3", "https://www.sec.gov/Archives/edgar/data/1/s3.htm")
    return TickerReport(
        ticker=ticker,
        company="Test & Co",
        generated=TODAY,
        runway=runway,
        dilution=dilution,
        offerings=[OfferingFiling(shelf, "shelf registration", 150e6)],
        offerings_since=date(2024, 11, 11),
        periodic_report=Filing("10-Q", FILED, "10-Q", "https://www.sec.gov/Archives/edgar/data/1/q.htm"),
        quotes=['We may sell up to $50.0 million under the "Sales Agreement" <ATM>.'],
        earlier_reports=["2026-11-01.html"],
    )


def test_runway_range_and_wording():
    runway = make_runway()  # 120 / 30 = 12 months, 120 / 40 = 9 months
    assert runway_range(runway) == (9, 12)
    assert duration_range(9, 12) == "9 to 12 months"
    assert duration_range(12, 12.2) == "about 12 months"
    assert duration_range(63, 162) == "5.2 to 13.5 years"
    assert duration_range(18, 30) == "18 months to 2.5 years"
    assert duration_range(14, math.inf) == "14 months or more"
    assert duration_range(math.inf, math.inf) == "not burning cash"
    assert duration_range(None, None) == "not available"
    assert run_out(Q_END, 9, 12) == "between Jun 2027 and Sep 2027"
    assert runway_headline(runway) == "Cash lasts 9 to 12 months, running out between Jun 2027 and Sep 2027."


def test_runway_headline_edge_cases():
    assert runway_headline(Runway()) == "Cash runway could not be calculated."
    assert runway_headline(make_runway(latest=5e6, average=2e6)) == "Operations are not burning cash."
    mixed = make_runway(latest=5e6, average=-40e6)
    assert runway_range(mixed) == (9, math.inf)
    assert runway_headline(mixed) == "Cash lasts 9 months or more, running out no earlier than Jun 2027."


def test_dilution_headline():
    assert dilution_headline(make_report().dilution) == "Share count is up 25% over one year."
    assert dilution_headline(Dilution()) == "Share count history is incomplete."


def test_ticker_page_contains_figures_sources_charts_and_quotes():
    text = render_ticker_report(make_report())

    assert text.startswith("<!doctype html>")
    assert "<title>TEST report, 2026-11-12</title>" in text
    assert '<h1 class="wordmark">TEST</h1>' in text
    assert "Test &amp; Co" in text
    assert "Cash lasts 9 to 12 months" in text
    assert '<span class="value">$120.0M</span>' in text
    assert "10-Q, as of 2026-09-30, filed 2026-11-05" in text
    assert 'class="chart strip"' in text
    assert "Operating cash flow by quarter" in text
    assert "Weighted average shares by quarter" in text
    assert "against 80.0M in the quarter ended 2025-09-30" in text
    assert "equal to 25% of shares outstanding" in text
    assert '<a href="https://www.sec.gov/Archives/edgar/data/1/s3.htm">Open on sec.gov</a>' in text
    assert "$150.0M" in text
    assert "<li>We may sell up to $50.0 million under the &quot;Sales Agreement&quot; &lt;ATM&gt;.</li>" in text
    assert "<strong>Data note.</strong> cash figure includes restricted cash" in text
    assert '<a href="2026-11-01.html">2026-11-01</a>' in text
    assert '<a href="../index.html">Watchlist summary</a>' in text


def test_ticker_page_shows_revenue_section_and_debt():
    revenue = [
        QuarterFlow(date(2025, 12, 31), 10e6, Fact("Rev", date(2025, 1, 1), date(2025, 12, 31), 40e6, "10-K", FILED)),
        QuarterFlow(Q_END, 12e6, fact("Rev", 12e6, start=date(2026, 7, 1))),
    ]
    report = make_report()
    report.financials = Financials(
        revenue=revenue,
        gross_profit=[QuarterFlow(Q_END, 6e6, fact("GP", 6e6, start=date(2026, 7, 1)))],
        debt=20e6,
        debt_facts=[fact("LongTermDebt", 20e6)],
    )
    text = render_ticker_report(report)
    assert 'id="revenue"' in text
    assert "Revenue was $12.0M in the quarter ended 2026-09-30." in text
    assert "10-K filed 2026-11-05: 12-month total minus the earlier quarters" in text
    assert '<span class="value">50.0%</span>' in text
    assert '<span class="value">$20.0M</span>' in text
    assert '<span class="value">$100.0M</span>' in text  # $120M cash minus $20M debt
    assert "From the filing" not in text

    report.financials.margin_outliers = [(Q_END, 50.0, 70.0)]
    assert "Check that filing for a one-off charge" in render_ticker_report(report)
    report.filing_notes = [FilingNote(Q_END, "Inventory charge.", "https://x/q", 1.2e6),
                           FilingNote(date(2025, 12, 31), "Something else.", "https://x/k")]
    text = render_ticker_report(report)
    assert "Check that filing" not in text
    assert "<strong>From the filing.</strong> Gross margin in the quarter ended 2026-09-30 was 50.0%" in text
    assert "Without the $1.2M charge, gross margin would have been 60.0% (estimate" in text  # (6 + 1.2) / 12
    assert '<a href="https://x/q">Source</a>' in text
    assert "From the filing, quarter ended 2025-12-31.</strong> Something else." in text
    assert "includes a $1.2M one-off charge" in text  # on the margin chart's hover


def test_ticker_page_renders_every_new_section_and_links_them():
    report = make_report()
    bars = [Bar(date(2026, 1, 1) + timedelta(days=i), 1, 1, 1, 1 + i / 100, 1000) for i in range(300)]
    report.technicals = compute_technicals(bars)
    report.valuation = compute_valuation(2.0, TODAY, report.dilution.shares, "cover page", 25e6,
                                         120e6, None, 40e6, 20e6, None)
    report.assumptions = TickerAssumptions("TEST", tuple(
        CaseAssumption(case, 3, (StreamAssumption(WHOLE, multiple, ("ttm",), growth),), raise_discount_pct=10,
                       note=f"{case} note", sources=("https://x/src",))
        for case, growth, multiple in (("bear", 0, 1), ("base", 20, 4), ("bull", 40, 6))
    ))
    report.scenarios = run_all(report.assumptions, report.valuation, 40e6, {WHOLE: {"ttm": 40e6}})
    report.insiders = InsiderSummary(since=date(2025, 11, 12))
    report.catalysts = [Catalyst(date(2027, 3, 31), "2027-03-31", "10-K due", "filing deadline", "", "SEC", True)]
    report.eight_ks = [EightK(Filing("8-K", date(2026, 9, 18), "", "https://x/8k.htm"),
                              [("3.01", "Listing rule deficiency or delisting notice", True)])]
    report.eight_k_since = date(2025, 11, 12)
    text = render_ticker_report(report)

    for anchor in ("runway", "dilution", "valuation", "catalysts", "price", "ownership"):
        assert f'id="{anchor}"' in text and f'href="#{anchor}"' in text
    assert 'href="#revenue"' not in text  # no financials, no link
    assert "Valued at 2.0x trailing sales" in text  # (200 - 120) / 40
    assert "Next dated event, 2027-03-31: 10-K due (estimate)." in text
    assert "<strong>Listing rule deficiency or delisting notice</strong>" in text
    assert "No open-market insider buying or selling in the last 12 months." in text
    assert "market value (no debt tagged)" in text
    assert "<h3>Scenarios, 3 and 5 years out</h3>" in text
    assert "Base case, 3 years: $" in text and "within a range of $" in text
    assert 'class="chart range"' in text and text.count('class="mark ') == 6
    assert "from last four quarters, +20% a year; 4.0x sales at the end" in text
    assert '<a href="https://x/src">source 1</a>' in text and "base note" in text
    assert "Show revenue and value by stream" in text and "Placeholder assumptions" not in text

    summary = render_summary([report], TODAY, link_prefix="")
    assert "Base case value per share" in summary and " in 3 years</td>" in summary


def test_profitability_section_peer_table_and_summary_column():
    from src.financials import compute_financials
    from src.profitability import compute_profitability
    from src.sections import PeerRow
    from tests.test_profitability import build as build_profitability
    from tests.test_runway import company

    report = make_report()
    report.profitability = build_profitability()
    report.valuation = compute_valuation(2.0, TODAY, report.dilution.shares, "cover page", None,
                                         120e6, None, 60e6, 36e6, None)
    other = compute_profitability(company(), compute_financials(company()))
    report.peers = [PeerRow("TEST", "", report.valuation, None, is_self=True, profitability=report.profitability),
                    PeerRow("PEER", "../PEER/x.html", None, None, profitability=other)]
    text = render_ticker_report(report)

    assert 'id="profitability"' in text and 'href="#profitability"' in text
    assert "Operating loss was 13% of revenue over the last four quarters, 27 points better than a year earlier" in text
    assert "free cash flow was -23% of revenue." in text
    assert "Operating income by quarter" in text and "Free cash flow by quarter" in text
    assert "1.0 yrs · 0.2 yrs · 1.8 yrs" in text  # the stat
    assert '<td class="num">1.0 / 0.2 / 1.8</td>' in text
    assert "<h3>Against the comparison companies</h3>" in text and '<a href="../PEER/x.html">PEER</a>' in text

    summary = render_summary([report], TODAY, link_prefix="")
    assert "-13% (+27 pts)" in summary


def test_forward_multiple_stat_peer_columns_and_summary():
    from src.estimates import choose_forward
    from src.sections import PeerRow
    from tests.test_estimates import DEC_2026, Q3, rows

    report = make_report()
    forward = choose_forward(rows((125e6, 123e6, 126e6, 7, 97.6e6), (150e6, 145e6, 160e6, 7, 125e6)), DEC_2026, Q3)
    report.valuation = compute_valuation(2.0, TODAY, report.dilution.shares, "cover page", None,
                                         120e6, None, 60e6, 36e6, None, forward=forward)
    report.peers = [PeerRow("TEST", "", report.valuation, None, is_self=True),
                    PeerRow("PEER", "", compute_valuation(1.0, TODAY, report.dilution.shares, "cover page", None,
                                                         10e6, None, 60e6, 36e6, None), None)]
    text = render_ticker_report(report)
    ev = report.valuation.enterprise_value
    assert "EV / next year&#x27;s sales, consensus" in text
    assert f"FY2027 consensus $150.0M ($145.0M to $160.0M), 7 analysts; Yahoo analyst consensus" in text
    assert f"{ev / 150e6:.1f}x" in text
    assert "<td class=\"num\">+20%</td><td class=\"num\">7</td>" in text
    assert "<td class=\"num\">none</td>" in text  # the peer without coverage
    summary = render_summary([report], TODAY, link_prefix="")
    assert "EV / next year&#x27;s sales, consensus" in summary


def test_revenue_split_block_and_summary_column():
    no_q4 = [t for t in TAGGED if t[0].form != "10-K"]
    reported = [QuarterFlow(date.fromisoformat(x), 1, fact("Rev", 1)) for x in ("2025-09-30", "2025-12-31", "2026-03-31")]
    report = make_report()
    report.financials = Financials(revenue=reported)
    report.revenue_splits = [compute_split(TAGGED, CHOICE), compute_split(no_q4, CHOICE, reported)]
    text = render_ticker_report(report)
    assert "<h3>Revenue by product and service</h3>" in text
    assert "Quarter ended 2026-03-31 against a year earlier: Product +40% (70% of revenue), " \
           "Software and other services +20% (30% of revenue)." in text
    assert "Gross margin, quarter" in text and "64.3%" in text
    assert "Not reported by stream" in text
    assert '<td class="num">not reported</td>' in text

    summary = render_summary([report], TODAY, link_prefix="")
    assert "Growth by stream, 4 quarters unless stated" in summary
    assert "Product n/a · Software and other services n/a" in summary  # only one year of history
    assert "not split" in render_summary([make_report()], TODAY, link_prefix="")


def test_ticker_page_handles_missing_data():
    text = render_ticker_report(TickerReport("NONE", "", TODAY, Runway(), Dilution()))
    assert "Cash runway could not be calculated." in text
    assert "Share count history is incomplete." in text
    assert "None in this period." in text
    assert 'class="chart strip"' not in text


def test_summary_ranks_by_shortest_runway_and_links_with_the_given_prefix():
    safe = make_report("SAFE", cash=400e6)
    tight = make_report("TIGHT", cash=60e6)
    text = render_summary([safe, tight], TODAY, link_prefix="")

    assert "TIGHT has the shortest runway: 4 to 6 months." in text
    assert text.index('href="TIGHT/2026-11-12.html"') < text.index('href="SAFE/2026-11-12.html"')
    assert "<strong>Data note.</strong> SAFE: cash figure includes restricted cash" in text
    assert 'href="../SAFE/2026-11-12.html"' in render_summary([safe, tight], TODAY)


def test_usd():
    assert usd(64.5e6) == "$64.5M"
    assert usd(-15e6) == "-$15.0M"
    assert usd(None) == "n/a"

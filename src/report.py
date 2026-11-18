"""Render analysis results as self-contained HTML pages. No network access.

Each page embeds its stylesheet and script from src/assets, so a report opens offline
and keeps looking the same after the assets change.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from src.charts import (
    MONTHS,
    Column,
    Point,
    StripRow,
    add_months,
    column_chart,
    fit_horizon,
    line_chart,
    month_year,
    runway_strip,
)
from src.dilution import Dilution, OfferingFiling
from src.edgar import Filing
from src.html_kit import (  # noqa: F401  (re-exported for callers and tests)
    DISCLAIMER,
    dollars,
    growth,
    e,
    multiple,
    notes,
    page,
    money,
    percent,
    share_count,
    small,
    source,
    stat,
    table,
    usd,
)
from src.financials import FilingNote, Financials
from src.streams import RevenueSplit, member_label
from src.metrics import Fact
from src.profitability import Profitability
from src.runway import Runway
from src.catalysts import Catalyst, EightK
from src.ownership import HolderFiling, InsiderSummary
from src.sections import (
    PeerRow,
    catalysts_section,
    financials_section,
    ownership_section,
    points,
    price_section,
    profitability_section,
    valuation_section,
)
from src.technicals import Technicals
from src.scenarios import Scenario, TickerAssumptions
from src.valuation import Valuation

BURN_HISTORY_QUARTERS = 8


@dataclass
class TickerReport:
    ticker: str
    company: str
    generated: date
    runway: Runway
    dilution: Dilution
    offerings: list[OfferingFiling] = field(default_factory=list)
    offerings_since: date | None = None
    periodic_report: Filing | None = None  # the 10-Q or 10-K the quotes come from
    quotes: list[str] = field(default_factory=list)
    earlier_reports: list[str] = field(default_factory=list)  # file names of older reports
    financials: Financials | None = None
    profitability: Profitability | None = None
    filing_notes: list[FilingNote] = field(default_factory=list)  # from filing_notes.csv
    revenue_splits: list[RevenueSplit] = field(default_factory=list)  # as chosen in revenue_streams.csv
    technicals: Technicals | None = None
    price_error: str = ""  # why price data is missing, shown on the page
    valuation: Valuation | None = None
    scenarios: list[Scenario] = field(default_factory=list)  # every case at every horizon
    assumptions: TickerAssumptions | None = None
    peers: list[PeerRow] = field(default_factory=list)  # comparison rows, this ticker included
    insiders: InsiderSummary | None = None
    holders: list[HolderFiling] = field(default_factory=list)
    holders_since: date | None = None
    ownership_error: str = ""
    catalysts: list[Catalyst] = field(default_factory=list)  # upcoming, soonest first
    eight_ks: list[EightK] = field(default_factory=list)
    eight_k_since: date | None = None


# --- runway and dilution wording ---------------------------------------------------

def duration(months: float) -> str:
    if months < 23.5:
        return f"{months:.0f} months"
    return f"{months / 12:.1f} years"


def runway_text(runway: Runway, burn: float | None) -> str:
    if runway.liquidity is None or burn is None:
        return "n/a"
    months = runway.months(burn)
    return "not burning cash" if months is None else duration(months)


def runway_range(runway: Runway) -> tuple[float | None, float | None]:
    """Shortest and longest runway in months across the two burn rates.

    inf means operations were not burning cash at that rate; None means no data.
    """
    values = []
    for burn in (runway.burn_latest, runway.burn_average):
        if runway.liquidity is None or burn is None:
            continue
        months = runway.months(burn)
        values.append(math.inf if months is None else months)
    if not values:
        return None, None
    return min(values), max(values)


def duration_range(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "not available"
    if math.isinf(low):
        return "not burning cash"
    if math.isinf(high):
        return f"{duration(low)} or more"
    shorter, longer = duration(low), duration(high)
    if shorter == longer:
        return f"about {shorter}"
    if shorter.split()[1] == longer.split()[1]:
        return f"{shorter.split()[0]} to {longer}"
    return f"{shorter} to {longer}"


def run_out(start: date, low: float | None, high: float | None) -> str:
    """When the cash runs out, as a phrase that follows 'running out'."""
    if low is None or high is None or math.isinf(low):
        return ""
    first = month_year(add_months(start, low))
    if math.isinf(high):
        return f"no earlier than {first}"
    last = month_year(add_months(start, high))
    return f"around {first}" if first == last else f"between {first} and {last}"


def runway_headline(runway: Runway) -> str:
    low, high = runway_range(runway)
    if low is None or runway.cash is None:
        return "Cash runway could not be calculated."
    if math.isinf(low):
        return "Operations are not burning cash."
    return f"Cash lasts {duration_range(low, high)}, running out {run_out(runway.cash.end, low, high)}."


def dilution_headline(dilution: Dilution) -> str:
    def phrase(pct: float) -> str:
        if round(pct) == 0:
            return "flat"
        return f"{'up' if pct > 0 else 'down'} {abs(pct):.0f}%"

    one, three = dilution.change_1y_pct, dilution.change_3y_pct
    if one is None and three is None:
        return "Share count history is incomplete."
    if one is None:
        return f"Share count is {phrase(three)} over three years."
    if three is None:
        return f"Share count is {phrase(one)} over one year."
    return f"Share count is {phrase(one)} over one year and {phrase(three)} over three."


# --- building blocks ---------------------------------------------------------------

def strip_row(report: TickerReport, name: str = "", href: str = "", with_text: bool = False) -> StripRow | None:
    runway = report.runway
    if runway.cash is None:
        return None
    low, high = runway_range(runway)
    text = ""
    if with_text:
        text = duration_range(low, high)
        out = run_out(runway.cash.end, low, high)
        if out:
            text += f", running out {out}"
    return StripRow(name, href, runway.cash.end, low, high, text)


# --- per-ticker page ---------------------------------------------------------------

def render_ticker_report(report: TickerReport) -> str:
    runway, dilution = report.runway, report.dilution
    parts = [
        '<header class="masthead"><div>'
        f'<h1 class="wordmark">{e(report.ticker)}</h1>'
        + (f'<p class="company">{e(report.company)}</p>' if report.company else "")
        + "</div>"
        f'<p class="meta">SEC filings as of {report.generated}<br>'
        '<a href="../index.html">Watchlist summary</a></p></header>'
    ]

    # Cash runway
    block = ['<section class="block" id="runway"><p class="eyebrow">Cash runway</p>', f"<h2>{e(runway_headline(runway))}</h2>"]
    if runway.cash is not None:
        pieces = []
        if runway.burn_latest is not None:
            pieces.append(f"{runway_text(runway, runway.burn_latest)} at last quarter's burn of {usd(runway.burn_latest)}")
        if runway.burn_average is not None:
            pieces.append(
                f"{runway_text(runway, runway.burn_average)} at the four-quarter average of "
                f"{usd(runway.burn_average)} a quarter"
            )
        lede = f"Starting from {usd(runway.liquidity)} on {runway.cash.end}"
        if pieces:
            lede += ": " + ", and ".join(pieces)
        block.append(f'<p class="lede">{e(lede)}.</p>')
        row = strip_row(report)
        if row:
            block.append(runway_strip([row], report.generated, fit_horizon([row])))

    cash_detail = source(runway.cash)
    if runway.investments:
        cash_detail = (
            f"{usd(runway.cash.val)} cash plus {usd(runway.investments.val)} short-term investments. {cash_detail}"
        )
    latest = runway.latest_quarter
    block.append(
        '<dl class="stats">'
        + stat("Cash and short-term investments", usd(runway.liquidity), cash_detail)
        + stat("Operating cash burn, last quarter", usd(runway.burn_latest), source(latest.source) if latest else "")
        + stat(
            "Operating cash burn, four-quarter average",
            usd(runway.burn_average),
            "average of the four quarters charted below" if runway.trailing else "",
        )
        + debt_stats(runway, report.financials)
        + "</dl>"
    )
    block.append(
        '<p class="small">Runway is cash and short-term investments divided by operating cash burn. '
        "Capital spending, debt repayments and long-term investments are not included.</p>"
    )
    block.append(notes(runway.notes + (report.financials.debt_notes if report.financials else [])))

    quarters = runway.quarters[-BURN_HISTORY_QUARTERS:]
    if quarters:
        worst = min(quarters, key=lambda q: q.val)
        block.append(
            column_chart(
                "Operating cash flow by quarter",
                "In $ millions. Below the line means cash was used. Check for one-off quarters before trusting the average.",
                [
                    Column(
                        top=MONTHS[q.end.month - 1],
                        bottom=str(q.end.year),
                        value=q.val / 1e6,
                        tip_head=f"Quarter ended {q.end}",
                        tip_value=usd(q.val),
                        tip_detail=f"{q.source.form} filed {q.source.filed}",
                        label=usd(q.val) if q is quarters[-1] or q is worst else "",
                    )
                    for q in quarters
                ],
            )
        )
        block.append(
            "<details><summary>Show as a table, with the filing each figure came from</summary>"
            + table(
                [("Quarter ended", "date"), ("Operating cash flow", "num"), ("Reported in", "")],
                [
                    [str(q.end), e(usd(q.val)), e(f"{q.source.form} filed {q.source.filed}")]
                    for q in reversed(quarters)
                ],
            )
            + "</details>"
        )
    block.append("</section>")
    parts.append("".join(block))
    parts.append(financials_section(report.financials, report.filing_notes, report.revenue_splits))
    parts.append(profitability_section(report.profitability, report.peers))

    # Dilution
    block = ['<section class="block" id="dilution"><p class="eyebrow">Dilution</p>', f"<h2>{e(dilution_headline(dilution))}</h2>"]
    shares = dilution.shares
    potential_label = "Potential new shares"
    if dilution.potential_is_partial:
        potential_label += " (warrants and options only)"
    overhang = dilution.overhang_pct
    potential_detail = f"as of {dilution.potential_as_of}" if dilution.potential_as_of else ""
    if overhang is not None:
        potential_detail = f"equal to {percent(overhang, signed=False)} of shares outstanding, {potential_detail}"
    shares_detail = f"{dilution.shares_basis}: {source(shares)}" if shares else ""
    if dilution.share_classes:
        shares_detail += "; " + " + ".join(
            f"{member_label(member)} {share_count(count)}" for member, count in dilution.share_classes
        )
    block.append(
        '<dl class="stats">'
        + stat("Shares outstanding", share_count(shares.val if shares else None), shares_detail)
        + stat("Change over one year", percent(dilution.change_1y_pct), _comparison(dilution.quarter_avg_1y))
        + stat("Change over three years", percent(dilution.change_3y_pct), _comparison(dilution.quarter_avg_3y))
        + stat(potential_label, share_count(dilution.potential_shares), potential_detail)
        + stat("Net financing cash, last four quarters", usd(dilution.financing_ttm), "equity and debt combined")
        + "</dl>"
    )
    block.append(
        '<p class="small">Potential new shares are what options, warrants, RSUs, convertibles and '
        "earnouts could add, including ones far out of the money.</p>"
    )
    block.append(notes(dilution.notes))

    if dilution.history:
        block.append(
            line_chart(
                "Weighted average shares by quarter",
                "In millions. Fourth quarters are missing because annual reports give only the full-year average.",
                [
                    Point(
                        when=f.end,
                        value=f.val / 1e6,
                        tip_head=f"Quarter ended {f.end}",
                        tip_value=share_count(f.val),
                        tip_detail=f"{f.form} filed {f.filed}",
                    )
                    for f in dilution.history
                ],
            )
        )
        block.append(
            "<details><summary>Show as a table, with the filing each figure came from</summary>"
            + table(
                [("Quarter ended", "date"), ("Weighted average shares", "num"), ("Reported in", "")],
                [
                    [str(f.end), e(share_count(f.val)), e(f"{f.form} filed {f.filed}")]
                    for f in reversed(dilution.history)
                ],
            )
            + "</details>"
        )

    since = f" since {report.offerings_since}" if report.offerings_since else ""
    block.append(f"<h3>Registration and offering filings{since}</h3>")
    if report.offerings:
        block.append(
            table(
                [("Filed", "date"), ("Form", "form"), ("What it is", ""), ("Registered", "num"), ("Document", "")],
                [
                    [
                        str(o.filing.filed),
                        e(o.filing.form),
                        e(o.label),
                        e(usd(o.amount)) if o.amount else "",
                        f'<a href="{e(o.filing.url)}">Open on sec.gov</a>',
                    ]
                    for o in report.offerings
                ],
            )
        )
    else:
        block.append('<p class="small">None in this period.</p>')

    if report.periodic_report:
        filing = report.periodic_report
        block.append("<h3>What the latest report says about selling programs</h3>")
        block.append(
            f'<p class="small">Sentences about shelf registrations, at-the-market programs and equity lines, '
            f'quoted from the <a href="{e(filing.url)}">{e(filing.form)} filed {filing.filed}</a>. '
            "This is raw text, so a stray page header can appear mid-sentence.</p>"
        )
        if report.quotes:
            block.append(
                f"<details><summary>Show {len(report.quotes)} quoted sentences</summary>"
                '<ul class="quotes">' + "".join(f"<li>{e(q)}</li>" for q in report.quotes) + "</ul></details>"
            )
        else:
            block.append('<p class="small">No sentences about these programs were found.</p>')
    block.append("</section>")
    parts.append("".join(block))
    parts.append(valuation_section(report.ticker, report.valuation, report.scenarios, report.peers, report.assumptions))
    if report.eight_k_since:
        parts.append(catalysts_section(report.catalysts, report.eight_ks, report.eight_k_since))
    parts.append(price_section(report.technicals, report.price_error))
    parts.append(ownership_section(report.insiders, report.holders, report.holders_since, report.ownership_error))

    footer = [f"<p>Generated {report.generated} from SEC EDGAR data and yfinance prices. {DISCLAIMER}</p>"]
    if report.earlier_reports:
        links = ", ".join(
            f'<a href="{e(name)}">{e(name.removesuffix(".html"))}</a>' for name in report.earlier_reports
        )
        footer.append(f"<p>Earlier reports: {links}</p>")
    parts.append("<footer>" + "".join(footer) + "</footer>")
    parts.insert(1, section_nav("".join(parts)))

    title = f"{report.ticker} report, {report.generated}"
    return page(title, "\n".join(parts))


SECTIONS = [
    ("runway", "Runway"),
    ("revenue", "Revenue"),
    ("profitability", "Profitability"),
    ("dilution", "Dilution"),
    ("valuation", "Valuation"),
    ("catalysts", "Catalysts"),
    ("price", "Price"),
    ("ownership", "Insiders"),
]


def section_nav(body: str) -> str:
    """Links to the sections a page actually has, in page order."""
    links = "".join(f'<a href="#{anchor}">{label}</a>' for anchor, label in SECTIONS if f'id="{anchor}"' in body)
    return f'<nav class="toc" aria-label="Sections">{links}</nav>' if links else ""


def debt_stats(runway: Runway, financials: Financials | None) -> str:
    """Debt and cash net of debt, for the runway section. Empty without financials."""
    if financials is None:
        return ""
    if financials.debt is None:
        return stat("Debt", "None tagged", "no debt in the XBRL data; confirm on the balance sheet")
    detail = ", ".join(sorted({f.tag for f in financials.debt_facts}))
    first = financials.debt_facts[0]
    debt = stat("Debt, carrying value", usd(financials.debt), f"{detail}: {source(first)}")
    if runway.liquidity is None:
        return debt
    return debt + stat(
        "Cash and investments minus debt",
        usd(runway.liquidity - financials.debt),
        "leases not counted as debt",
    )


def _comparison(earlier: Fact | None) -> str:
    if earlier is None:
        return "no comparable quarter"
    return f"against {share_count(earlier.val)} in the quarter ended {earlier.end}"


# --- watchlist summary --------------------------------------------------------------

def render_summary(reports: list[TickerReport], generated: date, link_prefix: str = "../") -> str:
    """One page comparing every ticker. `link_prefix` leads from this page to reports/."""

    def href(report: TickerReport) -> str:
        return f"{link_prefix}{report.ticker}/{generated}.html"

    def link(report: TickerReport) -> str:
        return f'<a href="{e(href(report))}">{e(report.ticker)}</a>'

    def shortest(report: TickerReport) -> float:
        low, _ = runway_range(report.runway)
        return math.inf if low is None else low

    ranked = sorted(reports, key=shortest)
    parts = [
        '<header class="masthead"><div><h1 class="wordmark">Watchlist</h1>'
        f'<p class="company">{len(reports)} companies, ranked by how soon the cash runs out</p></div>'
        f'<p class="meta">SEC filings as of {generated}</p></header>'
    ]

    block = ['<section class="block"><p class="eyebrow">Cash runway</p>']
    if ranked and not math.isinf(shortest(ranked[0])):
        first = ranked[0]
        low, high = runway_range(first.runway)
        block.append(f"<h2>{e(first.ticker)} has the shortest runway: {e(duration_range(low, high))}.</h2>")
    else:
        block.append("<h2>No company on the list is burning cash.</h2>")
    rows = [strip_row(r, name=r.ticker, href=href(r), with_text=True) for r in ranked]
    block.append(runway_strip([row for row in rows if row], generated))
    block.append(
        table(
            [("Ticker", "ticker"), ("Balance sheet date", "date"), ("Cash and investments", "num"),
             ("Burn, last quarter", "num"), ("Burn, four-quarter average", "num"),
             ("Runway at last quarter's burn", "num"), ("Runway at average burn", "num")],
            [
                [
                    link(r),
                    str(r.runway.cash.end) if r.runway.cash else "n/a",
                    e(usd(r.runway.liquidity)),
                    e(usd(r.runway.burn_latest)),
                    e(usd(r.runway.burn_average)),
                    e(runway_text(r.runway, r.runway.burn_latest)),
                    e(runway_text(r.runway, r.runway.burn_average)),
                ]
                for r in ranked
            ],
        )
    )
    block.append("</section>")
    parts.append("".join(block))

    diluted = sorted(reports, key=lambda r: r.dilution.change_1y_pct or 0, reverse=True)
    block = ['<section class="block"><p class="eyebrow">Dilution</p>']
    if diluted and diluted[0].dilution.change_1y_pct:
        top = diluted[0]
        block.append(
            f"<h2>{e(top.ticker)} added the most shares: "
            f"{e(percent(top.dilution.change_1y_pct))} in a year.</h2>"
        )
    else:
        block.append("<h2>Share counts</h2>")
    block.append(
        table(
            [("Ticker", "ticker"), ("Shares outstanding", "num"), ("One-year change", "num"),
             ("Three-year change", "num"), ("Potential new shares", "num"),
             ("Potential as % of shares", "num"), ("Net financing, last four quarters", "num")],
            [
                [
                    link(r),
                    e(share_count(r.dilution.shares.val if r.dilution.shares else None)),
                    e(percent(r.dilution.change_1y_pct)),
                    e(percent(r.dilution.change_3y_pct)),
                    e(share_count(r.dilution.potential_shares)) + ("*" if r.dilution.potential_is_partial else ""),
                    e(percent(r.dilution.overhang_pct, signed=False)),
                    e(usd(r.dilution.financing_ttm)),
                ]
                for r in diluted
            ],
        )
    )
    if any(r.dilution.potential_is_partial for r in reports):
        block.append('<p class="small">* Warrants and options only.</p>')
    block.append("</section>")
    parts.append("".join(block))
    parts.append(_setup_summary(reports, link))

    flagged = [
        f"{r.ticker}: {note}"
        for r in reports
        for note in r.runway.notes + r.dilution.notes
        + [n for n in (r.technicals.notes if r.technicals else []) if "below $1.00" in n]
    ]
    if flagged:
        parts.append(f'<section class="block"><p class="eyebrow">Data notes</p>{notes(flagged)}</section>')

    parts.append(f"<footer><p>Generated {generated} from SEC EDGAR data and yfinance prices. {DISCLAIMER}</p></footer>")
    return page(f"Watchlist summary, {generated}", "\n".join(parts))


def _setup_summary(reports: list[TickerReport], link) -> str:
    """Growth, valuation, trend, positioning and the next event, one row per ticker."""
    def fin(r: TickerReport, attr: str):
        return getattr(r.financials, attr) if r.financials else None

    def tech(r: TickerReport, attr: str):
        return getattr(r.technicals, attr) if r.technicals else None

    def next_event(r: TickerReport) -> str:
        if not r.catalysts:
            return "none dated"
        c = r.catalysts[0]
        return f"{c.when}: {c.event}" + (" (estimate)" if c.estimate else "")

    def flagged(r: TickerReport) -> str:
        count = sum(1 for k in r.eight_ks if k.flagged)
        return str(count) if count else "none"

    def by_stream(r: TickerReport) -> str:
        """Four-quarter growth of each stream in the first split chosen for the ticker, or
        year-to-date growth when some stream lacks four quarters a year apart."""
        split = r.revenue_splits[0] if r.revenue_splits else None
        end = split.latest_end if split else None
        if end is None:
            return "not split"
        if any(s.growth_ttm(end) is None for s in split.streams) and all(s.growth_ytd is not None for s in split.streams):
            months = split.streams[0].ytd_months
            return " · ".join(f"{s.label} {growth(s.growth_ytd)}" for s in split.streams) + f" (first {months} months)"
        return " · ".join(f"{s.label} {growth(s.growth_ttm(end))}" for s in split.streams)

    def base_case(r: TickerReport) -> str:
        if not r.assumptions or not r.scenarios:
            return "n/a"
        horizon = r.assumptions.horizons[0]
        base = next((s for s in r.scenarios if s.case.case == "base" and s.years == horizon), None)
        if base is None:
            return "n/a"
        text = f"{money(base.per_share)} ({percent(base.change_pct)}) in {horizon} years"
        return text + (", placeholder" if r.assumptions.placeholder else "")

    def operating(r: TickerReport) -> str:
        p = r.profitability
        if p is None or p.operating_margin is None:
            return "n/a"
        change = p.operating_margin_change
        return percent(p.operating_margin) + (f" ({points(change)})" if change is not None else "")

    ranked = sorted(reports, key=lambda r: -(fin(r, "growth_ttm") or -1e9))
    rows = [
        [
            link(r),
            e(percent(fin(r, "growth_ttm"))),
            e(by_stream(r)),
            e(percent(fin(r, "gross_margin_ttm"), signed=False)),
            e(operating(r)),
            e(percent(r.profitability.free_cash_margin if r.profitability else None)),
            e(multiple(r.valuation.ev_sales if r.valuation else None)),
            e(multiple(r.valuation.ev_forward_sales if r.valuation else None)),
            e(base_case(r)),
            e(percent(tech(r, "vs_sma200"))),
            e(percent(r.technicals.short.pct_float, signed=False, digits=1)
              if r.technicals and r.technicals.short else "n/a"),
            e(dollars(r.insiders.net_value) if r.insiders else "n/a"),
            e(flagged(r)),
            e(next_event(r)),
        ]
        for r in ranked
    ]
    top = ranked[0] if ranked else None
    headline = "Growth, valuation and setup"
    if top and fin(top, "growth_ttm") is not None:
        headline = f"{top.ticker} is growing fastest: revenue {percent(fin(top, 'growth_ttm'))} over four quarters."
    return (
        '<section class="block"><p class="eyebrow">Growth, valuation and setup</p>'
        f"<h2>{e(headline)}</h2>"
        + table(
            [("Ticker", "ticker"), ("Revenue growth, 4 quarters", "num"), ("Growth by stream, 4 quarters unless stated", ""),
             ("Gross margin, 4 quarters", "num"),
             ("Operating margin, 4 quarters (change in a year)", "num"), ("Free cash flow / revenue, 4 quarters", "num"),
             ("EV / sales", "num"), ("EV / next year's sales, consensus", "num"), ("Base case value per share", "num"), ("Price against 200-day average", "num"), ("Short interest, % of float", "num"),
             ("Insider buys minus sales, 12 months", "num"), ("8-Ks worth reading, 12 months", "num"),
             ("Next event", "")],
            rows,
        )
        + small("Revenue and margins from SEC filings; prices and short interest from yfinance (unofficial). "
                "Insider figures count open-market and 10b5-1 trades only. Each ticker's page has the sources.")
        + "</section>"
    )

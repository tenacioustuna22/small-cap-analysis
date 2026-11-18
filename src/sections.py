"""Report sections beyond runway and dilution. Each takes analysis results and returns HTML."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from src.catalysts import Catalyst, EightK
from src.charts import (
    Column,
    Point,
    RangeMark,
    Reference,
    Stack,
    column_chart,
    line_chart,
    range_chart,
    stacked_column_chart,
)
from src.financials import FilingNote, Financials, margin_excluding, quarter_near
from src.html_kit import (
    disclosure,
    dollars,
    e,
    filed_in,
    growth,
    link,
    money,
    multiple,
    notes,
    percent,
    quarter_label,
    section,
    share_count,
    shares_text,
    small,
    stat,
    stats,
    table,
    table_view,
    usd,
)
from src.metrics import QuarterFlow
from src.ownership import DISCRETIONARY, PLAN_SALE, HolderFiling, InsiderSummary, InsiderTrade, by_owner
from src.estimates import SOURCE as ESTIMATE_SOURCE
from src.prices import Bar
from src.profitability import Profitability
from src.streams import RevenueSplit
from src.technicals import ShortInterest, Technicals
from src.scenarios import EARLY_YEARS, START_LABELS, WHOLE, Scenario, StreamAssumption, TickerAssumptions
from src.valuation import Valuation

HISTORY_QUARTERS = 8


def flow_source(q: QuarterFlow | None) -> str:
    """Where a single-quarter figure came from, saying so when it was derived."""
    if q is None:
        return ""
    fact = q.source
    if fact.start and (fact.end - fact.start).days > 100:
        months = round((fact.end - fact.start).days / 30.44)
        return f"{fact.form} filed {fact.filed}: {months}-month total minus the earlier quarters"
    return f"{fact.form}, quarter ended {fact.end}, filed {fact.filed}"


def _at(series: list[QuarterFlow], q: QuarterFlow) -> QuarterFlow | None:
    return next((s for s in series if s.end == q.end), None)


# --- revenue and margins ------------------------------------------------------------

def financials_headline(f: Financials) -> str:
    if f.growth_ttm is not None:
        verb = "grew" if f.growth_ttm >= 0 else "fell"
        line = f"Revenue {verb} {abs(f.growth_ttm):.0f}% over the last four quarters"
        if f.gross_margin_ttm is not None:
            line += f", at a {f.gross_margin_ttm:.0f}% gross margin"
        return line + "."
    if f.latest:
        return f"Revenue was {usd(f.latest.val)} in the quarter ended {f.latest.end}."
    return "Revenue history is incomplete."


def margin_notes(f: Financials, filing_notes: list[FilingNote]) -> str:
    """Unusual gross margin quarters, explained where a filing note covers them, plus any other notes."""
    by_quarter = {n.period_end: n for n in filing_notes}
    out = []
    for end, margin, usual in f.margin_outliers:
        lead = f"Gross margin in the quarter ended {end} was {margin:.1f}%, against a usual {usual:.0f}%."
        note = by_quarter.pop(end, None)
        if note is None:
            out.append(f'<p class="note"><strong>Data note.</strong> {e(lead)} '
                       "Check that filing for a one-off charge before comparing quarters.</p>")
            continue
        text = f"{lead} {note.note}"
        adjusted = margin_excluding(f, note)
        if adjusted is not None:
            text += (f" Without the {usd(note.cost_charge)} charge, gross margin would have been "
                     f"{adjusted:.1f}% (estimate: gross profit plus the charge, divided by revenue).")
        out.append(f'<p class="note"><strong>From the filing.</strong> {e(text)} {link(note.source_url, "Source")}</p>')
    for note in sorted(by_quarter.values(), key=lambda n: n.period_end):
        out.append(f'<p class="note"><strong>From the filing, quarter ended {note.period_end}.</strong> '
                   f'{e(note.note)} {link(note.source_url, "Source")}</p>')
    return "".join(out)


def financials_section(
    f: Financials | None,
    filing_notes: list[FilingNote] | None = None,
    splits: list[RevenueSplit] | None = None,
) -> str:
    if f is None:
        return ""
    charges = {n.period_end: n.cost_charge for n in filing_notes or [] if n.cost_charge}
    latest = f.latest
    year_ago_q = quarter_near(f.revenue, latest.end - timedelta(days=365)) if latest else None
    net = _at(f.net_income, latest) if latest else None
    opex = f.opex_latest
    gp_latest = _at(f.gross_profit, latest) if latest else None

    figures = stats(
        stat("Revenue, last quarter", usd(latest.val if latest else None), flow_source(latest)),
        stat(
            "Revenue, last four quarters",
            usd(f.revenue_ttm),
            f"four quarters ended {latest.end}" if latest and f.revenue_ttm is not None else "",
        ),
        stat(
            "Growth, last four quarters",
            percent(f.growth_ttm),
            f"against {usd(f.revenue_ttm_prior)} in the four quarters before" if f.revenue_ttm_prior else "",
        ),
        stat(
            "Growth, last quarter",
            percent(f.growth_quarter),
            f"against {usd(year_ago_q.val)} in the quarter ended {year_ago_q.end}" if year_ago_q else "",
        ),
        stat(
            "Gross margin, last quarter",
            percent(f.gross_margin_quarter, signed=False, digits=1),
            f"gross profit {usd(gp_latest.val)}" if gp_latest else "",
        ),
        stat("Gross margin, last four quarters", percent(f.gross_margin_ttm, signed=False, digits=1),
             f"gross profit {usd(f.gross_profit_ttm)}" if f.gross_profit_ttm is not None else ""),
        stat(
            "Operating expenses, last quarter",
            usd(opex.val if opex else None),
            f"{percent(f.opex_change)} against a year earlier" if f.opex_change is not None else flow_source(opex),
        ),
        stat("Net income, last quarter", usd(net.val if net else None), flow_source(net)),
    )

    quarters = f.revenue[-HISTORY_QUARTERS:]
    charts = ""
    if quarters:
        charts += column_chart(
            "Revenue by quarter",
            "In $ millions.",
            [
                Column(
                    *quarter_label(q.end),
                    value=q.val / 1e6,
                    tip_head=f"Quarter ended {q.end}",
                    tip_value=usd(q.val),
                    tip_detail=filed_in(q.source),
                    label=usd(q.val) if q is quarters[0] or q is quarters[-1] else "",
                )
                for q in quarters
            ],
        )
        margins = [(end, m) for end, m in f.margins if end >= quarters[0].end]
        if margins:
            charts += line_chart(
                "Gross margin by quarter",
                "Gross profit as a share of revenue. A sudden drop is usually a one-off charge, such as an inventory write-down.",
                [
                    Point(end, m, f"Quarter ended {end}", f"{m:.1f}%",
                          f"includes a {usd(charges[end])} one-off charge" if end in charges
                          else "gross profit / revenue")
                    for end, m in margins
                ],
                suffix="%",
            )
        rows = []
        for q in reversed(quarters):
            gp, op, ni = _at(f.gross_profit, q), _at(f.opex, q), _at(f.net_income, q)
            margin = gp.val / q.val * 100 if gp and q.val else None
            rows.append([
                str(q.end),
                e(usd(q.val)),
                e(usd(gp.val if gp else None)),
                e(percent(margin, signed=False, digits=1)),
                e(usd(op.val if op else None)),
                e(usd(ni.val if ni else None)),
                e(flow_source(q)),
            ])
        charts += table_view(
            [("Quarter ended", "date"), ("Revenue", "num"), ("Gross profit", "num"), ("Gross margin", "num"),
             ("Operating expenses", "num"), ("Net income", "num"), ("Reported in", "")],
            rows,
        )

    explain = small(
        "Fourth quarters come from the 10-K: the full-year total minus the first three quarters. "
        "Growth compares the latest four quarters with the four before them, which smooths out lumpy "
        "device orders."
    )
    streams = "".join(split_block(s) for s in splits or [])
    return section("revenue", "Revenue and margins", financials_headline(f), figures, explain,
                   notes(f.notes), margin_notes(f, filing_notes or []), charts, streams)


# --- path to profitability ----------------------------------------------------------

def breakeven_text(years: float | None) -> str:
    """A straight-line breakeven for a table cell."""
    if years is None:
        return "n/a"
    if years == 0:
        return "now"
    if math.isinf(years):
        return "not improving"
    return f"{years:.1f} yrs" if years <= 10 else "over 10 yrs"


def _breakeven_short(years: float | None) -> str:
    if years is None:
        return "n/a"
    if years == 0:
        return "now"
    if math.isinf(years):
        return "–"
    return f"{years:.1f}" if years <= 10 else ">10"


def points(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.0f} pts"


def profitability_headline(p: Profitability) -> str:
    m = p.operating_margin
    if m is None:
        return "Profitability needs four quarters of operating income and revenue."
    kind = "profit" if m >= 0 else "loss"
    line = f"Operating {kind} was {abs(m):.0f}% of revenue over the last four quarters"
    change = p.operating_margin_change
    if change is not None and abs(change) >= 1:
        line += f", {abs(change):.0f} points {'better' if change > 0 else 'worse'} than a year earlier"
    if p.free_cash_margin is not None:
        line += f"; free cash flow was {p.free_cash_margin:+.0f}% of revenue"
    return line + "."


def _ttm_detail(p: Profitability) -> str:
    return f"four quarters ended {p.end}" if p.end else ""


def profitability_peer_table(rows: list[PeerRow]) -> str:
    def name(r: PeerRow) -> str:
        label = link(r.href, r.ticker) if r.href and not r.is_self else e(r.ticker)
        return f"<strong>{label}</strong>" if r.is_self else label

    ranked = sorted(rows, key=lambda r: -(r.valuation.ev_sales or 0) if r.valuation else 0)
    out = []
    for r in ranked:
        p = r.profitability
        out.append([
            name(r),
            e(multiple(r.valuation.ev_sales if r.valuation else None)),
            e(multiple(r.valuation.ev_forward_sales if r.valuation else None)),
            e(percent(p.revenue_growth if p else None)),
            e(percent(p.operating_margin if p else None)),
            e(points(p.operating_margin_change if p else None)),
            e(percent(p.before_stock_pay_margin if p else None)),
            e(percent(p.stock_pay_pct if p else None, signed=False)),
            e(percent(p.free_cash_margin if p else None)),
            e(percent(p.share_growth_pct if p else None)),
            e(f"{p.rule_of_40:+.0f}" if p and p.rule_of_40 is not None else "n/a"),
            e(" / ".join(_breakeven_short(y) for y in (
                p.operating_breakeven_years, p.before_stock_pay_breakeven_years, p.free_cash_breakeven_years))
              if p else "n/a"),
        ])
    return table(
        [("Ticker", "ticker"), ("EV / sales", "num"), ("EV / next year's sales", "num"), ("Revenue growth", "num"),
         ("Operating margin", "num"),
         ("Change in a year", "num"), ("Before stock pay", "num"), ("Stock pay / revenue", "num"),
         ("Free cash flow / revenue", "num"), ("Share growth", "num"), ("Rule of 40", "num"),
         ("Breakeven, years: operating / before stock pay / free cash flow", "num")],
        out,
    )


def profitability_section(p: Profitability | None, peers: list[PeerRow] | None = None) -> str:
    if p is None or p.end is None:
        return ""
    figures = stats(
        stat("Operating margin, last four quarters", percent(p.operating_margin),
             f"operating income {usd(p.operating_income_ttm)} on revenue {usd(p.revenue_ttm)}; "
             f"{points(p.operating_margin_change)} against a year earlier"),
        stat("Operating margin before stock pay", percent(p.before_stock_pay_margin),
             f"adds back {usd(p.stock_pay_ttm)} of stock pay, {percent(p.stock_pay_pct, signed=False)} of revenue"),
        stat("Free cash flow, last four quarters", usd(p.free_cash_ttm),
             f"{percent(p.free_cash_margin)} of revenue; operating cash flow minus capex; "
             f"{usd(p.free_cash_ttm_prior)} a year earlier"),
        stat("Share of extra revenue reaching operating income", percent(p.incremental_margin),
             f"operating expenses {percent(p.opex_growth)}, gross profit {percent(p.gross_profit_growth)} in a year"),
        stat("Share count, one year", percent(p.share_growth_pct), "weighted average, latest quarter against a year earlier"),
        stat("Rule of 40", f"{p.rule_of_40:+.0f}" if p.rule_of_40 is not None else "n/a",
             f"revenue growth {percent(p.revenue_growth)} plus free cash flow margin {percent(p.free_cash_margin)}"),
        stat("Straight-line breakeven",
             " · ".join(breakeven_text(y) for y in (p.operating_breakeven_years, p.before_stock_pay_breakeven_years,
                                                     p.free_cash_breakeven_years)),
             "operating · before stock pay · free cash flow, if the last year's change simply continued"),
    )
    explain = small(
        "All figures are the last four quarters against the four before, from SEC filings. "
        "\"Before stock pay\" adds back stock-based pay only, so every company is measured the same way; "
        "companies' own \"adjusted EBITDA\" also leaves out depreciation and items each one chooses, so it "
        "reads higher. The straight-line breakeven is an extrapolation of one year's change, not a forecast."
    )

    oi = p.operating_income[-HISTORY_QUARTERS:]
    added = {n.period_end for n in p.charges_added_back}
    stock = {q.end: q for q in p.stock_pay}
    fcf = {q.end: q for q in p.free_cash}
    charts = ""
    if oi:
        charts += column_chart(
            "Operating income by quarter",
            "In $ millions. Below zero is a loss." + (" One-off charges noted from the filings are added back." if added else ""),
            [Column(*quarter_label(q.end), value=q.val / 1e6, tip_head=f"Quarter ended {q.end}", tip_value=usd(q.val),
                    tip_detail=("one-off charge added back; " if q.end in added else "") + filed_in(q.source),
                    label=usd(q.val) if q is oi[0] or q is oi[-1] else "")
             for q in oi],
        )
    cash = p.free_cash[-HISTORY_QUARTERS:]
    if cash:
        charts += column_chart(
            "Free cash flow by quarter",
            "In $ millions: operating cash flow minus capex. Swings with collections and prepayments.",
            [Column(*quarter_label(q.end), value=q.val / 1e6, tip_head=f"Quarter ended {q.end}", tip_value=usd(q.val),
                    tip_detail=flow_source(q), label=usd(q.val) if q is cash[0] or q is cash[-1] else "")
             for q in cash],
        )
    if oi:
        rows = []
        for q in reversed(oi):
            s, f = stock.get(q.end), fcf.get(q.end)
            rows.append([
                str(q.end),
                e(usd(q.val)) + (" *" if q.end in added else ""),
                e(usd(s.val if s else None)),
                e(usd(q.val + s.val if s else None)),
                e(usd(f.val if f else None)),
                e(flow_source(q)),
            ])
        charts += table_view(
            [("Quarter ended", "date"), ("Operating income", "num"), ("Stock pay", "num"),
             ("Before stock pay", "num"), ("Free cash flow", "num"), ("Reported in", "")],
            rows,
        ) + (small("* One-off charge added back (filing_notes.csv).") if added else "")

    peer_block = ""
    if peers and len(peers) > 1:
        peer_block = (
            "<h3>Against the comparison companies</h3>"
            + profitability_peer_table(peers)
            + small("Sorted by EV / sales, so you can see whether higher multiples go with a nearer breakeven. "
                    "Breakeven is the straight-line extrapolation described above: \"now\" means already "
                    "positive, \"–\" not improving. "
                    "With this few companies, read it company by company; it is too small for a statistical fit.")
        )
    return section("profitability", "Path to profitability", profitability_headline(p),
                   figures, explain, notes(p.notes), charts, peer_block)


# --- revenue streams ----------------------------------------------------------------

def split_lead(split: RevenueSplit) -> str:
    """One sentence: each stream's growth against a year earlier, and its share now."""
    end = split.latest_end
    if end is None:
        return ""
    parts = []
    for s in split.streams:
        g, share = s.growth_quarter(end), split.share(s, end)
        text = f"{s.label} {growth(g)}" if g is not None else s.label
        if share is not None:
            text += f" ({share:.0f}% of revenue)"
        parts.append(text)
    return f"Quarter ended {end} against a year earlier: " + ", ".join(parts) + "."


def split_block(split: RevenueSplit) -> str:
    end = split.latest_end
    heading = f"<h3>Revenue {split.title[:1].lower() + split.title[1:]}</h3>"
    if end is None:
        return heading + notes(split.notes)
    quarters = split.timeline[-HISTORY_QUARTERS:]
    has_margin = any(s.cost for s in split.streams)
    ytd_months = next((s.ytd_months for s in split.streams if s.growth_ytd is not None), None)

    rows = []
    for s in split.streams:
        q = s.at(end)
        row = [
            e(s.label),
            e(usd(q.val)),
            e(percent(split.share(s, end), signed=False)),
            e(growth(s.growth_quarter(end))),
        ]
        if ytd_months:
            row.append(e(growth(s.growth_ytd)))
        row += [e(usd(s.ttm(end))), e(growth(s.growth_ttm(end)))]
        if has_margin:
            row.append(e(percent(s.margin(end), signed=False, digits=1)))
        rows.append(row)
    headers = [("Stream", ""), ("Last quarter", "num"), ("Share", "num"), ("Growth, quarter", "num")]
    if ytd_months:
        headers.append((f"Growth, first {ytd_months} months", "num"))
    headers += [("Last four quarters", "num"), ("Growth, four quarters", "num")]
    if has_margin:
        headers.append(("Gross margin, quarter", "num"))
    summary = table(headers, rows)

    labels = [s.label for s in split.streams]
    stacks = []
    for qend in quarters:
        if qend not in split.quarters:
            stacks.append(Stack(*quarter_label(qend), parts=[0.0] * len(labels), tip_head=f"Quarter ended {qend}",
                                tip_value="Not reported by stream", tip_detail="the filings give no split for it",
                                label="n/a"))
            continue
        values = [s.at(qend).val for s in split.streams]
        total = sum(values)
        stacks.append(Stack(
            *quarter_label(qend),
            parts=[v / 1e6 for v in values],
            tip_head=f"Quarter ended {qend}",
            tip_value=f"{usd(total)} in total",
            tip_detail=" · ".join(f"{name} {usd(v)}" for name, v in zip(labels, values)),
            label=usd(total) if qend in (quarters[0], quarters[-1]) else "",
        ))
    chart = stacked_column_chart(
        f"Revenue {split.title[:1].lower() + split.title[1:]}, by quarter",
        "In $ millions. The first stream in the legend sits at the bottom.",
        labels,
        stacks,
    )
    detail_rows = []
    for qend in reversed(quarters):
        if qend not in split.quarters:
            detail_rows.append([str(qend)] + ["not reported"] * len(labels) + [""])
            continue
        cells = [str(qend)]
        for s in split.streams:
            cells.append(e(usd(s.at(qend).val)))
        cells.append(e(flow_source(split.streams[0].at(qend))))
        detail_rows.append(cells)
    chart += table_view([("Quarter ended", "date")] + [(name, "num") for name in labels] + [("Reported in", "")],
                        detail_rows)
    explain = small(
        f"From the dimensional tags in the 10-Q and 10-K filings ({e(split.axis)}). "
        "Growth compares with the same period a year earlier; year-to-date figures are the totals as filed. "
        "Fourth quarters are the 10-K year minus the first nine months."
        + (" Gross margin uses each stream's own cost of revenue." if has_margin else "")
    )
    return heading + f"<p>{e(split_lead(split))}</p>" + summary + chart + explain + notes(split.notes)


# --- price and trading --------------------------------------------------------------

PRICE_SOURCE = "yfinance (Yahoo Finance, unofficial)"


def price_headline(t: Technicals) -> str:
    if not t.last:
        return "Price data is not available."
    line = f"Closed at {money(t.last.close)} on {t.last.day}"
    if t.vs_sma200 is not None:
        line += f", {abs(t.vs_sma200):.0f}% {'above' if t.vs_sma200 >= 0 else 'below'} its 200-day average"
    if t.from_high is not None and t.from_high < -1:
        line += f" and {abs(t.from_high):.0f}% under its 52-week high"
    return line + "."


def _month_ends(t: Technicals) -> list[tuple[Bar, float | None, float | None]]:
    """The last session of each month over the past year, with the 50- and 200-day averages then."""
    avg50, avg200 = dict(t.sma50_series), dict(t.sma200_series)
    by_month: dict[tuple[int, int], Bar] = {}
    for bar in t.bars:
        if bar.day > t.last.day - timedelta(days=365):
            by_month[(bar.day.year, bar.day.month)] = bar
    return [(bar, avg50.get(bar.day), avg200.get(bar.day)) for bar in by_month.values()]


def _price_tip(bar: Bar, avg50: dict, avg200: dict) -> str:
    parts = [f"volume {share_count(bar.volume)}"]
    if bar.day in avg50:
        parts.append(f"50-day {money(avg50[bar.day])}")
    if bar.day in avg200:
        parts.append(f"200-day {money(avg200[bar.day])}")
    return " · ".join(parts)


def price_section(t: Technicals | None, error: str = "") -> str:
    if t is None:
        if not error:
            return ""
        return section("price", "Price and trading", "Price data is not available.", notes([error]))
    last = t.last
    if last is None:
        return section("price", "Price and trading", price_headline(t), notes(t.notes))

    as_of = f"{last.day} close, {PRICE_SOURCE}"
    if t.dropped_live:
        as_of += "; today's session is still trading and is left out"
    returns = " · ".join(f"{label.split()[0]}{label.split()[1][0]} {percent(v)}" for label, v in t.returns.items())
    figures = stats(
        stat("Last close", money(last.close), as_of),
        stat("Against the 50-day average", percent(t.vs_sma50), f"50-day average {money(t.sma50)}"),
        stat("Against the 200-day average", percent(t.vs_sma200), f"200-day average {money(t.sma200)}"),
        stat(
            "52-week range",
            f"{money(t.low52[1])} to {money(t.high52[1])}",
            f"{percent(t.from_high)} from the high on {t.high52[0]}" if t.high52 else "",
        ),
        stat("Return, 12 months", percent(t.returns.get("12 months")), returns),
        stat(
            "Volume, 20-day average",
            share_count(t.volume20),
            f"{t.volume_ratio:.2f} times the 3-month average" if t.volume_ratio else "",
        ),
        stat("14-day RSI", f"{t.rsi14:.0f}" if t.rsi14 is not None else "n/a",
             "above 70 is often read as overbought, below 30 as oversold"),
        _short_stat(t.short),
        stat("Held by institutions", percent(t.institutions_pct, signed=False),
             f"insiders {percent(t.insiders_pct, signed=False)}; {PRICE_SOURCE}" if t.insiders_pct is not None else PRICE_SOURCE),
    )

    year = [b for b in t.bars if b.day > last.day - timedelta(days=365)]
    avg50, avg200 = dict(t.sma50_series), dict(t.sma200_series)
    chart = line_chart(
        "Daily close, last 12 months",
        f"In dollars, adjusted for splits. Trend: {t.trend}.",
        [Point(b.day, b.close, str(b.day), money(b.close), _price_tip(b, avg50, avg200)) for b in year],
        prefix="$",
        suffix="",
        references=[
            Reference("50-day average", t.sma50_series, "solid"),
            Reference("200-day average", t.sma200_series, "dashed"),
        ],
        series_label="Daily close",
        zero_based=False,
    )
    month_rows = [
        [str(bar.day), e(money(bar.close)), e(money(a50)), e(money(a200)), e(share_count(bar.volume))]
        for bar, a50, a200 in reversed(_month_ends(t))
    ]
    chart += disclosure(
        "Show month-end closes as a table",
        table([("Session", "date"), ("Close", "num"), ("50-day average", "num"), ("200-day average", "num"),
               ("Volume", "num")], month_rows),
    )
    explain = small(
        f"Prices and short interest come from {PRICE_SOURCE}, which can lag or break. "
        "Short interest is reported by exchanges twice a month, so it trails the price."
    )
    return section("price", "Price and trading", price_headline(t), figures, chart, explain, notes(t.notes))


# --- valuation ----------------------------------------------------------------------

@dataclass
class PeerRow:
    ticker: str
    href: str  # link to its page, "" for comparison-only tickers
    valuation: Valuation | None
    financials: Financials | None
    is_self: bool = False
    profitability: Profitability | None = None


def valuation_headline(ticker: str, v: Valuation | None) -> str:
    if v is None or v.market_cap is None:
        return "Valuation needs a price and a share count."
    ev = v.enterprise_value
    if ev is not None and ev < 0:
        return f"The market values {ticker} at {usd(v.market_cap)}, less than its net cash."
    if v.ev_sales is not None:
        return f"Valued at {multiple(v.ev_sales)} trailing sales: an enterprise value of {usd(ev)}."
    return f"Market value is {usd(v.market_cap)}."


def forward_detail(v: Valuation) -> str:
    f = v.forward
    if f is None:
        return "no analyst revenue estimate available"
    spread = f" ({usd(f.low)} to {usd(f.high)})" if f.low and f.high else ""
    who = "1 analyst" if f.analysts == 1 else f"{f.analysts} analysts"
    return f"{f.label} consensus {usd(f.average)}{spread}, {who}; {ESTIMATE_SOURCE}, {f.as_of}"


def peer_table(rows: list[PeerRow]) -> str:
    def name(r: PeerRow) -> str:
        label = link(r.href, r.ticker) if r.href and not r.is_self else e(r.ticker)
        return f"<strong>{label}</strong>" if r.is_self else label

    ranked = sorted(rows, key=lambda r: -(r.valuation.ev_sales or 0) if r.valuation else 0)
    return table(
        [("Ticker", "ticker"), ("Market value", "num"), ("Enterprise value", "num"), ("EV / sales", "num"),
         ("EV / next year's sales", "num"), ("EV / gross profit", "num"), ("Revenue growth, 4 quarters", "num"),
         ("Expected growth, next year", "num"), ("Analysts", "num"), ("Gross margin, 4 quarters", "num")],
        [
            [
                name(r),
                e(usd(r.valuation.market_cap if r.valuation else None)),
                e(usd(r.valuation.enterprise_value if r.valuation else None)),
                e(multiple(r.valuation.ev_sales if r.valuation else None)),
                e(multiple(r.valuation.ev_forward_sales if r.valuation else None)),
                e(multiple(r.valuation.ev_gross_profit if r.valuation else None)),
                e(percent(r.financials.growth_ttm if r.financials else None)),
                e(percent(_forward(r).growth if _forward(r) else None)),
                e(str(_forward(r).analysts) if _forward(r) else "none"),
                e(percent(r.financials.gross_margin_ttm if r.financials else None, signed=False)),
            ]
            for r in ranked
        ],
    )


def _forward(r: PeerRow):
    return r.valuation.forward if r.valuation else None


def _breakeven(years: float) -> str:
    return "never" if math.isinf(years) else f"year {years:g}"


def valuation_section(
    ticker: str,
    v: Valuation | None,
    scenarios: list[Scenario],
    peers: list[PeerRow],
    assumptions: TickerAssumptions | None = None,
) -> str:
    if v is None:
        return ""
    figures = ""
    if v.market_cap is not None:
        shares_detail = (
            f"{money(v.price)} on {v.price_day} × {share_count(v.shares.val)} shares "
            f"({v.shares_basis}, {v.shares.end})"
        )
        figures = stats(
            stat("Market value", usd(v.market_cap), shares_detail),
            stat("Fully diluted market value", usd(v.diluted_market_cap),
                 f"adds {share_count(v.potential_shares)} potential shares" if v.potential_shares else ""),
            stat("Enterprise value", usd(v.enterprise_value),
                 (f"market value + {usd(v.debt)} debt" if v.debt is not None else "market value (no debt tagged)")
                 + f" − {usd(v.liquidity)} cash and investments"),
            stat("EV / sales, last four quarters", multiple(v.ev_sales), f"revenue {usd(v.revenue_ttm)}"),
            stat("EV / next year's sales, consensus", multiple(v.ev_forward_sales), forward_detail(v)),
            stat("EV / gross profit, last four quarters", multiple(v.ev_gross_profit),
                 f"gross profit {usd(v.gross_profit_ttm)}"),
            stat("Price / book", multiple(v.price_book),
                 f"stockholders' equity {usd(v.equity.val)}, {v.equity.form} as of {v.equity.end}" if v.equity else ""),
        )
    parts = [figures, notes(v.notes)]
    if len(peers) > 1:
        parts.append("<h3>Against the rest of the watchlist</h3>")
        parts.append(peer_table(peers))
        parts.append(small(
            "Peers are the active and comparison tickers in watchlist.csv. A wide gap in multiples usually "
            "reflects different growth, margins or survival risk, so read it next to those columns. "
            f"Next year's sales and expected growth are {ESTIMATE_SOURCE}, for the "
            "fiscal year ending closest to a year after each company's latest quarter; with one or two "
            "analysts they are thin."
        ))

    if scenarios and assumptions:
        parts.append(scenarios_block(v, scenarios, assumptions))
    return section("valuation", "Valuation", valuation_headline(ticker, v), *parts)


def _stream_assumption(s: StreamAssumption) -> str:
    """Core business: from the last four quarters, +8% a year (+6% after year 3), 3.0x."""
    if s.revenue_by_year:
        path = ", ".join(f"{v / 1e6:g}" for v in s.revenue_by_year)
        how = f"yearly path ${path}M"
    else:
        start = " or ".join(START_LABELS.get(o, o) if isinstance(o, str) else usd(o) for o in s.start)
        how = f"from {start}, {percent(s.growth_pct)} a year"
        if s.late_growth_pct is not None and s.late_growth_pct != s.growth_pct:
            how += f" ({percent(s.late_growth_pct)} after year {EARLY_YEARS})"
    value = "no exit multiple" if s.ev_sales == 0 else f"{multiple(s.ev_sales)} sales at the end"
    text = f"{how}; {value}"
    return text if s.name == WHOLE else f"{s.name}: {text}"


def scenario_headline(scenarios: list[Scenario], horizon: int) -> str:
    """Base case at the shortest horizon, with the bear-to-bull range."""
    at = {s.case.case: s for s in scenarios if s.years == horizon}
    if "base" not in at:
        return ""
    line = f"Base case, {horizon} years: {money(at['base'].per_share)} a share ({percent(at['base'].change_pct)})"
    if "bear" in at and "bull" in at:
        line += f", within a range of {money(at['bear'].per_share)} to {money(at['bull'].per_share)}"
    return line + "."


def scenarios_block(v: Valuation, scenarios: list[Scenario], a: TickerAssumptions) -> str:
    horizons = " and ".join(str(h) for h in a.horizons)
    parts = [f"<h3>Scenarios, {horizons} years out</h3>", f"<p>{e(scenario_headline(scenarios, a.horizons[0]))}</p>"]
    if a.caveats:
        items = "".join(f"<li>{e(c)}</li>" for c in a.caveats)
        parts.append(f'<div class="note"><strong>Read before the figures.</strong><ul>{items}</ul></div>')
    if a.placeholder:
        parts.append(
            '<p class="note"><strong>Placeholder assumptions.</strong> These cases are mechanical: they scale '
            "trailing growth and today's multiple up and down. They are a starting point for writing real "
            "assumptions into assumptions.toml, not a forecast.</p>"
        )

    by_case: dict[str, list[Scenario]] = {}
    for s in scenarios:
        by_case.setdefault(s.case.case, []).append(s)
    markers = {h: i for i, h in enumerate(a.horizons[:2])}
    rows = [
        (case.title(), [
            RangeMark(s.per_share, markers[s.years], f"{case.title()} case, {s.years} years",
                      f"{money(s.per_share)} a share", f"{percent(s.change_pct)} against today, "
                      f"{percent(s.annual_return_pct)} a year")
            for s in items if s.years in markers
        ])
        for case, items in by_case.items()
    ]
    parts.append(range_chart(
        "Value per share by case",
        "Not discounted to today. The dashed line is today's price.",
        rows,
        [f"{h} years" for h in markers],
        (f"Today {money(v.price)}", v.price),
    ))

    result_rows = [
        [
            f"<strong>{e(s.case.case.title())}</strong>",
            str(s.years),
            e(usd(s.revenue)),
            e(multiple(s.implied_ev_sales)),
            e(usd(s.cash_burned)),
            (e(usd(s.raised)) + f'<br><span class="src">{e(share_count(s.new_shares))} new shares at '
             f'{e(money(s.raise_price))}</span>') if s.raised else "none",
            e(money(s.per_share)),
            e(percent(s.change_pct)),
            e(percent(s.annual_return_pct)),
        ]
        for s in scenarios
    ]
    parts.append(table(
        [("Case", ""), ("Years", "num"), ("Revenue that year", "num"), ("EV / sales", "num"), ("Cash burned", "num"),
         ("Equity raised", "num"), ("Value per share", "num"), ("Against today", "num"), ("A year", "num")],
        result_rows,
    ))

    burn_used = {s.case.case: s.annual_burn for s in scenarios}
    assumption_rows = []
    for case in a.cases:
        detail = "<br>".join(e(_stream_assumption(s)) for s in case.streams)
        why = e(case.note)
        if case.sources:
            why += (" " if why else "") + " ".join(link(url, f"source {i + 1}") for i, url in enumerate(case.sources))
        burn = burn_used.get(case.case)
        burn_cell = (e(usd(burn)) + ' a year<br><span class="src">'
                     + ("set in assumptions.toml" if case.annual_burn is not None else "last four quarters")
                     + "</span>") if burn is not None else "n/a"
        assumption_rows.append([
            f"<strong>{e(case.case.title())}</strong>",
            detail,
            burn_cell,
            e(_breakeven(case.breakeven_years)),
            e(percent(case.raise_discount_pct, signed=False)) if case.raise_discount_pct else "none",
            why,
        ])
    parts.append(table([("Case", ""), ("Revenue and exit multiple", "prose narrow"), ("Cash burn at the start", "num"),
                        ("Burn reaches zero", "num"),
                        ("Raise discount", "num"), ("Why", "prose")], assumption_rows))

    stream_rows = [
        [e(s.case.case.title()), str(s.years), e(r.name if r.name != WHOLE else "Whole company"),
         e(r.start_label) + (f" {e(usd(r.start_value))}" if r.start_value is not None else ""),
         e(usd(r.revenue)), e(multiple(r.ev_sales)), e(usd(r.enterprise_value))]
        for s in scenarios for r in s.streams
    ]
    parts.append(disclosure("Show revenue and value by stream", table(
        [("Case", ""), ("Years", "num"), ("Stream", ""), ("Starting point", ""), ("Revenue that year", "num"),
         ("EV / sales", "num"), ("Enterprise value", "num")], stream_rows)))
    parts.append(small(
        "Each stream's revenue in the final year times its multiple gives enterprise value; the cash left at "
        "the end is added. Burn falls in a straight line to zero by the breakeven year. Cash needed beyond "
        "today's balance is raised by selling shares at the stated discount to today's price, which adds shares. "
        "Values are not discounted to today; the yearly figure is the annualized change. Options and warrants "
        "are not counted."
    ))
    return "".join(parts)


# --- insiders and holders -----------------------------------------------------------

def insider_headline(s: InsiderSummary | None) -> str:
    if s is None:
        return "Insider filings could not be read."
    bought, sold = s.bought_value, s.sold_value
    if not bought and not sold:
        return "No open-market insider buying or selling in the last 12 months."
    if bought and not sold:
        return f"Insiders bought {dollars(bought)} of stock on the open market in the last 12 months, and sold none."
    if sold and not bought:
        return f"Insiders sold {dollars(sold)} of stock in the last 12 months, and bought none."
    more = "bought" if bought > sold else "sold"
    return f"Insiders {more} more than they {'sold' if more == 'bought' else 'bought'}: {dollars(bought)} bought, {dollars(sold)} sold."


def _trade_row(t: InsiderTrade) -> list[str]:
    return [
        str(t.day),
        e(t.owner) + (f'<br><span class="src">{e(t.role)}</span>' if t.role else ""),
        e(t.kind),
        e(("+" if t.acquired else "-") + shares_text(t.shares)),
        e(money(t.price)) if t.price else "",
        e(dollars(t.value)) if t.value else "",
        e(shares_text(t.owned_after)),
        link(t.filing.url, f"Form {t.filing.form}"),
    ]


TRADE_HEADERS = [("Date", "date"), ("Insider", ""), ("Type", ""), ("Shares", "num"), ("Price", "num"),
                 ("Value", "num"), ("Owned after", "num"), ("Filing", "")]


def ownership_section(s: InsiderSummary | None, holders: list[HolderFiling], holders_since, error: str = "") -> str:
    if s is None and not holders and not error:
        return ""
    parts = []
    if s is not None:
        planned = sum(1 for t in s.trades if t.kind == PLAN_SALE)
        parts.append(stats(
            stat("Open-market buys", dollars(s.bought_value),
                 f"{shares_text(s.bought_shares)} shares by {len(s.buyers)} insider{'s' if len(s.buyers) != 1 else ''}"),
            stat("Sales", dollars(s.sold_value),
                 f"{shares_text(s.sold_shares)} shares by {len(s.sellers)} insider{'s' if len(s.sellers) != 1 else ''}"
                 + (f"; {planned} under 10b5-1 plans" if planned else "")),
            stat("Sold to cover taxes", shares_text(s.tax_shares), "shares sold or withheld when stock awards vested"),
            stat("Period", f"since {s.since}", f"{len({t.filing.url for t in s.trades})} Form 4 filings with stock transactions"),
        ))
        if s.unreadable:
            parts.append(notes([f"{s.unreadable} Form 4 filings could not be read and are left out"]))
        key = [t for t in s.trades if t.kind in DISCRETIONARY or t.kind == PLAN_SALE]
        rest = [t for t in s.trades if t not in key]
        owners = by_owner(s.trades)
        if owners:
            parts.append("<h3>Open-market trades by insider</h3>")
            parts.append(table(
                [("Insider", ""), ("Bought", "num"), ("Sold", "num"), ("Sold under 10b5-1 plan", "num"),
                 ("Last trade", "date"), ("Owned after it", "num")],
                [
                    [
                        e(o.owner) + (f'<br><span class="src">{e(o.role)}</span>' if o.role else ""),
                        e(dollars(o.bought)) if o.bought else "",
                        e(dollars(o.sold)) if o.sold else "",
                        e(dollars(o.planned)) if o.planned else "",
                        str(o.last_day),
                        e(shares_text(o.owned_after)),
                    ]
                    for o in owners
                ],
            ))
        if key:
            parts.append(disclosure(f"Show all {len(key)} open-market and plan trades",
                                    table(TRADE_HEADERS, [_trade_row(t) for t in key])))
        if rest:
            parts.append(disclosure(
                f"Show {len(rest)} other transactions: grants, exercises and tax sales",
                table(TRADE_HEADERS, [_trade_row(t) for t in rest]),
            ))
        parts.append(small(
            "Only open-market buys and sales reflect an insider's own decision. Sales coded as covering taxes "
            "(read from each filing's footnotes) and 10b5-1 plan sales are scheduled in advance. "
            "Derivative transactions, such as option grants, are not listed."
        ))
    if error:
        parts.append(notes([error]))

    parts.append(f"<h3>Holders of 5% or more, filings since {holders_since}</h3>")
    if holders:
        parts.append(table(
            [("Filed", "date"), ("Form", "form"), ("Holder", ""), ("Shares", "num"), ("% of class", "num"), ("Document", "")],
            [
                [
                    str(h.filing.filed),
                    e(h.filing.form),
                    e(h.holder) if h.holder else '<span class="src">named in the filing</span>',
                    e(shares_text(h.shares)) if h.shares is not None else "",
                    (e(percent(h.percent, signed=False, digits=1))
                     + ('<br><span class="src">under 5%</span>' if h.percent < 5 else ""))
                    if h.percent is not None else "",
                    link(h.filing.url, "Open on sec.gov"),
                ]
                for h in holders
            ],
        ))
        parts.append(small(
            "The newest filing per holder. 13G filers declare a passive stake; 13D filers may seek to influence "
            "the company. A holder marked under 5% has cut or sold its stake and stops reporting. Filings "
            "before 2025 are free-form documents, so their holder and size are not read."
        ))
    else:
        parts.append(small("None in this period."))
    return section("ownership", "Insiders and holders", insider_headline(s), *parts)


# --- catalysts ----------------------------------------------------------------------

def catalyst_headline(events: list[Catalyst]) -> str:
    if not events:
        return "No dated events ahead."
    first = events[0]
    return f"Next dated event, {first.when}: {first.event}{' (estimate)' if first.estimate else ''}."


def catalysts_section(events: list[Catalyst], eight_ks: list[EightK], eight_k_since) -> str:
    parts = []
    if events:
        parts.append(table(
            [("When", "date"), ("Event", ""), ("Type", ""), ("Source", "")],
            [
                [
                    e(c.when),
                    e(c.event),
                    e(c.kind),
                    (link(c.source_url, c.source) if c.source_url else e(c.source))
                    + ('<br><span class="src">estimate</span>' if c.estimate else ""),
                ]
                for c in events
            ],
        ))
    parts.append(small(
        "Researched events go in catalysts.csv with their source: ticker, date (2027-03-15, 2027-03 or 2027-Q1), "
        "type, event, source_url. The earnings date and filing deadline are added automatically."
    ))

    parts.append(f"<h3>8-K filings since {eight_k_since}</h3>")
    if eight_ks:
        flagged = [k for k in eight_ks if k.flagged]
        if flagged:
            names = sorted({desc for k in flagged for _, desc, flag in k.items if flag})
            parts.append(notes([f"{len(flagged)} filing{'s' if len(flagged) != 1 else ''} with items worth reading: "
                                + "; ".join(names).lower()]))
        parts.append(table(
            [("Filed", "date"), ("What it reports", ""), ("Document", "")],
            [
                [
                    str(k.filing.filed),
                    "<br>".join(
                        (f"<strong>{e(desc)}</strong>" if flag else e(desc)) + f' <span class="tag">item {e(num)}</span>'
                        for num, desc, flag in k.items
                    ),
                    link(k.filing.url, "Open on sec.gov"),
                ]
                for k in eight_ks
            ],
        ))
        parts.append(small("Items in bold often move a small-cap stock: listing notices, share sales, new debt, "
                           "impairments, auditor changes and restatements."))
    else:
        parts.append(small("None in this period."))
    return section("catalysts", "Catalysts and events", catalyst_headline(events), *parts)


def _short_stat(s: ShortInterest | None) -> str:
    if s is None:
        return stat("Short interest", "n/a", "not in the quote data")
    detail = f"{share_count(s.shares)} shares as of {s.as_of}"
    if s.days_to_cover is not None:
        detail += f", {s.days_to_cover:.1f} days to cover"
    if s.change_pct is not None:
        detail += f", {percent(s.change_pct)} on the month before"
    return stat("Short interest, % of float", percent(s.pct_float, signed=False, digits=1), detail)

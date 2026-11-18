"""Write HTML reports for watchlist tickers into reports/.

Each run writes:
    reports/<TICKER>/<today>.html   the full analysis for one company, with sources
    reports/_summary/<today>.html   every active ticker side by side
    reports/index.html              the latest summary: open this one

Running again on the same day overwrites that day's files; earlier days are kept.
The summary and index are only written when no tickers are named. Peer tables always
compare against every active and peer ticker in watchlist.csv.

Usage:
    python scripts/report.py              active tickers in watchlist.csv
    python scripts/report.py HUMA TMC     specific tickers (any status)
    python scripts/report.py --months 12  offering filings from the last 12 months
    python scripts/report.py --refresh    ignore cached downloads
    python scripts/report.py --open       open the result in the browser
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from src import edgar, ixbrl, prices  # noqa: E402
from src.dilution import (  # noqa: E402
    OFFERING_SENTENCE_PATTERN,
    compute_dilution,
    latest_periodic_report,
    offering_filings,
    use_cover_shares,
)
from src.catalysts import (  # noqa: E402
    earnings_from_quote,
    load_catalysts,
    next_filing_deadline,
    recent_8ks,
    upcoming,
)
from src.charts import add_months  # noqa: E402
from src.filing_text import matching_sentences  # noqa: E402
from src.ownership import (  # noqa: E402
    HOLDER_FORMS,
    INSIDER_FORMS,
    HolderFiling,
    latest_by_holder,
    parse_form4,
    parse_schedule13,
    summarize_insiders,
)
from src.estimates import choose_forward, fiscal_year_end  # noqa: E402
from src.financials import compute_financials, load_filing_notes  # noqa: E402
from src.profitability import compute_profitability  # noqa: E402
from src.report import TickerReport, render_summary, render_ticker_report  # noqa: E402
from src.runway import compute_runway  # noqa: E402
from src.sections import PeerRow  # noqa: E402
from src.streams import PERIODIC_FORMS, RevenueSplit, compute_split, load_split_choices  # noqa: E402
from src.technicals import compute_technicals  # noqa: E402
from src.scenarios import (  # noqa: E402
    WHOLE,
    AssumptionError,
    check_streams,
    load_assumptions,
    placeholder_assumptions,
    run_all,
)
from src.valuation import compute_valuation  # noqa: E402
from src.watchlist import load_tickers, load_watchlist  # noqa: E402

REPORTS_DIR = ROOT / "reports"


def build(ticker: str, company_name: str, today: date, since: date, refresh: bool) -> TickerReport:
    company = edgar.company_facts(ticker, refresh=refresh)
    profile = edgar.submissions(ticker, refresh=refresh)
    filings = edgar.recent_filings(profile)
    periodic = latest_periodic_report(filings)
    quotes = []
    if periodic:
        quotes = matching_sentences(edgar.filing_document(periodic.url), OFFERING_SENTENCE_PATTERN)
    runway = compute_runway(company, today=today)
    dilution = compute_dilution(company, today=today)
    tagged, unreadable = periodic_facts(filings, today)
    apply_cover_shares(dilution, tagged)
    financials = compute_financials(company, runway.cash.end if runway.cash else None)
    filing_notes = load_filing_notes(ticker)
    profitability = compute_profitability(company, financials, dilution.change_1y_pct, filing_notes)
    technicals, price_error, info = None, "", {}
    try:
        info = prices.quote_info(ticker, refresh)
        technicals = compute_technicals(prices.price_history(ticker, refresh), info)
    except prices.PriceError as error:
        price_error = str(error)
        print(f"{ticker}: WARNING: {error}")

    forward = None
    if info:
        try:
            forward = choose_forward(prices.revenue_estimates(ticker, refresh), fiscal_year_end(info),
                                     financials.latest.end if financials.latest else None)
        except prices.PriceError as error:
            print(f"{ticker}: WARNING: {error}")

    last = technicals.last if technicals else None
    valuation = compute_valuation(
        price=last.close if last else None,
        price_day=last.day if last else None,
        shares=dilution.shares,
        shares_basis=dilution.shares_basis,
        potential_shares=dilution.potential_shares,
        liquidity=runway.liquidity,
        debt=financials.debt,
        revenue_ttm=financials.revenue_ttm,
        gross_profit_ttm=financials.gross_profit_ttm,
        equity=financials.equity,
        forward=forward,
    )
    splits = revenue_splits(ticker, tagged, unreadable, financials)
    assumptions = load_assumptions(ticker) or placeholder_assumptions(valuation, financials.growth_ttm)
    starts = {WHOLE: financials.start_values()}
    if assumptions and assumptions.split:
        split = next((s for s in splits if s.title == assumptions.split), None)
        if split is None:
            raise AssumptionError(f"[{ticker}]: split {assumptions.split!r} is not a title in revenue_streams.csv "
                                  f"for {ticker} (titles: {', '.join(s.title for s in splits) or 'none'})")
        check_streams(assumptions, [s.label for s in split.streams])
        starts = {s.label: s.start_values() for s in split.streams}
    burn = runway.burn_average if runway.burn_average is not None else runway.burn_latest
    scenarios = run_all(assumptions, valuation, (burn or 0.0) * 4, starts) if assumptions else []
    insiders, holders, holders_since = ownership(filings, today)

    events = load_catalysts(ticker)
    for automatic in (
        earnings_from_quote(info, today),
        next_filing_deadline(filings, profile.get("category", ""), profile.get("fiscalYearEnd", ""), today),
    ):
        if automatic:
            events.append(automatic)
    eight_k_since = add_months(today, -EIGHT_K_MONTHS)

    return TickerReport(
        ticker=ticker,
        company=company_name or company.get("entityName", ""),
        generated=today,
        runway=runway,
        dilution=dilution,
        offerings=offering_filings(filings, company, since),
        offerings_since=since,
        periodic_report=periodic,
        quotes=quotes,
        financials=financials,
        profitability=profitability,
        filing_notes=filing_notes,
        revenue_splits=splits,
        technicals=technicals,
        price_error=price_error,
        valuation=valuation,
        scenarios=scenarios,
        assumptions=assumptions,
        insiders=insiders,
        holders=holders,
        holders_since=holders_since,
        catalysts=upcoming(events, today),
        eight_ks=recent_8ks(filings, eight_k_since),
        eight_k_since=eight_k_since,
    )


INSIDER_MONTHS = 12
HOLDER_YEARS = 3
EIGHT_K_MONTHS = 12
STREAM_YEARS = 3  # 10-Qs and 10-Ks read for revenue splits; each also carries the year before


def periodic_facts(filings: list[edgar.Filing], today: date) -> tuple[list, list[str]]:
    """Tagged facts from each 10-Q and 10-K of the last STREAM_YEARS, newest first, plus
    the ones that could not be read. Documents are cached for good."""
    since = add_months(today, -12 * STREAM_YEARS)
    tagged, unreadable = [], []
    for filing in (f for f in filings if f.form in PERIODIC_FORMS and f.filed >= since):
        try:
            tagged.append((filing, ixbrl.parse_facts(edgar.filing_document(filing.url))))
        except (edgar.EdgarError, ixbrl.IxbrlError) as error:
            unreadable.append(f"{filing.form} filed {filing.filed}: {error}")
    return sorted(tagged, key=lambda t: t[0].filed, reverse=True), unreadable


def revenue_splits(ticker: str, tagged: list, unreadable: list[str], financials) -> list[RevenueSplit]:
    """Revenue streams for the splits chosen in revenue_streams.csv."""
    splits = [compute_split(tagged, choice, financials.revenue) for choice in load_split_choices(ticker)]
    for split in splits:
        split.notes += [f"could not read {u}" for u in unreadable]
    return splits


def apply_cover_shares(dilution, tagged: list) -> None:
    """Use the newest filing's cover page share count (all classes) for the current count."""
    for filing, facts in tagged:
        cover = ixbrl.cover_shares(facts)
        if cover:
            use_cover_shares(dilution, *cover, filing)
            return


def ownership(filings: list[edgar.Filing], today: date):
    """Insider trades from Form 4s and the newest 5% holder filings. Documents are cached for good."""
    since = add_months(today, -INSIDER_MONTHS)
    trades, unreadable = [], 0
    for filing in (f for f in filings if f.form in INSIDER_FORMS and f.filed >= since):
        try:
            trades += parse_form4(edgar.xml_document(filing), filing)
        except (edgar.EdgarError, ET.ParseError):
            unreadable += 1
    holders_since = add_months(today, -12 * HOLDER_YEARS)
    holders = []
    for filing in (f for f in filings if f.form in HOLDER_FORMS and f.filed >= holders_since):
        if filing.form.startswith("SCHEDULE"):
            try:
                holders.append(parse_schedule13(edgar.xml_document(filing), filing))
                continue
            except edgar.EdgarError:
                pass
        holders.append(HolderFiling(filing, "", None, None, None))
    return summarize_insiders(trades, since, unreadable), latest_by_holder(holders), holders_since


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Write HTML reports into reports/.")
    parser.add_argument("tickers", nargs="*", help="tickers (default: watchlist.csv)")
    parser.add_argument("--months", type=int, default=24, help="how far back to list offering filings")
    parser.add_argument("--refresh", action="store_true", help="ignore cached downloads")
    parser.add_argument("--open", action="store_true", help="open the result in the browser")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    watchlist = load_watchlist()
    whole_watchlist = not args.tickers
    tickers = [t.upper() for t in args.tickers] or load_tickers()
    # Peer tables compare against every active and comparison ticker, whatever was asked for.
    comparison = list(dict.fromkeys(tickers + load_tickers(("active", "peer"))))
    today = date.today()
    since = today - timedelta(days=round(args.months * 30.44))

    built: dict[str, TickerReport] = {}
    failed = False
    for ticker in comparison:
        name = watchlist.get(ticker, {}).get("company", "")
        try:
            built[ticker] = build(ticker, name, today, since, args.refresh)
        except (edgar.EdgarError, AssumptionError) as error:
            print(f"{ticker}: ERROR: {error}")
            failed = failed or ticker in tickers

    has_page = set(load_tickers()) | set(tickers)
    peer_rows = {
        t: PeerRow(t, f"../{t}/{today}.html" if t in has_page else "", r.valuation, r.financials,
                   profitability=r.profitability)
        for t, r in built.items()
    }

    reports: list[TickerReport] = []
    written: list[Path] = []
    for ticker in tickers:
        report = built.get(ticker)
        if report is None:
            continue
        report.peers = [replace(row, is_self=(t == ticker)) for t, row in peer_rows.items()]
        path = REPORTS_DIR / ticker / f"{today}.html"
        if path.parent.exists():
            report.earlier_reports = sorted(
                (p.name for p in path.parent.glob("*.html") if p.name != path.name), reverse=True
            )
        written.append(write(path, render_ticker_report(report)))
        print(f"{ticker}: {path.relative_to(ROOT)}")
        reports.append(report)

    to_open = written[0] if written else None
    if reports and whole_watchlist:
        dated = write(REPORTS_DIR / "_summary" / f"{today}.html", render_summary(reports, today, "../"))
        index = write(REPORTS_DIR / "index.html", render_summary(reports, today, ""))
        print(f"Summary: {dated.relative_to(ROOT)}")
        print(f"Open this: {index.relative_to(ROOT)}")
        to_open = index
    elif reports:
        print("Summary not rewritten: run without tickers to refresh it.")

    if args.open and to_open:
        webbrowser.open(to_open.as_uri())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

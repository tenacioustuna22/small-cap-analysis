"""Dilution picture for watchlist tickers, from SEC EDGAR data.

Usage:
    python scripts/dilution.py                active tickers in watchlist.csv
    python scripts/dilution.py HUMA TMC       specific tickers
    python scripts/dilution.py --months 12    offering filings from the last 12 months
    python scripts/dilution.py --sentences 0  skip the quotes from the latest report
    python scripts/dilution.py --refresh      ignore cached downloads
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from src import edgar  # noqa: E402
from src.dilution import (  # noqa: E402
    OFFERING_SENTENCE_PATTERN,
    compute_dilution,
    latest_periodic_report,
    offering_filings,
)
from src.filing_text import matching_sentences  # noqa: E402
from src.watchlist import load_tickers  # noqa: E402


def millions(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1e6:,.1f}"


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.0f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Dilution picture from SEC EDGAR data.")
    parser.add_argument("tickers", nargs="*", help="tickers (default: watchlist.csv)")
    parser.add_argument("--months", type=int, default=24, help="how far back to list offering filings")
    parser.add_argument("--sentences", type=int, default=8, help="max quotes per ticker from the latest report")
    parser.add_argument("--refresh", action="store_true", help="ignore cached downloads")
    args = parser.parse_args()

    sys.stdout.reconfigure(errors="replace")
    load_dotenv(ROOT / ".env")
    tickers = [t.upper() for t in args.tickers] or load_tickers()
    since = date.today() - timedelta(days=round(args.months * 30.44))

    header = (
        f"{'Ticker':<7}{'Shares':>8}  {'As of':<11}{'Basis':<16}"
        f"{'Avg Q':>8}{'1y chg':>8}{'3y chg':>8}{'Potential':>11}{'Overhang':>10}{'Fin 4Q':>9}"
    )
    print("Dilution. Shares in millions, dollars in $ millions. Source: SEC EDGAR.")
    print(header)
    print("-" * len(header))

    details: list[str] = []
    failed = False
    for ticker in tickers:
        try:
            company = edgar.company_facts(ticker, refresh=args.refresh)
            filings = edgar.recent_filings(edgar.submissions(ticker, refresh=args.refresh))
            dilution = compute_dilution(company)
            offerings = offering_filings(filings, company, since)
            report = latest_periodic_report(filings)
            quotes = []
            if report and args.sentences > 0:
                quotes = matching_sentences(edgar.filing_document(report.url), OFFERING_SENTENCE_PATTERN)
        except edgar.EdgarError as error:
            print(f"{ticker:<7}ERROR: {error}")
            failed = True
            continue

        shares = dilution.shares
        potential = millions(dilution.potential_shares) + ("*" if dilution.potential_is_partial else "")
        print(
            f"{ticker:<7}"
            f"{millions(shares.val if shares else None):>8}  "
            f"{str(shares.end) if shares else 'n/a':<11}"
            f"{dilution.shares_basis:<16}"
            f"{millions(dilution.quarter_avg.val if dilution.quarter_avg else None):>8}"
            f"{percent(dilution.change_1y_pct):>8}"
            f"{percent(dilution.change_3y_pct):>8}"
            f"{potential:>11}"
            f"{percent(dilution.overhang_pct).lstrip('+'):>10}"
            f"{millions(dilution.financing_ttm):>9}"
        )

        details.append("")
        details.append(f"=== {ticker} ===")
        for note in dilution.notes:
            details.extend(textwrap.wrap(f"Note: {note}", 100, subsequent_indent="      "))
        details.append(f"Registration and offering filings since {since}:")
        if not offerings:
            details.append("  none")
        for offering in offerings:
            amount = f"  ${offering.amount / 1e6:,.1f}M registered" if offering.amount else ""
            details.append(f"  {offering.filing.filed}  {offering.filing.form:<8}{offering.label}{amount}")
            details.append(f"              {offering.filing.url}")
        if report and args.sentences > 0:
            details.append(f"From the {report.form} filed {report.filed} ({report.url}):")
            if not quotes:
                details.append("  no sentences about shelf, at-the-market or equity line programs")
            for quote in quotes[: args.sentences]:
                details.extend(textwrap.wrap(quote, 100, initial_indent="  - ", subsequent_indent="    "))
            if len(quotes) > args.sentences:
                details.append(f"  ({len(quotes) - args.sentences} more; raise --sentences to see them)")

    print()
    print("Shares    = latest share count; Basis says where it comes from")
    print("Avg Q     = weighted average basic shares for the latest quarter")
    print("1y / 3y   = change in Avg Q against the same quarter one and three years earlier")
    print("Potential = shares that options, warrants, RSUs, convertibles and earnouts could add,")
    print("            including ones far out of the money (* = warrants and options only)")
    print("Overhang  = Potential as a percentage of Shares")
    print("Fin 4Q    = net cash from financing over the trailing four quarters (equity and debt)")
    print("\n".join(details))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

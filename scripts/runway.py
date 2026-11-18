"""Cash runway for watchlist tickers, from SEC EDGAR XBRL data.

Usage:
    python scripts/runway.py              active tickers in watchlist.csv
    python scripts/runway.py HUMA TMC     specific tickers
    python scripts/runway.py --refresh    ignore cached downloads
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from src import edgar  # noqa: E402
from src.runway import Runway, compute_runway  # noqa: E402
from src.watchlist import load_tickers  # noqa: E402


def money(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1e6:,.1f}"


def months(runway: Runway, burn: float | None) -> str:
    if runway.liquidity is None or burn is None:
        return "n/a"
    result = runway.months(burn)
    return "no burn" if result is None else f"{result:.0f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cash runway from SEC EDGAR data.")
    parser.add_argument("tickers", nargs="*", help="tickers (default: watchlist.csv)")
    parser.add_argument("--refresh", action="store_true", help="ignore cached downloads")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    tickers = [t.upper() for t in args.tickers] or load_tickers()

    header = (
        f"{'Ticker':<7}{'As of':<12}{'Form':<6}{'Filed':<12}"
        f"{'Cash':>9}{'ST inv':>9}{'Total':>9}{'Burn Q':>9}{'Burn avg':>10}"
        f"{'Mo (Q)':>9}{'Mo (avg)':>10}"
    )
    print("Cash runway. Dollar figures in $ millions. Source: SEC EDGAR XBRL company facts.")
    print(header)
    print("-" * len(header))

    notes: list[str] = []
    failed = False
    for ticker in tickers:
        try:
            runway = compute_runway(edgar.company_facts(ticker, refresh=args.refresh))
        except edgar.EdgarError as error:
            print(f"{ticker:<7}ERROR: {error}")
            failed = True
            continue

        cash = runway.cash
        print(
            f"{ticker:<7}"
            f"{str(cash.end) if cash else 'n/a':<12}"
            f"{cash.form if cash else '':<6}"
            f"{str(cash.filed) if cash else '':<12}"
            f"{money(cash.val if cash else None):>9}"
            f"{money(runway.investments.val if runway.investments else 0.0):>9}"
            f"{money(runway.liquidity):>9}"
            f"{money(runway.burn_latest):>9}"
            f"{money(runway.burn_average):>10}"
            f"{months(runway, runway.burn_latest):>9}"
            f"{months(runway, runway.burn_average):>10}"
        )
        notes.extend(f"{ticker}: {note}" for note in runway.notes)

    print()
    print("Total    = cash and equivalents + short-term investments (long-term investments excluded)")
    print("Burn Q   = operating cash used in the latest quarter")
    print("Burn avg = average quarterly operating cash used over the trailing four quarters")
    print("Mo       = months of runway at that burn rate; capex and debt repayments are not included")
    if notes:
        print()
        print("Notes:")
        for note in notes:
            print(f"  {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

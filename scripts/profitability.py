"""Path to profitability for watchlist companies, next to what the market pays for them.

Usage:
    python scripts/profitability.py              active and peer tickers in watchlist.csv
    python scripts/profitability.py BFLY CEVA    specific tickers
    python scripts/profitability.py --refresh    ignore cached downloads
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from scripts.report import build  # noqa: E402
from src import edgar  # noqa: E402
from src.scenarios import AssumptionError  # noqa: E402
from src.watchlist import load_tickers, load_watchlist  # noqa: E402


def pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.0f}%" if signed else f"{value:.0f}%"


def years(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == 0:
        return "now"
    if math.isinf(value):
        return "worse"
    return f"{value:.1f}y" if value <= 10 else ">10y"


def main() -> int:
    parser = argparse.ArgumentParser(description="Path to profitability from SEC EDGAR data.")
    parser.add_argument("tickers", nargs="*", help="tickers (default: active and peer in watchlist.csv)")
    parser.add_argument("--refresh", action="store_true", help="ignore cached downloads")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    watchlist = load_watchlist()
    tickers = [t.upper() for t in args.tickers] or load_tickers(("active", "peer"))
    today = date.today()

    rows, failed = [], False
    for ticker in tickers:
        try:
            r = build(ticker, watchlist.get(ticker, {}).get("company", ""), today, today - timedelta(days=730),
                      args.refresh)
        except (edgar.EdgarError, AssumptionError) as error:
            print(f"{ticker}: ERROR: {error}")
            failed = True
            continue
        rows.append(r)
    rows.sort(key=lambda r: -(r.valuation.ev_sales or 0) if r.valuation else 0)

    cols = [("Ticker", 7), ("Qtr end", 11), ("EV/S", 7), ("EV/fwd", 7), ("Fwd g", 6), ("An", 3), ("Growth", 7), ("GM", 5), ("OpM", 6), ("OpM chg", 8),
            ("ex-SBC", 7), ("SBC", 5), ("FCF", 6), ("Incr", 6), ("Opex g", 7), ("GP g", 6), ("Shares", 7),
            ("R40", 6), ("BE op", 7), ("BE exSBC", 9), ("BE FCF", 7)]
    header = "".join(f"{name:<{w}}" if i < 2 else f"{name:>{w}}" for i, (name, w) in enumerate(cols))
    print("Path to profitability, last four quarters against the four before. Source: SEC EDGAR XBRL company "
          "facts; EV from yfinance prices.")
    print(header)
    print("-" * len(header))
    notes = []
    for r in rows:
        p, v, f = r.profitability, r.valuation, r.financials
        cells = [
            r.ticker, str(p.end) if p and p.end else "n/a",
            f"{v.ev_sales:.1f}x" if v and v.ev_sales is not None else "n/a",
            f"{v.ev_forward_sales:.1f}x" if v and v.ev_forward_sales is not None else "n/a",
            pct(v.forward.growth if v and v.forward else None),
            str(v.forward.analysts) if v and v.forward else "0",
            pct(p.revenue_growth if p else None), pct(f.gross_margin_ttm if f else None, signed=False),
            pct(p.operating_margin if p else None),
            f"{p.operating_margin_change:+.0f}pp" if p and p.operating_margin_change is not None else "n/a",
            pct(p.before_stock_pay_margin if p else None), pct(p.stock_pay_pct if p else None, signed=False),
            pct(p.free_cash_margin if p else None), pct(p.incremental_margin if p else None),
            pct(p.opex_growth if p else None), pct(p.gross_profit_growth if p else None),
            pct(p.share_growth_pct if p else None), pct(p.rule_of_40 if p else None),
            years(p.operating_breakeven_years if p else None),
            years(p.before_stock_pay_breakeven_years if p else None),
            years(p.free_cash_breakeven_years if p else None),
        ]
        print("".join(f"{c:<{w}}" if i < 2 else f"{c:>{w}}" for i, (c, (_, w)) in enumerate(zip(cells, cols))))
        if v and v.price_day:
            notes.append(f"{r.ticker}: price {v.price_day}"
                         + (f"; forward = {v.forward.label} consensus {v.forward.average / 1e6:,.1f}M, "
                            f"as of {v.forward.as_of}" if v.forward else "; no analyst revenue estimate"))
            notes.extend(f"{r.ticker}: {n}" for n in (v.forward.notes if v.forward else []))
        notes.extend(f"{r.ticker}: {n}" for n in (p.notes if p else []))

    print()
    print("EV/S     enterprise value / revenue, last four quarters")
    print("EV/fwd   enterprise value / next year's analyst revenue consensus (Yahoo via yfinance, unofficial); "
          "Fwd g its growth over the year before; An number of analysts")
    print("Growth   revenue, four quarters against the four before; GM gross margin")
    print("OpM      operating margin (GAAP); OpM chg its change in percentage points")
    print("ex-SBC   operating margin before stock pay (depreciation left in); SBC stock pay / revenue")
    print("FCF      operating cash flow minus capex, / revenue")
    print("Incr     share of the year's extra revenue that reached operating income")
    print("Opex g, GP g   growth of operating expenses and of gross profit")
    print("Shares   weighted average share count, latest quarter against a year earlier")
    print("R40      Rule of 40: revenue growth + FCF margin")
    print("BE       years to zero if the last year's change continues in a straight line "
          "(an extrapolation, not a forecast); 'worse' = not improving")
    if notes:
        print()
        for n in notes:
            print(f"  {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Print the evidence for writing scenario assumptions: starting revenue, guidance,
contracts, burn, dilution and peer multiples, each with its source.

This is research material for assumptions.toml, not a report page.

Usage:
    python scripts/evidence.py BFLY
    python scripts/evidence.py HYPR --releases 6 --deal-months 36
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402

import report as report_script  # noqa: E402
from src import edgar  # noqa: E402
from src.charts import add_months  # noqa: E402
from src.filing_text import MAX_SENTENCE_CHARS, sentences, to_text  # noqa: E402
from src.html_kit import money, percent, usd  # noqa: E402
from src.scenarios import START_LABELS  # noqa: E402
from src.watchlist import load_tickers, load_watchlist  # noqa: E402

GUIDANCE = re.compile(
    r"guidance|outlook|reaffirm|full[- ]year|break-?even|profitab|adjusted EBITDA"
    r"|expects?\b.{0,80}\b(revenue|cash|growth|margin)",
    re.IGNORECASE,
)
CONTRACTS = re.compile(
    r"remaining performance obligation|deferred revenue|backlog|co-development|upfront|milestone"
    r"|license (fee|agreement|revenue)|royalt",
    re.IGNORECASE,
)
BOILERPLATE = re.compile(r"forward-looking|Private Securities Litigation|undue reliance|risks and uncertainties", re.I)


def quotes(document_html: str, pattern: re.Pattern[str], limit: int = 12) -> list[str]:
    """Prose sentences matching `pattern`, without safe-harbor boilerplate, each once."""
    seen, out = set(), []
    for sentence in sentences(to_text(document_html)):
        s = sentence.strip()
        if not (40 <= len(s) <= MAX_SENTENCE_CHARS) or not pattern.search(s) or BOILERPLATE.search(s):
            continue
        key = re.sub(r"\W+", "", s.lower())
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:limit]


GUIDANCE_BLOCK = re.compile(r"\b(?:Financial )?(?:Guidance|Outlook)\b\s+(?=[A-Z•])")
BLOCK_END = re.compile(r"Reconciliation|Conference Call|Non-GAAP Financial Measures|About [A-Z]|Forward-Looking", re.I)
# Guidance states a range ("$123 million to $126 million"); headline bullets quoting results do not.
RANGE = re.compile(r"\$\s?[\d.,]+\s*(?:million|billion|[MB])?\s*(?:to|-|–)\s*\$\s?[\d.,]+", re.I)


def guidance_blocks(document_html: str, limit: int = 3) -> list[str]:
    """Bulleted guidance sections ("Guidance Raised revenue guidance ... • Revenue of $X to $Y"),
    which sentence splitting misses. Each block runs to the next section heading."""
    text = to_text(document_html)
    starts = [m.start() for m in GUIDANCE_BLOCK.finditer(text)]
    out = []
    for i, start in enumerate(starts):
        stop = min(start + 900, starts[i + 1] if i + 1 < len(starts) else len(text))
        tail = text[start:stop]
        end = BLOCK_END.search(tail, 20)
        block = tail[: end.start() if end else len(tail)].strip()
        if RANGE.search(block) and not BOILERPLATE.search(block) and block not in out:
            out.append(block)
    return out[:limit]


def heading(text: str) -> None:
    print(f"\n== {text} " + "=" * max(0, 76 - len(text)))


def starting_points(r) -> None:
    heading("Starting revenue (annual, for `start` in assumptions.toml)")
    f = r.financials
    if f and f.latest:
        print(f"Whole company, latest quarter ended {f.latest.end}:")
        for kind, value in f.start_values().items():
            print(f"  {kind:15} {usd(value):>9}  {START_LABELS[kind]}")
    for split in r.revenue_splits:
        end = split.latest_end
        if end is None:
            continue
        print(f"\n{split.title} (latest quarter {end}):")
        for s in split.streams:
            values = ", ".join(f"{k} {usd(v)}" for k, v in s.start_values().items())
            print(f"  {s.label}: {values}")
            print(f"    growth: quarter {percent(s.growth_quarter(end))}, year to date {percent(s.growth_ytd)}, "
                  f"four quarters {percent(s.growth_ttm(end))}")
        print("  by quarter:")
        for qend in split.timeline[-8:]:
            cells = "  ".join(f"{s.label} {usd(s.at(qend).val) if s.at(qend) else 'n/a':>8}" for s in split.streams)
            print(f"    {qend}  {cells}")


def guidance(filings: list[edgar.Filing], count: int) -> None:
    heading(f"Guidance and outlook, last {count} earnings releases (8-K item 2.02, exhibit 99.1)")
    releases = [f for f in filings if f.form in ("8-K", "8-K/A") and "2.02" in f.items][:count]
    if not releases:
        print("  no earnings 8-Ks in the filing list")
    for filing in releases:
        try:
            url = edgar.press_release(filing)
        except edgar.EdgarError as error:
            print(f"\n{filing.filed}: could not list the filing: {error}")
            continue
        if url is None:
            print(f"\n{filing.filed}: no exhibit 99.1 found in {filing.url}")
            continue
        document = edgar.filing_document(url)
        blocks = guidance_blocks(document)
        found = [q for q in quotes(document, GUIDANCE) if not any(q[:80] in b for b in blocks)]
        print(f"\nRelease filed {filing.filed}: {url}")
        for b in blocks:
            print(f"  [guidance] {b}")
        for q in found or ([] if blocks else ["(no guidance or outlook sentences)"]):
            print(f"  - {q}")


def contracts(r, filings: list[edgar.Filing], months: int, today: date) -> None:
    heading("Contracted revenue and deals")
    if r.periodic_report:
        print(f"{r.periodic_report.form} filed {r.periodic_report.filed}: {r.periodic_report.url}")
        for q in quotes(edgar.filing_document(r.periodic_report.url), CONTRACTS, limit=15):
            print(f"  - {q}")
    since = add_months(today, -months)
    deals = [f for f in filings if f.form in ("8-K", "8-K/A") and "1.01" in f.items and f.filed >= since]
    print(f"\nMaterial agreements (8-K item 1.01) since {since}: {len(deals)}")
    for filing in deals:
        print(f"\n{filing.form} filed {filing.filed}: {filing.url}")
        found = [q for q in quotes(edgar.filing_document(filing.url), re.compile(r"agreement", re.I), limit=6)
                 if "$" in q or "%" in q] or ["(no sentence with an amount; read the filing)"]
        for q in found:
            print(f"  - {q}")


def burn_and_shares(r) -> None:
    heading("Cash burn and dilution")
    runway = r.runway
    if runway.cash:
        print(f"Cash and investments {usd(runway.liquidity)} ({runway.cash.form}, as of {runway.cash.end})")
    print("Operating cash flow by quarter:")
    for q in runway.quarters[-8:]:
        print(f"  {q.end}  {usd(q.val):>9}")
    if runway.burn_average is not None:
        print(f"Four-quarter average burn {usd(runway.burn_average)} a quarter, {usd(runway.burn_average * 4)} a year "
              "(scenarios use the yearly figure)")
    d = r.dilution
    if d.shares:
        classes = " + ".join(f"{m.rsplit(':', 1)[-1]} {v / 1e6:.1f}M" for m, v in d.share_classes)
        print(f"Shares {d.shares.val / 1e6:.1f}M ({d.shares_basis}, {d.shares.end}){' = ' + classes if classes else ''}; "
              f"one-year change {percent(d.change_1y_pct)}")
    print(f"ATM, shelf and equity line sentences in the latest 10-Q/10-K: {len(r.quotes)} (see the dilution section)")


def cash_margin(r) -> float | None:
    """Four-quarter operating cash flow as a percentage of four-quarter revenue
    (negative means the company used cash)."""
    quarters, f = r.runway.trailing, r.financials
    if not quarters or len(quarters) < 4 or not f or not f.revenue_ttm:
        return None
    return sum(q.val for q in quarters) / f.revenue_ttm * 100


def multiple(value: float | None) -> str:
    return f"{value:.1f}x" if value is not None and value > 0 else "n/a"


def peers(r, today: date, since: date) -> None:
    heading("Comparison tickers (status peer in watchlist.csv)")
    names = load_watchlist()
    tickers = load_tickers(("peer",))
    if not tickers:
        print("  none yet: add candidates to watchlist.csv with status peer")
        return
    print(f"  {'ticker':7} {'EV/sales':>9} {'EV/gross profit':>16} {'growth 4q':>10} {'gross margin':>13} "
          f"{'op. cash flow':>14}  price")
    rows = [(r.ticker, r)]
    for t in tickers:
        try:
            rows.append((t, report_script.build(t, names.get(t, {}).get("company", ""), today, since, refresh=False)))
        except Exception as error:  # a peer failing should not hide the rest
            print(f"  {t:7} could not be built: {error}")
    for t, p in rows:
        v, f = p.valuation, p.financials
        print(f"  {t:7} {multiple(v.ev_sales if v else None):>9} {multiple(v.ev_gross_profit if v else None):>16} "
              f"{percent(f.growth_ttm if f else None):>10} {percent(f.gross_margin_ttm if f else None, signed=False):>13} "
              f"{percent(cash_margin(p)):>14}  {money(v.price) if v else 'n/a'} on {v.price_day if v else 'n/a'}")
    print("  op. cash flow: last four quarters of operating cash flow as a share of revenue (negative = cash used)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence for scenario assumptions.")
    parser.add_argument("ticker")
    parser.add_argument("--releases", type=int, default=4, help="earnings releases to read")
    parser.add_argument("--deal-months", type=int, default=24, help="how far back to list material agreements")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    ticker = args.ticker.upper()
    today = date.today()
    since = today - timedelta(days=730)
    names = load_watchlist()
    r = report_script.build(ticker, names.get(ticker, {}).get("company", ""), today, since, refresh=False)
    filings = edgar.recent_filings(edgar.submissions(ticker))

    v = r.valuation
    print(f"{ticker} evidence, {today}. Price {money(v.price) if v else 'n/a'} on {v.price_day if v else 'n/a'}; "
          f"market value {usd(v.market_cap) if v else 'n/a'}; EV/sales {v.ev_sales:.1f}x" if v and v.ev_sales else "")
    starting_points(r)
    guidance(filings, args.releases)
    contracts(r, filings, args.deal_months, today)
    burn_and_shares(r)
    peers(r, today, since)
    return 0


if __name__ == "__main__":
    sys.exit(main())

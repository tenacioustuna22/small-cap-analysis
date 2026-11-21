"""Free watchlist check: read the feeds in research/<TICKER>/watch/<TICKER>_feeds.toml, log
anything new.

New items go into research/<TICKER>/watch/<TICKER>_seen.csv with status "new". Claude reports on
them in the GitHub workflow (.github/workflows/watch-check.yml), then this script marks them
"reported". No Claude usage happens here.

Usage:
    python scripts/watch_check.py                      every ticker with a feeds file
    python scripts/watch_check.py BFLY --dry-run       print what is new, change nothing
    python scripts/watch_check.py --mode weekend       also the weekend-only sources (W7)
    python scripts/watch_check.py --issue-body out.md  write the issue text for the workflow
    python scripts/watch_check.py --mark-reported      after Claude's report: new -> reported
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from src import feeds, news_watch  # noqa: E402
from src.news_watch import Entry, Item  # noqa: E402

RESEARCH = ROOT / "research"
RAW_BASE = "https://raw.githubusercontent.com/tenacioustuna22/small-cap-analysis/main/research"


def paths(ticker: str) -> dict[str, Path]:
    watch = RESEARCH / ticker / "watch"
    return {
        "feeds": watch / f"{ticker}_feeds.toml",
        "seen": watch / f"{ticker}_seen.csv",
        "state": watch / f"{ticker}_watch_state.json",
    }


def all_tickers() -> list[str]:
    return sorted(p.name.removesuffix("_feeds.toml") for p in RESEARCH.glob("*/watch/*_feeds.toml"))


def notify_for(mode: str) -> tuple[str, ...]:
    return ("now", "weekend") if mode == "weekend" else ("now",)


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def correlation_item(source: dict, config, state: dict, today: date) -> list[Item]:
    """W7: rolling return correlation, stored in the state file; an item only when it moves."""
    from src.prices import PriceError, price_history

    ticker, benchmark = source["ticker"], source["benchmark"]
    window = int(source.get("window", 60))
    try:
        a = [(b.day, b.close) for b in price_history(ticker, refresh=True) if b.day < today]
        b = [(b.day, b.close) for b in price_history(benchmark, refresh=True) if b.day < today]
    except PriceError as error:
        raise feeds.FeedError(str(error)) from error
    result = news_watch.return_correlation(a, b, window)
    if result is None:
        raise feeds.FeedError(f"fewer than {window} shared trading days")
    value, start, end = result
    saved = state.setdefault("correlation", {})
    previous = saved.get(source["name"], {}).get("value")
    saved[source["name"]] = {"value": round(value, 3), "from": str(start), "to": str(end), "window": window}
    reason = news_watch.correlation_flag(
        value, previous, float(source.get("low", 0.3)), float(source.get("move", 0.2))
    )
    if reason is None:
        return []
    title = (
        f"{ticker} vs {benchmark} {window}-day return correlation {value:+.2f} "
        f"({start} to {end}, yfinance), {reason}; previous {previous:+.2f}"
    )
    return [Item(source["item"], source["notify"], source["name"], title, "", "", end)]


def entries_for(source: dict, config) -> list[Entry]:
    """Fetch one source. Sources that cover several tickers raise on the first failure."""
    kind, since = source["kind"], config.baseline_date
    if kind == "rss":
        return feeds.feed_entries(source["url"])
    if kind == "google_news":
        return feeds.feed_entries(feeds.google_news_url(source["query"]))
    if kind == "sec_8k":
        return feeds.eight_k_entries(source["ticker"], source["items"], since)
    if kind == "sec_form_d":
        return feeds.form_d_entries(source["company"], source["cik"], since)
    if kind == "sec_earnings":
        entries = []
        for ticker in source["tickers"]:
            try:
                entries += feeds.earnings_entries(ticker, since)
            except feeds.FeedError as error:
                raise feeds.FeedError(f"{ticker}: {error}") from error
        return entries
    raise feeds.FeedError(f"unhandled kind {kind}")


def check(ticker: str, mode: str, dry_run: bool, today: date) -> tuple[list[dict], dict[str, str]]:
    """Run every source for one ticker. Returns (rows waiting for Claude, failures)."""
    p = paths(ticker)
    config = news_watch.load_config(p["feeds"])
    seen = news_watch.load_seen(p["seen"])
    state = load_state(p["state"])
    before = json.dumps(state, sort_keys=True)
    failures: dict[str, str] = {}
    found: list[Item] = []

    for source in config.sources:
        if source["kind"] == "correlation" and mode != "weekend":
            continue
        name = source["name"]
        try:
            if source["kind"] == "correlation":
                found += correlation_item(source, config, state, today)
            else:
                found += news_watch.to_items(entries_for(source, config), source, config)
        except feeds.FeedError as error:
            failures[name] = str(error)
            record = state.setdefault("failures", {}).setdefault(name, {"count": 0, "since": str(today)})
            record["count"] += 1
            record["last_error"] = str(error)
            continue
        state.get("failures", {}).pop(name, None)

    fresh = news_watch.new_items(found, seen, config.sources)
    seen += [news_watch.seen_row(item, today) for item in fresh]
    waiting = news_watch.pending(seen, notify_for(mode))

    print(f"{ticker}: {len(fresh)} new, {len(waiting)} waiting for Claude ({mode} run)")
    for item in fresh:
        print(f"  [{item.item}] {item.title} ({item.published or 'no date'}, {item.publisher or item.source})")
    for name, reason in failures.items():
        print(f"  could not check {name}: {reason}")

    if not dry_run:
        if fresh:
            news_watch.save_seen(p["seen"], seen)
        if json.dumps(state, sort_keys=True) != before:
            save_state(p["state"], state)
    return waiting, failures


def write_output(key: str, value: str) -> None:
    """Pass a value to later workflow steps (GitHub Actions), if running there."""
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Free watchlist news check.")
    parser.add_argument(
        "tickers", nargs="*", help="tickers (default: every research/*/watch/*_feeds.toml)"
    )
    parser.add_argument("--mode", choices=("now", "weekend"), default="now")
    parser.add_argument("--dry-run", action="store_true", help="print only; change no files")
    parser.add_argument("--issue-body", type=Path, help="write the GitHub issue text here")
    parser.add_argument("--mark-reported", action="store_true", help="set waiting rows to reported")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    tickers = [t.upper() for t in args.tickers] or all_tickers()
    if not tickers:
        print("No research/*/watch/*_feeds.toml files found.")
        return 1

    if args.mark_reported:
        for ticker in tickers:
            p = paths(ticker)
            rows = news_watch.load_seen(p["seen"])
            count = news_watch.mark_reported(rows, notify_for(args.mode))
            if count and not args.dry_run:
                news_watch.save_seen(p["seen"], rows)
            print(f"{ticker}: {count} row(s) marked reported")
        return 0

    today = date.today()
    bodies, with_items = [], []
    for ticker in tickers:
        waiting, failures = check(ticker, args.mode, args.dry_run, today)
        if waiting or args.mode == "weekend":
            with_items.append(ticker)
            watch_url = f"{RAW_BASE}/{ticker}/{ticker}_watch.md"
            bodies.append(news_watch.render_issue(ticker, waiting, failures, args.mode, watch_url))

    if args.issue_body and bodies:
        args.issue_body.parent.mkdir(parents=True, exist_ok=True)
        args.issue_body.write_text("\n\n".join(bodies) + "\n", encoding="utf-8")
    write_output("has_new", "true" if with_items else "false")
    write_output("tickers", " ".join(with_items))
    return 0


if __name__ == "__main__":
    sys.exit(main())

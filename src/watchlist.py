"""Read the watchlist. watchlist.csv is the only place tickers are listed.

The `status` column decides what scripts run on by default:
    active    full analysis and a report page
    peer      comparison only: appears in valuation tables, no page of its own
    inactive  kept on the list but skipped
A row without a status counts as active.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / "watchlist.csv"
STATUSES = ("active", "peer", "inactive")


def load_watchlist(path: Path = WATCHLIST_PATH) -> dict[str, dict[str, str]]:
    """Every watchlist row keyed by upper-case ticker, in file order."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = {
            row["ticker"].strip().upper(): {k: (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(f)
            if (row.get("ticker") or "").strip()
        }
    for ticker, row in rows.items():
        row["status"] = (row.get("status") or "active").lower()
        if row["status"] not in STATUSES:
            raise ValueError(f"{ticker}: unknown status {row['status']!r} in {path.name}")
    return rows


def load_tickers(statuses: tuple[str, ...] = ("active",), path: Path = WATCHLIST_PATH) -> list[str]:
    """Tickers with one of the given statuses, in file order."""
    return [t for t, row in load_watchlist(path).items() if row["status"] in statuses]

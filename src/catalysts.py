"""Dated upcoming events and recent 8-K events. Pure functions.

Hand-researched catalysts live in catalysts.csv, one row per event with its source.
Two kinds are added automatically and labelled as such: the next earnings date from
Yahoo (unofficial) and the SEC deadline for the next 10-Q or 10-K (an estimate).
"""
from __future__ import annotations

import calendar
import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.edgar import Filing

ROOT = Path(__file__).resolve().parents[1]
CATALYSTS_PATH = ROOT / "catalysts.csv"

# SEC filing deadlines in days after the period end, by filer status.
DEADLINES = {
    "large accelerated": {"10-Q": 40, "10-K": 60},
    "accelerated": {"10-Q": 40, "10-K": 75},
    "non-accelerated": {"10-Q": 45, "10-K": 90},
}

# 8-K items worth reading. The flagged ones often move a small-cap stock.
ITEMS = {
    "1.01": ("Entered a material agreement", False),
    "1.02": ("Ended a material agreement", True),
    "1.03": ("Bankruptcy or receivership", True),
    "2.01": ("Completed an acquisition or sale of assets", False),
    "2.02": ("Results of operations", False),
    "2.03": ("Took on a debt obligation", True),
    "2.04": ("Debt obligation accelerated", True),
    "2.05": ("Restructuring or exit costs", True),
    "2.06": ("Material impairment", True),
    "3.01": ("Listing rule deficiency or delisting notice", True),
    "3.02": ("Sold shares in an unregistered offering", True),
    "3.03": ("Changed shareholder rights", True),
    "4.01": ("Changed auditor", True),
    "4.02": ("Earlier financial statements no longer reliable", True),
    "5.01": ("Change in control", True),
    "5.02": ("Director or officer change", False),
    "5.03": ("Charter or bylaw change (includes reverse splits)", False),
    "5.07": ("Shareholder vote results", False),
    "7.01": ("Regulation FD disclosure", False),
    "8.01": ("Other events", False),
}


@dataclass(frozen=True)
class Catalyst:
    day: date  # for sorting; the end of the month or quarter when the date is not exact
    when: str  # as shown: 2027-03-15, Mar 2027, Q1 2027
    event: str
    kind: str
    source_url: str
    source: str  # who says so
    estimate: bool = False


@dataclass(frozen=True)
class EightK:
    filing: Filing
    items: list[tuple[str, str, bool]]  # (number, description, flagged)

    @property
    def flagged(self) -> bool:
        return any(flag for _, _, flag in self.items)


def parse_when(text: str) -> tuple[date, str]:
    """2027-03-15 (a day), 2027-03 (a month) or 2027-Q1 (a quarter). Returns (sort date, label)."""
    text = text.strip()
    if m := re.fullmatch(r"(\d{4})-Q([1-4])", text, re.I):
        year, quarter = int(m[1]), int(m[2])
        month = quarter * 3
        return date(year, month, calendar.monthrange(year, month)[1]), f"Q{quarter} {year}"
    if m := re.fullmatch(r"(\d{4})-(\d{2})", text):
        year, month = int(m[1]), int(m[2])
        return date(year, month, calendar.monthrange(year, month)[1]), f"{calendar.month_abbr[month]} {year}"
    day = date.fromisoformat(text)
    return day, str(day)


def load_catalysts(ticker: str, path: Path = CATALYSTS_PATH) -> list[Catalyst]:
    if not path.exists():
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("ticker") or "").strip().upper() != ticker.upper():
                continue
            day, label = parse_when(row["date"])
            out.append(Catalyst(day, label, row["event"].strip(), (row.get("type") or "").strip(),
                                (row.get("source_url") or "").strip(), "catalysts.csv"))
    return out


def earnings_from_quote(info: dict, today: date) -> Catalyst | None:
    """Next earnings date from Yahoo's quote data, if it is still ahead."""
    stamp = info.get("earningsTimestampStart") or info.get("earningsTimestamp")
    if not isinstance(stamp, (int, float)):
        return None
    day = datetime.fromtimestamp(stamp, tz=timezone.utc).date()
    if day < today:
        return None
    estimate = bool(info.get("isEarningsDateEstimate"))
    return Catalyst(day, str(day), "Earnings report" + (" (date not confirmed)" if estimate else ""),
                    "earnings", "", "yfinance (unofficial)", estimate=estimate)


def filer_status(category: str) -> str:
    text = (category or "").lower()
    if "large accelerated" in text:
        return "large accelerated"
    if "non-accelerated" in text:
        return "non-accelerated"
    if "accelerated" in text:
        return "accelerated"
    return "non-accelerated"


def _quarter_after(end: date) -> date:
    index = end.year * 12 + end.month + 2  # three months on, as a 0-based month index
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, calendar.monthrange(year, month)[1])


def next_filing_deadline(filings: list[Filing], category: str, fiscal_year_end: str, today: date) -> Catalyst | None:
    """When the next 10-Q or 10-K is due, from the last period reported and the filer status."""
    periodic = [f for f in filings if f.form in ("10-Q", "10-K") and f.report_date]
    if not periodic:
        return None
    last = max(periodic, key=lambda f: f.report_date).report_date
    status = filer_status(category)
    period = _quarter_after(last)
    while True:
        is_year_end = fiscal_year_end and period.strftime("%m%d") == fiscal_year_end
        form = "10-K" if is_year_end else "10-Q"
        due = period + timedelta(days=DEADLINES[status][form])
        if due >= today:
            break
        period = _quarter_after(period)
    return Catalyst(
        due, str(due), f"{form} due for the period ended {period}", "filing deadline", "",
        f"SEC deadline for a {status} filer; earnings usually come a few days before", estimate=True,
    )


def recent_8ks(filings: list[Filing], since: date) -> list[EightK]:
    out = []
    for f in filings:
        if f.form not in ("8-K", "8-K/A") or f.filed < since:
            continue
        items = []
        for number in (n.strip() for n in f.items.split(",") if n.strip()):
            if number == "9.01":  # exhibits only
                continue
            description, flag = ITEMS.get(number, ("Item " + number, False))
            items.append((number, description, flag))
        if items:
            out.append(EightK(f, items))
    return sorted(out, key=lambda k: k.filing.filed, reverse=True)


def upcoming(catalysts: list[Catalyst], today: date) -> list[Catalyst]:
    return sorted((c for c in catalysts if c.day >= today), key=lambda c: c.day)

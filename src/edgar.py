"""Fetch and cache SEC EDGAR data. No calculations live here."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import requests

from src.metrics import Fact

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "edgar"

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

CACHE_MAX_AGE_HOURS = 24
MIN_SECONDS_BETWEEN_REQUESTS = 0.15  # SEC limit is 10 requests/second

_last_request_time = 0.0


class EdgarError(RuntimeError):
    pass


@dataclass(frozen=True)
class Filing:
    form: str
    filed: date
    description: str
    url: str
    items: str = ""  # 8-K item numbers, such as "2.02,9.01"
    report_date: date | None = None  # period the filing covers, for 10-Qs and 10-Ks


def _user_agent() -> str:
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise EdgarError(
            "SEC_USER_AGENT is not set. Copy .env.example to .env and fill it in "
            "(the SEC asks for a name and contact email)."
        )
    return ua


def _get_text(url: str, cache_path: Path, refresh: bool, max_age_hours: float | None) -> str:
    """Return text from the cache if it is fresh, otherwise download and cache it.

    `max_age_hours=None` means the cached copy never expires.
    """
    global _last_request_time

    if not refresh and cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if max_age_hours is None or age_hours < max_age_hours:
            return cache_path.read_text(encoding="utf-8")

    wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.time() - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    response = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=60)
    _last_request_time = time.time()

    if response.status_code != 200:
        raise EdgarError(f"SEC returned HTTP {response.status_code} for {url}")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def _get_json(url: str, cache_path: Path, refresh: bool) -> dict:
    return json.loads(_get_text(url, cache_path, refresh, CACHE_MAX_AGE_HOURS))


FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"


def full_text_search(phrase: str, forms: list[str], since: date) -> dict:
    """EDGAR full-text search for an exact phrase in filings of the given forms, filed since
    `since`. Always fetched fresh (the cached copy is only a record of the last answer)."""
    query = urlencode({
        "q": f'"{phrase}"', "forms": ",".join(forms),
        "dateRange": "custom", "startdt": since.isoformat(), "enddt": date.today().isoformat(),
    })
    slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{phrase}_{'_'.join(forms)}").strip("_")
    return _get_json(f"{FULL_TEXT_URL}?{query}", CACHE_DIR / "full_text" / f"{slug}.json", refresh=True)


def filing_document(url: str) -> str:
    """Raw HTML of a filed document. Filings never change, so the cache never expires."""
    prefix = "https://www.sec.gov/Archives/edgar/data/"
    if not url.startswith(prefix):
        raise EdgarError(f"Not an EDGAR archive URL: {url}")
    return _get_text(url, CACHE_DIR / "documents" / url[len(prefix):], False, None)


def filing_files(filing: Filing) -> list[str]:
    """URLs of every file in a filing's folder, from its index.json (cached permanently)."""
    folder = filing.url.rsplit("/", 1)[0] if filing.url.rsplit("/", 1)[-1].count(".") else filing.url
    listing = json.loads(filing_document(f"{folder}/index.json"))
    return [f"{folder}/{item['name']}" for item in listing.get("directory", {}).get("item", [])]


# ex99_1, ex-99.1, ex991, dex991 (Donnelley), xexx991 (Workiva); not ex992 or ex9910.
EXHIBIT_99_1 = re.compile(r"ex[x_.\-]*99[._\-]?0?1(?!\d)", re.IGNORECASE)


def press_release(filing: Filing) -> str | None:
    """URL of exhibit 99.1 (the press release an earnings 8-K carries), found by file name."""
    names = [u for u in filing_files(filing) if u.lower().endswith((".htm", ".html"))]
    return next((u for u in names if EXHIBIT_99_1.search(u.rsplit("/", 1)[-1])), None)


def raw_xml_url(url: str) -> str:
    """Forms 3/4/5 and new-format 13D/G list a rendered copy (in an `xsl...` folder) as
    their primary document; the raw XML is the same file name one folder up."""
    folder, _, name = url.rpartition("/")
    parent, _, last = folder.rpartition("/")
    return f"{parent}/{name}" if last.startswith("xsl") else url


def xml_document(filing: Filing) -> str:
    """Raw XML of an ownership filing, cached permanently."""
    return filing_document(raw_xml_url(filing.url))


def ticker_to_cik(ticker: str, refresh: bool = False) -> int:
    data = _get_json(TICKERS_URL, CACHE_DIR / "company_tickers.json", refresh)
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            return int(entry["cik_str"])
    raise EdgarError(f"Ticker {ticker} not found in the SEC ticker list")


def company_facts(ticker: str, refresh: bool = False) -> dict:
    """All XBRL facts the company has reported, as returned by data.sec.gov."""
    cik = ticker_to_cik(ticker, refresh)
    return _get_json(
        FACTS_URL.format(cik=cik),
        CACHE_DIR / "companyfacts" / f"CIK{cik:010d}.json",
        refresh,
    )


def submissions(ticker: str, refresh: bool = False) -> dict:
    """Company profile and its most recent filings, as returned by data.sec.gov."""
    return submissions_for_cik(ticker_to_cik(ticker, refresh), refresh)


def submissions_for_cik(cik: int, refresh: bool = False) -> dict:
    """The same, by CIK, for companies with no ticker (private issuers filing Form D)."""
    return _get_json(
        SUBMISSIONS_URL.format(cik=cik),
        CACHE_DIR / "submissions" / f"CIK{cik:010d}.json",
        refresh,
    )


def recent_filings(company_submissions: dict) -> list[Filing]:
    """Parse the recent filings list (about the last 1,000 filings), newest first."""
    cik = int(company_submissions["cik"])
    recent = company_submissions["filings"]["recent"]
    count = len(recent["accessionNumber"])
    items = recent.get("items") or [""] * count
    report_dates = recent.get("reportDate") or [""] * count
    filings = []
    for i, accession in enumerate(recent["accessionNumber"]):
        document = recent["primaryDocument"][i]
        folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}"
        filings.append(
            Filing(
                form=recent["form"][i],
                filed=date.fromisoformat(recent["filingDate"][i]),
                description=recent["primaryDocDescription"][i],
                url=f"{folder}/{document}" if document else folder,
                items=items[i] or "",
                report_date=date.fromisoformat(report_dates[i]) if report_dates[i] else None,
            )
        )
    return sorted(filings, key=lambda f: f.filed, reverse=True)


def facts_for_tag(
    company: dict, tag: str, unit: str = "USD", taxonomy: str = "us-gaap"
) -> list[Fact]:
    """Parse one XBRL tag into Fact objects. Returns [] if the company never used the tag."""
    entries = company.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get(unit, [])
    return [
        Fact(
            tag=tag,
            start=date.fromisoformat(e["start"]) if "start" in e else None,
            end=date.fromisoformat(e["end"]),
            val=float(e["val"]),
            form=e.get("form", ""),
            filed=date.fromisoformat(e["filed"]),
        )
        for e in entries
    ]

"""Fetch what the watchlist check reads: RSS/Atom feeds, Google News search, EDGAR filings and
full-text search, CourtListener docket entries.

Fetching only; filtering and de-duplication live in src/news_watch.py. Every failure raises
FeedError so the check can list the source under "could not check" instead of guessing.
"""
from __future__ import annotations

import os
import time
from datetime import date, timedelta
from urllib.parse import quote, urlsplit

import requests

from src import edgar, news_watch
from src.news_watch import Entry, parse_feed

# A generic client name: no personal details go to news sites (EDGAR gets SEC_USER_AGENT).
USER_AGENT = "Mozilla/5.0 (compatible; small-cap-analysis watch-check)"
GOOGLE_NEWS_DAYS = 7  # the feed only needs to cover the gap between runs, with room to spare
SECONDS_BETWEEN_REQUESTS = 3.0  # per host; Google News answers HTTP 429 to quick bursts
RETRY_AFTER_SECONDS = 30.0  # one retry after a 429

_last_request: dict[str, float] = {}


class FeedError(RuntimeError):
    pass


def google_news_url(query: str, days: int = GOOGLE_NEWS_DAYS) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote(f"{query} when:{days}d")
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def _polite_get(url: str) -> requests.Response:
    host = urlsplit(url).netloc
    wait = SECONDS_BETWEEN_REQUESTS - (time.time() - _last_request.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    except requests.RequestException as error:
        raise FeedError(f"request failed: {error}") from error
    finally:
        _last_request[host] = time.time()


def feed_entries(url: str) -> list[Entry]:
    response = _polite_get(url)
    if response.status_code == 429:
        time.sleep(RETRY_AFTER_SECONDS)
        response = _polite_get(url)
    if response.status_code != 200:
        raise FeedError(f"HTTP {response.status_code}")
    try:
        return parse_feed(response.text)
    except ValueError as error:
        raise FeedError(str(error)) from error


def _filings(submissions: dict, since: date) -> list[edgar.Filing]:
    return [f for f in edgar.recent_filings(submissions) if f.filed >= since]


def eight_k_entries(ticker: str, items: list[str], since: date) -> list[Entry]:
    """8-Ks (and amendments) since `since` that carry any of the given item numbers."""
    try:
        filings = _filings(edgar.submissions(ticker, refresh=True), since)
    except (edgar.EdgarError, requests.RequestException) as error:
        raise FeedError(str(error)) from error
    entries = []
    for f in filings:
        found = [i for i in f.items.split(",") if i in items]
        if f.form.startswith("8-K") and found:
            entries.append(Entry(f"{ticker} {f.form}, items {f.items}", f.url, f.filed, "sec.gov"))
    return entries


def earnings_entries(ticker: str, since: date) -> list[Entry]:
    """10-Qs, 10-Ks and earnings 8-Ks (item 2.02) filed since `since`."""
    try:
        filings = _filings(edgar.submissions(ticker, refresh=True), since)
    except (edgar.EdgarError, requests.RequestException) as error:
        raise FeedError(str(error)) from error
    entries = []
    for f in filings:
        if f.form in ("10-Q", "10-K") or (f.form == "8-K" and "2.02" in f.items.split(",")):
            label = f"{f.form} for the period ended {f.report_date}" if f.report_date else f"{f.form}, items {f.items}"
            entries.append(Entry(f"{ticker} {label}", f.url, f.filed, "sec.gov"))
    return entries


def form_d_search_entries(queries: list[str], forms: list[str], since: date) -> list[Entry]:
    """EDGAR full-text search for filings naming any of `queries` (exact phrases), filed since
    `since`. Each Form D found is opened (cached permanently) so the title carries the amounts."""
    entries = []
    for query in queries:
        try:
            response = edgar.full_text_search(query, forms, since)
        except (edgar.EdgarError, requests.RequestException) as error:
            raise FeedError(f"{query}: {error}") from error
        for hit in news_watch.efts_hits(response, since):
            summary = ""
            if hit.form in ("D", "D/A"):
                try:
                    summary = news_watch.form_d_summary(edgar.filing_document(hit.document_url))
                except (edgar.EdgarError, requests.RequestException, ValueError) as error:
                    summary = f"amounts not read: {error}"
            title = f"{hit.form} filed {hit.filed}: {hit.filer} (names {query})"
            entries.append(Entry(f"{title}; {summary}" if summary else title, hit.index_url, hit.filed, "sec.gov"))
    return entries


COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v4/docket-entries/"
COURTLISTENER_DAYS = 21  # entries older than this are left to the seen-log
COURTLISTENER_MAX_PAGES = 5  # 20 entries a page; a free token allows 125 requests a day
_docket_cache: dict[tuple, list[Entry]] = {}


def docket_entries(dockets: list[dict], since: date) -> list[Entry]:
    """New entries on CourtListener dockets, with the court's description of each, through the
    API (a free account token in COURTLISTENER_TOKEN). The web pages refuse automated reads."""
    token = os.environ.get("COURTLISTENER_TOKEN", "").strip()
    if not token:
        raise FeedError("COURTLISTENER_TOKEN is not set")
    since = max(since, date.today() - timedelta(days=COURTLISTENER_DAYS))
    headers = {"Authorization": f"Token {token}", "User-Agent": USER_AGENT}
    entries = []
    for docket in dockets:
        key = (docket["id"], docket["name"], since)
        if key in _docket_cache:  # two sources may read the same docket in one run
            entries += _docket_cache[key]
            continue
        found: list[Entry] = []
        url: str | None = COURTLISTENER_API
        params: dict | None = {"docket": docket["id"], "date_filed__gte": since.isoformat(), "order_by": "-date_filed"}
        for _ in range(COURTLISTENER_MAX_PAGES):
            if not url:
                break
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
            except requests.RequestException as error:
                raise FeedError(f"{docket['name']}: request failed: {error}") from error
            if response.status_code != 200:
                raise FeedError(f"{docket['name']}: HTTP {response.status_code}")
            page = response.json()
            found += news_watch.docket_entries(page.get("results", []), docket["id"], docket["name"])
            url, params = page.get("next"), None
        _docket_cache[key] = found
        entries += found
    return entries


def form_d_entries(company: str, cik: int, since: date) -> list[Entry]:
    """Form D (and D/A) filings since `since`. Private issuers have a CIK but no ticker."""
    try:
        filings = _filings(edgar.submissions_for_cik(int(cik), refresh=True), since)
    except (edgar.EdgarError, requests.RequestException) as error:
        raise FeedError(str(error)) from error
    return [
        Entry(f"{company} {f.form} (notice of a private placement)", f.url, f.filed, "sec.gov")
        for f in filings
        if f.form in ("D", "D/A")
    ]

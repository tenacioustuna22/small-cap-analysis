"""Watchlist news check: parse feeds, filter, de-duplicate against the seen-log, render issues.

Pure functions and local file handling only; network fetching lives in src/feeds.py, and
scripts/watch_check.py runs both. The config format is explained at the top of
research/BFLY/watch/BFLY_feeds.toml.
"""
from __future__ import annotations

import csv
import html
import math
import re
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SEEN_COLUMNS = ("first_seen", "item", "notify", "source", "title", "publisher", "url", "published", "status")
STATUSES = ("new", "reported", "baselined", "dismissed")
NOTIFY = ("now", "weekend")

COMMON_KEYS = {"name", "kind", "item", "notify", "title_must", "match_titles", "fast"}
KIND_KEYS = {
    "rss": {"url"},
    "google_news": {"query"},
    "sec_8k": {"ticker", "items"},
    "sec_form_d": {"company", "cik"},
    "sec_earnings": {"tickers"},
    "sec_fulltext": {"queries", "forms"},
    "courtlistener": {"dockets"},
    "correlation": {"ticker", "benchmark", "window", "weekday", "low", "move"},
}
TOP_KEYS = {"ticker", "baseline_date", "promote", "filters", "source", "weekend_only"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    """One thing a feed or filing list returned, before filtering."""
    title: str
    url: str
    published: date | None
    publisher: str = ""  # the publisher's domain, when the feed names it


@dataclass(frozen=True)
class Item:
    """An entry that passed the filters, tagged with its watchlist item."""
    item: str
    notify: str
    source: str
    title: str
    publisher: str
    url: str
    published: date | None


@dataclass
class Config:
    ticker: str
    baseline_date: date
    promote_pattern: re.Pattern | None
    promote_item: str
    blocked_domains: list[str]
    blocked_titles: list[re.Pattern]
    sources: list[dict]
    weekend_only: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- config


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    unknown = set(raw) - TOP_KEYS
    if unknown:
        raise ConfigError(f"{path.name}: unknown top-level keys {sorted(unknown)}")
    for key in ("ticker", "baseline_date", "source"):
        if key not in raw:
            raise ConfigError(f"{path.name}: missing '{key}'")

    promote = raw.get("promote", {})
    filters = raw.get("filters", {})
    names = set()
    for source in raw["source"]:
        name = source.get("name")
        if not name:
            raise ConfigError(f"{path.name}: a [[source]] has no name")
        if name in names:
            raise ConfigError(f"{path.name}: source name '{name}' is used twice")
        names.add(name)
        kind = source.get("kind")
        if kind not in KIND_KEYS:
            raise ConfigError(f"{path.name}: source '{name}' has unknown kind {kind!r}")
        extra = set(source) - COMMON_KEYS - KIND_KEYS[kind]
        if extra:
            raise ConfigError(f"{path.name}: source '{name}' has unknown keys {sorted(extra)}")
        missing = KIND_KEYS[kind] - set(source) - {"window", "weekday", "low", "move"}
        if missing:
            raise ConfigError(f"{path.name}: source '{name}' is missing {sorted(missing)}")
        if kind == "courtlistener" and not all(
            isinstance(d, dict) and isinstance(d.get("id"), int) and d.get("name") for d in source["dockets"]
        ):
            raise ConfigError(f"{path.name}: source '{name}' dockets must be {{ id = 123, name = \"...\" }}")
        if not re.fullmatch(r"W\d+", source.get("item", "")):
            raise ConfigError(f"{path.name}: source '{name}' needs item = \"W1\" (or W2, ...)")
        source.setdefault("notify", "now")
        if source["notify"] not in NOTIFY:
            raise ConfigError(f"{path.name}: source '{name}' notify must be one of {NOTIFY}")
        source.setdefault("match_titles", kind not in ("correlation",))
        source.setdefault("fast", False)
        if not isinstance(source["fast"], bool):
            raise ConfigError(f"{path.name}: source '{name}' fast must be true or false")
        if source["fast"] and source["notify"] != "now":
            raise ConfigError(f"{path.name}: source '{name}' is fast, so notify must be \"now\"")

    baseline = raw["baseline_date"]
    if isinstance(baseline, str):
        baseline = date.fromisoformat(baseline)
    return Config(
        ticker=raw["ticker"].upper(),
        baseline_date=baseline,
        promote_pattern=re.compile(promote["title"], re.IGNORECASE) if promote.get("title") else None,
        promote_item=promote.get("item", ""),
        blocked_domains=[d.lower().removeprefix("www.") for d in filters.get("blocked_domains", [])],
        blocked_titles=[re.compile(p, re.IGNORECASE) for p in filters.get("blocked_titles", [])],
        sources=raw["source"],
        weekend_only=list(raw.get("weekend_only", [])),
    )


# ---------------------------------------------------------------- feed parsing

ATOM = "{http://www.w3.org/2005/Atom}"


def _domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    text = text.strip()
    try:
        return parsedate_to_datetime(text).date()  # RSS: Tue, 17 Nov 2026 16:39:00 -0500
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()  # Atom
    except ValueError:
        return None


def parse_feed(xml_text: str) -> list[Entry]:
    """Entries from an RSS 2.0 or Atom feed. Raises ValueError if it is neither."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ValueError(f"not a valid feed: {error}") from error

    entries = []
    if root.tag == "rss":
        for node in root.iter("item"):
            title = html.unescape((node.findtext("title") or "").strip())
            link = (node.findtext("link") or "").strip()
            source = node.find("source")
            publisher = _domain(source.get("url", "")) if source is not None else _domain(link)
            if source is not None and source.text:
                title = strip_publisher(title, source.text.strip())
            entries.append(Entry(title, link, _parse_date(node.findtext("pubDate")), publisher))
    elif root.tag == f"{ATOM}feed":
        for node in root.iter(f"{ATOM}entry"):
            title = html.unescape((node.findtext(f"{ATOM}title") or "").strip())
            link_node = node.find(f"{ATOM}link")
            link = link_node.get("href", "") if link_node is not None else ""
            when = node.findtext(f"{ATOM}published") or node.findtext(f"{ATOM}updated")
            entries.append(Entry(title, link, _parse_date(when), _domain(link)))
    else:
        raise ValueError(f"not an RSS or Atom feed (root element {root.tag})")
    return entries


@dataclass(frozen=True)
class EftsHit:
    """One filing from an EDGAR full-text search answer."""
    form: str
    filed: date
    filer: str
    index_url: str
    document_url: str


def efts_hits(response: dict, since: date) -> list[EftsHit]:
    """Filings in an efts.sec.gov search answer, filed on or after `since`, one per filing."""
    hits, done = [], set()
    for hit in response.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        accession = src.get("adsh") or hit.get("_id", "").split(":")[0]
        filed = _parse_date(src.get("file_date"))
        ciks = src.get("ciks") or []
        if not accession or not ciks or filed is None or filed < since or accession in done:
            continue
        done.add(accession)
        folder = f"https://www.sec.gov/Archives/edgar/data/{int(ciks[0])}/{accession.replace('-', '')}"
        document = hit.get("_id", "").partition(":")[2] or "primary_doc.xml"
        names = [re.sub(r"\s+\(CIK \d+\)\s*$", "", n).strip() for n in src.get("display_names") or []]
        hits.append(EftsHit(src.get("form", ""), filed, "; ".join(names) or f"CIK {int(ciks[0])}",
                            f"{folder}/", f"{folder}/{document}"))
    return hits


def _money(text: str | None) -> str:
    if not text:
        return "n/a"
    try:
        return f"${float(text):,.0f}"
    except ValueError:
        return text.strip()  # "Indefinite"


def form_d_summary(xml_text: str) -> str:
    """The figures of a Form D (primary_doc.xml) in one line: amount sold and offered, first
    sale, investors. Raises ValueError if it is not a Form D."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ValueError(f"not valid XML: {error}") from error
    for node in root.iter():  # drop any namespace so the tag names below match
        node.tag = node.tag.rpartition("}")[2]
    amounts = root.find(".//offeringSalesAmounts")
    if amounts is None:
        raise ValueError("no offeringSalesAmounts: not a Form D")
    first = root.find(".//typeOfFiling/dateOfFirstSale")
    if first is not None and first.findtext("value"):
        first_sale = first.findtext("value").strip()
    elif first is not None and (first.findtext("yetToOccur") or "").strip().lower() == "true":
        first_sale = "yet to occur"
    else:
        first_sale = "n/a"
    investors = (root.findtext(".//investors/totalNumberAlreadyInvested") or "n/a").strip()
    amendment = (root.findtext(".//typeOfFiling/newOrAmendment/isAmendment") or "").strip().lower() == "true"
    return (
        f"{_money(amounts.findtext('totalAmountSold'))} sold of {_money(amounts.findtext('totalOfferingAmount'))}"
        f" offered, first sale {first_sale}, {investors} investors" + (" (amendment)" if amendment else "")
    )


def docket_entries(results: list[dict], docket_id: int, case: str) -> list[Entry]:
    """Entries from a CourtListener docket-entries API page. The title carries the court's
    description of the entry, so an order can be told from a routine filing."""
    entries = []
    for result in results:
        number = result.get("entry_number")
        documents = result.get("recap_documents") or []
        text = (result.get("description") or "").strip()
        if not text:
            text = next(((d.get("description") or "").strip() for d in documents if d.get("description")), "")
        text = re.sub(r"\s+", " ", text) or "no description on CourtListener"
        if len(text) > 300:
            text = text[:297].rstrip() + "..."
        label = f"#{number}" if number is not None else "unnumbered"
        anchor = f"entry-{number}" if number is not None else f"minute-entry-{result.get('id')}"
        entries.append(Entry(
            f"{case} {label}: {text}",
            f"https://www.courtlistener.com/docket/{docket_id}/#{anchor}",
            _parse_date(result.get("date_filed")),
            "courtlistener.com",
        ))
    return entries


def strip_publisher(title: str, publisher: str) -> str:
    """Google News appends ' - Publisher' to every title."""
    suffix = f" - {publisher}"
    return title[: -len(suffix)] if publisher and title.endswith(suffix) else title


# ---------------------------------------------------------------- filtering


def blocked_domain(domain: str, blocked: list[str]) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in blocked)


def to_items(entries: list[Entry], source: dict, config: Config) -> list[Item]:
    """Apply the date, domain, title filters and the promotion rule to one source's entries."""
    must = re.compile(source["title_must"], re.IGNORECASE) if source.get("title_must") else None
    items = []
    for entry in entries:
        if entry.published is not None and entry.published < config.baseline_date:
            continue
        if blocked_domain(entry.publisher, config.blocked_domains):
            continue
        if any(p.search(entry.title) for p in config.blocked_titles):
            continue
        if must and not must.search(entry.title):
            continue
        item = source["item"]
        if config.promote_pattern and config.promote_pattern.search(entry.title):
            item = config.promote_item or item
        items.append(
            Item(item, source["notify"], source["name"], entry.title, entry.publisher, entry.url, entry.published)
        )
    return items


TRACKING_PARAMS = re.compile(r"^(utm_|oc$|ref$|cmpid$)", re.IGNORECASE)


def normalize_url(url: str) -> str:
    """Lower-case host, no www, no tracking parameters. The fragment is kept: CourtListener
    tells docket entries apart by it."""
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)])
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), query, parts.fragment))


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(title).lower()).strip()


def _title_key(title: str) -> str | None:
    key = normalize_title(title)
    return key if len(key) >= 20 else None  # short titles are too generic to match on


def new_items(found: list[Item], seen: list[dict], sources: list[dict]) -> list[Item]:
    """Items not already in the seen-log, and not repeated within this run.

    Matches on the URL, and for sources with match_titles on the title too, because Google
    News gives every syndicated copy of a story its own redirect URL.
    """
    match_titles = {s["name"]: s.get("match_titles", True) for s in sources}
    urls = {normalize_url(r["url"]) for r in seen if r.get("url")}
    titles = {normalize_title(r["title"]) for r in seen if r.get("title")}
    result = []
    for item in found:
        url_key = normalize_url(item.url) if item.url else None
        title_key = _title_key(item.title) if match_titles.get(item.source, True) else None
        if (url_key and url_key in urls) or (title_key and title_key in titles):
            continue
        if not url_key and not title_key:
            title_key = normalize_title(item.title)  # still record it, by its whole title
            if title_key in titles:
                continue
        result.append(item)
        if url_key:
            urls.add(url_key)
        if title_key:
            titles.add(title_key)
    return result


# ---------------------------------------------------------------- seen-log


def load_seen(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("status") not in STATUSES:
            raise ConfigError(f"{path.name}: status {row.get('status')!r} is not one of {STATUSES}")
    return rows


def save_seen(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SEEN_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def seen_row(item: Item, today: date) -> dict:
    return {
        "first_seen": today.isoformat(),
        "item": item.item,
        "notify": item.notify,
        "source": item.source,
        "title": item.title,
        "publisher": item.publisher,
        "url": item.url,
        "published": item.published.isoformat() if item.published else "",
        "status": "new",
    }


def pending(rows: list[dict], notify: tuple[str, ...] = ("now",)) -> list[dict]:
    """Rows waiting for Claude: status new, with one of the given notify values."""
    return [r for r in rows if r["status"] == "new" and r["notify"] in notify]


def mark_reported(rows: list[dict], notify: tuple[str, ...]) -> int:
    count = 0
    for row in pending(rows, notify):
        row["status"] = "reported"
        count += 1
    return count


# ---------------------------------------------------------------- W7 correlation


def return_correlation(
    a: list[tuple[date, float]], b: list[tuple[date, float]], window: int
) -> tuple[float, date, date] | None:
    """Pearson correlation of the last `window` daily returns on days both series traded.

    Returns (value, first return day, last return day), or None with too little data.
    """
    b_by_day = dict(b)
    days = [(d, close, b_by_day[d]) for d, close in a if d in b_by_day]
    days.sort()
    returns = [
        (days[i][0], days[i][1] / days[i - 1][1] - 1, days[i][2] / days[i - 1][2] - 1)
        for i in range(1, len(days))
    ]
    if len(returns) < window:
        return None
    returns = returns[-window:]
    xs = [r[1] for r in returns]
    ys = [r[2] for r in returns]
    mx, my = sum(xs) / window, sum(ys) / window
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy), returns[0][0], returns[-1][0]


def correlation_flag(value: float, previous: float | None, low: float, move: float) -> str | None:
    """Why the new correlation is worth reporting, or None."""
    if previous is not None and (previous > low) != (value > low):
        return f"crossed {low:.2f}"
    if previous is not None and abs(value - previous) >= move:
        return f"moved {value - previous:+.2f}"
    return None


# ---------------------------------------------------------------- issue body


def render_issue(
    ticker: str, rows: list[dict], failures: dict[str, str], mode: str, watch_url: str = ""
) -> str:
    """Markdown body for the GitHub issue: the flagged items grouped by watchlist item."""
    lines = [f"## {ticker}: {len(rows)} item(s) for Claude ({mode} run)", ""]
    if watch_url:
        lines += [f"Watchlist: {watch_url}", ""]
    by_item: dict[str, list[dict]] = {}
    for row in rows:
        by_item.setdefault(row["item"], []).append(row)
    for item in sorted(by_item, key=lambda w: int(w[1:])):
        lines.append(f"**{item}**")
        for row in by_item[item]:
            when = row["published"] or "no date"
            publisher = f", {row['publisher']}" if row["publisher"] else ""
            title = row["title"].replace("[", "(").replace("]", ")")
            link = f"[{title}]({row['url']})" if row["url"] else title
            lines.append(f"- {link} ({when}{publisher}; source: {row['source']})")
        lines.append("")
    if failures:
        lines.append("**Could not check**")
        lines += [f"- {name}: {reason}" for name, reason in sorted(failures.items())]
        lines.append("")
    return "\n".join(lines)

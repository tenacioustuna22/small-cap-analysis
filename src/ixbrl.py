"""Read tagged values out of an inline XBRL filing (the 10-Q or 10-K HTML itself).

EDGAR's company facts API leaves out values reported along a dimension, such as revenue
by product line, segment or region. The filing documents carry them: every number is an
`ix:nonFraction` element whose context names its period and its dimension members.
Pure parsing, no network access.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

IX = "{http://www.xbrl.org/2013/inlineXBRL}"
XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"


class IxbrlError(ValueError):
    pass


@dataclass(frozen=True)
class DimFact:
    concept: str  # with its prefix, such as us-gaap:Revenues
    start: date | None  # None for balance sheet (point in time) values
    end: date
    dims: tuple[tuple[str, str], ...]  # sorted (axis, member) pairs; () for a total
    value: float
    unit: str


@dataclass(frozen=True)
class _Context:
    start: date | None
    end: date
    dims: tuple[tuple[str, str], ...]


def _contexts(root: ET.Element) -> dict[str, _Context]:
    out = {}
    for ctx in root.iter(f"{XBRLI}context"):
        period = ctx.find(f"{XBRLI}period")
        if period is None:
            continue
        instant = period.findtext(f"{XBRLI}instant")
        start = period.findtext(f"{XBRLI}startDate")
        end = instant or period.findtext(f"{XBRLI}endDate")
        if not end:
            continue
        dims = []
        for member in ctx.iter(f"{XBRLDI}explicitMember"):
            dims.append((member.get("dimension", ""), (member.text or "").strip()))
        for member in ctx.iter(f"{XBRLDI}typedMember"):
            dims.append((member.get("dimension", ""), "".join(member.itertext()).strip()))
        out[ctx.get("id", "")] = _Context(
            start=date.fromisoformat(start.strip()) if start and not instant else None,
            end=date.fromisoformat(end.strip()),
            dims=tuple(sorted(dims)),
        )
    return out


def parse_number(text: str, fmt: str = "", scale: str = "0", sign: str = "") -> float | None:
    """The value an `ix:nonFraction` stands for. Returns None when the text is not a number."""
    fmt = fmt.rsplit(":", 1)[-1]
    if fmt in ("fixed-zero", "zerodash", "numdash"):
        value = 0.0
    else:
        cleaned = text.strip()
        if fmt in ("num-comma-decimal", "numcommadecimal"):
            cleaned = cleaned.replace(".", "").replace(" ", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "").replace(" ", "")
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        if not cleaned or cleaned == ".":
            return 0.0 if text.strip() in ("-", "—", "–") else None
        try:
            value = float(cleaned)
        except ValueError:
            return None
    value *= 10 ** int(scale or 0)
    return -value if sign == "-" else value


COVER_SHARES = "dei:EntityCommonStockSharesOutstanding"


def cover_shares(facts: list[DimFact]) -> tuple[float, date, list[tuple[str, float]]] | None:
    """Shares outstanding from the cover page, summed across share classes on the latest
    cover date: (total, as of, [(class member, shares)]). None when the cover has none."""
    cover = [f for f in facts if f.concept == COVER_SHARES and f.start is None]
    if not cover:
        return None
    latest = max(f.end for f in cover)
    on_day = [f for f in cover if f.end == latest]
    # A company with one class tags a total with no dimension; with several, one value per class.
    by_class: dict[str, float] = {}
    for f in on_day:
        name = f.dims[0][1] if f.dims else ""
        by_class.setdefault(name, f.value)
    if "" in by_class and len(by_class) > 1:
        del by_class[""]  # a total alongside the classes would count twice
    return sum(by_class.values()), latest, sorted(by_class.items())


def parse_facts(document: str) -> list[DimFact]:
    """Every numeric fact in an inline XBRL document."""
    try:
        root = ET.fromstring(document.encode("utf-8") if isinstance(document, str) else document)
    except ET.ParseError as error:
        raise IxbrlError(f"not well-formed inline XBRL: {error}") from error
    contexts = _contexts(root)
    if not contexts:
        raise IxbrlError("no XBRL contexts found: the document is probably not inline XBRL")
    facts = []
    for el in root.iter(f"{IX}nonFraction"):
        ctx = contexts.get(el.get("contextRef", ""))
        if ctx is None:
            continue
        value = parse_number("".join(el.itertext()), el.get("format", ""), el.get("scale", "0"), el.get("sign", ""))
        if value is None:
            continue
        facts.append(DimFact(el.get("name", ""), ctx.start, ctx.end, ctx.dims, value, el.get("unitRef", "")))
    return facts

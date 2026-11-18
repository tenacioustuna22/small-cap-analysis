"""Insider transactions (Form 4) and 5% holders (Schedule 13D/G). Pure parsing and sums."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime

from src.edgar import Filing

INSIDER_FORMS = {"4", "4/A"}
HOLDER_FORMS = {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A",
                "SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A"}

BUY = "Open-market buy"
SALE = "Open-market sale"
PLAN_SALE = "Planned sale (10b5-1)"
TAX_SALE = "Sold to cover taxes"
AWARD = "Grant or award"
EXERCISE = "Option or warrant exercise"
GIFT = "Gift"
OTHER = "Other"
DISCRETIONARY = {BUY, SALE}  # the trades that say something about an insider's view

TAX_PATTERN = re.compile(r"sell[- ]to[- ]cover|tax withholding|withholding (tax )?obligation|satisfy .{0,40}tax", re.I)
PLAN_PATTERN = re.compile(r"10b5-1", re.I)
CODE_KINDS = {"P": BUY, "A": AWARD, "M": EXERCISE, "X": EXERCISE, "C": EXERCISE, "F": TAX_SALE, "G": GIFT}


@dataclass(frozen=True)
class InsiderTrade:
    owner: str
    role: str
    day: date
    code: str
    kind: str
    shares: float
    price: float | None
    acquired: bool
    owned_after: float | None
    filing: Filing

    @property
    def value(self) -> float | None:
        return self.shares * self.price if self.price else None


def _text(element: ET.Element | None, path: str) -> str:
    found = element.find(path) if element is not None else None
    return (found.text or "").strip() if found is not None and found.text else ""


def _number(element: ET.Element, path: str) -> float | None:
    raw = _text(element, path)
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def _role(owner: ET.Element) -> str:
    rel = owner.find("reportingOwnerRelationship")
    roles = []
    if _text(rel, "isOfficer") in ("1", "true"):
        roles.append(_text(rel, "officerTitle") or "Officer")
    if _text(rel, "isDirector") in ("1", "true"):
        roles.append("Director")
    if _text(rel, "isTenPercentOwner") in ("1", "true"):
        roles.append("10% owner")
    if _text(rel, "isOther") in ("1", "true"):
        roles.append(_text(rel, "otherText") or "Other")
    return ", ".join(roles)


def parse_form4(xml_text: str, filing: Filing) -> list[InsiderTrade]:
    """Non-derivative transactions (common stock bought, sold, granted) from one Form 4."""
    root = ET.fromstring(xml_text.encode("utf-8"))
    owner = root.find("reportingOwner")
    name = _text(owner, "reportingOwnerId/rptOwnerName")
    role = _role(owner) if owner is not None else ""
    plan = _text(root, "aff10b5One") in ("1", "true")
    footnotes = {f.get("id"): (f.text or "") for f in root.iter("footnote")}

    trades = []
    for t in root.iter("nonDerivativeTransaction"):
        code = _text(t, "transactionCoding/transactionCode")
        shares = _number(t, "transactionAmounts/transactionShares/value")
        day = _text(t, "transactionDate/value")
        if not code or shares is None or not day:
            continue
        notes = " ".join(footnotes.get(ref.get("id"), "") for ref in t.iter("footnoteId"))
        if code == "S":
            if TAX_PATTERN.search(notes):
                kind = TAX_SALE
            elif plan or PLAN_PATTERN.search(notes):
                kind = PLAN_SALE
            else:
                kind = SALE
        else:
            kind = CODE_KINDS.get(code, OTHER)
        trades.append(
            InsiderTrade(
                owner=name.title() if name.isupper() else name,
                role=role,
                day=date.fromisoformat(day[:10]),
                code=code,
                kind=kind,
                shares=shares,
                price=_number(t, "transactionAmounts/transactionPricePerShare/value"),
                acquired=_text(t, "transactionAmounts/transactionAcquiredDisposedCode/value") == "A",
                owned_after=_number(t, "postTransactionAmounts/sharesOwnedFollowingTransaction/value"),
                filing=filing,
            )
        )
    return trades


@dataclass
class InsiderSummary:
    since: date
    trades: list[InsiderTrade] = field(default_factory=list)  # newest first
    unreadable: int = 0  # Form 4s that could not be parsed

    def _sum(self, kind: str, attr: str) -> float:
        return sum(getattr(t, attr) or 0.0 for t in self.trades if t.kind == kind)

    @property
    def bought_shares(self) -> float:
        return self._sum(BUY, "shares")

    @property
    def bought_value(self) -> float:
        return self._sum(BUY, "value")

    @property
    def sold_shares(self) -> float:
        return self._sum(SALE, "shares") + self._sum(PLAN_SALE, "shares")

    @property
    def sold_value(self) -> float:
        return self._sum(SALE, "value") + self._sum(PLAN_SALE, "value")

    @property
    def tax_shares(self) -> float:
        return self._sum(TAX_SALE, "shares")

    @property
    def net_value(self) -> float:
        """Open-market buys minus discretionary and planned sales, in dollars."""
        return self.bought_value - self.sold_value

    @property
    def buyers(self) -> list[str]:
        return sorted({t.owner for t in self.trades if t.kind == BUY})

    @property
    def sellers(self) -> list[str]:
        return sorted({t.owner for t in self.trades if t.kind in (SALE, PLAN_SALE)})


@dataclass(frozen=True)
class OwnerTotals:
    owner: str
    role: str
    bought: float  # dollars, open market
    sold: float  # dollars, discretionary open-market sales
    planned: float  # dollars, 10b5-1 plan sales
    last_day: date
    owned_after: float | None  # after their most recent trade


def by_owner(trades: list[InsiderTrade]) -> list[OwnerTotals]:
    """Open-market and plan totals per insider, biggest dollar activity first."""
    groups: dict[str, list[InsiderTrade]] = {}
    for t in trades:
        if t.kind in (BUY, SALE, PLAN_SALE):
            groups.setdefault(t.owner, []).append(t)
    out = []
    for owner, rows in groups.items():
        latest = max(rows, key=lambda t: t.day)
        def total(kind: str) -> float:
            return sum(t.value or 0.0 for t in rows if t.kind == kind)
        out.append(OwnerTotals(owner, latest.role, total(BUY), total(SALE), total(PLAN_SALE),
                               latest.day, latest.owned_after))
    return sorted(out, key=lambda o: -(o.bought + o.sold + o.planned))


def summarize_insiders(trades: list[InsiderTrade], since: date, unreadable: int = 0) -> InsiderSummary:
    kept = sorted((t for t in trades if t.day >= since), key=lambda t: (t.day, t.filing.filed), reverse=True)
    return InsiderSummary(since, kept, unreadable)


# --- 5% holders ---------------------------------------------------------------------

@dataclass(frozen=True)
class HolderFiling:
    filing: Filing
    holder: str  # "" when the filing is free-form HTML
    shares: float | None
    percent: float | None
    event: date | None

    @property
    def activist(self) -> bool:
        """13D filers may seek influence; 13G filers declare they are passive."""
        return "13D" in self.filing.form


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_schedule13(xml_text: str, filing: Filing) -> HolderFiling:
    """Holder name, shares and percent of class from a new-format (XML) 13D or 13G."""
    holder, shares, pct, event = "", None, None, None
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return HolderFiling(filing, "", None, None, None)
    for el in root.iter():
        name, text = _local(el.tag), (el.text or "").strip()
        if not text:
            continue
        if name == "reportingPersonName" and not holder:
            holder = text
        elif name in ("reportingPersonBeneficiallyOwnedAggregateNumberOfShares", "aggregateAmountOwned") and shares is None:
            shares = _float(text)
        elif name in ("classPercent", "percentOfClass") and pct is None:
            pct = _float(text)
        elif name in ("eventDateRequiresFilingThisStatement", "dateOfEvent") and event is None:
            event = _date(text)
    return HolderFiling(filing, holder, shares, pct, event)


def _float(text: str) -> float | None:
    try:
        return float(text.replace(",", "").rstrip("%"))
    except ValueError:
        return None


def _date(text: str) -> date | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def latest_by_holder(filings: list[HolderFiling]) -> list[HolderFiling]:
    """The newest filing per named holder, plus every unnamed (HTML) filing, newest first."""
    seen: dict[str, HolderFiling] = {}
    unnamed = []
    for h in sorted(filings, key=lambda h: h.filing.filed, reverse=True):
        if not h.holder:
            unnamed.append(h)
        elif h.holder.lower() not in seen:
            seen[h.holder.lower()] = h
    return sorted(list(seen.values()) + unnamed, key=lambda h: h.filing.filed, reverse=True)

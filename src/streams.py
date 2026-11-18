"""Revenue split into streams (business line, product versus service, region).

The split comes from the dimensional facts in each 10-Q and 10-K (see `ixbrl.py`).
Which split to show is a per-company choice in revenue_streams.csv. Quarters are built
the same way as total revenue: year-to-date totals are turned into single quarters and
the fourth quarter is the 10-K year minus the first nine months. Pure functions.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from src.edgar import Filing
from src.financials import COST_OF_REVENUE_TAGS, REVENUE_TAGS, margin_at, quarter_near, trailing_sum
from src.ixbrl import DimFact
from src.metrics import Fact, QuarterFlow, pct_change, quarterly_flows, start_values, year_to_date  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
STREAMS_PATH = ROOT / "revenue_streams.csv"
PERIODIC_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A"}
MAX_STREAMS = 3  # chart colours available; members past the second fold into "Other"
MISMATCH_PCT = 1.0  # streams that miss the reported total by more than this get a note

# Member names whose automatic label reads badly.
LABELS = {
    "country:US": "United States",
    "us-gaap:NonUsMember": "Outside the US",
    "us-gaap:ProductMember": "Product",
    "us-gaap:ServiceMember": "Service",
    "us-gaap:CommonClassAMember": "Class A",
    "us-gaap:CommonClassBMember": "Class B",
}


@dataclass(frozen=True)
class SplitChoice:
    axis: str  # such as us-gaap:ReportingUnitAxis
    title: str  # such as "By business line"
    aliases: tuple[tuple[str, str], ...] = ()  # (old member, current member) for renamed members


def _aliases(text: str) -> tuple[tuple[str, str], ...]:
    """"old=new; old2=new2" from the merge column."""
    pairs = []
    for part in filter(None, (p.strip() for p in (text or "").split(";"))):
        old, sep, new = part.partition("=")
        if not sep or not old.strip() or not new.strip():
            raise ValueError(f"merge entry {part!r} should look like old:Member=new:Member")
        pairs.append((old.strip(), new.strip()))
    return tuple(pairs)


def load_split_choices(ticker: str, path: Path = STREAMS_PATH) -> list[SplitChoice]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            SplitChoice(row["axis"].strip(), row["title"].strip(), _aliases(row.get("merge", "")))
            for row in csv.DictReader(handle)
            if (row.get("ticker") or "").strip().upper() == ticker.upper()
        ]


def member_label(member: str) -> str:
    """bfly:CoreBusinessMember -> Core business."""
    if member in LABELS:
        return LABELS[member]
    name = member.rsplit(":", 1)[-1]
    name = re.sub(r"Member$", "", name)
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)
    text = " ".join(w if w.isupper() and len(w) > 1 else w.lower() for w in words)
    return text[:1].upper() + text[1:] if text else member


@dataclass
class Stream:
    member: str
    label: str
    revenue: list[QuarterFlow] = field(default_factory=list)  # oldest first
    cost: list[QuarterFlow] = field(default_factory=list)  # cost of revenue, when tagged on the same axis
    ytd: Fact | None = None  # year-to-date total ending with the latest quarter, as filed
    ytd_prior: Fact | None = None  # the same months a year earlier

    @property
    def latest(self) -> QuarterFlow | None:
        return self.revenue[-1] if self.revenue else None

    @property
    def ytd_months(self) -> int | None:
        return round((self.ytd.end - self.ytd.start).days / 30.44) if self.ytd else None

    def start_values(self) -> dict[str, float]:
        """Annual revenue starting points a scenario can build on, in dollars."""
        return start_values(self.latest, self.ttm(self.latest.end) if self.latest else None, self.ytd)

    @property
    def growth_ytd(self) -> float | None:
        return pct_change(self.ytd.val if self.ytd else None, self.ytd_prior.val if self.ytd_prior else None)

    def at(self, end: date) -> QuarterFlow | None:
        return next((q for q in self.revenue if q.end == end), None)

    def year_ago(self, end: date) -> QuarterFlow | None:
        return quarter_near(self.revenue, end - timedelta(days=365))

    def growth_quarter(self, end: date) -> float | None:
        now, then = self.at(end), self.year_ago(end)
        return pct_change(now.val if now else None, then.val if then else None)

    def ttm(self, end: date) -> float | None:
        return trailing_sum(self.revenue, end)

    def growth_ttm(self, end: date) -> float | None:
        then = self.year_ago(end)
        return pct_change(self.ttm(end), self.ttm(then.end) if then else None)

    def margin(self, end: date) -> float | None:
        """Gross margin in one quarter, from this stream's own cost of revenue."""
        if not self.cost:
            return None
        gross = [QuarterFlow(r.end, r.val - c.val, r.source)
                 for r in self.revenue for c in self.cost if c.end == r.end]
        return margin_at(gross, self.revenue, end)


@dataclass
class RevenueSplit:
    axis: str
    title: str
    concept: str = ""
    streams: list[Stream] = field(default_factory=list)  # in the order the newest filing lists them
    notes: list[str] = field(default_factory=list)
    reported_quarters: list[date] = field(default_factory=list)  # quarters with total revenue

    @property
    def quarters(self) -> list[date]:
        """Quarter ends that every stream reports, oldest first."""
        if not self.streams:
            return []
        common = set.intersection(*({q.end for q in s.revenue} for s in self.streams))
        return sorted(common)

    @property
    def timeline(self) -> list[date]:
        """Every quarter from the first split quarter to the last, including ones without a split."""
        split = self.quarters
        if not split:
            return []
        between = {d for d in self.reported_quarters if split[0] <= d <= split[-1]}
        return sorted(between | set(split))

    @property
    def missing(self) -> list[date]:
        have = set(self.quarters)
        return [d for d in self.timeline if d not in have]

    @property
    def latest_end(self) -> date | None:
        return self.quarters[-1] if self.quarters else None

    def total(self, end: date) -> float | None:
        values = [s.at(end) for s in self.streams]
        return sum(q.val for q in values) if all(values) else None

    def share(self, stream: Stream, end: date) -> float | None:
        total, part = self.total(end), stream.at(end)
        return part.val / total * 100 if total and part else None


def _facts(tagged: list[tuple[Filing, list[DimFact]]], concept: str, choice: SplitChoice) -> dict[str, list[Fact]]:
    """Facts for one concept split along exactly one axis, per member (renamed members joined)."""
    renamed = dict(choice.aliases)
    out: dict[str, list[Fact]] = {}  # members in the order the newest filing lists them
    for filing, facts in sorted(tagged, key=lambda t: t[0].filed, reverse=True):
        for f in facts:
            if f.concept != concept or f.start is None or len(f.dims) != 1 or f.dims[0][0] != choice.axis:
                continue
            member = renamed.get(f.dims[0][1], f.dims[0][1])
            out.setdefault(member, []).append(Fact(f"{concept} [{member}]", f.start, f.end, f.value, filing.form, filing.filed))
    return out


def compute_split(
    tagged: list[tuple[Filing, list[DimFact]]],
    choice: SplitChoice,
    total_revenue: list[QuarterFlow] | None = None,
) -> RevenueSplit:
    """Quarterly revenue per member of `choice.axis`, from the parsed periodic filings."""
    split = RevenueSplit(choice.axis, choice.title)
    split.reported_quarters = [q.end for q in total_revenue or []]
    by_member: dict[str, list[Fact]] = {}
    for tag in REVENUE_TAGS:
        by_member = _facts(tagged, f"us-gaap:{tag}", choice)
        if by_member:
            split.concept = f"us-gaap:{tag}"
            break
    if not by_member:
        split.notes.append(f"no revenue is tagged along {choice.axis} in the filings read")
        return split

    costs: dict[str, list[Fact]] = {}
    for tag in COST_OF_REVENUE_TAGS:
        costs = _facts(tagged, f"us-gaap:{tag}", choice)
        if costs:
            break

    streams = [
        Stream(member, member_label(member), quarterly_flows(facts), quarterly_flows(costs.get(member, [])))
        for member, facts in by_member.items()
    ]
    # Keep the filing's order, so a stream keeps its colour when the streams change rank.
    streams = [s for s in streams if s.revenue]
    for s in streams:
        s.ytd, s.ytd_prior = year_to_date(by_member[s.member], s.latest.end)
    if len(streams) > MAX_STREAMS:
        kept, rest = streams[: MAX_STREAMS - 1], streams[MAX_STREAMS - 1:]
        other = Stream("other", "Other")
        ends = set.intersection(*({q.end for q in s.revenue} for s in rest))
        other.revenue = [QuarterFlow(end, sum(s.at(end).val for s in rest), rest[0].at(end).source) for end in sorted(ends)]
        streams = kept + [other]
        split.notes.append(f"the last {len(rest)} streams the filing lists are combined as Other")
    split.streams = streams

    if not split.quarters:
        split.notes.append("the streams share no quarter, so they cannot be compared side by side")
    if split.missing:
        split.notes.append(
            "no split for the quarter" + ("s" if len(split.missing) > 1 else "") + " ended "
            + ", ".join(str(d) for d in split.missing)
            + ": the filings read do not report it, so four-quarter figures that need "
            + ("those quarters" if len(split.missing) > 1 else "that quarter") + " show n/a"
        )
    for end in split.quarters[-8:] if total_revenue else []:
        reported = next((q.val for q in total_revenue if q.end == end), None)
        summed = split.total(end)
        if reported and summed is not None and abs(summed - reported) / abs(reported) * 100 > MISMATCH_PCT:
            split.notes.append(
                f"in the quarter ended {end} the streams add up to ${summed / 1e6:.1f}M against "
                f"${reported / 1e6:.1f}M reported in total; the split may leave something out"
            )
    return split

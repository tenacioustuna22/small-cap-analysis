"""Dilution picture from EDGAR data: share count trend, overhang, funding, offerings."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from src.edgar import Filing, facts_for_tag
from src.metrics import (
    Fact,
    latest_instant,
    pct_change,
    quarterly_flows,
    single_quarter_values,
    trailing_four_quarters,
    value_near,
)

# Point-in-time share counts, best first. The cover page count is dated just before
# the filing, so it is the most current. Companies with several share classes report
# these per class, which EDGAR's company facts leave out.
SHARES_OUTSTANDING_TAGS = [
    ("dei", "EntityCommonStockSharesOutstanding", "cover page"),
    ("us-gaap", "CommonStockSharesOutstanding", "balance sheet"),
    ("us-gaap", "CommonStockSharesIssued", "balance sheet"),
]
WEIGHTED_SHARES_TAG = "WeightedAverageNumberOfSharesOutstandingBasic"
ANTIDILUTIVE_TAG = "AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShareAmount"
WARRANTS_TAG = "ClassOfWarrantOrRightOutstanding"
OPTIONS_TAG = "ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsOutstandingNumber"
FINANCING_CASH_FLOW_TAG = "NetCashProvidedByUsedInFinancingActivities"

STALE_AFTER_DAYS = 135  # a quarter plus the 45-day 10-Q filing window
REVERSE_SPLIT_DROP_PCT = -20.0

# Filing types that register or sell securities.
OFFERING_FORMS = {
    "S-3": "shelf registration",
    "S-3ASR": "automatic shelf registration",
    "S-1": "registration statement",
    "F-3": "shelf registration",
    "EFFECT": "registration declared effective",
    "424B2": "prospectus supplement",
    "424B3": "prospectus, often resale by existing holders",
    "424B4": "prospectus for a priced offering",
    "424B5": "prospectus supplement: offering or at-the-market program",
    "424B7": "prospectus for resale by existing holders",
}

# Sentences worth quoting from the latest 10-Q or 10-K: programs that let the company
# keep selling shares. Completed offerings already show in the share count and the
# filing list, so they are left out.
OFFERING_SENTENCE_PATTERN = re.compile(
    r"at[- ]the[- ]market|\bATM\b|sales agreement|equity distribution agreement"
    r"|shelf registration|equity line|common stock purchase agreement",
    re.IGNORECASE,
)


@dataclass
class Dilution:
    shares: Fact | None = None
    shares_basis: str = ""
    quarter_avg: Fact | None = None  # weighted average shares, latest quarter
    quarter_avg_1y: Fact | None = None  # same quarter one year earlier
    quarter_avg_3y: Fact | None = None  # same quarter three years earlier
    history: list[Fact] = field(default_factory=list)  # quarterly averages, last three years
    potential_shares: float | None = None
    potential_as_of: date | None = None
    potential_is_partial: bool = False
    financing_ttm: float | None = None
    share_classes: list[tuple[str, float]] = field(default_factory=list)  # from the filing's cover page
    notes: list[str] = field(default_factory=list)

    @property
    def change_1y_pct(self) -> float | None:
        return _change(self.quarter_avg, self.quarter_avg_1y)

    @property
    def change_3y_pct(self) -> float | None:
        return _change(self.quarter_avg, self.quarter_avg_3y)

    @property
    def overhang_pct(self) -> float | None:
        """Potential new shares as a percentage of current shares."""
        if self.shares is None or self.potential_shares is None or self.shares.val == 0:
            return None
        return self.potential_shares / self.shares.val * 100


@dataclass(frozen=True)
class OfferingFiling:
    filing: Filing
    label: str
    amount: float | None  # dollars registered, when the fee table states it


def _change(new: Fact | None, old: Fact | None) -> float | None:
    return pct_change(new.val if new else None, old.val if old else None)


NO_POINT_IN_TIME = "no point-in-time share count in EDGAR's summary data"


def use_cover_shares(
    result: Dilution, total: float, as_of: date, classes: list[tuple[str, float]], filing: Filing
) -> bool:
    """Take the cover page count read from the filing itself when it is newer than what
    company facts gave. EDGAR's summary data drops per-class counts; the filing has them."""
    if result.shares is not None and result.shares_basis == "cover page" and result.shares.end >= as_of:
        return False
    result.shares = Fact("dei:EntityCommonStockSharesOutstanding", None, as_of, total, filing.form, filing.filed)
    result.shares_basis = "cover page"
    result.share_classes = classes if len(classes) > 1 else []
    result.notes = [n for n in result.notes if not n.startswith(NO_POINT_IN_TIME)]
    return True


def compute_dilution(company: dict, today: date | None = None) -> Dilution:
    today = today or date.today()
    result = Dilution()

    # Share count trend from quarterly weighted averages: every company reports these.
    quarters = single_quarter_values(facts_for_tag(company, WEIGHTED_SHARES_TAG, unit="shares"))
    if quarters:
        result.quarter_avg = quarters[-1]
        history_start = result.quarter_avg.end - timedelta(days=3 * 365 + 20)
        result.history = [q for q in quarters if q.end >= history_start]
        earlier = quarters[:-1]
        result.quarter_avg_1y = value_near(earlier, result.quarter_avg.end - timedelta(days=365))
        result.quarter_avg_3y = value_near(earlier, result.quarter_avg.end - timedelta(days=3 * 365))
        if (today - result.quarter_avg.end).days > STALE_AFTER_DAYS:
            result.notes.append(f"latest share data is for the quarter ended {result.quarter_avg.end}")
    else:
        result.notes.append("no weighted average share count found")

    # Current share count: the most recent point-in-time figure, if there is a fresh one.
    candidates = []
    for taxonomy, tag, basis in SHARES_OUTSTANDING_TAGS:
        fact = latest_instant(facts_for_tag(company, tag, unit="shares", taxonomy=taxonomy))
        if fact is not None and (today - fact.end).days <= STALE_AFTER_DAYS:
            candidates.append((fact, basis))
    if candidates:
        newest = max(fact.end for fact, _ in candidates)
        result.shares, result.shares_basis = next(c for c in candidates if c[0].end == newest)
    elif result.quarter_avg is not None:
        result.shares, result.shares_basis = result.quarter_avg, "quarter average"
        result.notes.append(
            f"{NO_POINT_IN_TIME} (typical for companies "
            "with several share classes); using the latest quarter's weighted average, "
            "which lags any recent issuance"
        )

    for label, pct in (("one year", result.change_1y_pct), ("three years", result.change_3y_pct)):
        if pct is not None and pct < REVERSE_SPLIT_DROP_PCT:
            result.notes.append(
                f"share count fell {abs(pct):.0f}% over {label}: check for a reverse split "
                "before reading the trend"
            )

    _set_potential_shares(company, result)

    financing = trailing_four_quarters(quarterly_flows(facts_for_tag(company, FINANCING_CASH_FLOW_TAG)))
    if financing:
        result.financing_ttm = sum(q.val for q in financing)
    else:
        result.notes.append("fewer than four consecutive quarters of financing cash flow")
    return result


def _set_potential_shares(company: dict, result: Dilution) -> None:
    """Shares that options, warrants, RSUs, convertibles and earnouts could add."""
    excluded = [f for f in facts_for_tag(company, ANTIDILUTIVE_TAG, unit="shares") if f.start]
    if excluded:
        latest = max(excluded, key=lambda f: (f.end, f.start, f.filed))
        result.potential_shares, result.potential_as_of = latest.val, latest.end
        return

    # Fallback: add up the instruments that are tagged individually.
    parts = [
        latest_instant(facts_for_tag(company, tag, unit="shares"))
        for tag in (WARRANTS_TAG, OPTIONS_TAG)
    ]
    parts = [p for p in parts if p is not None]
    if not parts:
        result.notes.append("no potentially dilutive securities found under the known tags")
        return
    newest = max(p.end for p in parts)
    current = [p for p in parts if p.end == newest]
    result.potential_shares = sum(p.val for p in current)
    result.potential_as_of = newest
    result.potential_is_partial = True
    result.notes.append(
        "potential shares counts warrants and options only; RSUs, convertibles and "
        "earnout shares are not included"
    )


def offering_filings(filings: list[Filing], company: dict, since: date) -> list[OfferingFiling]:
    """Registration and prospectus filings since `since`, newest first."""
    registered = {
        (f.form, f.filed): f.val
        for f in facts_for_tag(company, "TtlOfferingAmt", taxonomy="ffd")
    }
    found = []
    for filing in filings:
        base_form = filing.form.removesuffix("/A")
        if filing.filed < since or base_form not in OFFERING_FORMS:
            continue
        label = OFFERING_FORMS[base_form] + (" (amendment)" if filing.form.endswith("/A") else "")
        found.append(OfferingFiling(filing, label, registered.get((filing.form, filing.filed))))
    return sorted(found, key=lambda o: o.filing.filed, reverse=True)


def latest_periodic_report(filings: list[Filing]) -> Filing | None:
    """The most recent 10-Q or 10-K."""
    reports = [f for f in filings if f.form in ("10-Q", "10-K")]
    return max(reports, key=lambda f: f.filed, default=None)

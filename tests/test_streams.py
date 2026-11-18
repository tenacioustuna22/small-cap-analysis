from datetime import date

import pytest

from src.edgar import Filing
from src.ixbrl import DimFact
from src.metrics import Fact, QuarterFlow
from src.streams import SplitChoice, compute_split, load_split_choices, member_label, year_to_date

AXIS = "srt:ProductOrServiceAxis"
REV = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
COST = "us-gaap:CostOfGoodsAndServicesSold"
PRODUCT, SERVICE, OLD_SERVICE = "us-gaap:ProductMember", "bfly:SoftwareAndOtherServicesMember", "us-gaap:ServiceOtherMember"


def d(text: str) -> date:
    return date.fromisoformat(text)


def fact(start: str, end: str, member: str | None, value: float, concept: str = REV) -> DimFact:
    dims = ((AXIS, member),) if member else ()
    return DimFact(concept, d(start), d(end), dims, value, "usd")


def filing(form: str, filed: str) -> Filing:
    return Filing(form, d(filed), "", f"https://x/{filed}.htm")


# 2025: product 10, 11, 12 then a 10-K year of 46 (so Q4 is 13); services 5 a quarter,
# reported under its old member name in the 10-K. 2026 Q1: product 14, services 6.
TAGGED = [
    (filing("10-Q", "2025-05-01"), [fact("2025-01-01", "2025-03-31", PRODUCT, 10), fact("2025-01-01", "2025-03-31", SERVICE, 5),
                                    fact("2025-01-01", "2025-03-31", PRODUCT, 4, COST)]),
    (filing("10-Q", "2025-08-01"), [fact("2025-04-01", "2025-06-30", PRODUCT, 11), fact("2025-01-01", "2025-06-30", PRODUCT, 21),
                                    fact("2025-04-01", "2025-06-30", SERVICE, 5), fact("2025-01-01", "2025-06-30", SERVICE, 10)]),
    (filing("10-Q", "2025-11-01"), [fact("2025-07-01", "2025-09-30", PRODUCT, 12), fact("2025-01-01", "2025-09-30", PRODUCT, 33),
                                    fact("2025-07-01", "2025-09-30", SERVICE, 5), fact("2025-01-01", "2025-09-30", SERVICE, 15)]),
    (filing("10-K", "2026-02-27"), [fact("2025-01-01", "2025-12-31", PRODUCT, 46), fact("2025-01-01", "2025-12-31", OLD_SERVICE, 20),
                                    fact("2025-01-01", "2025-12-31", None, 66)]),
    (filing("10-Q", "2026-05-01"), [fact("2026-01-01", "2026-03-31", PRODUCT, 14), fact("2026-01-01", "2026-03-31", SERVICE, 6),
                                    fact("2026-01-01", "2026-03-31", PRODUCT, 5, COST),
                                    fact("2025-01-01", "2025-03-31", PRODUCT, 10), fact("2025-01-01", "2025-03-31", SERVICE, 5)]),
]
CHOICE = SplitChoice(AXIS, "By product and service", ((OLD_SERVICE, SERVICE),))


def totals(*pairs: tuple[str, float]) -> list[QuarterFlow]:
    return [QuarterFlow(d(end), val, Fact("Rev", None, d(end), val, "10-Q", d(end))) for end, val in pairs]


def test_streams_turn_year_to_date_totals_into_quarters_and_join_renamed_members():
    split = compute_split(TAGGED, CHOICE)
    assert [s.label for s in split.streams] == ["Product", "Software and other services"]  # the newest filing's order
    product, service = split.streams
    assert [q.val for q in product.revenue] == [10, 11, 12, 13, 14]
    assert [q.val for q in service.revenue] == [5, 5, 5, 5, 6]  # Q4 from the old member name
    assert product.revenue[3].source.form == "10-K"
    end = d("2026-03-31")
    assert split.latest_end == end
    assert product.growth_quarter(end) == pytest.approx(40)
    assert split.share(product, end) == 70
    assert product.ttm(end) == 50 and product.growth_ttm(end) is None  # no earlier year to compare
    assert product.margin(end) == pytest.approx(64.3, abs=0.1)  # (14 - 5) / 14
    assert service.margin(end) is None and split.notes == []


def test_without_the_alias_the_fourth_quarter_goes_missing_and_is_noted():
    reported = totals(("2025-03-31", 15), ("2025-06-30", 16), ("2025-09-30", 17), ("2025-12-31", 18), ("2026-03-31", 20))
    split = compute_split(TAGGED, SplitChoice(AXIS, "x"), reported)
    # The old member has a year but no quarters, so it drops out and services lose Q4.
    assert len(split.streams) == 2
    assert split.missing == [d("2025-12-31")]
    assert any("no split for the quarter ended 2025-12-31" in n for n in split.notes)

    joined = compute_split(TAGGED, CHOICE, reported)
    assert joined.missing == [] and joined.timeline == joined.quarters


def test_gaps_and_mismatched_totals_are_noted():
    no_q4 = [t for t in TAGGED if t[0].form != "10-K"]
    reported = totals(("2025-03-31", 15), ("2025-06-30", 16), ("2025-09-30", 17), ("2025-12-31", 18), ("2026-03-31", 99))
    split = compute_split(no_q4, CHOICE, reported)
    assert split.missing == [d("2025-12-31")]
    assert d("2025-12-31") in split.timeline
    assert any("no split for the quarter ended 2025-12-31" in n for n in split.notes)
    assert any(n.startswith("in the quarter ended 2026-03-31 the streams add up") for n in split.notes)  # 20 vs 99
    assert not any("2025-09-30 the streams" in n for n in split.notes)  # 17 matches


def test_year_to_date_growth_uses_the_filed_totals():
    def f(start: str, end: str, val: float, filed: str = "2026-11-01") -> Fact:
        return Fact("x", d(start), d(end), val, "10-Q", d(filed))

    facts = [f("2026-01-01", "2026-09-30", 27.6), f("2025-01-01", "2025-09-30", 5.3),
             f("2025-01-01", "2025-09-30", 5.0, filed="2025-11-01"),  # superseded by the later filing
             f("2026-07-01", "2026-09-30", 11.1), f("2025-01-01", "2025-12-31", 9.0, filed="2026-02-27")]
    now, prior = year_to_date(facts, d("2026-09-30"))
    assert (now.val, prior.val) == (27.6, 5.3)
    assert year_to_date(facts, d("2026-03-31")) == (None, None)

    split = compute_split(TAGGED[:3], CHOICE)  # latest is 2025-09-30, nothing a year earlier
    product = split.streams[0]
    assert product.ytd.val == 33 and product.ytd_months == 9 and product.growth_ytd is None


def test_missing_axis_and_member_labels(tmp_path):
    split = compute_split(TAGGED, SplitChoice("us-gaap:ReportingUnitAxis", "By business line"))
    assert split.streams == [] and "no revenue is tagged" in split.notes[0]
    assert member_label("bfly:CoreBusinessMember") == "Core business"
    assert member_label("us-gaap:NonUsMember") == "Outside the US"
    assert member_label("hypr:MRISystemsMember") == "MRI systems"

    path = tmp_path / "revenue_streams.csv"
    path.write_text("ticker,axis,title,merge\nbfly,a:Axis,By line,old:A=new:B; old:C=new:D\nHYPR,b:Axis,By b,\n", encoding="utf-8")
    assert load_split_choices("BFLY", path) == [SplitChoice("a:Axis", "By line", (("old:A", "new:B"), ("old:C", "new:D")))]
    assert load_split_choices("HYPR", path)[0].aliases == ()
    path.write_text("ticker,axis,title,merge\nBFLY,a:Axis,x,broken\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_split_choices("BFLY", path)

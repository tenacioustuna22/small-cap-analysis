from datetime import date

import pytest

from src.ixbrl import DimFact, IxbrlError, cover_shares, parse_facts, parse_number

DOC = """<?xml version='1.0' encoding='ASCII'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
<body><div style="display:none"><ix:header><ix:resources>
  <xbrli:context id="q"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context>
  <xbrli:context id="q-emb"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>
    <xbrli:segment><xbrldi:explicitMember dimension="us-gaap:ReportingUnitAxis">bfly:EmbeddedMember</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context>
  <xbrli:context id="bs"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2026-09-30</xbrli:instant></xbrli:period></xbrli:context>
</ix:resources></ix:header></div>
<table><tr>
  <td><ix:nonFraction name="us-gaap:Revenues" contextRef="q" unitRef="usd" scale="3" decimals="-3" format="ixt:num-dot-decimal">32,598</ix:nonFraction></td>
  <td><ix:nonFraction name="us-gaap:Revenues" contextRef="q-emb" unitRef="usd" scale="3" decimals="-3">11,088</ix:nonFraction></td>
  <td>(<ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="q" unitRef="usd" scale="3" sign="-">12,807</ix:nonFraction>)</td>
  <td><ix:nonFraction name="us-gaap:LongTermDebt" contextRef="bs" unitRef="usd" format="ixt:fixed-zero">&#8212;</ix:nonFraction></td>
  <td><ix:nonFraction name="us-gaap:Missing" contextRef="nowhere" unitRef="usd">5</ix:nonFraction></td>
</tr></table></body></html>"""


def test_facts_carry_period_dimensions_scale_and_sign():
    facts = parse_facts(DOC)
    assert len(facts) == 4  # the fact with an unknown context is dropped
    total, embedded, loss, debt = facts
    assert total == DimFact("us-gaap:Revenues", date(2026, 7, 1), date(2026, 9, 30), (), 32_598_000, "usd")
    assert embedded.dims == (("us-gaap:ReportingUnitAxis", "bfly:EmbeddedMember"),)
    assert embedded.value == 11_088_000
    assert loss.value == -12_807_000
    assert debt.start is None and debt.end == date(2026, 9, 30) and debt.value == 0


def test_number_formats():
    assert parse_number("1,234.5") == 1234.5
    assert parse_number("1.234,5", "ixt:num-comma-decimal") == 1234.5
    assert parse_number("7", scale="6") == 7_000_000
    assert parse_number("—") == 0
    assert parse_number("n/a") is None


def cover(value: float, day: str, member: str | None) -> DimFact:
    dims = (("us-gaap:StatementClassOfStockAxis", member),) if member else ()
    return DimFact("dei:EntityCommonStockSharesOutstanding", None, date.fromisoformat(day), dims, value, "shares")


def test_cover_shares_sum_every_class_on_the_latest_date():
    facts = [cover(246_034_996, "2026-10-19", "us-gaap:CommonClassAMember"),
             cover(21_426_937, "2026-10-19", "us-gaap:CommonClassBMember"),
             cover(200_000_000, "2026-07-20", "us-gaap:CommonClassAMember")]
    total, day, classes = cover_shares(facts)
    assert total == 267_461_933 and day == date(2026, 10, 19)
    assert classes == [("us-gaap:CommonClassAMember", 246_034_996), ("us-gaap:CommonClassBMember", 21_426_937)]
    assert cover_shares([cover(5e6, "2026-10-19", None)])[0] == 5e6
    # A total tagged next to the classes is not counted twice.
    assert cover_shares(facts[:2] + [cover(267_461_933, "2026-10-19", None)])[0] == 267_461_933
    assert cover_shares([]) is None


def test_documents_without_inline_xbrl_are_rejected():
    with pytest.raises(IxbrlError):
        parse_facts("<html><body>plain</body></html>")
    with pytest.raises(IxbrlError):
        parse_facts("<html><body><p>unclosed</body></html>")

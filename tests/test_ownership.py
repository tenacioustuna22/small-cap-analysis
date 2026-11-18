from datetime import date

from src.edgar import Filing, raw_xml_url
from src.ownership import (
    BUY,
    PLAN_SALE,
    SALE,
    TAX_SALE,
    HolderFiling,
    by_owner,
    latest_by_holder,
    parse_form4,
    parse_schedule13,
    summarize_insiders,
)

FILING = Filing("4", date(2026, 8, 25), "4", "https://www.sec.gov/Archives/edgar/data/1/2/xslF345X06/ownership.xml")


def form4(code: str, shares: float, price: float, footnote: str = "", plan: bool = False, officer: str = "Chief Operating Officer") -> str:
    ref = '<footnoteId id="F1"/>' if footnote else ""
    return f"""<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>TEISSEYRE THOMAS</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>true</isOfficer>
      <officerTitle>{officer}</officerTitle></reportingOwnerRelationship>
  </reportingOwner>
  <aff10b5One>{"true" if plan else "false"}</aff10b5One>
  <nonDerivativeTable><nonDerivativeTransaction>
    <transactionDate><value>2026-08-24</value></transactionDate>
    <transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
    <transactionAmounts>
      <transactionShares><value>{shares}</value>{ref}</transactionShares>
      <transactionPricePerShare><value>{price}</value></transactionPricePerShare>
      <transactionAcquiredDisposedCode><value>{"A" if code == "P" else "D"}</value></transactionAcquiredDisposedCode>
    </transactionAmounts>
    <postTransactionAmounts><sharesOwnedFollowingTransaction><value>671256</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
  </nonDerivativeTransaction></nonDerivativeTable>
  <footnotes><footnote id="F1">{footnote}</footnote></footnotes>
</ownershipDocument>"""


def test_raw_xml_url_drops_the_rendering_folder():
    assert raw_xml_url(FILING.url) == "https://www.sec.gov/Archives/edgar/data/1/2/ownership.xml"
    assert raw_xml_url("https://x/a/b/doc.htm") == "https://x/a/b/doc.htm"


def test_sales_are_split_by_why_they_happened():
    tax = parse_form4(form4("S", 7345, 0.854, "effected to cover tax withholding obligations ... a sell to cover provision"), FILING)[0]
    assert tax.kind == TAX_SALE
    assert tax.owner == "Teisseyre Thomas" and tax.role == "Chief Operating Officer, Director"
    assert tax.value == 7345 * 0.854 and tax.owned_after == 671256 and not tax.acquired

    assert parse_form4(form4("S", 100, 1.0, plan=True), FILING)[0].kind == PLAN_SALE
    assert parse_form4(form4("S", 100, 1.0, "made under a Rule 10b5-1 trading plan"), FILING)[0].kind == PLAN_SALE
    assert parse_form4(form4("S", 100, 1.0), FILING)[0].kind == SALE
    buy = parse_form4(form4("P", 1000, 2.0), FILING)[0]
    assert buy.kind == BUY and buy.acquired


def test_summary_counts_discretionary_trades_only():
    trades = (
        parse_form4(form4("P", 1000, 2.0), FILING)
        + parse_form4(form4("S", 500, 3.0), FILING)
        + parse_form4(form4("S", 300, 3.0, "sell to cover"), FILING)
    )
    s = summarize_insiders(trades, since=date(2026, 1, 1))
    assert s.bought_value == 2000 and s.sold_value == 1500
    assert s.tax_shares == 300
    assert s.net_value == 500
    assert s.buyers == ["Teisseyre Thomas"]
    assert summarize_insiders(trades, since=date(2026, 9, 1)).trades == []

    totals = by_owner(trades)
    assert len(totals) == 1
    assert (totals[0].bought, totals[0].sold, totals[0].planned) == (2000, 1500, 0)  # tax sale left out


SCHEDULE_13G = """<?xml version="1.0" encoding="UTF-8"?><edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
<formData><coverPageHeader><eventDateRequiresFilingThisStatement>06/30/2026</eventDateRequiresFilingThisStatement></coverPageHeader>
<coverPageHeaderReportingPersonDetails><reportingPersonName>BlackRock, Inc.</reportingPersonName>
<reportingPersonBeneficiallyOwnedAggregateNumberOfShares>4671587</reportingPersonBeneficiallyOwnedAggregateNumberOfShares>
<classPercent>5.5</classPercent></coverPageHeaderReportingPersonDetails></formData></edgarSubmission>"""


def test_schedule_13g_fields_and_latest_per_holder():
    filing = Filing("SCHEDULE 13G", date(2026, 7, 28), "", "u")
    h = parse_schedule13(SCHEDULE_13G, filing)
    assert (h.holder, h.shares, h.percent, h.event) == ("BlackRock, Inc.", 4671587, 5.5, date(2026, 6, 30))
    assert not h.activist
    assert parse_schedule13("<html>not xml", filing).holder == ""

    older = HolderFiling(Filing("SCHEDULE 13G", date(2026, 1, 30), "", "v"), "BLACKROCK, INC.", 1, 5.1, None)
    html = HolderFiling(Filing("SC 13D", date(2025, 3, 1), "", "w"), "", None, None, None)
    latest = latest_by_holder([older, h, html])
    assert latest == [h, html] and html.activist

from datetime import date, timedelta
from pathlib import Path

import pytest

from src import news_watch as nw
from src.news_watch import Entry, Item

ROOT = Path(__file__).resolve().parents[1]

GOOGLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
<item><title>Sonic Incytes partners with Madrigal - Investing.com</title>
<link>https://news.google.com/rss/articles/abc?oc=5</link>
<pubDate>Thu, 19 Nov 2026 20:27:16 GMT</pubDate>
<source url="https://www.investing.com">Investing.com</source></item>
<item><title>Old story - Example</title><link>https://news.google.com/rss/articles/old</link>
<pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate><source url="https://example.com">Example</source></item>
</channel></rss>"""

COURT_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>CourtListener.com Custom Search Feed</title>
<entry><title>Disney Enterprises Inc. v. Midjourney Inc.</title>
<link href="https://www.courtlistener.com/docket/70513159/266/disney-enterprises-inc-v-midjourney-inc/"/>
<published>2026-11-19T00:00:00-08:00</published></entry>
<entry><title>Disney Enterprises Inc. v. Midjourney Inc.</title>
<link href="https://www.courtlistener.com/docket/70513159/disney-enterprises-inc-v-midjourney-inc/#minute-entry-485913322"/>
<updated>2026-11-17T00:00:00-08:00</updated></entry>
</feed>"""


def config(**overrides) -> nw.Config:
    values = dict(
        ticker="BFLY",
        baseline_date=date(2026, 11, 18),
        promote_pattern=nw.re.compile("Butterfly Network", nw.re.IGNORECASE),
        promote_item="W1",
        blocked_domains=["simplywall.st"],
        blocked_titles=[nw.re.compile(r"price target", nw.re.IGNORECASE)],
        sources=[],
    )
    values.update(overrides)
    return nw.Config(**values)


def source(**overrides) -> dict:
    values = {"name": "News: test", "item": "W2", "kind": "google_news", "notify": "now", "match_titles": True}
    values.update(overrides)
    return values


def entry(title: str, url: str = "https://example.com/a", day: date | None = date(2026, 11, 19), publisher="example.com"):
    return Entry(title, url, day, publisher)


# ---------------------------------------------------------------- parsing


def test_google_news_rss_strips_publisher_and_reads_domain_and_date():
    entries = nw.parse_feed(GOOGLE_RSS)
    assert entries[0] == Entry(
        "Sonic Incytes partners with Madrigal",
        "https://news.google.com/rss/articles/abc?oc=5",
        date(2026, 11, 19),
        "investing.com",
    )
    assert len(entries) == 2


def test_atom_feed_uses_published_or_updated():
    entries = nw.parse_feed(COURT_ATOM)
    assert [e.published for e in entries] == [date(2026, 11, 19), date(2026, 11, 17)]
    assert entries[1].url.endswith("#minute-entry-485913322")
    assert entries[0].publisher == "courtlistener.com"


def test_html_page_is_not_a_feed():
    with pytest.raises(ValueError):
        nw.parse_feed("<html><body>Just a moment...</body></html>")


# ---------------------------------------------------------------- config


def test_the_bfly_feeds_file_loads():
    cfg = nw.load_config(ROOT / "research" / "BFLY" / "watch" / "BFLY_feeds.toml")
    assert cfg.ticker == "BFLY"
    assert cfg.baseline_date == date(2026, 11, 18)
    assert {s["item"] for s in cfg.sources} == {"W1", "W2", "W3", "W4", "W5", "W6", "W7"}
    assert next(s for s in cfg.sources if s["kind"] == "correlation")["match_titles"] is False
    assert {s["name"] for s in cfg.sources if s["fast"]} == {"Butterfly press releases", "BFLY 8-K"}


def test_bfly_blocklist_drops_noise_and_keeps_news():
    cfg = nw.load_config(ROOT / "research" / "BFLY" / "watch" / "BFLY_feeds.toml")
    blocked = [
        "Butterfly Network falls 6.58% in Thursday's session",
        "Butterfly Network, Inc. (BFLY) stock price, news, quote and history",
        "Form 4 Butterfly Network, Inc: Jonathan M. Rothberg (Director) For: 13 November",
        "Butterfly Network director Jonathan Rothberg sells $2.2M in shares",
        "Butterfly Network price target raised to $7",
    ]
    kept = [
        "Butterfly Network shares jump as Midjourney unveils imaging platform built on ultrasound-on-chip",
        "Butterfly Network CEO Sees Chip Revenue Dwarfing Ultrasound Device Business",
    ]
    for title in blocked:
        assert any(p.search(title) for p in cfg.blocked_titles), title
    for title in kept:
        assert not any(p.search(title) for p in cfg.blocked_titles), title


def write_config(tmp_path, text: str) -> Path:
    path = tmp_path / "X_feeds.toml"
    path.write_text('ticker = "X"\nbaseline_date = 2026-11-18\n' + text, encoding="utf-8")
    return path


def test_config_rejects_unknown_keys_and_bad_items(tmp_path):
    with pytest.raises(nw.ConfigError, match="unknown keys"):
        nw.load_config(write_config(tmp_path, '[[source]]\nname="a"\nitem="W1"\nkind="rss"\nurl="u"\nqeury="x"\n'))
    with pytest.raises(nw.ConfigError, match="needs item"):
        nw.load_config(write_config(tmp_path, '[[source]]\nname="a"\nitem="1"\nkind="rss"\nurl="u"\n'))
    with pytest.raises(nw.ConfigError, match="missing"):
        nw.load_config(write_config(tmp_path, '[[source]]\nname="a"\nitem="W1"\nkind="google_news"\n'))
    with pytest.raises(nw.ConfigError, match="used twice"):
        nw.load_config(write_config(
            tmp_path, '[[source]]\nname="a"\nitem="W1"\nkind="rss"\nurl="u"\n' * 2
        ))


def test_fast_flag_defaults_off_and_must_be_a_boolean_on_a_now_source(tmp_path):
    rss = '[[source]]\nname="a"\nitem="W1"\nkind="rss"\nurl="u"\n'
    assert nw.load_config(write_config(tmp_path, rss)).sources[0]["fast"] is False
    assert nw.load_config(write_config(tmp_path, rss + "fast = true\n")).sources[0]["fast"] is True
    with pytest.raises(nw.ConfigError, match="true or false"):
        nw.load_config(write_config(tmp_path, rss + 'fast = "yes"\n'))
    with pytest.raises(nw.ConfigError, match="is fast"):
        nw.load_config(write_config(tmp_path, rss + 'fast = true\nnotify = "weekend"\n'))


# ---------------------------------------------------------------- filtering


def test_to_items_filters_by_date_domain_title_and_title_must():
    entries = [
        entry("Sonic Incytes raises Series B"),
        entry("Sonic Incytes old news", day=date(2026, 11, 17)),
        entry("Sonic Incytes on a spam site", publisher="news.simplywall.st"),
        entry("Sonic Incytes price target", url="https://example.com/b"),
        entry("Unrelated company raises money", url="https://example.com/c"),
        entry("Sonic Incytes undated", url="https://example.com/d", day=None),
    ]
    items = nw.to_items(entries, source(title_must="Sonic Incytes"), config())
    assert [i.title for i in items] == ["Sonic Incytes raises Series B", "Sonic Incytes undated"]
    assert items[0].item == "W2" and items[0].notify == "now"


def test_titles_naming_butterfly_are_promoted_to_w1():
    items = nw.to_items([entry("Merge Labs expands Butterfly Network deal")], source(), config())
    assert items[0].item == "W1"


def item(title: str, url: str = "", source_name: str = "News: test") -> Item:
    return Item("W2", "now", source_name, title, "example.com", url, date(2026, 11, 19))


def test_new_items_skip_seen_urls_and_syndicated_titles():
    seen = [{"url": "https://example.com/story", "title": "Sonic Incytes partners with Madrigal on liver"}]
    found = [
        item("Different title", "https://www.example.com/story/?utm_source=x"),
        item("Sonic Incytes partners with Madrigal on liver!", "https://other.com/copy"),
        item("A genuinely new story about partners", "https://other.com/new"),
        item("A genuinely new story about partners", "https://third.com/new"),  # repeat in this run
    ]
    assert [i.url for i in nw.new_items(found, seen, [source(name="News: test")])] == ["https://other.com/new"]


def test_docket_entries_with_the_same_title_are_kept_apart_by_fragment():
    court = source(name="Court", kind="rss", match_titles=False)
    found = [
        item("Disney Enterprises Inc. v. Midjourney Inc.", "https://cl.org/docket/1/#minute-entry-1", "Court"),
        item("Disney Enterprises Inc. v. Midjourney Inc.", "https://cl.org/docket/1/#minute-entry-2", "Court"),
    ]
    seen = [{"url": "https://cl.org/docket/1/#minute-entry-1", "title": "Disney Enterprises Inc. v. Midjourney Inc."}]
    assert [i.url for i in nw.new_items(found, seen, [court])] == ["https://cl.org/docket/1/#minute-entry-2"]


def test_items_without_url_are_matched_on_the_whole_title():
    w7 = source(name="Corr", kind="correlation", match_titles=False)
    found = [item("BFLY vs ARKK 0.25", source_name="Corr")]
    assert nw.new_items(found, [], [w7]) == found
    assert nw.new_items(found, [{"url": "", "title": "BFLY vs ARKK 0.25"}], [w7]) == []


# ---------------------------------------------------------------- seen-log


def test_seen_log_round_trip_and_marking(tmp_path):
    path = tmp_path / "X_seen.csv"
    rows = [
        nw.seen_row(item("Now item", "https://a"), date(2026, 11, 20)),
        nw.seen_row(Item("W3", "weekend", "Court", "Docket entry", "", "https://b", None), date(2026, 11, 20)),
    ]
    nw.save_seen(path, rows)
    loaded = nw.load_seen(path)
    assert loaded[1]["published"] == "" and loaded[0]["status"] == "new"
    assert [r["title"] for r in nw.pending(loaded)] == ["Now item"]
    assert [r["title"] for r in nw.pending(loaded, ("now", "weekend"))] == ["Now item", "Docket entry"]
    assert nw.mark_reported(loaded, ("now",)) == 1
    assert [r["status"] for r in loaded] == ["reported", "new"]


def test_seen_log_rejects_unknown_status(tmp_path):
    path = tmp_path / "X_seen.csv"
    path.write_text(",".join(nw.SEEN_COLUMNS) + "\n2026-11-20,W1,now,s,t,p,u,,done\n", encoding="utf-8")
    with pytest.raises(nw.ConfigError):
        nw.load_seen(path)


# ---------------------------------------------------------------- correlation


def series(values: list[float], start=date(2026, 1, 1)) -> list[tuple[date, float]]:
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


def test_correlation_of_moves_in_step_and_opposite():
    a = series([100, 102, 101, 105, 103, 108])
    same = series([50, 51, 50.5, 52.5, 51.5, 54])  # identical daily returns
    value, first, last = nw.return_correlation(a, same, 5)
    assert value == pytest.approx(1.0)
    assert (first, last) == (date(2026, 1, 2), date(2026, 1, 6))
    opposite = series([100, 98, 99, 95, 97, 92])
    assert nw.return_correlation(a, opposite, 5)[0] < -0.9


def test_correlation_uses_only_shared_days_and_needs_a_full_window():
    a = series([100, 102, 101, 105])
    b = series([50, 51, 50.5, 52.5])[:-1] + [(date(2026, 2, 1), 60)]
    assert nw.return_correlation(a, b, 3) is None  # only two shared returns
    assert nw.return_correlation(a, b, 2)[0] == pytest.approx(1.0)


def test_correlation_flags_crossing_and_large_moves():
    assert nw.correlation_flag(0.25, 0.72, 0.3, 0.2) == "crossed 0.30"
    assert nw.correlation_flag(0.45, 0.72, 0.3, 0.2) == "moved -0.27"
    assert nw.correlation_flag(0.65, 0.72, 0.3, 0.2) is None
    assert nw.correlation_flag(0.65, None, 0.3, 0.2) is None


# ---------------------------------------------------------------- issue


def test_issue_groups_by_item_in_number_order_and_lists_failures():
    rows = [
        nw.seen_row(Item("W10", "now", "s", "Ten", "", "", None), date(2026, 11, 20)),
        nw.seen_row(Item("W2", "now", "s", "Deal [update]", "x.com", "https://x.com/a", date(2026, 11, 19)), date(2026, 11, 20)),
    ]
    body = nw.render_issue("BFLY", rows, {"BFLY 8-K": "HTTP 403"}, "now")
    assert body.index("**W2**") < body.index("**W10**")
    assert "[Deal (update)](https://x.com/a) (2026-11-19, x.com; source: s)" in body
    assert "- Ten (no date; source: s)" in body
    assert "**Could not check**\n- BFLY 8-K: HTTP 403" in body


# ---------------------------------------------------------------- EDGAR full-text search, Form D

EFTS = {"hits": {"hits": [
    {"_id": "0002087109-25-000001:primary_doc.xml", "_source": {
        "ciks": ["0002087109"], "adsh": "0002087109-25-000001", "form": "D", "file_date": "2025-10-07",
        "display_names": ["Gaingels Sonic Incytes 2025 LLC  (CIK 0002087109)"]}},
    {"_id": "0002087109-25-000001:other.xml", "_source": {  # same filing, another document
        "ciks": ["0002087109"], "adsh": "0002087109-25-000001", "form": "D", "file_date": "2025-10-07"}},
    {"_id": "0001675206-16-000001:primary_doc.xml", "_source": {
        "ciks": ["0001675206"], "adsh": "0001675206-16-000001", "form": "D", "file_date": "2016-05-24",
        "display_names": ["Merge Labs, Inc.  (CIK 0001675206)"]}},
]}}

FORM_D = """<?xml version="1.0"?>
<edgarSubmission><submissionType>D</submissionType>
<primaryIssuer><entityName>Gaingels Sonic Incytes 2025 LLC</entityName></primaryIssuer>
<offeringData>
  <typeOfFiling><newOrAmendment><isAmendment>false</isAmendment></newOrAmendment>
    <dateOfFirstSale><value>2025-09-30</value></dateOfFirstSale></typeOfFiling>
  <offeringSalesAmounts><totalOfferingAmount>109844</totalOfferingAmount>
    <totalAmountSold>109844</totalAmountSold><totalRemaining>0</totalRemaining></offeringSalesAmounts>
  <investors><totalNumberAlreadyInvested>15</totalNumberAlreadyInvested></investors>
</offeringData></edgarSubmission>"""


def test_efts_hits_one_per_filing_since_the_date_with_archive_links():
    hits = nw.efts_hits(EFTS, date(2025, 1, 1))
    assert len(hits) == 1
    hit = hits[0]
    assert (hit.form, hit.filed, hit.filer) == ("D", date(2025, 10, 7), "Gaingels Sonic Incytes 2025 LLC")
    assert hit.index_url == "https://www.sec.gov/Archives/edgar/data/2087109/000208710925000001/"
    assert hit.document_url.endswith("/000208710925000001/primary_doc.xml")


def test_form_d_summary_reads_amounts_first_sale_and_investors():
    assert nw.form_d_summary(FORM_D) == "$109,844 sold of $109,844 offered, first sale 2025-09-30, 15 investors"
    later = FORM_D.replace("<value>2025-09-30</value>", "<yetToOccur>true</yetToOccur>").replace(
        "<totalOfferingAmount>109844", "<totalOfferingAmount>Indefinite").replace(
        "<isAmendment>false", "<isAmendment>true")
    assert nw.form_d_summary(later) == "$109,844 sold of Indefinite offered, first sale yet to occur, 15 investors (amendment)"
    with pytest.raises(ValueError):
        nw.form_d_summary("<edgarSubmission/>")


# ---------------------------------------------------------------- CourtListener docket entries

DOCKET_PAGE = [
    {"id": 1, "entry_number": 274, "date_filed": "2026-11-21",
     "description": "NOTICE OF MOTION AND MOTION to Compel Midjourney's Compliance", "recap_documents": []},
    {"id": 2, "entry_number": None, "date_filed": "2026-11-20", "description": "",
     "recap_documents": [{"description": "Text Only Scheduling Notice"}]},
    {"id": 3, "entry_number": 35, "date_filed": "2026-11-20", "description": "", "recap_documents": [{}]},
]


def test_docket_entries_carry_the_description_and_a_unique_link():
    entries = nw.docket_entries(DOCKET_PAGE, 70513159, "Disney v. Midjourney")
    assert [e.title for e in entries] == [
        "Disney v. Midjourney #274: NOTICE OF MOTION AND MOTION to Compel Midjourney's Compliance",
        "Disney v. Midjourney unnumbered: Text Only Scheduling Notice",
        "Disney v. Midjourney #35: no description on CourtListener",
    ]
    assert entries[0].url == "https://www.courtlistener.com/docket/70513159/#entry-274"
    assert entries[1].url == "https://www.courtlistener.com/docket/70513159/#minute-entry-2"
    assert entries[0].published == date(2026, 11, 21)


def test_bfly_rulings_filter_sends_rulings_now_and_leaves_routine_orders_for_saturday():
    config = nw.load_config(ROOT / "research" / "BFLY" / "watch" / "BFLY_feeds.toml")
    rulings = next(s for s in config.sources if s["name"] == "Court dockets: rulings")
    case = "Disney v. Midjourney (C.D. Cal. 2:25-cv-05275)"
    sent = [
        "#280: ORDER GRANTING IN PART Defendant's Motion for Judgment on the Pleadings 139",
        "#281: (IN CHAMBERS) ORDER RE MOTION FOR JUDGMENT ON THE PLEADINGS",
        "#282: MINUTES OF Motion Hearing held before Judge John A. Kronstadt",
        "#283: NOTICE OF SETTLEMENT filed by Plaintiffs",
        "#284: STIPULATION of Dismissal filed by Plaintiffs",
    ]
    held = [
        "#266: ORDER GRANTING DEFENDANT MIDJOURNEY,INC.'S APPLICATION FOR LEAVE TO FILE UNDER SEAL",
        "#267: (IN CHAMBERS) ORDER CHANGING THE TIME FOR THE MOTION HEARING 139",
        "#24: ORDER by Judge John A. Kronstadt: granting 23 APPLICATION to Appear Pro Hac Vice",
        "#274: NOTICE OF MOTION AND MOTION to Compel Midjourney's Compliance With the Court's Orders",
        "#34: Order AND ~Util - Set/Reset Deadlines/Hearings",
        "#275: PROOF OF SERVICE filed by Plaintiffs re Order",
    ]
    entries = [Entry(f"{case} {t}", f"https://x/#{i}", date(2026, 11, 23)) for i, t in enumerate(sent + held)]
    titles = [i.title for i in nw.to_items(entries, rulings, config)]
    assert titles == [f"{case} {t}" for t in sent]
    assert rulings["notify"] == "now"
    names = [s["name"] for s in config.sources]
    assert names.index("Court dockets: rulings") < names.index("Court dockets: all filings")


def test_courtlistener_dockets_need_an_id_and_a_name(tmp_path):
    path = tmp_path / "X_feeds.toml"
    path.write_text('ticker = "X"\nbaseline_date = 2026-11-18\n[[source]]\nname = "d"\nitem = "W3"\n'
                    'kind = "courtlistener"\ndockets = [{ id = "70513159", name = "Disney" }]\n')
    with pytest.raises(nw.ConfigError, match="dockets"):
        nw.load_config(path)


def test_bfly_blocks_simply_wall_st_pieces_but_not_real_news():
    config = nw.load_config(ROOT / "research" / "BFLY" / "watch" / "BFLY_feeds.toml")
    source = next(s for s in config.sources if s["name"] == "News: Butterfly Network")
    junk = [
        "What Butterfly Network Buyers Were Betting On Before A 104% Rally",
        "Investors Who Bought Butterfly Network Five Years Ago Are Up 150%",
        "Here's Why We're Not Too Worried About Butterfly Network's Cash Burn Situation",
        "Is Butterfly Network (NYSE:BFLY) Using Too Much Debt?",
        "Revenues Tell The Story For Butterfly Network, Inc. (NYSE:BFLY) As Its Stock Soars 26%",
        "Butterfly Network, Inc.'s (NYSE:BFLY) P/S Is Still On The Mark Following 26% Share Price Bounce",
        "Retail investors who own 45% along with institutions invested in Butterfly Network",
        "Butterfly Network Valuation Check After Recent Share Price Momentum",
    ]
    real = [
        "Butterfly Network to Present at 9th Annual Evercore Healthcare Conference on December 1, 2026",
        "Butterfly Network and Midjourney expand Ultrasound-on-Chip agreement",
        "Are AI startups overvalued? Venture investors weigh the narrative",  # no Butterfly: kept
    ]
    entries = [Entry(t, f"https://finance.yahoo.com/{i}", date(2026, 11, 22), "finance.yahoo.com")
               for i, t in enumerate(junk + real)]
    assert [i.title for i in nw.to_items(entries, source, config)] == real

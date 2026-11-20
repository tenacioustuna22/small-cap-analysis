# BFLY watchlist: what could move the price

**For the checker.** Check the items below for information newer than each baseline, and report
in the format at the bottom. Baselines are as of **2026-11-18** unless the item says otherwise.

**How the checking is automated:**

- **The free check:** twice a day, `scripts/watch_check.py` reads the news feeds and EDGAR queries
  in `research/BFLY_feeds.toml`. It logs anything new in `research/BFLY_seen.csv` and uses no
  Claude.
- **Claude's report:** when the free check finds something, Claude follows
  `research/watch_agent_prompt.md`, judges the items against this file, and writes a report in
  `research/watch_reports/`. The report is posted to a GitHub issue labelled `watch`.
- **Saturdays:** Claude also covers the court docket, the checks with no free feed, and W7.
- **The workflow** is `.github/workflows/watch-check.yml`.

- **This file:**
  <https://raw.githubusercontent.com/tenacioustuna22/small-cap-analysis/main/research/BFLY_watch.md>
- **Background, if needed:** the summary
  <https://raw.githubusercontent.com/tenacioustuna22/small-cap-analysis/main/research/BFLY.md>.
  The full notes are `research/BFLY_detail.md` in the same repo.

## Rules

1. **Every figure needs a source link and a date.** Never state a number from memory. If a source
   is secondary (news, aggregator), label it **(unverified)**.
2. **Only report what is newer than the baseline.** If a finding repeats the baseline, leave it
   out. If it conflicts with the baseline, report the conflict and both sources. Rows in
   `research/BFLY_seen.csv` marked `reported`, `baselined` or `dismissed` have already been
   reported; don't report them again.
3. **If you could not check an item,** say so and why (page wouldn't load, no access). Don't skip
   it silently.
4. **No buy or sell advice.** Say which part of the thesis a finding supports or weakens, and why.
5. **Some things are already covered by code in the repo,** so don't spend time on them:
   - stock prices and short interest
   - Yahoo analyst consensus
   - BFLY's SEC 8-K items, Form 4 insider trades and 13D/G holder filings
   - earnings dates.

   Exception: the free check flags BFLY 8-K items 1.01, 7.01 and 8.01, because a new Embedded
   deal can appear there first. When one is flagged, read it for W1.

## The thesis in three lines

1. Butterfly's Core business (handheld ultrasound, about $85M a year, about 6% growth) is worth
   roughly $1.22 a share. About four-fifths of the price is a bet on **Embedded**, the program that
   licenses its ultrasound chip to other companies.
2. The companies signing Embedded deals are AI and brain-interface firms. The chip turns
   ultrasound into raw data for software, so **new, large deals depend on AI and neurotech money**.
3. Value depends on how many large deals are signed, whether partners' products ship (so the
   revenue share and royalties start), and AI sentiment, which also sets what BFLY pays for new
   cash through its $150M stock sale program (ATM).

## Items, most important first

### W1. New Embedded deals and partner news from Butterfly

- **Tests:** deal flow, the core of the thesis.
- **How often:** weekly.
- **Where:**
  - [Butterfly press releases](https://ir.butterflynetwork.com/News/press-releases/default.aspx).
    The list loads dynamically; if it fails, search Business Wire for "Butterfly Network".
  - [BFLY filings on EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001804176&type=8-K&dateb=&owner=include&count=40),
    for exhibits attached to a deal announcement.
  - Partner announcements (see W2).
- **Baseline:**
  - **Named partners:** Midjourney (Nov 2025), Forest Neurotech (Oct 2023), Mendaera (Dec 2023),
    Sonic Incytes, Aleph Neuro, Merge Labs (release 2026-09-01), Bridge Neurotech (2026-10-06),
    and one brain-interface partner still in stealth.
  - **Partner count:** the Q2 2026 release said 11 partners. The Q3 2026 release (2026-10-29) said
    three brain-interface partners were added, but gave no new total.
  - **Disclosed deal sizes:**
    - Midjourney: $65M fixed over 5 years, plus up to $9M of milestones.
    - Forest: $20M over 5 years.
    - No others.
  - **Partner products:** Mendaera is the only partner with a product on sale (launched
    2026-10-01).
- **Significant:**
  - a new partner, with its field and how it is funded
  - any disclosed deal size or revenue-share rate
  - a partner product launch
  - the stealth partner being named
  - a partner leaving
  - news on the Apollo chip (the next-generation chip).

### W2. Funding for the brain-interface partners

- **Tests:** whether partners can pay milestones and sign larger deals. This is the most direct
  link between AI and neurotech money and BFLY.
- **How often:** weekly for news; monthly for SEC filings.
- **Where:**
  - news searches for each company name plus "funding", "raises" or "Series"
  - SEC Form D filings, which companies file when raising private money. Search EDGAR company
    names, for example
    [Merge Labs](https://www.sec.gov/cgi-bin/browse-edgar?company=merge+labs&type=D&owner=include&action=getcompany).
    Form D can be late, missing or leave the amount blank.
- **Baseline:**

  | Partner | Latest known funding | Source |
  |---|---|---|
  | Merge Labs | $252M seed, 2026-01-15, led by OpenAI with Bain Capital and others, at a reported ~$850M valuation | [SiliconANGLE](https://siliconangle.com/?p=727965), [Tom's Hardware](https://www.tomshardware.com/peripherals/wearable-tech/sam-altman-raises-usd252-million-for-brain-computer-interface-venture-but-merge-labs-is-still-in-an-early-research-phase) (unverified) |
  | Bridge Neurotech | $13.5M, General Catalyst | [TheNextWeb](https://thenextweb.com/news/bridge-neurotech-13-5m-ultrasound-brain-computer-interface) (unverified) |
  | Forest Neurotech | Research organization under Convergent Research; UK safety trial funded by ARIA from March 2025, running about 3.5 years | [Convergent Research](https://www.convergentresearch.org/ecosystem/forest), [Digital Health](https://www.digitalhealth.net/2025/01/brain-implant-will-be-trialled-by-nhs-to-help-treat-neural-conditions) |
  | Aleph Neuro, Mendaera, Sonic Incytes | not recorded | first run: record the latest round |

- **Significant:**
  - any new round, and its size against the last one
  - a down round or layoffs
  - a partner shutting down or pivoting away from ultrasound
  - a new strategic investor.

### W3. Midjourney: scanner, finances and the copyright lawsuit

- **Tests:** BFLY's biggest partner. Its fixed fees ($10M a year to 2030) stop only on breach or
  insolvency, and the upside depends on the scanner shipping.
- **How often:** weekly.
- **Where:**
  - [Midjourney Medical blog](https://www.midjourney.com/medical/blogpost), which promises regular
    updates
  - news searches for "Midjourney Medical", "Midjourney scanner" and "Midjourney revenue"
  - for the lawsuit, [CourtListener](https://www.courtlistener.com/) (search "Disney v.
    Midjourney") and news.
- **Baseline:**
  - **The scanner:**
    - Announced 2026-06-18.
    - The prototype is a ring of 40 Butterfly chip modules; later versions are to use
      "substantially more".
    - It will be marketed first as a wellness product (body composition), with FDA approval sought
      later.
    - The first spa, in San Francisco, is planned for the end of 2027. The owner expects nearer
      2029.
  - **Finances:**
    - self-funded from subscriptions, with no outside investors
    - revenue "well above $200 million" in 2023, per its CEO; later estimates of $500-600M are
      third-party guesses
    - from [WinBuzzer, 2026-03-31](https://winbuzzer.com/2026/03/31/midjourney-revenue-above-200-million-hardware-push-xcxwbn/)
      (unverified).
  - **The lawsuit:**
    - Disney and Universal sued in June 2025 in federal court in Los Angeles (C.D. Cal.), alleging
      copyright infringement.
    - Warner Bros. Discovery's suit was consolidated with it.
    - The studios seek an injunction, damages and a jury trial.
    - As of mid-2026, it was in discovery disputes.
    - No settlement or trial date found as of 2026-11-18
      ([Art Newspaper, 2026-07-09](https://www.theartnewspaper.com/2026/07/09/midjourney-demands-hollywood-AI-secrets),
      [Graphic Policy](https://graphicpolicy.com/2025/11/14/court-suggests-disney-v-midjourney-go-to-mediation/);
      unverified).
- **Significant:**
  - **The scanner:** a change to the spa date, a scanner or module count, an FDA submission, or
    research trial results.
  - **The lawsuit:** any ruling, injunction, settlement or damages figure.
  - **Finances:** outside fundraising (it would mean Midjourney is no longer self-funded), layoffs,
    or a drop in subscriptions.

### W4. Venture funding for AI applications and neurotech (the sector)

- **Tests:** the pool future partners draw from.
- **How often:** quarterly, when the reports come out, plus any major headline.
- **Where:**
  - PitchBook-NVCA Venture Monitor, free summary, quarterly, about a month after quarter end
    (search "PitchBook NVCA Venture Monitor")
  - [Crunchbase News](https://news.crunchbase.com/), for its AI and health funding roundups
  - neurotech or brain-computer-interface funding roundups in trade press.
- **Baseline:** not recorded. **First run:** record the latest quarter's AI venture funding and any
  neurotech or brain-interface total, with sources.
- **Significant:**
  - AI or neurotech funding falling noticeably from the previous quarter
  - large AI raises failing or being cut
  - AI IPOs pulled
  - the reverse of any of these.

### W5. Brain-interface peers and competing ultrasound chips

- **Tests:** whether brain-interface money keeps flowing, and whether BFLY's chip keeps its edge.
- **How often:** monthly.
- **Where:** news searches for the companies listed below.
- **Baseline:**
  - **Brain-interface peers:** Neuralink, Synchron and Precision Neuroscience. Funding is not
    recorded; **first run:** record each one's latest round.
  - **Ultrasound brain-interface companies:** Nudge (focused-ultrasound stimulation), and Gestala
    and Sisun Tech in China. These are unlikely to buy from a US supplier
    ([InsideBCI](https://insidebci.com/news/2026-09-01-merge-labs-butterfly-network-poseidon-ultrasound-chip-bci-licensing-deal/)).
  - **Exo Imaging:** a piezoelectric ultrasound chip with 4,096 elements, over $300M raised, and a
    Samsung Medison investment in May 2025 ([Pulse 2.0](https://pulse2.com/exo-imaging-35-million/);
    unverified).
- **Significant:**
  - a brain-interface or imaging company choosing Exo or another chip over Butterfly's
  - Exo licensing its chip to third parties
  - a large round or shutdown at a peer
  - results showing ultrasound brain interfaces working through an intact skull, which would be
    good for the thesis.

### W6. The AI spending cycle (early warning)

- **Tests:** the mood that funds W2 and W4. It is not a direct driver; it can boom while neurotech
  funding dries up.
- **How often:** in earnings weeks, and monthly otherwise.
- **Where:** each company's quarterly earnings release and call coverage: Microsoft, Alphabet,
  Amazon, Meta, Oracle, and Nvidia for data-center revenue.
- **Baseline:** not recorded. **First run:** record each company's latest capex guidance (for its
  current and next fiscal year) and Nvidia's latest data-center revenue and guidance, with sources.
- **Significant:**
  - a capex guidance cut, or wording such as "moderating" or "digesting"
  - a widening gap between capex and cloud revenue growth
  - Nvidia guiding data-center revenue down.

  Q4 results arrive in late January and early February 2027, close to BFLY's 2027 guidance.

### W7. Is BFLY trading on AI sentiment or its own news? (optional)

- **Tests:** which of the items above to weight.
- **How often:** monthly.
- **Measure:** the 60-day correlation of daily returns, BFLY against ARKK, from any free price
  source.
- **Baseline:**
  - +0.72 from 2026-09-22 to 2026-11-16
  - +0.38 from April 2026 to 2026-09-22 (computed in the repo from yfinance).
- **If you can't compute it,** say so and skip it.
- **Significant:**
  - **Falling toward 0.2-0.3:** BFLY is trading on its own news.
  - **Staying high:** weight W4 and W6 more.

## Calendar

| When | What | Why it matters |
|---|---|---|
| Late Jan to early Feb 2027 | Big tech Q4 results and capex guidance | W6 early warning |
| About late Feb 2027 | BFLY Q4 2026 results, 2027 guidance, and the 2026 10-K (the 2025 10-K was filed 2026-02-27) | Guidance against the $150.2M consensus; Midjourney's remaining contracted revenue; ATM shares sold |
| End of 2027 (stated) | Midjourney's first spa, San Francisco | W3 |
| About Sep 2028 | Forest's UK trial ends | W2, W5 |
| About Oct 2028 | Forest's 5-year Butterfly agreement ends | W1 |
| 2030 | Midjourney's fixed license fees end | W1, W3 |

## Report format

```
BFLY: <n> significant, <n> new, <n> nothing new, <n> skipped   (one line, for the notification)

BFLY watch report, <date checked>
Baselines read from BFLY_watch.md as of <baseline date in the file>

New findings
- [W#] SIGNIFICANT (only if it meets the item's "Significant" list) <what happened>,
  <date of the event>. Source: <link> (unverified if secondary)
  Thesis: supports / weakens / neutral, because <one line>
  Suggested new baseline: <value, date>

Nothing new
- W#, W#: checked, nothing newer than the baseline

Skipped (not relevant to the thesis, judged from the title)
- <title>, <publisher>

Not read (page limit reached)
- [W#] <title>: <link>

Could not check
- W#: <reason>

Coming up in the next 30 days (from the calendar or news; weekend runs)
- <date>: <event>
```

Leave out a section that would be empty, except "Nothing new" and "Could not check". Write
"none" there.

When the owner brings a report back to the stock-analysis project:

- the findings are checked and added to the research notes
- the baselines in this file are updated
- the matching rows in `BFLY_seen.csv` are set to `baselined` or `dismissed`
- the `watch` issue is closed.

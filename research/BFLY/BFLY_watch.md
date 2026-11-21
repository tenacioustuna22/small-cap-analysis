# BFLY watchlist: what could move the price

**For the checker.** Check the items below for information newer than each baseline, and report
in the format at the bottom. Baselines are as of **2026-11-18** unless the item says otherwise.

**How the checking is automated:**

- **The free check:** twice a day, `scripts/watch_check.py` reads the news feeds and EDGAR queries
  in `research/BFLY/watch/BFLY_feeds.toml`. It logs anything new in
  `research/BFLY/watch/BFLY_seen.csv` and uses no Claude.
- **Claude's report:** when the free check finds something, Claude follows
  `research/watch_agent_prompt.md`, judges the items against this file, and writes a report in
  `research/BFLY/watch/reports/`. The report is posted to a GitHub issue labelled `watch`.
- **Fast lane:** on weekdays, every 15 minutes around market hours, the free check also looks at
  Butterfly's press releases and its 8-Ks only, so a deal announcement is reported within about
  half an hour.
- **Saturdays:** Claude also covers the court docket, the checks with no free feed, and W7.
- **The workflow** is `.github/workflows/watch-check.yml`.

- **This file:**
  <https://raw.githubusercontent.com/tenacioustuna22/small-cap-analysis/main/research/BFLY/BFLY_watch.md>
- **Background, if needed:** the summary
  <https://raw.githubusercontent.com/tenacioustuna22/small-cap-analysis/main/research/BFLY/BFLY.md>.
  The full notes are `research/BFLY/BFLY_detail.md` in the same repo.

## Rules

1. **Every figure needs a source link and a date.** Never state a number from memory. If a source
   is secondary (news, aggregator), label it **(unverified)**.
2. **Only report what is newer than the baseline.** If a finding repeats the baseline, leave it
   out. If it conflicts with the baseline, report the conflict and both sources. Rows in
   `research/BFLY/watch/BFLY_seen.csv` marked `reported`, `baselined` or `dismissed` have already been
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
    Form D can be late, missing or leave the amount blank. None of the partners files under its own
    name (EDGAR company search, 2026-11-20). "Merge Labs, Inc." (CIK 1675206) is an unrelated 2016
    San Antonio company. An investment vehicle, "MERGE LABS Sep 2025 a Series of CGF2021 LLC" (CIK
    2101077), filed a Form D on 2025-12-16. Use EDGAR full-text search by name, monthly.
- **Baseline** (other partners recorded 2026-11-20):

  | Partner | Latest known funding | Source |
  |---|---|---|
  | Merge Labs | $252M seed, 2026-01-15, led by OpenAI with Bain Capital and others, at a reported ~$850M valuation | [SiliconANGLE](https://siliconangle.com/?p=727965), [Tom's Hardware](https://www.tomshardware.com/peripherals/wearable-tech/sam-altman-raises-usd252-million-for-brain-computer-interface-venture-but-merge-labs-is-still-in-an-early-research-phase) (unverified) |
  | Bridge Neurotech | $13.5M, General Catalyst | [TheNextWeb](https://thenextweb.com/news/bridge-neurotech-13-5m-ultrasound-brain-computer-interface) (unverified) |
  | Forest Neurotech | Research organization under Convergent Research; UK safety trial funded by ARIA from March 2025, running about 3.5 years | [Convergent Research](https://www.convergentresearch.org/ecosystem/forest), [Digital Health](https://www.digitalhealth.net/2025/01/brain-implant-will-be-trialled-by-nhs-to-help-treat-neural-conditions) |
  | Mendaera | $73M Series B, 2024-09-26, led by Threshold Ventures with Lux Capital, PFM Health Sciences and Fred Moll. Earlier: $24M Series A (Lux, about Aug 2023, unverified) | [Business Wire release](https://www.businesswire.com/news/home/20240926902349/en) |
  | Sonic Incytes | US$7.3M Series A, Dec 2021, led by Nimbus Synergies. CB Insights lists a later Series B; not confirmed | [company release via MedTech Innovator](https://medtechinnovator.org/sonic-incytes-successfully-completes-series-a-raise-of-us7-3m-to-accelerate-velacurtm-commercialization/); CB Insights (unverified) |
  | Sonic Incytes, commercial | Multi-year partnership with Madrigal Pharmaceuticals (maker of Rezdiffra, a MASH drug) for Velacur ONE liver assessment, 2026-11-19. No financial terms. Velacur ONE got FDA 510(k) clearance K251728 (letter 2025-06-26). **Open:** no source says whether Velacur ONE uses Butterfly's chip. If it does, this is a W1 partner product on sale | [Business Wire via BioSpace](https://www.biospace.com/press-releases/sonic-incytes-announces-multi-year-partnership-with-madrigal-pharmaceuticals-to-advance-non-invasive-liver-assessment-in-mash), [FDA summary](https://fda.innolitics.com/device/K251728) |
  | Aleph Neuro | No funding, investors or valuation disclosed, as of 2026-11-20. Launched publicly 2026-06-25 as a brain-interface research lab | [RuntimeWire](https://runtimewire.com/article/aleph-neuro-ultrasound-brain-imaging-launch) (unverified) |

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
- **Baseline** (recorded 2026-11-20; secondary summaries, as the report PDF was not opened):
  - **US venture, Q3 2026 (PitchBook-NVCA Venture Monitor):**
    - $98.4B of deal value across about 5,012 deals in the quarter
    - $515.8B so far in 2026
    - AI's share of deal value: 82.7% for 2026 to date, and 65.9% in Q3 alone.

    Sources: [NVCA report PDF](https://nvca.org/wp-content/uploads/2026/10/Q3-2026-PitchBook-NVCA-Venture-Monitor.pdf),
    [Relve summary](https://relvehq.com/blog/noise/pitchbook-venture-monitor-515b-exits-lag) (unverified).
    The Q4 report is due about late January 2027.
  - **Global, Q3 2026 (Crunchbase):** $159B, of which AI was 64% (search summary; unverified).
  - **Brain interfaces:** no authoritative total. Two trackers:
    - PitchBook, as reported by the FT on 2026-09-17: BCI funding passed $1B in 2026
      ([remio summary](https://www.remio.ai/post/pitchbook-bci-funding-tops-1-billion-but-clinical-proof-still-lags))
    - NewMarketPitch: about $933M in the first half of 2026
      ([NewMarketPitch](https://newmarketpitch.com/blogs/news/brain-computer-interface-funding-deals)).

    Both unverified, with different scopes, so don't compare them with each other. Chinese
    start-ups closed at least 28 rounds from January to September 2026, against 4 for US ones
    (same tracker).
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
  - **Brain-interface peers** (recorded 2026-11-20; all secondary, so unverified):

    | Peer | Latest known | Source |
    |---|---|---|
    | Neuralink | $650M Series E, June 2025, at about $9B. Aggregators claim 2026 rounds and $22-48B valuations; none confirmed | [Longevity.Technology](https://longevity.technology/news/neuralink-raises-600-million-to-advance-brain-computer-interface-tech/) |
    | Synchron | $200M Series D, 2025-11-06, led by Double Point Ventures. **2026-11-12:** paused enrollment in its second-generation Stentrode trials after a performance problem with the device's lead. The company says it is not a safety issue and the FDA did not order it. A claimed June 2026 Series E is not confirmed | [Fierce Biotech](https://www.fiercebiotech.com/medtech/synchron-raises-200m-advance-its-brain-computer-interface-paralysis), [MD+DI](https://www.mddionline.com/neurological/synchron-s-bci-trial-pause-what-went-wrong-with-stentrode) |
    | Precision Neuroscience | $250M Series D, 2026-09-25, co-led by Pershing Square and the Ackman Oxman Institute. $430M raised in total; about $1B valuation (NYT) | [MassDevice](https://www.massdevice.com/precision-neuroscience-raises-250m-in-series-d-for-its-bci/), [TheNextWeb](https://thenextweb.com/news/precision-neuroscience-250m-series-d-1bn-valuation-ackman) |
    | Science Corp (added 2026-11-20) | $400M Series D, 2026-11-17/18. Investors: Khosla, Ackman Oxman Institute, Tenet Healthcare and others. More than $900M raised since 2021; a $3.5B valuation from one unnamed source. Its implant (PRIMA, retinal) uses light, not ultrasound. Previous round: $230M Series C, March 2026 | [MedTech Dive](https://www.medtechdive.com/news/science-corporation-raises-400m-to-commercialize-bci-device/875009/) |
  - **Ultrasound brain-interface companies:** Nudge (focused-ultrasound stimulation), and Gestala
    and Sisun Tech in China. These are unlikely to buy from a US supplier
    ([InsideBCI](https://insidebci.com/news/2026-09-01-merge-labs-butterfly-network-poseidon-ultrasound-chip-bci-licensing-deal/)).
  - **Exo Imaging:** a piezoelectric ultrasound chip with 4,096 elements, over $300M raised, and a
    Samsung Medison investment in May 2025 ([Pulse 2.0](https://pulse2.com/exo-imaging-35-million/);
    unverified).
    - **Gates Foundation grant** (recorded 2026-11-21): $11,594,471 committed in September 2026,
      over 28 months, announced 2026-11-19. It is for a low-cost, AI-enabled point-of-care
      ultrasound platform for non-expert health workers in low- and middle-income countries
      ([grant record](https://www.gatesfoundation.org/about/committed-grants/2026/10/inv-100015)).
      The release says the platform is being developed for handheld ultrasound and
      "OEM-integrated systems", but names no licensee or OEM partner and mentions no brain-interface
      use ([Business Wire via FinancialContent](https://www.financialcontent.com/article/bizwire-2026-11-19-exo-receives-116-million-grant-to-expand-access-to-ai-powered-ultrasound)).
      Its earlier Gates grant was $1,000,000 in April 2025, over 12 months
      ([grant record](https://www.gatesfoundation.org/about/committed-grants/2025/04/inv-084044)).
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
- **Baseline** (recorded 2026-11-20). Actual capex is from each earnings release (8-K exhibit
  99.1). Guidance is often given only on the call; call figures are secondary, so unverified.
  Nobody has guided 2027 yet; Q4 calls in late January and early February 2027 should.

  | Company | Latest quarter's capex (release) | Guidance |
  |---|---|---|
  | Meta | $34.91B in Q3 2026, including principal payments on finance leases | 2026: $135-145B, narrowed from $130-145B (release, [8-K filed 2026-10-21](https://www.sec.gov/Archives/edgar/data/1326801/000162828026066700/meta-09302026xexhibit991.htm)). No 2027 figure |
  | Alphabet | $51.4B of property and equipment purchases in Q3 2026, against $24.0B a year earlier ([8-K filed 2026-10-28](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000080/googexhibit991q32026.htm)) | 2026: $195-205B, kept on the 2026-10-28 call (unverified). Earlier it said 2027 would rise "significantly" |
  | Microsoft | $39.4B of additions to property and equipment in the September 2026 quarter, against $19.4B a year earlier ([8-K filed 2026-10-28](https://www.sec.gov/Archives/edgar/data/789019/000119312526436122/msft-ex99_1.htm)) | not recorded (given on the call) |
  | Amazon | $77.3B of property and equipment purchases in Q3 2026, against $35.1B a year earlier; $210.7B over four quarters, net of proceeds ([8-K filed 2026-10-29](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000038/amzn-20260930xex991.htm)) | not recorded (given on the call) |
  | Oracle | see its [Q1 FY2027 release](https://www.sec.gov/Archives/edgar/data/1341439/000119312526387905/orcl-ex99_1.htm) (filed 2026-09-10) | FY2027 (ending May 2027): about $90-95B gross, of which about $70B is self-funded and $20-25B is to be repaid by customers. It also plans about $40B of debt and equity raising (2026-09-10 call; [Outlook Business](https://www.outlookbusiness.com/corporate/oracle-forecasts-95-bn-in-capex-for-fy27-plans-to-raise-40-bn-in-debt-and-equity), unverified) |
  | Nvidia | Data-center revenue of $107.6B in Q3 FY2027 (ended 2026-10-25): up 110% on a year earlier and 21% on the quarter before ([CFO commentary, 8-K filed 2026-11-17](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27cfocommentary.htm)) | Q4 FY2027 revenue: $130.0B ±3%, assuming no data-center compute revenue from China ([release](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27pr.htm)) |
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
  - +0.62 over the 60 trading days from 2026-08-27 to 2026-11-19 (yfinance, computed 2026-11-20).
    This is the window the Saturday run uses, so compare later values with this one, not with
    the two above.
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
- the baselines in this file are updated, and so is the owner's status page, `BFLY_status.md`
- the matching rows in `watch/BFLY_seen.csv` are set to `baselined` or `dismissed`
- the `watch` issue is closed.

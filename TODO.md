# BFLY scenarios: decisions and to-do

## Before 2026-12-05: two weekend checks Claude can't do (weekend report, 2026-11-21)

- **EDGAR Form D full-text search (W2, monthly).** Claude's step can only use WebFetch, which
  can't send the `User-Agent` the SEC requires, so efts.sec.gov returns 403. Move the search into
  `scripts/watch_check.py` (a new source kind, run in weekend mode on the first weekend of the
  month) so it arrives as waiting items, and drop it from `[[weekend_only]]`.
- **Court docket (W3, every Saturday).** CourtListener's pages return 403 to Claude, and its
  search feed has no entry descriptions, so the weekend run can't tell an order from a routine
  filing. The CourtListener API gives descriptions but needs a free account token. Ask the owner
  before adding it (a key). Until then, the owner opens the two docket pages by hand.

## Next up: redesign the daily report (owner, 2026-11-21)

The report pages (`scripts/report.py`) predate the thesis, the scenarios work and the watchlist.
They also write a fresh dated copy of every page each day, though most of a page only changes
with a new 10-Q or 10-K. Redesign them with the owner before automating them. Starting sketch:

- **One page per ticker, kept up to date.** Overwrite it each run, with history in git, instead
  of a new dated copy every day (about 600 KB of near-duplicates a day).
- **"What changed since the last run" at the top:**
  - the price and volume move
  - new filings: 8-K items, Form 4 trades, offering filings, 10-Q/10-K
  - short interest
  - watch findings.

  Say "nothing changed" when that's so.
- **The status page built in:** the W1–W7 table from `research/BFLY/BFLY_status.md`, and the
  three-line thesis.
- **Slow sections below, each with its filing date:** runway, dilution, financials, scenarios.
- **Then automate it:**
  - a GitHub workflow after the close
  - an `actions/cache` for `data/`
  - `TZ=America/Los_Angeles`
  - GitHub Pages for reading on the phone: add `.nojekyll`, or Pages drops `reports/_summary/`
  - email only on failure.

  The first run shows whether Yahoo blocks GitHub's machines. If it does, the price sections show
  the error.
- The Windows task "Stock analysis daily report" isn't registered on this PC (checked
  2026-11-21), so the report isn't running anywhere now.
- Old Markdown reports from 2026-11-12 are still in `reports/_summary/`, `HUMA/`, `HYPR/` and
  `TMC/`. Remove them in the redesign.

## Readability (owner, 2026-11-21)

Done 2026-11-21. The owner's view of where things stand is now
[research/BFLY/BFLY_status.md](research/BFLY/BFLY_status.md). It has one row per watch item, recent
changes and the coming dates, and is updated with the baselines.
- **New layout:** BFLY's files are in `research/BFLY/`, and the automation's files (feeds,
  seen-log, state, reports) are in `research/BFLY/watch/`.
- **`BFLY.md`:** "What to watch" became a pointer. The points found nowhere else moved to
  `BFLY_detail.md`, "What to watch for AI conditions".
- **Not trimmed:** `BFLY_detail.md` and this file. Revisit them if they get in the way.

## Scenario work

Working list for writing BFLY's bear/base/bull cases into `assumptions.toml`.
Started 2026-11-15. Prices as of 2026-11-13 ($6.08). The research behind these decisions is in
[research/BFLY/BFLY_detail.md](research/BFLY/BFLY_detail.md).

## Decided

| Item | Bear | Base | Bull |
|---|---|---|---|
| Core growth a year | 0% | 6% | 12% (years 1-3), 10% (years 4-5) |
| Core EV/sales at the end | 1.0x | 2.5x | 4.0x |
| Embedded revenue, $M per year 2027-2031 | 28, 14, 7, 6, 1 | 41, 30, 26, 25, 22 | 53, 50, 54, 61, 68 |
| Embedded EV/sales at the end | 0x | 1.5x | 5.0x |
| Cash burn at the start (2027, $M a year, capex included) | 45 | 30 | 20 |
| Burn reaches zero | never | never | year 3 (during 2029) |
| Raise discount to today's price | 75% | 50% | 10% |
| **Result, value per share at 3 / 5 years** (price $6.08, 2026-11-13) | **$0.31 / $0.26** | **$1.22 / $1.15** | **$3.15 / $3.79** |

- Core starts from nine months of 2026 annualized ($85.5M; Q3 2026 10-Q).
- Core comparison companies: LUNG, SGHT, ARAY, PRCT, IRTC, STXS. Embedded comparison: CEVA only.
- Embedded bear = Midjourney's remaining fixed contract (about $27.8M after 2026, about $7M a
  year until the term ends in late 2030; 2025 10-K) plus the other partners at their
  pre-Midjourney level (about $7M a year: $5.3M in the first nine months of 2025; the full year
  ex-Midjourney was nearer $6.5M, offset by Midjourney possibly running late). Revised reasoning,
  same numbers: 2025's figure included $2.8M of one-off chip sales, so the recurring base was only
  about $3.5-4.5M; Merge Labs' signed deal (Sept 2026, terms not disclosed) fills the gap. No new deals
  and no growth. 11 Embedded partners as of the Q2 2026 release (filed 2026-07-30).

## To decide, in order

0. Done 2026-11-15:
   - Bear path rebuilt from contracted pieces only, giving 28, 14, 7, 6, 1.
   - Base path is 41, 30, 26, 25, 22: the contracted pieces, plus milestones and hardware, about
     one new deal a year at about $12M, and small royalties.
   - 2027 leans toward management's "space we are in now" (about $44M). Later years follow the
     measured signing rate.
   - The pieces are in research/BFLY/BFLY_detail.md.
1. (merged into 0)
2. Done 2026-11-15: Embedded bull path 53, 50, 54, 61, 68. It is the base pieces plus:
   - more milestones and hardware
   - 2 new deals a year at about $15M
   - larger royalties
   - a placeholder spa row: revenue share and chips, starting 2029.

   Management's $550M 2030 target is left out.
3. Done 2026-11-15: Embedded EV/sales at the end is 0x / 1.5x / 5.0x.
   - Bear: everything left is contract tails, whose cash is already in the burn.
   - Base: a shrinking stream of fees that have to be re-won.
   - Bull: a little above CEVA's 4.4x, as it grows faster and royalties reach about 44% by 2031.
   - Today's EV ($1.52B) is above even the bull at 5 years (about $0.9B, undiscounted). That gap is
     a finding, not something to tune away.
4. Done 2026-11-16: starting burn is 45 / 30 / 20 ($M in 2027, capex included). Built from:
   - the 2026 underlying loss (about $21M a year)
   - profit from the revenue change at about 70% margin
   - Midjourney revenue already paid for (-7)
   - cost growth (0 / -3 / -5)
   - in the bear, -5 for receivables not collected or litigation not covered
   - capex (-4).

   The breakdown is in research/BFLY/BFLY_detail.md.
5. Done 2026-11-16: breakeven never / never / 3 years; raise discount 75% / 50% / 10%.
   - Burn was rolled forward year by year, and each straight-line setting was picked to match.
   - Base never breaks even on its own revenue.
   - 10% is the January 2025 offering ($3.15 against a $3.51 close).
   - The bear and base discounts reflect where the price would be by the time of the raise.
6. Done 2026-11-16:
   - `assumptions.toml` written, reports regenerated, tests pass (111).
   - Sanity checks:
     - 2027 revenue: base $132M, against consensus of $150M; bull about equal to consensus.
     - Exit EV/sales 0.9-4.3x, inside the peer range.
     - Bear dilution is 68M shares at 5 years, understated as noted.
     - The base case's -80% against today is explained in "What the market is pricing".
   - The model's limits are shown above the figures (the new `caveats` key), at the owner's
     request: "they change the story that these figures show in reality".

## Parked (come back to these, don't let them stall the list above)

- **Embedded deal log** (from the 2026-11-18 hypothesis in `research/BFLY/BFLY.md`): one row per
  partner. Fields:
  - date announced, partner, field
  - how the partner is funded (latest round, investors)
  - deal size where disclosed, and the source.

  Start from the partner table in `research/BFLY/BFLY_detail.md`, then BFLY's 8-Ks and press
  releases. This is how to test whether signings follow AI and neurotech funding.
- **AI-conditions watch script and report section** (not built). It needs no new data source:
  - big tech capex, actual and guided, from EDGAR XBRL
  - Form D filings for the brain-interface companies (Merge, Bridge, Forest; peers Neuralink,
    Synchron, Precision)
  - BFLY's rolling 60-day correlation with ARKK and SMH, from yfinance.

  The design is in `research/BFLY/BFLY_detail.md`, "What to watch for AI conditions".

- Check the Midjourney scanner and spa details against official sources, then add the spa
  opening to `catalysts.csv`. Details to check: announced June 2026, at 300 Grant Avenue,
  San Francisco, a stated 2027 opening (the owner expects nearer 2029), and a 60-second scan
  target against a reported ~20 minutes.
- Find out why Q4 2025 product revenue was $18.1M, the highest quarter shown. It makes Q4 2026 a
  hard comparison. Read the Q4 2025 release and the 2025 10-K.
- Estimate (to be confirmed by the 2026 10-K): Q4 2025 Embedded was about $7.5-8.5M and Core
  about $23-24M. Method: product revenue plus Core's usual $5-6M of services. Midjourney was
  $6.8M of it (2025 10-K: $17.5M received, $6.8M recognized in 2025), so other partners were only
  about $1-2M that quarter and about $6.5M for 2025, falling quarter by quarter.
- Midjourney agreement (10-K exhibit 10.26, partly redacted):
  - Termination is only for uncured material breach or insolvency, and payments stop after it.
  - A missed license payment costs Midjourney its exclusivity.
  - Milestones are accepted within 10 business days.
  - The revenue share covers a "scanning service", at a redacted percentage.
  - Chips are sold at cost plus a redacted margin.
  - There is an upgrade option at a redacted fee.
  - Revenue is counted by development cost incurred against forecast.
  - The transaction price is about $70M, $5M above the fixed fees, probably expected milestones.
- Embedded partners named in releases:
  - Midjourney.
  - Aleph Neuro (Q2 2026).
  - Merge Labs and Bridge Neurotech, two of "three BCI partners" added (Q3 2026 release).
  - Mendaera, "first partner to launch a commercial product built on Butterfly technology on
    October 1, 2026".
  - Sonic Incytes (Feb 2025).
  - The count was 11 at Q2 2026; the Q3 release gives no new total.
- Customer concentration (10-Qs and 10-K; only the 10% threshold is tagged, not actual shares):
  - Q3 2026: two customers were each over 10% of total revenue, i.e. over $3.26M each.
  - Nine months 2026: only one was over 10%.
  - Q1 and Q2 2026: one each.
  - 2025: one customer over 10% of the year ($9.76M) while none were over 10% in the first nine
    months, but Midjourney's 2025 revenue was only $6.8M. Either that was a Core customer with a
    large Q4 2025 order (product revenue was $18.1M), or Midjourney earned more than $3M under the
    March 2025 term sheet before the agreement. Unresolved.
  - Who the second Q3 2026 customer is (an Embedded partner or a Core buyer) is unresolved. Check
    the Q3 call or the 2026 10-K.
- 2025 Embedded included about $2.8M of one-off chip sales (product revenue) to "one of our Octiv
  partners" in the first half of 2025 (Q2 2025 10-Q; the Q2 and Q3 2026 10-Qs call it
  non-recurring). So other partners' recurring 2025 revenue was only about $3.5-4.5M, not $6.5M.
  If that chip buyer was Midjourney under its March 2025 term sheet, it would also explain the 2025
  over-10% customer ($6.8M + $2.8M is close to the $9.76M threshold). Unconfirmed.
- Second over-10% customer in Q3 2026: another session read earnings call summaries and inferred
  Merge Labs (deal announced 2026-09-01; upfront and milestone license payments, hardware purchase
  commitments, access fees). That is an inference. No 8-K item 1.01 was filed for Merge, unlike
  Midjourney, so BFLY did not treat it as a material agreement.
- Done 2026-11-15: checked against the Investing.com Q3 transcript; details in research/BFLY/BFLY_detail.md.
  The wording differs slightly: "live in the space that we are in now ... carry that on into 2027".
  Management quotes to verify in a transcript before citing them:
  - The CFO said Embedded should hold "near this level into 2027".
  - The CEO said guidance counts only signed work.
  - The CEO said Mendaera's meaningful revenue is "a year or two" out.
- Watch each quarter:
  - Embedded revenue.
  - Gross margin, since a cost overrun on the contract would show there.
  - Milestone payments.
  - Any 8-K on an amendment or license upgrade.
  - Midjourney's remaining contracted revenue in the 2026 10-K.
- Bear note for Embedded: Midjourney stopping payment, only through breach or insolvency, is a
  stated risk, not part of the path. It argues for a 0x or very low bear multiple.
- After the Q4 2026 results (about late February 2027): revisit Core growth (Q4 guidance implies
  Core below Q4 2025 unless BFLY beats it again) and Embedded's starting point (the 10-K gives a
  four-quarter total).
- The page could note that 2026 Embedded revenue is front-loaded. BFLY recognizes Midjourney's
  revenue as the work progresses, ahead of the cash, so 2026 growth and EV/sales flatter the
  ongoing business.
- The $35.4M of Midjourney revenue expected in 2026 is the 2025 10-K's forecast (56% of $63.2M),
  not a reported figure. Embedded reported $27.6M for the first nine months of 2026, all partners
  together, so that forecast would leave other partners almost nothing. When the 2026 10-K is out,
  check how much Midjourney contracted revenue is left at year end. That gives 2026's actual
  Midjourney revenue and what remains for 2027-2030.
- Page line (include it, no longer optional): what today's price implies, for example the 2030
  revenue needed at the peer multiples. Today's price is above our bull case.
- Done 2026-11-16: what everyone says about Embedded, and Embedded without Midjourney (estimate).
  Both are in research/BFLY/BFLY_detail.md.
  - Outside Midjourney, Embedded was about $1M a quarter in 2025, mostly Forest.
  - It was about $4.5-6M in Q3 2026, mostly Merge Labs' signing.
  - The base case assumes the rest of Embedded about doubles in 2027.
  - Midjourney's 2026 revenue may be lower than we assumed ($17.5-21.4M over nine months), which
    leaves more for 2027. Check against the 2026 10-K before changing the paths.
- Still open: analyst reasoning. Needham started at Buy with a $10 target, date unconfirmed. Only
  summaries were found for the J.P. Morgan, TD Cowen, Bank of America and Morgan Stanley talks;
  check the replays on BFLY's investor relations site.
- Find the bull argument: what management pitched about the platform, and what analysts cite.
  Read the Q4 2025, Q1 2026 and Q2 2026 call transcripts. Analyst targets are $10-15 (Yahoo,
  2026-11-13). Hypotheses are in research/BFLY/BFLY_detail.md, "What the market is pricing". If something
  real turns up, revisit the bull case.
- Management track record (research/BFLY/BFLY_detail.md):
  - Confirm "$550M" on the Q3 2026 call replay. The only written target is "over $500 million"
    (investor day, 2024-03-19).
  - Compare the 2020-21 SPAC merger projections (Longview proxy) with actual results.
- Done 2026-11-16: the fall from the September peak. Details are in research/BFLY/BFLY_detail.md, "The fall from the
  September peak". Watch:
  - How much of the $150M ATM (filed 2026-10-29) has been sold. Check the next cover-page share
    count and the 2026 10-K.
  - Whether Rothberg files more Form 144s, and Fidelity's next 13G (15.0% at 2026-09-30).
  - Any Midjourney news.
  - Model question for later: the scenarios raise money only when cash runs out, at a discount.
    An ATM selling near today's price, which is above every case, would raise value per share in the
    model, not cut it. Decide whether to model ATM sales.
- Done 2026-11-16:
  - The path to profitability: section, comparison table and `scripts\profitability.py`.
  - The forward multiple (EV / next year's consensus sales).

  Neither closes BFLY's premium over the comparison companies (research/BFLY/BFLY_detail.md).
- Next:
  - Growth speeding up (latest quarter's growth against a year earlier), across the companies.
  - Then rebuild the scenario burn from costs, one decision at a time. Start with gross margin per
    stream.
- Possibly later: share of recurring revenue, and balance sheet strength (net cash and runway),
  in the comparison table.
- HYPR: its scenarios, its comparison companies (STXS, ARAY, possibly NNOX), and its September
  2026 item 3.01 notice and ATM use.

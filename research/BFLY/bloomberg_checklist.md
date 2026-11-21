# Bloomberg session checklist

For a session at the school's Bloomberg terminal, with Claude open on the laptop alongside.
Priorities run from the gaps that matter most for the BFLY hypothesis (see the top of
[BFLY.md](BFLY.md)) to nice-to-haves. Stop wherever time runs out.

## Before you start

- **How to use it:** type a security, press the yellow key for its type, then a function code and
  `<GO>`. For example: `BFLY US` `<EQUITY>` `DES` `<GO>`. To find a company by name, start typing it
  and pick from the drop-down.
- **Stuck? Press `HELP` twice.** It opens a live chat with Bloomberg's help desk. Ask in plain
  words, for example "where do I find venture funding rounds for a private company?". The function
  codes below are from memory; if one doesn't work, ask them.
- **Recording what you find:**
  - Note each finding in your own words, with "per Bloomberg, accessed <date>".
  - Don't paste tables into the repo: it is public, and Bloomberg's licence generally forbids
    redistribution.
  - Put any raw exports in `data\bloomberg\`, which is git-ignored.
  - Check the school program's own rules.
- **Ask Claude live** when a screen is confusing, or to check whether a number fits what we have.

## 1. Funding for Embedded partners (most important, about 30 minutes)

This tests the top of the hypothesis: can the partners pay, and is money still flowing to
brain-interface and AI-application companies?

**For each company, record:**
- latest round: date, amount, valuation if shown, lead investors
- total raised
- any revenue or headcount figures
- any Butterfly relationship listed.

**The companies:**

| Group | Companies |
|---|---|
| Partners | Merge Labs, Bridge Neurotech, Forest Neurotech, Midjourney, Aleph Neuro, Mendaera, Sonic Incytes |
| Brain-interface peers | Neuralink, Synchron, Precision Neuroscience |
| Chip competitor | Exo Imaging |

**Also try:**
- **A sector view:** venture funding into neurotech or brain-computer interfaces, and into AI
  applications, by quarter for 2024-2026. Ask the help desk whether a screen or report shows this.
- **Midjourney revenue or subscriber estimates.** We only have secondary sources saying it is
  self-funded.

## 2. BFLY earnings call transcripts (about 30 minutes)

`BFLY US <EQUITY> EVTS <GO>`, then open the transcripts for:
- the Q4 2025 call (February 2026)
- the Q1, Q2 and Q3 2026 calls.

**Search inside each for:** Embedded, Midjourney, Merge, pipeline, royalty, revenue share, Apollo,
spa, ATM, breakeven.

**Questions to answer:**
- **Partners:** how many Embedded partners there are now, and are any sizes or terms given beyond
  Midjourney's and Forest's?
- **Pipeline:** what management says about deals still to come, and how many.
- **Midjourney:** anything about the timing of its revenue, and progress on the scanner or spa.
- **The ATM:** why it was filed, and whether shares have been sold under it.
- **Analysts' questions:** what they pushed on, which shows what the Street is worried about.

## 3. Analyst estimates in detail (about 15 minutes)

`BFLY US <EQUITY> EE <GO>` (estimates) and `ANR <GO>` (recommendations and targets).

**Record:**
- **Revenue estimates:** each analyst's figure for 2026, 2027 and 2028, plus the high, low and
  number of analysts. Compare with Yahoo's 2027 consensus: $150.2M from 7 analysts.
- **Segments:** any estimates for Embedded and Core separately. This would be new to us.
- **Profit and cash:** EBITDA, free cash flow and cash-burn estimates, if any.
- **Targets:** price targets with dates, and which firms hold which view.

## 4. Supply chain map (about 10 minutes)

`BFLY US <EQUITY> SPLC <GO>`
- **Customers listed:** look for any partner we don't know about, especially the brain-interface
  partner still in stealth.
- **Revenue shares:** any share of BFLY's revenue shown per customer. Note whether Bloomberg marks
  it as estimated or disclosed.

## 5. The AI spending cycle (about 15 minutes)

For Microsoft, Alphabet, Amazon, Meta and Oracle (`MSFT US`, `GOOGL US`, `AMZN US`, `META US`,
`ORCL US`), `EE <GO>`:
- **Capex consensus** for 2026 and 2027, and how it has moved over the last three months. A falling
  estimate is the early warning.
- **Nvidia (`NVDA US`):** data-center revenue consensus for its next fiscal year.

## 6. If time is left

- **Cost to borrow BFLY shares** (securities lending): shows how crowded the short side is. We only
  have short interest, at 15.9% of float.
- **Holders** (`HDS <GO>`): is anything more recent than Fidelity's 15.0% at 2026-09-30, and did
  Rothberg or Glenview sell more?
- **Bloomberg Intelligence research** (`BI <GO>`) on handheld ultrasound, brain-computer interfaces
  or medtech AI.
- **News search** for "ultrasound brain-computer interface" and "Butterfly Embedded" over the last
  six months (`CN <GO>` on BFLY, or the news search).

## Bring back

For each item: what you found, the date of the figure, and where on Bloomberg. We'll check it
against what we have and add it to `research/BFLY/BFLY_detail.md` and the deal log in `TODO.md`.

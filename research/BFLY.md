# BFLY: Butterfly Network

Updated 2026-11-16. Price $5.71 (close 2026-11-16). This is the summary to look back on. The working,
derivations and every source are in [BFLY_detail.md](BFLY_detail.md), and open items in
[TODO.md](../TODO.md). **(estimate)** marks our own arithmetic; **(unverified)** marks anything from
outside the filings.

## The story in five points

1. **Two businesses.**
   - **Core** (handheld ultrasound and software) is about $85M a year, growing about 6%.
   - **Embedded** (licensing its ultrasound chip to other companies) went from $5.3M to $27.6M in
     the first nine months of 2026 and supplied 87% of the growth (Q3 2026 10-Q).
2. **Embedded is mostly one contract: Midjourney.**
   - Terms: $65M of fixed fees over 5 years, up to $9M of milestones, and a revenue share and chip
     sales (rates redacted).
   - Revenue is reported as BFLY's development work progresses, so it is front-loaded into 2026.
     The cash arrives at about $10M a year until 2030.
   - Midjourney revenue drops sharply after 2026: about $17M in 2027, then about $4-6M a year
     (estimate).
3. **Outside Midjourney, Embedded is small** and steps up when a deal is signed. It earned about $1M
   a quarter in 2025 and about $4.5-6M in Q3 2026, mostly Merge Labs' signing (estimate).
4. **Every scenario is below the price.** Bear $0.31, base $1.22, bull $3.15 a share at 3 years
   (model, prices as of 2026-11-13).
5. **The price is a bet on two things:** management's plan (over $500M revenue by 2030), and AI
   and brain-interface money continuing to fund new Embedded partners. Neither the path to
   profitability nor next year's expected growth explains the premium over the comparison
   companies (2026-11-16).

## Key numbers

| Item | Value | Source |
|---|---|---|
| Revenue, first nine months of 2026 | $91.7M (Core $64.2M, Embedded $27.6M) | Q3 2026 10-Q |
| 2026 guidance | $123-126M; Q4 $31-34M, about 3% growth | Q3 release, 2026-10-29 |
| 2027 analyst consensus | $150.2M | Yahoo, 2026-11-15 |
| Cash | $122.3M; no debt tagged | Q3 10-Q |
| Underlying burn | about $21M a year; quarters swing with working capital | estimate |
| Shares | 267.5M, Class A plus B | 10-Q cover, 2026-10-19 |
| New stock program | $150M ATM, filed 2026-10-29; about 8-10% dilution if fully used | S-3ASR |
| Enterprise value | $1,522M, about 12x 2026 revenue (device peers 1-6x, CEVA 4.4x) | Yahoo, 2026-11-13 |
| EV / next year's sales | 9.4x 2027 consensus (peers 1.1-5.3x); the premium is the same as on trailing sales | Yahoo via yfinance, 2026-11-16 |
| Path to profitability | Operating margin -47% (+32 points in a year); free cash flow -22%, not improving; stock pay 21% of revenue | EDGAR, `scripts\profitability.py` |
| Short interest | 15.9% of float | Yahoo, 2026-10-30 |
| Analyst targets | $10-15 | Yahoo, 2026-11-13 |

## Scenarios (decided with the owner 2026-11-15/16)

| | Bear | Base | Bull |
|---|---|---|---|
| Core growth / exit EV/sales | 0% / 1.0x | 6% / 2.5x | 12% then 10% / 4.0x |
| Embedded, $M 2027 → 2031 / exit EV/sales | 28 → 1 / 0x | 41 → 22 / 1.5x | 53 → 68 / 5.0x |
| Burn at start / breakeven | $45M / never | $30M / never | $20M / 2029 |
| Raise discount | 75% | 50% | 10% |
| **Value per share, 3 / 5 years** | **$0.31 / $0.26** | **$1.22 / $1.15** | **$3.15 / $3.79** |

**Limits** (these change the story):
- Nothing reacts, such as cost cuts.
- Shares are raised only at zero cash.
- Values are undiscounted, and options and warrants are excluded.
- Not modeled: Midjourney defaulting, the class action exceeding insurance, Midjourney's license
  upgrade, renewal after 2030, and ATM sales.

## What today's price needs (estimate)

- **Just to hold the price:** with the bull case's Core, $6.08 in 2031 needs Embedded at about
  $190M of revenue at 5x, about 2.8 times the bull's $68M.
- **To earn 10% a year:** Embedded needs about $390M, which is about management's plan.
- **Management's plan as a case:** worth about $8.60-10.60 a share, so the price implies about a
  35-65% chance it happens.

## Why it fell from $9.93 (2026-09-22) to $5.71

- **The peak itself was a one-day spike:** +22% when Needham started coverage.
- **About half to three-quarters of the fall matches the AI and speculative-tech selloff**
  (estimate). Since the peak BFLY trades with ARKK (correlation +0.72), not with medtech, which
  rose.
- **BFLY-specific causes:**
  - The $150M ATM was filed with the Q3 results. The stock fell 14.9% the next day.
  - Insiders sold: Rothberg about $54M in July, Glenview about $35M in July and August, and the
    CEO made a discretionary sale on 2026-10-30.
  - On the other side, Fidelity added, reaching 15.0% by 2026-09-30.
- **Why AI matters:** the partners that matter (Midjourney, Merge Labs, Bridge, Aleph) are AI and
  brain-interface companies funded by tech money. Merge Labs was co-founded by Sam Altman with a
  $252M seed round. About four-fifths of the price is for growth beyond our base case.
- **Midjourney is self-funded** from subscriptions (secondary sources). Its risk is competition in
  image generation, not venture funding drying up.

## Main risks

- **Midjourney concentration:** a private company with no audited figures. Its payments stop only
  on breach or insolvency.
- **Falling reported Embedded revenue after 2026**, unless new deals replace Midjourney.
- **Dilution:** the ATM, and the base case never breaks even. Management's breakeven target has
  slipped from end-2027 to 2028.
- **Management's track record:** it cut 2025 guidance. Its 2030 target dates from March 2024,
  before Midjourney, and the businesses it rested on haven't delivered.
- **Cash quality:** receivables are up to about 105 days of sales (estimate). The class action is
  covered only if insurance is adequate.
- **Upside the model leaves out:** a second Midjourney-sized deal, the Apollo chip, the spa opening,
  and a takeover.

## Next checks

- **2026 10-K, about late February 2027:**
  - Midjourney's remaining contracted revenue, which gives its actual 2026 revenue.
  - 2027 guidance against the $150M consensus and our $132M base.
  - Q4 burn and receivables.
  - ATM shares sold.
- **Ongoing:**
  - New Embedded deals and their size.
  - Insider sale filings.
  - Fidelity's next filing.
  - Midjourney news.

## Key sources

- [2025 10-K](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000009/bfly-20251231.htm)
- [Midjourney agreement, exhibit 10.26](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000009/bfly-20251231xex1026.htm)
- [Q3 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000040/bfly-20260930.htm)
- [Q3 2026 release](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000038/bfly-20261029xexx991.htm)
- [S-3ASR and $150M ATM](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000043/butterflynetworkincs-3asr1.htm)

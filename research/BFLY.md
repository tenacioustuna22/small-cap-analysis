# BFLY: Butterfly Network

Updated 2026-11-18. Price $5.71 (close 2026-11-16). Working, derivations and every source:
[BFLY_detail.md](BFLY_detail.md). Open items: [TODO.md](../TODO.md). **(estimate)** marks our own
arithmetic; **(unverified)** marks anything from outside the filings.

## What to watch, and how it feeds Embedded

BFLY's premium rests on Embedded, the program that licenses its ultrasound chip to other
companies. The companies signing are AI and brain-interface firms, so their money is what to watch.
The list runs from the most direct link to the least:

1. **Neurotech funding: the most direct link.**
   - Brain-interface companies need it to sign deals and pay milestones. These are Merge Labs,
     Bridge Neurotech, Forest Neurotech, a partner still in stealth, and future partners.
   - Merge raised a $252M seed (OpenAI, Bain Capital and others). Bridge raised $13.5M, so it can't
     pay much.
   - Where to look:
     - partners' **Form D** filings on EDGAR (filed when raising private money; some file late or
       leave amounts blank)
     - funding news for brain-interface peers: Neuralink, Synchron and Precision.
2. **Venture funding for AI applications: where the next Midjourney comes from.**
   - Midjourney itself pays from its own subscriptions (unverified). Its risk is competition in image
     generation, not venture funding.
   - Where to look: the free PitchBook-NVCA Venture Monitor summary and Crunchbase News (quarterly,
     about a month's lag). Also large AI raises, and whether AI IPOs get done.
3. **The AI spending cycle: the early warning, not a direct driver.**
   - It sets the mood that funds the two layers above.
   - What to read:
     - Big tech capex, actual and guided (Microsoft, Alphabet, Amazon, Meta, Oracle).
     - Cloud revenue growth against that capex.
     - Nvidia data-center revenue.
     - ARKK and SMH.
   - It can boom while neurotech funding dries up, or the reverse.
4. **BFLY's own deal log: where all of it shows up.** For each new Embedded deal, record:
   - the date, partner and field
   - how the partner is funded
   - the size, where disclosed.

   **Watch deal size more than deal count.** Holding $5.71 needs Midjourney-sized deals (see
   "What today's price needs"). Also watch Embedded revenue and contracted revenue (RPO) in each
   10-Q.
5. **One gauge: BFLY's 60-day correlation with ARKK.**
   - It was +0.38 from April to the peak and +0.72 since.
   - **While it stays high,** BFLY trades as an AI stock, so weight layers 1-3.
   - **If it falls back to 0.2-0.3,** BFLY is trading on its own news again.

**Coming dates:**
- **January-February 2027:** big tech's 2027 capex guidance, and BFLY's 2027 revenue guidance
  against the $150.2M consensus and our $132M base. If both disappoint together, the two signals
  agree.
- **About late February 2027:** the 2026 10-K.
- **End of 2027:** Midjourney's first scanner spa, in San Francisco. That is the stated date; the
  owner expects it nearer 2029.

## What would change our mind

| Supports the thesis | Weakens it |
|---|---|
| A second Midjourney-sized deal | No new deal of size for several quarters |
| BCI and AI-application funding rounds continue | A partner's funding fails |
| A disclosed revenue-share rate, or a scanner count from Midjourney | A rival chip (such as Exo Imaging's) wins a brain-interface deal |
| 2027 guidance at or above the $150M consensus | 2027 guidance near our $132M base |
| The spa opens, and roughly on schedule | The correlation with ARKK falls while the price keeps falling (a BFLY-specific problem) |

## The hypothesis in one paragraph

- **Core** (handheld ultrasound, about $85M a year, growing about 6%) is worth roughly what device
  companies are worth: about $1.22 a share in our base case.
- **Embedded is the bet.** About four-fifths of the $5.71 price rests on Embedded, which licenses
  the chip.
- **What the chip does:**
  - It puts 8,960 transducers on one semiconductor chip, each driven by electronics underneath it.
  - That makes large, cheap, tileable arrays possible. Piezoelectric arrays can do the same only at
    far higher cost.
  - It turns ultrasound into raw data for software to read, which is why AI and brain-interface
    companies are the buyers.
- **So BFLY's value depends mainly on two things:**
  - how many *large* deals AI-funded companies sign
  - whether partners' products ship, so the revenue share and royalties start.
- **AI sentiment** moves the stock day to day. Through the ATM, it also sets what new cash costs.

## The chain, link by link

| Link | Evidence | How sure / what's unknown |
|---|---|---|
| 1. The chip does something others can't do cheaply at scale | Electronics on the chip remove the wiring limit; wired probes stop being practical above about 2,000 elements. Midjourney's scanner is a ring of 40 chips (about 358,000 elements, estimate) | Fairly sure. Piezoelectric matrix probes (Philips xMATRIX) exist but cost more. Exo Imaging's piezoelectric chip (4,096 elements, Samsung-backed) is the main rival |
| 2. The buyers are AI and brain-interface companies | Midjourney, Merge, Bridge, Aleph and a stealth partner. The tie runs through the method: rebuilding images from every angle, or decoding brain signals, takes heavy computing | Sure about who; the reason is our reading. The older medtech partners (Forest, Mendaera, Sonic Incytes) are small |
| 3. Embedded drives the growth and the premium | 87% of 2026 growth (Q3 10-Q). The premium holds on next year's sales: 9.4x against 1.1-5.3x for peers. Profitability doesn't explain it. Expected 2027 growth (+20%) is the same as PRCT's and IRTC's | Sure, but reached by ruling the other explanations out |
| 4. AI investment sets how many deals are signed, and how big | Deals since 2025 come from AI-funded companies | A pattern from a handful of deals, not yet a measured trend. The large deals probably go first in a slowdown |
| 5. Products shipping turns deals into lasting revenue | Midjourney: chip purchases plus a hardware revenue share. Merge: hardware commitments plus royalties | Chips sell at cost plus a markup; the revenue-share rate is redacted. Ultrasound brain interfaces through an intact skull are unproven, and years away |
| 6. AI sentiment moves the price, and the price feeds back | ARKK correlation +0.72 since the peak. Selling ATM shares at lower prices costs holders more | Part of the correlation is momentum and short-interest trading (15.9% of float), not information about deals |
| 7. Conventional metrics set the floor | Bear $0.31 and base $1.22 a share. Cash $122.3M, underlying burn about $21M a year, the $150M ATM | They set what's left without Embedded, and how long BFLY can wait for deals |

## Open questions (not disclosed anywhere we found)

- **The revenue-share and royalty rates**, which turn partner volume into profit.
- **Midjourney's actual 2026 revenue**, which the 2026 10-K should allow us to derive.
- **The size of deals** other than Midjourney's ($65M fixed plus up to $9M of milestones) and
  Forest's ($20M).
- **The sensor count:** the CEO says "about half a million sensors", but 40 chips × 8,960 is
  358,400.
- **Through the skull:** whether ultrasound brain interfaces work without removing part of it.
  Forest's UK trial enrolls people with part of the skull removed.

## Key numbers

| Item | Value | Source |
|---|---|---|
| Revenue, first nine months of 2026 | $91.7M (Core $64.2M, Embedded $27.6M) | Q3 2026 10-Q |
| 2026 guidance | $123-126M; Q4 $31-34M, about 3% growth | Q3 release, 2026-10-29 |
| 2027 analyst consensus | $150.2M, +20%, 7 analysts | Yahoo via yfinance, 2026-11-16 |
| Cash | $122.3M; no debt tagged | Q3 10-Q |
| Underlying burn | about $21M a year; quarters swing with working capital | estimate |
| Shares | 267.5M, Class A plus B | 10-Q cover, 2026-10-19 |
| New stock program | $150M ATM, filed 2026-10-29; about 8-10% dilution if fully used | S-3ASR |
| Enterprise value | $1,522M, about 12x 2026 revenue (device peers 1-6x, CEVA 4.4x) | Yahoo, 2026-11-13 |
| EV / next year's sales | 9.4x 2027 consensus (peers 1.1-5.3x) | Yahoo via yfinance, 2026-11-16 |
| Path to profitability | Operating margin -47% (+32 points in a year); free cash flow -22%, not improving; stock pay 21% of revenue | EDGAR, `scripts\profitability.py` |
| Short interest | 15.9% of float | Yahoo, 2026-10-30 |
| Analyst targets | $10-15 | Yahoo, 2026-11-13 |

**Midjourney's deal:**
- **Fixed fees:** $65M over 5 years, plus up to $9M of milestones, a revenue share and chip sales.
- **Revenue is front-loaded into 2026:** it is reported as BFLY's development work progresses.
  - Expected: about $17M in 2027, then about $4-6M a year (estimate).
  - The cash arrives at about $10M a year until 2030.
- **Outside Midjourney,** Embedded earned about $1M a quarter in 2025 and about $4.5-6M in Q3 2026,
  mostly from Merge's signing (estimate).

## Scenarios (decided with the owner 2026-11-15/16)

| | Bear | Base | Bull |
|---|---|---|---|
| Core growth / exit EV/sales | 0% / 1.0x | 6% / 2.5x | 12% then 10% / 4.0x |
| Embedded, $M 2027 → 2031 / exit EV/sales | 28 → 1 / 0x | 41 → 22 / 1.5x | 53 → 68 / 5.0x |
| Burn at start / breakeven | $45M / never | $30M / never | $20M / 2029 |
| Raise discount | 75% | 50% | 10% |
| **Value per share, 3 / 5 years** | **$0.31 / $0.26** | **$1.22 / $1.15** | **$3.15 / $3.79** |

Prices as of 2026-11-13. **Limits** (these change the story):
- Nothing reacts, such as cost cuts.
- Shares are raised only at zero cash.
- Values are undiscounted.
- Options and warrants are excluded.
- Not modeled:
  - Midjourney defaulting
  - the class action exceeding insurance
  - Midjourney's license upgrade
  - renewal after 2030
  - ATM sales.

**What today's price needs (estimate):**
- **Just to hold the price:** with the bull case's Core, $6.08 in 2031 needs Embedded at about $190M
  of revenue at 5x. That is about 2.8 times the bull's $68M.
- **To earn 10% a year:** Embedded needs about $390M, which is about management's plan (over $500M
  of total revenue by 2030).
- **Management's plan as a case:** worth about $8.60-10.60 a share, so the price implies about a
  35-65% chance it happens.

## Next checks

- **2026 10-K, about late February 2027:**
  - Midjourney's remaining contracted revenue, which gives its 2026 revenue.
  - 2027 guidance.
  - Q4 burn and receivables.
  - ATM shares sold.
- **Ongoing:**
  - new Embedded deals and their size (the deal log)
  - partner funding rounds
  - insider sale filings
  - Fidelity's next filing
  - Midjourney news, and its scanner and module counts as the spa nears.

## Main risks

- **Midjourney concentration:** a private company with no audited figures. Its payments stop only
  on breach or insolvency.
- **Reported Embedded revenue falls after 2026** unless new deals replace Midjourney's
  front-loaded revenue.
- **Dilution:**
  - the ATM
  - the base case never breaks even
  - management's breakeven target has slipped from end-2027 to 2028.
- **Management's track record:**
  - It cut its 2025 guidance.
  - Its 2030 target dates from March 2024, before Midjourney, and the businesses it rested on
    haven't delivered.
- **Cash quality:** receivables are up to about 105 days of sales (estimate). The class action is
  covered only if insurance is adequate.
- **Upside the model leaves out:**
  - a second Midjourney-sized deal
  - the Apollo chip
  - the spa opening
  - a takeover.

## Why it fell from $9.93 (2026-09-22) to $5.71

- **The peak was a one-day spike:** +22% when Needham started coverage.
- **About half to three-quarters of the fall matches the AI and speculative-tech selloff**
  (estimate). Medtech rose over the same period.
- **BFLY-specific causes:**
  - The $150M ATM was filed with the Q3 results; the stock fell 14.9% the next day.
  - Insider sales:
    - Rothberg, about $54M in July
    - Glenview, about $35M in July and August
    - a discretionary sale by the CEO on 2026-10-30.
  - Fidelity added, reaching 15.0% by 2026-09-30.

## Key sources

- [2025 10-K](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000009/bfly-20251231.htm)
- [Midjourney agreement, exhibit 10.26](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000009/bfly-20251231xex1026.htm)
- [Q3 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000040/bfly-20260930.htm)
- [Q3 2026 release](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000038/bfly-20261029xexx991.htm)
- [S-3ASR and $150M ATM](https://www.sec.gov/Archives/edgar/data/1804176/000180417626000043/butterflynetworkincs-3asr1.htm)
- [Butterfly on Midjourney's scanner, 2026-06-18](https://ir.butterflynetwork.com/News/press-releases/news-details/2026/Butterfly-Network-Provides-Commentary-on-Midjourney-Medicals-Full-Body-Ultrasound-Scanner-Announcement/default.aspx)
- [Merge Labs release, 2026-09-01](https://ir.butterflynetwork.com/News/press-releases/news-details/2026/Merge-Labs-and-Butterfly-Network-Partner-to-Advance-Ultrasound-Based-Brain-Computer-Interfaces/default.aspx)

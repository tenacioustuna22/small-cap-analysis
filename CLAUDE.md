# Stock Analysis

Python tooling for analyzing stocks, mainly US small caps. The owner uses it for both
long-term holds and shorter swing/catalyst trades.

## Watchlist

| Ticker | Company | Business | Status |
|--------|---------|----------|--------|
| BFLY | Butterfly Network | Handheld ultrasound | active |
| HYPR | Hyperfine | Portable MRI | active |
| TMC | TMC the metals company | Deep-sea polymetallic nodules | inactive |
| HUMA | Humacyte | Bioengineered human tissue / vessels | inactive |

Keep the watchlist in one place (`watchlist.csv`) and have code read it. Never hard-code
tickers in scripts. The list will grow. The `status` column decides what runs by default:
`active` gets full reports, `peer` appears only in valuation comparisons, `inactive` is
skipped. The current focus is BFLY and HYPR.

## What every analysis covers

1. **Fundamentals and runway**: cash and equivalents, quarterly burn, months of runway,
   debt, revenue growth, gross margin. Most of these companies are pre-profit, so
   survival and dilution matter more than P/E.
2. **Dilution**: share count trend, open shelf registrations (S-3), ATM programs,
   warrants, convertibles. Report fully diluted share count where possible.
3. **Catalysts**: dated upcoming events (FDA actions, permits, contracts, earnings),
   each with a source.
4. **Valuation**: EV/sales against peers, plus bull/base/bear scenarios with the
   assumptions stated.
5. **Technicals and flow**: trend, volume, short interest, insider and institutional
   transactions.

Frame conclusions for both horizons: the multi-year thesis, and the near-term setup.

## Workflow per company (owner, 2026-11-18)

1. **Build the full analysis** with the owner, as was done for BFLY: reports, scenarios, research
   notes, and a working hypothesis at the top of `research/<TICKER>/<TICKER>.md`. Each company's
   files live in `research/<TICKER>/` (layout under "Code conventions").
2. **Write a watchlist,** `research/<TICKER>/<TICKER>_watch.md`, of what could move the price.
   Claude, run by GitHub Actions, reads it cold (see "Watchlist automation" below), so the file
   must stand alone:
   - a three-line thesis
   - for each item: what to check, which part of the thesis it tests, exact URLs, how often, a
     baseline (last known value and date), and what counts as significant
   - a fixed report format, which says "nothing new" explicitly
   - the number rules above.

   Leave out what `scripts/report.py` already covers (8-K items, Form 4s, earnings dates, prices,
   short interest). Focus on press releases, partner funding, news and sector data.
   Also write `research/<TICKER>/watch/<TICKER>_feeds.toml`, the queries the free check runs.
   Copy BFLY's, and dry-run it to tune `title_must` and the blocklist. Then write the owner's
   status page, `research/<TICKER>/<TICKER>_status.md`, on BFLY's model: a short verdict, one
   table row per watch item (where it stands, better or worse since the thesis, last change),
   recent changes newest first (about ten; older ones go to the detail file), and what's coming
   up. Its figures come only from the watchlist's baselines.
3. **When the owner brings findings back** (or a `watch` issue's report arrives):
   - check them and add them to the research notes
   - update the watchlist's baselines, and the status page in the same edit, so the two never
     disagree (the automated report never edits either)
   - set the matching `research/<TICKER>/watch/<TICKER>_seen.csv` rows to `baselined` or
     `dismissed`
   - close the issue.

   Run `git pull` first, because the workflow commits to `main`.

## Watchlist automation (2026-11-20)

`.github/workflows/watch-check.yml` runs on GitHub. **cron-job.org starts it** through the API
(workflow_dispatch, which begins within seconds), because GitHub's own schedule ran 4 to 11 hours
late from 2026-11-21 to 2026-11-23. The jobs (times in each job's own time zone):
- `now`: 6:30 am Pacific, Sunday to Friday, and 1:30 pm Pacific every day
- `weekend`: 7:00 am Pacific, Saturday
- `fast`: every 15 minutes from 6:07 am to 4:52 pm Eastern on weekdays

The cron-job.org token is a fine-grained GitHub token for this repo only, with Actions read and
write; it expires, so renew it before the date in `TODO.md`. GitHub's own schedule stays as a
backup for the three main runs (14:30 and 21:30 UTC, Saturday 15:17 UTC); a late backup run finds
nothing new, and a second report in the same slot is named `-2`, never overwriting the first.
The **fast lane** checks only sources marked `fast = true` in the feeds
file (BFLY: its press release feed and 8-Ks). Mark only sources that move the price within the day
and tolerate frequent requests (never Google News). Its reports are named by Pacific time
(`<TICKER>_<day>_0637.md`) and Claude treats them as `now` runs. All runs share one concurrency
group; a dropped waiting run loses nothing, since the seen-log is the record.

- **Free check:** `scripts/watch_check.py` reads every `research/*/watch/*_feeds.toml` (RSS,
  Google News RSS, EDGAR 8-K, Form D and earnings filings, EDGAR full-text search with Form D
  amounts, CourtListener docket entries through its API, and partners' news pages that have no
  feed, whose first read is logged as baselined), filters the results,
  and appends new items to `research/<TICKER>/watch/<TICKER>_seen.csv`. The status column runs
  `new`, then `reported`, then `baselined` or `dismissed`. Source failures and the W7 correlation
  go in `research/<TICKER>/watch/<TICKER>_watch_state.json`. Pure logic lives in
  `src/news_watch.py` and fetching in `src/feeds.py`.
- **Claude, only when something is waiting:**
  - The workflow opens an issue labelled `watch`.
  - It runs `anthropics/claude-code-action` (Opus, on the owner's subscription through
    `CLAUDE_CODE_OAUTH_TOKEN`) with `research/watch_agent_prompt.md`.
  - The report goes to `research/<TICKER>/watch/reports/<TICKER>_<day>_<am|pm|weekend>.md` and
    is posted on the issue.
  - Items are then marked `reported`. A failed report leaves them `new` for the next run.
- **Saturday:** the run also covers `notify = "weekend"` sources (routine court docket entries;
  rulings are sent the same day), any `[[weekend_only]]` checks with no free feed, and the W7
  correlation.
- **What Claude can't reach:** in the workflow Claude has only web tools, which can't send the
  SEC's `User-Agent` and are refused by Cloudflare and CourtListener's pages. Anything from those
  sites has to be fetched by the free check and handed over in the waiting items. Don't try to
  get past a site's bot blocking (from GitHub or the owner's PC); use its API or drop the check.
- **Repo secrets:** `SEC_USER_AGENT`, `COURTLISTENER_TOKEN` (a free CourtListener account's API
  token, 125 requests a day; also in `.env` for local runs) and `CLAUDE_CODE_OAUTH_TOKEN`.

## Data sources (free only)

- **SEC EDGAR** (`data.sec.gov` XBRL company facts and filings) is the source of truth
  for financials. EDGAR requires a `User-Agent` header with contact details: read it
  from the `SEC_USER_AGENT` environment variable, never hard-code a name or email, and
  stay under 10 requests/second.
- **Prices**: `yfinance` (unofficial, can break or rate limit; fail loudly, don't guess).
- **Company IR pages and press releases** for catalysts and guidance.
- No paid APIs. Ask before adding any data source that needs a key.

## Rules for numbers

- Never state a financial figure from memory. Every number comes from fetched data, with
  its source and period (for example "10-Q, quarter ended 2026-09-30").
- Always show the as-of date for prices and the filing date for fundamentals.
- If data is missing or stale, say so. Do not fill gaps with estimates unless they are
  labeled as estimates with the method shown.
- Small-cap data is messy: check for reverse splits, SPAC-era share counts, and
  restated figures before comparing periods.
- Output is analysis, not financial advice. Present risks alongside any bullish case.

## Code conventions

- Python 3.11+, virtual environment in `.venv`, dependencies in `requirements.txt`.
- Environment is Windows with PowerShell. The folder path contains a space, so quote paths.
- Layout as code is added:
  - `src/` reusable modules (data fetching, metrics, valuation)
  - `scripts/` runnable entry points that take a ticker argument
  - `data/` cached raw downloads (git-ignored)
  - `reports/` generated HTML: `index.html` (latest summary), `<TICKER>/<date>.html`,
    `_summary/<date>.html`
  - `tests/` pytest tests for metric calculations
  - `research/<TICKER>/`, one folder per company (`research/watch_agent_prompt.md` is shared):
    - `<TICKER>.md` a brief summary (about a page or two): the story, key numbers, scenarios,
      risks, next checks, with estimates and unverified items labelled. The owner reads it to
      look back, so keep it short.
    - `<TICKER>_status.md` the owner's one-screen view of where each watch item stands now.
    - `<TICKER>_detail.md` working, derivations and full sources. Read it and the summary before
      working on that company's assumptions.
    - `<TICKER>_watch.md` the watchlist the automated report reads (thesis, baselines, rules).
    - `watch/` the automation's files: `<TICKER>_feeds.toml`, `<TICKER>_seen.csv`,
      `<TICKER>_watch_state.json` and `reports/`.
- Cache downloaded data in `data/` and reuse it; don't re-fetch on every run.
- Keep fetching separate from calculation so metrics can be tested on saved data.
- Secrets and personal details go in `.env` (git-ignored), never in code.

## Commands

Run from the project root in PowerShell.

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # then set SEC_USER_AGENT in .env

# Tests
.\.venv\Scripts\python.exe -m pytest -q

# Reports: writes reports\index.html, reports\<TICKER>\<date>.html, reports\_summary\<date>.html
.\.venv\Scripts\python.exe scripts\report.py --open    # active tickers, then open in the browser
.\.venv\Scripts\python.exe scripts\report.py HUMA TMC  # ticker pages only; summary is left alone
.\.venv\Scripts\python.exe scripts\report.py --refresh # ignore cached EDGAR data and prices

# Daily run: Task Scheduler task "Stock analysis daily report", weekdays 1:15 pm Pacific
# (15 minutes after the US close). Runs report.py --refresh; output in data\logs\daily_report.log
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\daily_report.ps1

# Cash runway in the terminal: active tickers, specific tickers, or bypass the 24-hour cache
.\.venv\Scripts\python.exe scripts\runway.py
.\.venv\Scripts\python.exe scripts\runway.py HUMA TMC
.\.venv\Scripts\python.exe scripts\runway.py --refresh

# Evidence for scenario assumptions: starting revenue, guidance, contracts, burn, peers
.\.venv\Scripts\python.exe scripts\evidence.py BFLY

# Dilution: share count trend, overhang, offering filings, quotes on ATM/shelf programs
.\.venv\Scripts\python.exe scripts\dilution.py
.\.venv\Scripts\python.exe scripts\dilution.py HUMA --months 12 --sentences 20

# Watchlist news check (free; the GitHub workflow runs it): print what is new, change nothing
.\.venv\Scripts\python.exe scripts\watch_check.py BFLY --dry-run
.\.venv\Scripts\python.exe scripts\watch_check.py BFLY --mode fast --dry-run    # fast lane only
.\.venv\Scripts\python.exe scripts\watch_check.py BFLY --mode weekend --dry-run  # adds W7

# Path to profitability next to EV/sales: active and peer tickers, or specific ones
.\.venv\Scripts\python.exe scripts\profitability.py
.\.venv\Scripts\python.exe scripts\profitability.py BFLY CEVA
```

## What exists so far

- `src/edgar.py` fetches and caches EDGAR data: ticker to CIK, XBRL company facts,
  the filing list, and filing documents (documents are cached permanently).
- `src/metrics.py` holds pure calculations, including turning year-to-date cash flow
  totals into single quarters.
- `src/runway.py` combines them into cash runway.
- `src/dilution.py` computes share count trend, potential shares, financing cash flow,
  and lists registration and prospectus filings.
- `src/filing_text.py` extracts prose sentences from filing HTML, used to quote what a
  10-Q says about ATM, shelf and equity line programs.
- `src/financials.py`: revenue, gross margin, operating expenses, net income and debt,
  with year-over-year and four-quarter growth. Flags quarters whose gross margin is far
  from the usual level (likely one-off charges). `filing_notes.csv` (ticker, period_end,
  note, cost_of_revenue_charge, source_url) holds what we read in the filing about a
  quarter; the revenue section shows it in place of the "check that filing" flag, and
  with a charge amount it adds the margin excluding the charge, labelled as an estimate.
- `src/ixbrl.py` reads every tagged number, with its period and dimension members, out of
  a 10-Q or 10-K document (inline XBRL). This is how to get values that company facts
  leaves out. `src/streams.py` uses it to split revenue into streams. Which split to show
  is set per ticker in `revenue_streams.csv` (ticker, axis, title, merge). `merge` joins a
  member the company renamed (`old:Member=new:Member`; separate several with `;`).
  Streams keep the filing's order so their colours stay put. The revenue section shows a
  stacked chart, growth for the quarter, year to date and four quarters, and gross margin
  per stream when cost of revenue is tagged on the same axis. To find a company's axes,
  parse its latest 10-Q and list the revenue facts that have dimensions.
- `src/prices.py` fetches daily bars and Yahoo quote data with yfinance (12-hour cache in
  `data/prices/`, raises `PriceError` on any failure). `src/technicals.py`: moving
  averages, 52-week range, returns, volume, RSI, short interest, consecutive closes under
  $1. A session still trading is left out, so figures use the last completed close.
- `prices.revenue_estimates` fetches Yahoo's analyst revenue consensus. `src/estimates.py`
  then picks the fiscal year ending closest to a year after the latest quarter, so periods line
  up across companies. That is FY2027 for December years and the year ending June 2027 for ARAY.
  Zeros mean no coverage, and a non-dollar estimate is skipped.
- `src/valuation.py`: market value, fully diluted value, enterprise value, EV/sales,
  EV / next year's consensus sales, EV/gross profit and price/book today. The current share count comes from the newest
  filing's cover page, summed across share classes (`ixbrl.cover_shares`).
- `src/scenarios.py`: bear/base/bull cases at each horizon (default 3 and 5 years), per
  revenue stream or for the whole company. Assumptions live in `assumptions.toml` (format
  explained at its top). Each stream gets either a start plus growth, or an explicit
  `revenue_by_year` path for lumpy contract revenue, and an exit EV/sales multiple
  (0 = no exit value). Each case sets its breakeven year, a raise discount, a note and
  sources, and optionally `annual_burn` ($M a year at the start; the default is the
  four-quarter average, which a one-off inflow can distort). Mistyped keys, missing cases and stream names that don't match the split stop
  the report with an error. Tickers without an entry get mechanical placeholders,
  labelled on the page. An optional per-ticker `caveats` list names the model limits that change
  how the figures should be read; the page shows it in a "Read before the figures" box.
- `scripts/evidence.py TICKER` prints the research material for assumptions:
  - starting revenue per stream (four quarters, year to date annualized, latest quarter × 4)
  - guidance blocks from earnings releases (8-K item 2.02, exhibit 99.1, found through the
    filing's `index.json`)
  - contract and backlog sentences from the latest 10-Q, and material agreements
    (8-K item 1.01)
  - burn by quarter, share classes, and peer multiples.
- `src/profitability.py`: path to profitability over four quarters against the four before.
  It covers:
  - operating margin and its change
  - margin before stock pay (a common yardstick in place of each company's own "adjusted EBITDA";
    depreciation stays in)
  - free cash flow
  - stock pay as a share of revenue
  - incremental margin, and opex growth against gross profit growth
  - share growth and the Rule of 40
  - a straight-line breakeven extrapolation.

  One-off charges recorded in `filing_notes.csv` are added back to gross profit and operating
  income. The ticker page's "Path to profitability" section (after revenue) shows:
  - these figures, with charts of operating income and free cash flow by quarter
  - a comparison table sorted by EV/sales.

  The summary page adds operating margin and free cash flow columns. `scripts/profitability.py`
  prints the same comparison in the terminal.
- `src/ownership.py` parses Form 4 XML into insider trades and splits sales into
  discretionary, 10b5-1 plan and sold-to-cover-taxes (from the footnotes). It also reads
  new-format Schedule 13D/G XML for 5% holders.
- `src/catalysts.py`: hand-researched events from `catalysts.csv` (date as 2027-03-15,
  2027-03 or 2027-Q1, each with a source), the next earnings date from Yahoo, the SEC
  deadline for the next 10-Q/10-K, and 8-K items named and flagged by importance.
- `src/report.py` assembles the ticker page and the summary. `src/sections.py` renders
  every section after runway and dilution, and `src/html_kit.py` holds formatting and HTML
  helpers. `scripts/report.py` is the main entry point and writes the files. Reports are
  dated by run day: a same-day rerun overwrites, earlier days are kept as history, and
  they are tracked in git. New analysis sections belong in the per-ticker page (add the
  anchor to `SECTIONS` in `report.py` for the nav), with a column in the summary.
- `src/charts.py` builds the charts (runway timeline, columns, lines with optional
  neutral reference lines such as the 50- and 200-day averages, hover slices for dense
  series) as HTML and CSS.
  `src/assets/report.css` and `report.js` are embedded into every page, so reports
  open offline; do not add external fonts, scripts or stylesheets.
- Report conventions: every figure shows its source and date, every chart has a table
  view, all outside text goes through `e()` in `src/html_kit.py`, and chart colours
  come from the CSS variables (light and dark values, both validated for colour-blind
  safety). After changing layout, screenshot the pages with headless Edge and look.
- XBRL tag choices live at the top of `runway.py`, `dilution.py` and `financials.py`.
  When a company's numbers look wrong, check which tags it uses first.

## Next: company-specific work

The general calculations are done. Still open, per company, with the owner:
- Fill `catalysts.csv` from IR pages and press releases.
- BFLY scenarios are written (decided with the owner 2026-11-15/16; reasoning in
  `research/BFLY/BFLY.md`, open items in `TODO.md`).
  - Results (prices 2026-11-13): bear $0.31, base $1.22, bull $3.15 a share at 3 years, all below
    the $6.08 price. Today's EV is above even the bull case.
  - Revisit after the 2026 10-K (late Feb 2027):
    - Core's four-quarter start (the `ttm` start takes over automatically)
    - Midjourney's remaining contracted revenue
    - Q4 2026 burn and receivables.
- HYPR's scenario assumptions are still to write, as one business, starting from
  `scripts\evidence.py`.
- Comparison tickers (chosen 2026-11-15, `peer` in watchlist.csv): LUNG, SGHT, ARAY, PRCT,
  IRTC and STXS for device multiples (read against growth, not averaged), and CEVA alone for
  Embedded's bull case (chip design licensing; IDCC and RMBS were rejected as poor fits).
  HYPR's own peers wait until BFLY's scenarios are done; NNOX (20-F filer) is untested.
- Read the filings behind flagged items, for example HYPR's September 2026 item 3.01 notice
  and ATM use. Done: BFLY's Q4 2025 operating cash flow (+$9.0M) includes the one-time $15M
  Midjourney fee, "paid upon entering into" the agreement in November 2025 (2025 10-K,
  filed 2026-02-27). The same 10-K says $63.2M of the $99.6M remaining performance
  obligations was Midjourney's, about 56% to be recognized in 2026; later 10-Qs do not
  split it out.

Record what a filing explains in `filing_notes.csv`, with its source. Done so far: BFLY's
Q3 2025 gross margin (inventory write-down).

## Known data limits

- BFLY first split revenue into Core and Embedded in its Q1 2026 10-Q, with 2025 quarters
  as comparatives. No filing gives Q4 2025 or anything earlier by business line, so its
  four-quarter figures stay n/a until the 2026 10-K; the page uses nine-month growth
  instead. Its product and service split goes back to 2023.
- When a filing tags gross profit and cost of revenue but no revenue total that company
  facts carries (CEVA's 2025 10-K), revenue for that period is their sum, noted on the page.
- EDGAR company facts leave out values reported per share class or per instrument. The
  current share count is therefore read from the newest filing's cover page (BFLY and
  HYPR tag Class A and Class B separately). It is dated a few days before the filing, so
  shares sold since then are still missing. The share count trend still uses quarterly
  weighted averages. HUMA's potential shares are warrants plus options only.
- Equity raise proceeds are not tagged consistently (HYPR and HUMA use custom tags), so
  dilution reports net financing cash flow, which mixes equity and debt.
- Remaining ATM or shelf capacity is not available as data. The dilution script quotes
  the relevant sentences from the latest 10-Q or 10-K; read them, and do not compute
  capacity from them without checking the filing.
- Shelf size comes from SEC fee-table data, which only some filings carry.
- The SEC returns HTTP 403 without a `User-Agent` containing contact details, so
  nothing fetches until `SEC_USER_AGENT` is set in `.env`.
- BFLY tags no debt in XBRL, so the page says "None tagged". Confirm on the balance sheet
  before treating it as zero.
- Scenarios value shares at today's basic count plus shares sold to cover burn; options
  and warrants are not counted, and nothing is discounted back to today. The burn path is
  a straight line to the breakeven year, so a revenue path that ends (such as an
  Embedded contract) does not raise burn by itself: set the breakeven year to match.
- yfinance is unofficial. Short interest, institutional ownership, earnings dates and analyst
  revenue consensus come from it and are labelled.
  - Consensus can rest on one to three analysts.
  - The page shows the analyst count and notes single-analyst or widely spread estimates.
  - ARAY has none. Yahoo's earnings date often lags; a past date is dropped.
- Form 4 parsing covers non-derivative trades only (option grants are left out).
  Schedule 13D/G filings before 2025 are free-form HTML, so only the link is shown.

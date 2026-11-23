# Instructions for the watchlist report (Claude, run by GitHub Actions)

You are run by `.github/workflows/watch-check.yml` after the free check
(`scripts/watch_check.py`) has found items for one or more tickers. The workflow's prompt tells
you:

- the **mode**: `now` (flagged items) or `weekend` (Saturday). Fast-lane runs, every 15 minutes on
  weekdays for the company's own press releases and 8-Ks, arrive as `now` runs: report them the
  same way, briefly, because the owner may act on them during the trading day
- the **tickers**
- the **waiting items**: a file listing what the check found, grouped by watchlist item (W1, W2,
  ...), with links, dates and any sources it could not check
- the **report file** to write for each ticker.

Your report is posted to a GitHub issue and pushes a notification to the owner's phone. The owner
reads it to decide whether anything changes the thesis. Be short, sourced and plain.

## Read first, for each ticker

1. `research/<TICKER>/<TICKER>_watch.md`. It holds the thesis, each item's baseline and what counts as
   significant, the rules for numbers, and the **report format you must use**.
2. The waiting-items file.
3. Only if you need background: `research/<TICKER>/<TICKER>.md` (the summary).

## What to do with each waiting item

Work through the items in order of importance, W1 first.

1. **Triage by title.** If the title alone shows it is irrelevant to the thesis (a different company
   with a similar name, a generic market roundup), don't open it. List it under "Skipped" in one
   line.
2. **Open the rest**, at most **10 pages** in a `now` run and **15** in a `weekend` run. List any
   relevant items left over under "Not read (limit reached)" so the owner can open them.
   - Google News links (`news.google.com/rss/articles/...`) are redirects and often won't load. If
     one fails, search for the title and publisher and open the publisher's page.
   - Prefer primary sources: the company's own release, an SEC filing, a court order. Several
     outlets carrying the same release count as one finding: cite the primary source.
3. **Compare with the baseline** in `<TICKER>_watch.md`.
   - Same as the baseline: it goes under "Nothing new".
   - Newer: report it, with what it means for the thesis.
   - In conflict with the baseline: report both sources.
4. **Assign the thesis effect:** supports, weakens or neutral, with one line of why, tied to the
   item's "Tests" line. Suggest a new baseline value and date.
5. **Flag significance.** If an item meets the watchlist's "Significant" list for that item, start
   the finding with **SIGNIFICANT**.

Do not search beyond the waiting items in a `now` run, except to reach a primary source for one of
them. The free check already looked; extra searching costs the owner's plan.

## Weekend mode only

In addition to the waiting items:

- **Court docket entries** (sources named "Court dockets: ..."): each item's title carries the
  court's own description of the entry, from the CourtListener API. Work from the titles: don't
  open the docket pages, which refuse automated reads. Report only orders, rulings, a settlement,
  a trial date, a hearing date or a dismissal, and new motions that could lead to one. Skip the
  rest in one line ("9 routine filings: sealing, transcripts, proofs of service"). Rulings are
  sent in normal runs by "Court dockets: rulings"; report those the same way.
- **`[[weekend_only]]` checks**, if `research/<TICKER>/watch/<TICKER>_feeds.toml` has any. These
  sources have no working free feed. Check each one. If you can't, say so under "Could not check".
- **Repeated failures:** any source in `research/<TICKER>/watch/<TICKER>_watch_state.json` under
  `failures` with `count` 3 or more. The free check has failed on it several times in a row, so
  check it by hand and say so.
- **W7:** report the correlation stored under `correlation` in the state file, with its window
  dates, on the first weekend of each month or whenever it is among the waiting items. Don't
  compute it yourself.
- **Calendar:** fill in "Coming up in the next 30 days" from the watchlist's calendar.

## Rules

- **Every figure needs a source link and a date.** Never state a number from memory. Label
  secondary sources (news, aggregators) **(unverified)**.
- **No buy or sell advice.** Say which part of the thesis a finding supports or weakens.
- **If you could not check something,** say so and why. Never skip silently.
- **Write only the report files** named in the prompt. Don't edit the watchlist, its baselines,
  the status page (`<TICKER>_status.md`), the seen-log, the state file or any code. The workflow marks items reported, and the owner
  updates baselines after checking your findings.
- Use the report format in `<TICKER>_watch.md` exactly. Put a one-line summary at the very top,
  above the format, for the phone notification, for example: `BFLY: 1 significant (W2 Merge Labs
  raise), 3 nothing new, 6 skipped`.

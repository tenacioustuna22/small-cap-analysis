BFLY: 0 significant, 0 new, 5 docket entries unreadable (CourtListener blocked; no ruling found in news), 2 weekend checks could not be done

BFLY watch report, 2026-11-21 (weekend)
Baselines read from BFLY_watch.md as of 2026-11-18 (W2, W4, W5 and W6 rows recorded 2026-11-20 and 2026-11-21)

Nothing new
- W3, the lawsuit: I could not read what the five waiting docket entries are (see "Could not check").
  A news search for a ruling, injunction, settlement or trial date in Disney v. Midjourney
  (C.D. Cal., lead case 2:25-cv-05275, Judge Kronstadt) or EVOX Productions v. Midjourney found
  nothing newer than the baseline. The latest items found date from July 2026 and cover the
  discovery dispute over the studios' own AI use, which the baseline already records. One
  background detail not in the baseline: the judge set a private-mediation deadline of
  2026-08-19, and no settlement has been reported since
  (https://chatgptiseatingtheworld.com/category/disney-v-midjourney/, unverified). The
  "News: Midjourney lawsuit" feed, which flags rulings in the news, has logged none.
  - Docket volume, from the CourtListener feed: the Disney docket received entries 264 to 275
    and two minute entries between 2026-11-17 and 2026-11-21. The EVOX docket received entries
    34 and 35 on 2026-11-20. None of them has a document on CourtListener (no one has bought
    the PDFs from PACER), and the feed shows no descriptions.
  - About a dozen filings in one week suggests active discovery or motion practice. That is a
    guess from the volume, not from what the entries say.
- W1, W2, W4, W5, W6: none of the waiting items concern them.
- W7: not due. This is not the first weekend of the month, and W7 is not among the waiting
  items. The state file holds +0.63 for 2026-08-28 to 2026-11-20, for reference.

Could not check
- W3, the court docket: CourtListener returned HTTP 403 for both docket pages (Disney
  https://www.courtlistener.com/docket/70513159/disney-enterprises-inc-v-midjourney-inc/ and
  EVOX https://www.courtlistener.com/docket/73698332/evox-productions-llc-v-midjourney-inc/).
  Its API needs a login (HTTP 401), and the search feed shows no entry descriptions. So I
  cannot say whether entries 266 to 275 (Disney) or 34 and 35 (EVOX) include an order. The
  owner should open the two docket pages in a browser. The free check's own fetch also timed
  out today (one failure, below the threshold of three for a manual check).
- W3, the Midjourney Medical blog ([[weekend_only]]): HTTP 403 (Cloudflare), as expected from
  the feeds file. No new post could be checked.
- W2, the EDGAR full-text Form D search ([[weekend_only]]): this check is due on the first
  weekend of the month, so not this one. A trial request failed anyway: SEC_USER_AGENT was not
  set in this step's environment, and efts.sec.gov returned HTTP 403. The December first-weekend
  run will need the variable.

Coming up in the next 30 days (from the calendar or news; weekend runs)
- none in the calendar. The next dated entries are big tech's Q4 results in late January to
  early February 2027.

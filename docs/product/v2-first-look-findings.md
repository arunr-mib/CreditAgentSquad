# v2 first look on the merged build (20 November 2026)

Screens: `docs/product/screens/v2-squad-home-night.png`, `v2-stripple-thread-night.png` (merged branch, innovation book, Priya, Night, 1440 px). All 14 browser journeys pass; these are quality findings against the demo's bar, not test failures.

## Bugs (fixed 20 Nov: ad4e591, 0f49333, 7a2d71c)
1. **"Runway falling" fires for Ferrogate**, which is cash-flow positive (runway not meaningful), and for most clients. A not-meaningful runway must never feed `runway_falling`; check the window logic against the truth's signal list.
2. **Duplicates in the briefing**: a signal and the work item raised from it show as two rows ("Signal: runway below watch" and "Dataflake Inc: runway below watch · waiting for you"). Show the work item only when one exists for the signal.
3. **Amounts printed raw** in titles ("equity round of 15,000,000.00"): titles must render figures through facts/formatting ("$15.0M"), never raw strings.

## Experience gaps (Phase 4b)
4. **A thread opens on old documents** with identical seed timestamps; the story (held MRR file, the new-line question, the draft) is not at the top. Open at what's new and group arrivals ("6 documents arrived for October").
5. **"16 need you"** is too many for one analyst's morning: signals the analyst can't act on should be listed, not counted; group by client.
6. **Nav shows 20 initial-letter circles** when collapsed (unreadable; several share a letter). Show only "Open cases" with names on hover/expand, or the top few.
7. Wording: "Mrr report" → "MRR report"; document types in plain words; "bank statement" vs "Account statement" naming.

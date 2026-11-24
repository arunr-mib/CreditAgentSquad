# v2 4b walkthrough (22 November 2026)

What was checked, by whom, and what is unverified. Screens: `docs/product/screens/v2-4b-*.png` (analyst Priya Raman for the thread, home, portfolio and client file; officer for Approvals; administrator for Oversight; Night, 1440 px, scale 2, from `scripts/screenshots.mjs`, fresh seed on a scratch database).

**Honest limit:** this was not a person's pass. The 1000 px and the officer (Helen) walks were made by the journeys and the a11y script, not by eye. Of the six screenshots I looked at only `v2-4b-home.png` and `v2-4b-client-file-covenants.png`; the other four were captured and not inspected by eye.

## First-look findings (`v2-first-look-findings.md`)
| # | Finding | State | Evidence |
|---|---|---|---|
| 1 | Runway falling fires for cash-flow-positive clients | Fixed (ad4e591); not re-seen on screen | the stand-in run closes Ferrogate with no exception; journeys check unmeasured runway against the API on every client |
| 2 | Signal and its work item listed twice | Fixed, seen | journey "briefing lists each thing once" passes for both roles; home shows each client's item once |
| 3 | Raw amounts in titles | Fixed, seen | journey checks no `1,234.00` in any briefing title (both roles); home shows "$15,000,000" |
| 4 | Thread opens on old documents | Fixed (journeys: `?case=` focus for every open case, both roles); the opening position of a thread with only documents was not looked at by eye | |
| 5 | "16 need you" | Fixed, seen | home says "8 need you" with a separate Watching list, one row per client |
| 6 | Nav shows 20 initial circles | Fixed, seen | collapsed nav shows the mark with a count, three icons and "7" for open cases |
| 7 | "Mrr report", document-type wording | Fixed, seen | home reads "MRR report for October 2026", "Bank statement" |

## New, not fixed here
- **Client file tab underline.** On `v2-4b-client-file-covenants.png` both "Overview" and "Covenants" show the active underline. Possibly a focus or transition artefact of the capture (the script waits for the lists, not for a transition), not confirmed. Check on the owner's screen.
- **Home row titles repeat the client.** "Dataflake Inc · Dataflake Inc: runway below watch" (also Nimbusfield, Lumora, Stripple). The title written by code starts with the client name; the row adds it again.
- **Stripple rows end in an ellipsis** ("names no company and shows 2025, not Oc...") on home; the full text is on the case.
- Full-axe run (`pnpm a11y`) is clean (0 serious or critical) on 17 pages; the keyboard pass reached 11 of 21 tab stops on the review room and 37 of 38 on home, 24 of 25 on Packages (every one reached has a focus ring; the unreached ones were not investigated).

## Final fix wave (22 November 2026)
- **Tab underline: fixed** (a real defect, not a capture artefact: TanStack's prefix-active Link). One tab is current on every view; a component test pins it.
- **Home and Approvals rows: fixed.** The server serves each title's subject without the client's name in front; rows wrap to two lines; a routed view wraps in full. Journey "rows name the client once, and at 1000 px every Approvals subject is shown unclipped" passes for analyst and officer. Stripple's held-export row now reads "a file names no company or month: which client and month?" (no year in the title).
- **Keyboard reach, investigated (M16).** On a fresh seed, tabbing from the top at 1440 px (scratchpad probe, same element query as `scripts/a11y.mjs`): review room 18 of 21, Packages 24 of 25, home 17 of 38. Every element not reached is expected, none points to a focus trap:
  - review room (3) and Packages (1): the hidden native `<select>` that each styled select keeps for forms (`tabindex=-1`); the person tabs to the styled select's own trigger button instead (not checked one by one here);
  - home (21): rows inside collapsed `<details>` groups (each client's Watching group, Recently decided, What Squad did overnight); a closed `<details>` hides its rows from the tab order by design (opening a group was not tested here). The earlier "37 of 38" was probably taken with groups open (not confirmed).
- Not re-checked by eye: the screenshots were not recaptured in this wave.

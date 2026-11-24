# v2 usability findings

`SYNTHETIC - FOR DEMONSTRATION`

> `SITE` = `https://credit-squad.vercel.app` (or `https://credit-squad-v2.vercel.app`).

**State: the owner's self-guided walk was held on 23 November 2026 and is triaged below ("Owner's walk"). Formal sessions were dropped by the owner's decision of 23 November.** The text that follows was written for the five sessions: Filled in after the five sessions from the observation sheets (by the facilitator, or by the controller from the sheets with the facilitator checking). Kit: `docs/product/usability/` (consent note, facilitator script, observation sheet, session log).

| | |
|---|---|
| Session dates | |
| Sessions held | 0 of 5 (4 analysts, 1 credit officer) |
| Build commit on the hosted site | |
| Address | `SITE` |
| Agents | off (no model key), unless the owner turned them on (Task 17) |
| Book | innovation book, reloaded fresh before each session, renamed clients |

## Triage rules

- **Severity:** blocker (could not finish, or was misled about a figure or a decision); major (finished only with help, or a wrong belief corrected later); minor (slowed); cosmetic (wording or look, no effect on the task). The note-taker proposes; triage sets it.
- **Observed, not interpreted:** "What happened" says what the participant did and said. Causes and fixes go in "Proposed fix".
- **Every blocker and major is fixed before v2 is called done**, each in its own commit (`fix(p5): …`) with a test. Where a rule is involved (own clients only, the router cannot decide, what a return gathers), the test is an API test, not only a screen test (`docs/lessons/a-second-may-act-rule-drifts-from-the-engine.md`).
- **After each fix:** a v2-only redeploy with `scripts/hosted/deploy-v2.sh`; re-run `pnpm e2e:smoke` and the read-only journeys against the hosted v2; repeat the frozen-site after-check after the last redeploy. The two frozen sites are never touched.
- **Minors and cosmetics:** the owner decides (fix now, backlog, or not changing).
- **v2 is called done** only when no blocker or major is open **and** the owner has read this file.
- **Lessons:** each new lesson is also written to `docs/lessons/` (one file per lesson, summary on the first line).

## Findings

| ID | Session(s) | Task | What happened (observed, not interpreted) | Severity | Seen by (n of 5) | Proposed fix | Decision | Fix commit | Re-checked |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

## Blockers and majors (fixed before v2 is done)

- None yet.

## Minors (owner decides)

- None yet.

## Not changing (with reason)

- None yet.

## Lessons

- None yet.

## Owner's walk, 23 November 2026

- **Who and how:** the owner, with a browser agent (a cloud Chromium, version not recorded, window 1007 px), following `docs/product/usability/self-guided-walkthrough.md` as Priya Raman, Helen Strand and Dana Whitfield. 15 of 16 steps completed. The agent read the page's accessibility text, so two findings concern text a sighted person does not see.
- **Verdict (owner):** the loop works end to end (briefing, thread, evidence, route, return, gathering, decision); trust is where it fails. "Do not trust a figure here without opening its source, and the sources often fail."
- **Triage (owner with the controller, 24 November):** every finding was checked against the code and the hosted data before it was accepted. Order agreed: (1) make the explanation visible, (2) say what really happened, (3) plain words and hierarchy, then a look-and-feel pass. Three reported blockers were downgraded with the owner's agreement; one was not reproduced.
- **Build walked:** 97e9ca8 on `https://credit-squad.vercel.app`, agents off.

Severity is the triaged one. "Checked" says what the code or data showed.

| ID | What was reported | Checked | Severity | Batch | State |
|---|---|---|---|---|---|
| W1 | Datamarrow: certificate says $6.1m unrestricted cash, Squad says $4.6m; the $1.5m gap has no visible source | Real. `bs.cash_restricted` is a stored fact the calculation does not use; no screen showed it | blocker | 1 | Fixed: "Not counted in this calculation" on the calculation's source |
| W2 | Source pages "could not be drawn" (Datamarrow's certificate) | The PDF is valid. The PDF library's modern build needs methods only the newest browsers have; nothing retried | blocker | 1 | Fixed: build for older browsers, "Try again", and a smoke check that a page draws |
| W3 | Cindrel's held file cannot be opened; nothing says its year is wrong | Real. It is a workbook, drawn as a PDF page; the reason was recorded nowhere | blocker | 1 | Fixed: sheet shown as stored text with a download; the case says why in words |
| W4 | Headroom on a client's button differs from its trend list (-5.2% vs -0.1%) | Real, in the list read to screen readers only: a fraction shown as a percentage | major | 1 | Fixed |
| W5 | "Chaser sent" says the reminder has gone to the borrower; nothing says it was not emailed | Real | major | 2 | Fixed: "I sent the reminder email"; Squad emails nothing |
| W6 | The reminder draft gives one due date for two items due on different days | Real: the earliest date was printed for all | major | 2 | Fixed: each item with its own date |
| W7 | A draft on Calvere Health showed "Sent by Tomas Keller" before the walk; step 6 had no draft to edit | Real and a rule gap: the own-clients rule did not cover drafts, so another analyst's sign-in sent it | major | 2 | Fixed: the engine's rule on start, edit and send; the thread says why |
| W8 | Review meeting banner says sheets were attached when none were | Real: the words were fixed text | major | 2 | Fixed: worded from the server's count |
| W9 | Nothing on Tavernel Grid says it is Tomas Keller's client or that Priya can only look | Real | major | 2 | Fixed: analyst named on thread and file; the engine's refusal shown |
| W10 | "Dana Whitcombe" and "Ruth Okafor-Bell" appear beside Dana Whitfield and Ruth Calloway | The book's documents name them (relationship manager, approving officer); the seed made them workspace users | minor | 2 | Fixed: kept on the record, inactive: no sign-in, never offered in Send to |
| W11 | Ask Squad box says "No model key is set for this deployment" | Real: jargon; "agents are off" appears nowhere | minor | 3 | Fixed: "Agents are off on this site", in the server's words, wherever Squad cannot answer or run |
| W12 | Why an analyst cannot decide a breach is said only after she routes it; the case says "With the credit officer" before it is sent | Real | minor | 3 | Fixed: the case says a credit officer decides it and that it is not yet sent; the send form says the decision is not hers |
| W13 | Briefing lists an overdue report above runway-below-watch clients, with no reason | By design (kind before severity) and unexplained | minor | 3 | Fixed: most serious first, then kind; the page says so |
| W14 | Tavernel's Signals repeat one line about 24 times | 27 distinct signals shown without covenant or period; old ones never close | minor | 3 | Fixed: one line per rule and covenant with the count and range of periods; each period on request. Old signals still never close |
| W15 | Package counts 993, 1,004 and 1,018 do not agree | Three honest counts of different things, badly labelled | minor | 3 | Fixed: each count labelled for what it counts |
| W16 | Stamps look future-dated; thread times differ from received dates | Correct UTC, seen from US Pacific; the thread uses local time and the file UTC; seeded thread messages carry the load time | minor | 3 | Fixed: thread times in UTC, saying so, like the file; a document shows its received date beside when it was put on file |
| W17 | Period label "31 Oct 2026 · 31 Oct 2026"; a monthly September shown as "Q3 2026" | Real | minor | 3 | Fixed: the date once; "period ended" where the screen does not know monthly from quarterly |
| W18 | Helen's Return button looked disabled but submitted | It was enabled; the secondary style is pale. Downgraded from blocker | minor | 3 | Fixed: a stronger button, and a line saying what is missing while it is disabled |
| W19 | The month picker would not take clicks | The browser's own month control. Downgraded from blocker | minor | 3 | Fixed: month and year lists |
| W20 | Sidebar is icons only at about 1007 px; "Open cases: 8 clients" counts clients | Collapsed at every width until opened; the label is wrong | minor | 3 | Fixed: open from 960 px unless the person folded it; "Clients with open cases" |
| W21 | The Squad-asks "Why" field appears only after Remember is ticked, and Confirm is disabled without saying why | Real | cosmetic | 3 | Fixed: the label says a reason will be asked; a line says why Confirm is disabled |
| W22 | "How I got here" is empty | Expected on a seeded book (no agent ran); the words do not say so | cosmetic | 3 | Fixed: the words say no agent ran on the case |
| W23 | Case detail sits under the Ask box; "Opening the case." lingers | The composer is pinned to the bottom of the window; the words are a loading state | cosmetic | 3 | Fixed: only the thread's own Ask box is pinned; "Loading the case." |
| W24 | Walk-through step 15 cannot be done; step 6 points at the wrong draft | The product is right (an officer returns only a case sent to her); the walk-through is wrong | n/a | 3 | Fixed: steps 6, 7 and 15 rewritten |
| W25 | Lists and counts did not refresh after an action until reload | Not reproduced: the code refreshes after every action and every four seconds. To be watched live | n/a | | Not reproduced |
| W26 | Sign-in filled the email with a trailing comma | Nothing in the product sets or stores the email: the browser agent's fill. Dropped from the product list with the owner's agreement | n/a | | Not a product finding |
| W27 | Kestrel Bay: a view quoting 4.90x against 4.00x by Ruth Okafor-Bell | Not in the hosted data, the seed or the code; no screenshot was kept. Withdrawn by the owner | n/a | | Unreproduced |
| W28 | Look and feel: no hierarchy for priority, placeholders, no filter on Documents, "a functional prototype" | Accepted as a direction, not a defect list | n/a | after 3 | Open: one design pass after the trust fixes |

Found while checking, not reported: the hosted smoke test fetched a source PDF but never drew it, so W2 passed every gate (now checked in the browser).

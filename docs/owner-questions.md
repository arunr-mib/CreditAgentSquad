# Questions for the owner (collected while you were away)

Each has the decision taken in the meantime; overrule any and I'll rework.

1. **MMAS reference for spreading templates.** I mapped every line of both templates to the conventional sections of a standard bank spread (the structure tools like Moody's MMAS use), using only public section names. If you have licensed MMAS line codes you want matched exactly, share the list and I'll add a code-level mapping. *Taken: generic section mapping.* **Owner (20 Nov): no licensed MMAS version; keep the generic mapping.**
2. **DSCR for startups.** Added for venture borrowers with the same formula as today. A startup with negative EBITDA shows a negative DSCR (a breach); one with no debt service can't be tested. *Taken: as described.* **Owner: yes.**

## Answered

- Squad experience spec, open questions: product name "Credit Squad" on screen (for now); client file redesigned; Night for analysts, Warm paper for officers. Recorded in the spec, section 15. **Owner: yes.**

## Added while you were away (Phase 1 build)

3. **Slipped funding round: what can the officer decide?** A round that passes its expected close raises a high-priority item offering "reviewed" or "escalate to committee", outside the monthly cycle. *Taken: those two options.* **Owner: question unclear.** Reworded: when a startup's expected funding round passes its date without closing, which responses should the alert offer? Proposed (industry practice), unless the owner says otherwise: (1) ask the client for a new timeline (Squad drafts the email; default), (2) note and keep watching, (3) reserve rights, (4) escalate to the credit officer or committee. **Owner (20 Nov): agreed, these four.**
4. **"Runway falling three months running".** Implemented as three successive monthly declines (four monthly figures). *Taken: as described.* **Owner: yes.**
5. **Monthly vs quarterly packs.** A pack whose heading says one/two/four/five/seven/eight/ten/eleven months, or "month ended", is filed as monthly financials; three/six/nine months stay quarterly interim statements. *Taken: as described; the Intake agent can still disagree and a person resolves it.* **Owner: yes.**
6. **Startup DSCR deductions.** Startups have no tax-paid or distributions lines, so a DSCR covenant that names those deductions on a startup can't be tested (shown as missing data). *Taken: as described.* **Owner: yes.**
7. **A cash-flow-positive startup whose certificate says it's not in compliance.** Runway is "not meaningful", so the bank's result is compliant; the certificate's own runway figure is ignored, but its "not in compliance" flag is still reported as a disagreement. *Taken: as described.* **Owner: agreed.**

## Standing approvals (owner, 20 Nov)

1. Phase plans are pre-approved: each plan is written, the owner is told, and building starts after a 10-minute objection window.
2. Live evaluation run in Phase 3 approved up to about $15 (estimate), once the stand-in gate passes and the answer key is signed.
3. The owner will sign the new answer key; it will come as one short table.
4. Phase 4 (experience) runs in parallel with Phases 2–3 in a separate worktree.
5. The test suite may be parallelised (dev-only `pytest-xdist`).
6. Phase 5 hosting pre-approved: a new Vercel project and a new `squad2` schema in the existing Supabase project, free tiers.
7. The owner will start recruiting 4 analysts and 1 credit officer for the usability sessions.
8. Git tags: approved, then skipped by the owner (the session cannot push tags). The pre-v2 version is commit 2292b38.

## Waiting for you (end of Phase 1, 20 Nov)

1. **Start Phases 2 and 4?** Phase 1 is done and verified. I paused before the two builds to stay within "not much beyond $10 while I'm out": Phase 2 is 10 tasks and Phase 4a is 15, each built and reviewed by separate agents. Say "go" and both start (Phase 4 in its own worktree).
2. **Names to check against real companies** before anything is shown outside the team. No web search was done; the table says what to check, not what was found. Check Stripple, Tessaract, Dataflake, Veridia, Halcyon and Quillon first. *Taken: names stay as the spec lists them.* **Owner: to check.**

   | Kind | Name | Where | Check first because |
   |---|---|---|---|
   | company | Dataflake Inc | Data infrastructure | data-infrastructure names are crowded |
   | company | Lumora Health | Digital health | - |
   | company | Brightvane Energy | Climate hardware | - |
   | company | Mosswell Robotics | Robotics | - |
   | company | Halcyon Grid | Energy software | a common word used by many companies |
   | company | Quillon AI | Applied AI | close to other 'Quill' product names |
   | company | Kelvra Bio | Biotech tools | - |
   | company | Orbitline Systems | Space software | - |
   | company | Stripple Tech | Fintech infrastructure | close in sound to a well-known payments company |
   | company | Veridia Payments | Payments | close to 'Veridian', used by several companies |
   | company | Tessaract Labs | Developer tools | a spelling variant of a common word used by many products |
   | company | Pellucid Sensors | Industrial IoT | - |
   | company | Corvane Analytics | B2B SaaS | - |
   | company | Nimbusfield Security | Cybersecurity | - |
   | company | Tidewell Medical | Medical devices | - |
   | company | Ferrogate Cloud | Cloud infrastructure | - |
   | person | Imogen Farrow | chief financial officer, Dataflake Inc | - |
   | person | Tobias Wenlock | chief financial officer, Lumora Health | - |
   | person | Odalys Prentiss | chief financial officer, Brightvane Energy | - |
   | person | Reuben Castellane | chief financial officer, Mosswell Robotics | - |
   | person | Marguerite Oyelowo | chief financial officer, Halcyon Grid | - |
   | person | Sunniva Hartigan | chief financial officer, Quillon AI | - |
   | person | Lysander Boateng | chief financial officer, Kelvra Bio | - |
   | person | Evander Pruitt | chief financial officer, Orbitline Systems | - |
   | person | Cosima Aldridge | chief financial officer, Stripple Tech | - |
   | person | Anselm Okonkwo-Reyes | chief financial officer, Veridia Payments | - |
   | person | Philippa Strand | chief financial officer, Tessaract Labs | - |
   | person | Garrick Lindahl | chief financial officer, Pellucid Sensors | - |
   | person | Henrietta Voss | chief financial officer, Corvane Analytics | - |
   | person | Wilhelmina Achterberg | chief financial officer, Nimbusfield Security | - |
   | person | Barnaby Ekwueme | chief financial officer, Tidewell Medical | - |
   | person | Ignatius Valcourt | chief financial officer, Ferrogate Cloud | - |

3. **Phase 2 choices I made where the spec was silent** (plan header, rulings table; overrule any):
   - Figures for the four extra clients:
     - Corvane: $8.4M cash, $0.60M burn, RML 14.0
     - Nimbusfield: $3.3M cash, $0.40M burn, RML 8.3
     - Tidewell: $4.3M cash after the restricted account, $0.35M burn, RML 12.3
     - Ferrogate: $16.0M cash, burn −$0.25M (cash-flow positive)
   - Every client has a drawn Bank of Stoic venture term loan.
   - Ferrogate (the only client with positive EBITDA) has a DSCR covenant: DSCR of at least 1.25x on a trailing-twelve-months basis from 2026-05-31, as a second terms version, per your earlier "have DSCR as well". *Decision taken, not a question.* A trailing-twelve-months test needs twelve published months, so May 2026 is the first possible test; an earlier start would leave "cannot test" rows through the history. None of the other 15 has a DSCR covenant.
4. **SaaS figures on monthly packs:** *Built in Phase 2 Task 7.* SaaS lines (MRR, ARR, customers) come from the monthly MRR report, and a financial pack without them still spreads.

## Added in Phase 2 (21 November)

5. **MRR export for Stripple.** The file is delivered as the real `mrr_export.xlsx` and as a PDF print of the same sheet, because intake accepts PDFs only. *Taken: both exist; the print is the file that is held.* **Owner (20 Nov): accept spreadsheets.** Built (Phase 3): intake takes .xlsx and .csv as documents with cell-level citations; the Stripple export is ingested and held with one question; PDF-only agents never receive a sheet.
6. **Due days for the monthly package:** financials and certificate 30 days (spec section 3); MRR report 15; bank statements 7. The 7 and 15 are mine: "Lumora October reporting 12 days late" at an as-of of 19 November needs an item due on 7 November. *Taken: as stated.*
7. **Tidewell's cash mismatch.** The calculation records a passing variance on the ledger only, so no item is raised today. The answer key expects an exception `cash.statement_mismatch` (statements to certificate), which needs a reconciliation step built in Phase 3. *Taken: the key expects it; the live cycle now raises it (`cash.statement_mismatch`, from a reconciliation of the bank statements to the certificate, Phase 3). The calculation-only and seeding tests still pin it as outside their scope; the stand-in suite asserts the live cycle raises it.*
8. **Corvane's plan miss is a breach.** Revenue is under 80 percent of the approved plan in September and October; the certificate says so honestly, so the exception is `covenant.breach`. *Taken: as described.*
9. **Sign the new answer key.** `synthetic/books/innovation/oracle.csv` has 107 rows: 91 unsigned (63 plus 28 expected signals: covenant tests, funding events, expected exceptions and current-period signals for the 16 innovation clients) and 16 signed (the four kept borrowers' v1 rows, unchanged). It will arrive as one short table (standing approval 3).
10. **Lumora's October tests are `cannot_test`.** Lumora's October package is late (the scenario is "October reporting 12 days late"), so the October covenant tests have no figures and the key records `cannot_test`, with `intake.missing_document` exceptions for the missing bank statements and MRR report. *Taken: as stated.* Overrule if you would rather the repaired pack test cleanly.
11. **Runway falling is stricter.** Runway falling now means losing more than one month of runway per month for three months (faster than the calendar), with four meaningful runway readings; it fires for Brightvane only. Before, any three-month decline fired, which is true of almost every startup that is burning cash. *Taken by the controller; overrule if you meant any decline.* The answer key lost three unsigned rows (Dataflake, Nimbusfield, Tidewell).

## Sign the answer key (Phase 3)

The one-table sign-off (91 unsigned rows, 28 of them signals, 22 of those low severity) is in `docs/owner-signoff-2026-11-21.md`, with the rulings to know while signing. Signing is required before the live pass, and nothing live runs until you also say go on the cost estimate.


## Owner decisions, 21 November 2026 (Phase 3 gates)

- **Answer key:** "Approve all". All 91 unsigned rows of `synthetic/books/innovation/oracle.csv` signed with `evals.signoff apply` (107 of 107 now signed).
- **Live record pass:** approved on Opus 5.5 (the model the product ships with), cap **$21** (estimate mid $12.65, high $20.23; `docs/live-run-estimate-2026-11-21.md`). One client is measured first; the run stops if that projects above the cap.

## Live record pass (owner, 21 Nov: "Opus, cap $21")

- Measured spend 8.31 US dollars (from recorded token counts; the estimate was mid 12.65). Gate passed on the live record scorecards; the replay of the recordings does not pass because fact ids differ per run (a product and harness fix, not a model result). Details: `docs/HANDOFF.md`, `docs/lessons/a-recorded-model-run-cannot-replay-agents-that-cite-fact-ids.md`.
- **Re-record (21 Nov, after the Phase 3 fix waves):** approved — Covenant, Review and Early Warning agents on Opus 5.5 for both books, cap **$5** (estimate $1.50–$3.50), to start only after the full test run passes.

## Phase 4b (21 Nov) — I chose a default for each so work continues; tell me to change any

1. **Packages, review room, calendar** are not in the Squad spec. Default: Task 5 deletes them (v1 keeps them at commit 2292b38). Keep any?
2. **Agents reading figures from spreadsheets** is out of 4b. Which phase should own it? Default: after Phase 5.
3. **Kestrel Bay wrong-abstain and Pellham wording** need a small billable re-record to prove fixed. Default: none in 4b; I will bring an estimate later.
4. **"Needs you" no longer counts signals** (a signal needing a decision already raises a work item). Default: accepted.
5. **Plain-words name for bank statements:** default "Bank account statement".
6. **"Squad gathers what was asked" on a return:** default: code lists the client's documents not yet attached and a person attaches one (or drafts a request to the client); Squad attaches nothing by itself.
7. **My Portfolio order:** default: lowest runway/headroom first, then clients with no measurement (for example a late package), then cash-flow-positive clients last — a client we know least about should not sit at the bottom.
   - **Owner, 21 Nov:** keep the review room. Task 5 moves it into Squad's look instead of deleting it. Packages: explained, decision pending (default stays: no Squad screen; the engine keeps generating and releasing them).

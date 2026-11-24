# Credit Squad v2: facilitator script

`SYNTHETIC - FOR DEMONSTRATION`

> **Fill in before session 1:** `SITE` = `https://credit-squad.vercel.app` (or `https://credit-squad-v2.vercel.app` if that is the project's name). Every address below starts with `SITE`.

For the facilitator and the note-taker (people chosen by the owner; agents do not run sessions). Five sessions: **P1 to P4 are analysts, P5 is the credit officer.** About 60 minutes each.

## What participants will see (read once before session 1)

- **The book:** 20 invented clients of Bank of Stoic. The book is **reloaded fresh before every session**, so each participant finds the same starting point.
- **Client names in use:** only these. If you see any other name for these clients on screen (for example an older name), **stop and tell the owner before the session**; outside participants must not see the old names.

  | Analyst | Clients |
  |---|---|
  | Priya Raman (the analyst account used in sessions) | Datamarrow Inc, Calvere Health, Brightvane Energy, Cindrel Tech, Meridew Analytics, Nimbusfield Security, Brackmere Medical, Ferrogate Cloud |
  | Tomas Keller | Mosswell Robotics, Tavernel Grid, Tarnavi AI, Kelvra Bio, Orbitline Systems, Veridia Payments, Vantrell Labs, Pellucid Sensors |
  | Analysts with no sign-in (Jules Hartmann, Theo Lindqvist) | Harrowgate Precision Components, Kestrel Bay Packaging, Briarstone Beverage, Pellham Grain & Milling |

- **What is going on with Priya's clients** (so you can recognise a right answer; never tell the participant):
  - **Datamarrow Inc:** the October certificate says minimum cash is met, but it counts cash pledged to a lease letter of credit; without it unrestricted cash is under the minimum. Squad raised a critical case (certificate and bank disagree). Runway about 7 months, the shortest in the book. A Series B extension term sheet is signed.
  - **Meridew Analytics:** revenue is under 80 percent of the approved plan in September and October: a covenant breach (revenue to plan).
  - **Cindrel Tech:** an awkward October package: a new line ("Contract liabilities"), capitalised software that could be misread, and an MRR export spreadsheet with no company name and the wrong year, which is held. Squad also asks one question: is the "Recurring revenue" line ARR or MRR?
  - **Calvere Health:** October package late (bank statements and MRR report missing), so October cannot be tested; Squad drafted a reminder to the client about the October MRR report.
  - **Nimbusfield Security:** a funding round expected to close on 6 November has not closed; runway under 9 months.
  - **Brackmere Medical:** a new escrow account opened in October; the certificate counts it as unrestricted cash, the bank statements show it restricted.
  - **Brightvane Energy:** runway falling fast three months running (still above 12 months).
  - **Ferrogate Cloud:** cash-flow positive, so runway is "not meaningful".
- **Agents are off** on this copy (no model key). Everything Squad already did is loaded and every person's action works: answer, edit and send a draft, route, return (Squad gathers what the officer asked for), decide, client file, My Portfolio, review room, packages. **Asking Squad a new free question, or "Run … now", is refused with a message that agents are off.** If the owner turns agents on (Task 17), change the consent note and task A4.
- **Rules the product enforces** (watch whether participants understand them; do not explain them up front):
  - An analyst acts only on **her own clients** (Priya cannot act on Tomas's clients, nor on clients with no analyst).
  - **Whoever routes a case cannot decide it** (two people always).
  - On a **return**, the officer states what is needed (document type and month, plus a reason). Code matches it: if exactly one document on file fits, Squad attaches it and says so in the thread; if none fits, Squad drafts a request to the client for the analyst to send; if several or a doubtful match, Squad asks the analyst to confirm.
  - "Send" on a draft records it; no real email is sent.

## Sign-ins

Password for every account: `squad-demo` (the shared demo password, `docs/DEPLOY.md`).

| Who | Email | Used by |
|---|---|---|
| Priya Raman, analyst | `priya.raman@bankofstoic.example` | P1 to P4; the facilitator for P5's preparation |
| Helen Strand, credit officer | `helen.strand@bankofstoic.example` | P5; the facilitator during A7 and A8 |
| Dana Whitfield, portfolio manager | `dana.whitfield@bankofstoic.example` | the facilitator, preparation of the review room |

## Before each session (allow 20 minutes)

- [ ] **Book is fresh:** the controller ran `uv run python -I scripts/hosted/v2_setup.py check --base "$SITE"` within the hour and it printed `ready`. Write the result in `session-log.md`. If not `ready`, do not start: the controller reloads the book (export the ledger first) and checks again.
- [ ] **New names on screen:** sign in as Priya, open My Portfolio, check the eight renamed clients show their new names (table above). Sign out.
- [ ] **Hardware:** laptop or desktop; browser window **at least 1000 px wide** (phones and tablets are not part of these sessions). Zoom at 100 percent.
- [ ] **Two separate browsers** (or one normal and one private window, so sign-ins do not mix): the participant's, signed out on the sign-in page; the facilitator's own.
- [ ] **Review room prepared** (analyst sessions, for A11): in the facilitator's browser sign in as Dana Whitfield, open the review room, create a meeting titled "December portfolio review", date 2026-12-03. Then raise an action: Client **Meridew Analytics**, Action "Bring a view on the revenue-to-plan breach", Owner **Priya Raman**, Due 2026-12-02. Sign out.
- [ ] **Facilitator's window signed in as Helen Strand** for analyst sessions (needed in A8).
- [ ] **Officer session (P5) only:** in the facilitator's browser sign in as Priya and route two cases to Helen Strand, each with a view (exact words matter; the note-taker checks them on screen later):
  - **Meridew Analytics**, revenue-to-plan breach: "Revenue under plan two months running; recommend a waiver with conditions."
  - **Datamarrow Inc**, minimum cash case: "The certificate counts pledged cash; I would reserve rights until the November package."
  Sign out as Priya, sign in as Helen in the facilitator's window only to check both appear in Approvals, then sign out. Leave the participant's browser on the sign-in page. Do the review room step too (P5 may use it in O6).
- [ ] Printed: consent note, observation sheets (one per task), this script. Timer ready. Note-taker has the participant code.
- [ ] Recording: off, unless the owner approved it **and** the participant says yes.

## Introduction (5 minutes)

- Welcome; read the consent note aloud; get the signature or spoken yes; note the participant code.
- Say: "I'll read you short tasks. Do them the way you would at work. Please think aloud. I can't help much, because we want to see where the product doesn't help you. You can skip anything."
- Sign the participant in (type the email and password for them, or show them on a card).

## Warm-up (5 minutes)

- What is your role, and for how many years?
- What tools do you use today to monitor borrowers (covenants, reporting, cash)?
- What does a normal morning of monitoring look like?
- When a covenant is broken, who decides what happens, and how does it reach them?

## Tasks: analysts (P1 to P4, signed in as Priya Raman), about 40 minutes

Read each task exactly as written. Give no hint about where to click. If asked "where is …?", answer "Where would you expect it?" After 3 minutes stuck, offer "Do you want to move on?" and mark *not done* or *done with help*.

Core tasks first; tasks marked *(if time)* are dropped when the session runs late.

| # | Area | Read to the participant | Success when (note-taker marks) |
|---|---|---|---|
| A1 | Briefing | "It is your morning. What does Squad say needs you today, and which would you deal with first? Why?" | Names one item at the top of the list and gives a reason taken from the screen (on a fresh book the top is likely the Datamarrow cash case). |
| A2 | Client thread | "Open Cindrel Tech. What arrived for October, and is anything held back?" | Names the October documents that arrived **and** that the MRR export spreadsheet is held (no company name, wrong year), or the held October reading. |
| A3 | Squad asks | "Squad has a question for you about Cindrel Tech. Answer it, and make sure Squad remembers your answer next time." | Chooses an option, ticks Remember, gives a reason, and sees it recorded with her name ("Recorded as Priya · remembered"). |
| A4 | Ask Squad | "Ask Squad something you would want to know about this client." | Types a question and reads why it was not answered (agents off). Note: what she asked, what she expected, and whether she saw the "off" message before or after typing. |
| A5 | Evidence | "Datamarrow's certificate says it meets its minimum cash covenant; Squad says it does not. Show me where each figure comes from." | Opens the source page beside the thread and points at the figure(s); bonus if she explains the pledged cash difference. |
| A6 | Draft | "Calvere Health's October package is late. Squad drafted a reminder. Change it as you like and send it." | Edits and sends; when asked "What happened when you sent it?" she says it was recorded and not emailed. |
| A7 | Route a case | "Meridew Analytics has a covenant case. Decide what you think should happen and send it to the credit officer with your view." | Routes the case to Helen Strand with a view in her own words. Note whether she looked for a "decide" button and what she made of not having one. |
| A8 | Return with gathering | (Facilitator does the steps below as Helen, then says:) "The officer sent it back. Do what she asks and send it back to her." | Finds the returned case in the same thread; sees what Squad attached (the October bank statement) and that Squad drafted a request to the client for the missing item; sends the draft or says she would; routes the case back to Helen with a view. |
| A9 | Client file | "Find Meridew Analytics' covenant results, and its documents for October." | Reaches the client file's Covenants and Documents views (any route). |
| A10 | Portfolio | "Which client has the shortest runway? Open its conversation." | Uses My Portfolio; opens Datamarrow Inc's thread. Note whether she noticed Calvere Health shows as not measured for October. |
| A11 | Review room *(if time)* | "There is a portfolio review coming up. Find it, and what you are asked to do for it." | Finds the review room, the "December portfolio review" meeting and the action on Meridew Analytics with her name. |
| A12 | Packages *(if time)* | "Prepare the monitoring package for Brightvane Energy for September, and check that its figures have sources." | Reaches Packages in the client file, prepares a package, and runs or reads its check. Note what she expected a package to be. |
| A13 | Whose client *(if time)* | "Open Tavernel Grid. What could you do for this client?" | Says it is Tomas Keller's client and that she can look but not act. Note what told her (or did not). |

**Facilitator as Helen during A8** (in the facilitator's browser, signed in as Helen Strand; do it quietly while the participant waits):

1. Open Approvals and open the Meridew Analytics case.
2. Choose to return it. In "what is missing" type: "Before I decide: the October bank statement, and the latest investor update on the plan to recover revenue."
3. Add two needed items: **Bank statement, October 2026** (on file once, so Squad attaches it) and **Investor update, October 2026** (not on file for this client, so Squad drafts a request to the client).
4. Press "Return to Priya Raman". **Do not decide** the case afterwards.

If the participant sends it back in A8, leave it waiting. The book is reloaded before the next session.

## Tasks: credit officer (P5, signed in as Helen Strand), about 40 minutes

Preparation is in the checklist above (two cases routed by Priya).

| # | Area | Read to the participant | Success when |
|---|---|---|---|
| O1 | Approvals | "What is waiting for your decision, and which would you take first?" | Names both cases routed by Priya (Meridew Analytics, Datamarrow Inc) and gives an order with a reason. Note how she reads any other items listed. |
| O2 | Decide | "Decide the Meridew Analytics case. Use the analyst's view and the evidence." | Records a decision with a reason; can say that the analyst who routed it could not decide it herself. |
| O3 | Evidence | "Before deciding Datamarrow, check the cash figure the case rests on." | Opens the source page and points at the figure; bonus if she finds the pledged cash. |
| O4 | Return | "For Datamarrow, ask the analyst for something you need before you decide." | Returns it with a reason and at least one needed item (document type and month). |
| O5 | Thread | "Where would the analyst see your decision on Meridew?" | Finds the decision in Meridew Analytics' client thread. |
| O6 | Portfolio and review room *(if time)* | "Which clients would you raise at the next portfolio review, and where would you look?" | Uses My Portfolio or the review room; names at least one client with a reason from the screen. |
| O7 | Ask Squad *(if time)* | "Ask Squad something you would want to know before deciding." | Reads why it was not answered (agents off). Note what she asked. |

## Debrief (10 minutes)

- What was easiest?
- What was hardest, or slowest?
- What did you expect to find and did not?
- Would you trust a figure shown here? Why, or why not? (Ask about one specific figure she used.)
- How did you feel about Squad drafting, asking and gathering for you?
- If you could change one thing, what would it be?
- Anything we did not ask that we should have?

Thank the participant. Do not discuss findings or say whether a task "worked".

## After the session (15 minutes)

- [ ] Note-taker finishes every observation sheet the same day (`observation-sheet.md`), using the participant code only.
- [ ] Add one line to `session-log.md`.
- [ ] Sign out of every window; close private windows.
- [ ] Tell the controller the session is over, so the book is reloaded before the next one (the ledger is exported first; the export file name goes in the log).
- [ ] If anything unusual happened (slow first load, sign-in failed, an error message), write the exact words in the log.

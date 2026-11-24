# Squad experience: design

Date: 2026-11-20. Status: **draft for owner review**. Companion to `2026-11-20-innovation-book-and-lending-layer-design.md`. It replaces the cockpit experience (`2026-11-18-cockpit-design.md`) for v2; the cockpit stays in v1. The reference for look and behaviour is the frozen demo at `https://c-squad.vercel.app` (source `docs/product/prototype/carly-morning.html`), and the lessons from its usability rounds.

## 1. Purpose and principles

The analyst should hardly need to open the product: Squad does the legwork overnight, tells her what needs her, shows how it got there, asks when it is unsure, and remembers what she teaches. The credit officer decides with evidence and a reason.

- **Muse in tone and conversation, command centre in numbers and evidence.** Warm, interruptible conversation; every figure cold and cited.
- **Colleague, not dashboard.** One agent on the surface ("Squad"), specialists named in its work trail (Intake, Spreading, Covenant agents; Code for calculation, no AI).
- **Calibrated trust.** Honest track records; friction only where judgement is needed (reason required, second person); never a figure without its source.
- **State is computed, never assumed.** Counts, badges and labels come from what actually happened (lesson: `docs/lessons/test-every-entry-route-not-just-the-guided-path.md`).

## 2. People and permissions

Primary: the commercial credit analyst. Second: the credit officer, who decides waivers and credit actions. Also: admin (no credit decisions). Permissions and the two-person rule are the engine's (`core/roles.py`, `domain/workflow.py`); the experience never decides who may do what.

## 3. Structure

| Place | What it is | Replaces in v1 |
|---|---|---|
| **Squad** (home) | The briefing and the main conversation: what Squad did overnight, what needs you, ordered by consequence | Command centre |
| **Client threads** | One conversation per client, which is also its history: documents in, figures read, tests, questions, drafts, decisions, hand-offs | Borrower 360 and timeline |
| **My Portfolio** | All clients by RML (innovation) or headroom (C&I), with trend; a row opens the client's thread | Portfolio |
| **Approvals** (officer) | Decisions waiting, each with the case, the evidence and the analyst's view | Command centre for officers |
| **Client file** (detail) | Redesigned detail views reached by "Open in client file": spread beside the source page, covenants, documents, funding events, history | Spreads, covenants, documents, loans, signals, reviews |
| **Evidence drawer** | Source page with the quote highlighted, the calculation, the clause, the history of a figure; pushes the conversation aside; resizable | Source drawer (reused) |
| **Oversight** (admin, review) | Agent activity, ledger, governance, evaluation results | Agent activity, governance |

Navigation: a collapsible left nav (Squad logo row = home with its needs-you count; My Portfolio; Open cases listing only clients with something open; the user's avatar). Default look: Night, nav collapsed. Other looks: Warm paper, Cool slate, Lavender mist, Sage. The command palette (Ctrl K) stays.

## 4. Squad presence

- Mark: four dots around one core, lavender (dots #8F7BF0, core #4A35B8). States: resting; working (dots turn, core breathes); needs you (an ember ring round the core); responding (a quarter turn with a ripple). Reduced motion turns movement off.
- Centred above the conversation with the label "Credit Squad" (elsewhere just "Squad"). Under it, one reserved line for confirmations ("Email sent as Carly · recorded"); nothing ever covers content.

## 5. Squad home: the briefing

Built from `GET /me/briefing`: open work items the user can act on (by role and assignment), overdue reporting, signals, funding events due, and what agents finished overnight. Ordered by consequence (breach before late before review). Each item says its state in words ("reminder drafted", "with Helen", "approved by Helen") and opens the client's thread at that case.

## 6. Client threads

Rebuilt from the record, so they cannot drift from it: ledger events, work items, agent runs, Copilot exchanges and drafts for the client, mapped to message types:

| Message | From |
|---|---|
| Squad report (what was done, figures as `{{fact:…}}` rendered by code) | agent run output |
| Work trail ("How I got here") | the runs, calculations and checks behind a case |
| Squad asks (options, one choice, optional "Remember") | question work item |
| Document arrived / held | `document.received`, `document.set_aside` |
| Draft to the client (edit, then "Send as Carly") | draft record |
| Decision, return, approval with reason | `work_item.decided` and related events |
| Free question and answer | `copilot.asked` |

Updates arrive by polling `GET /ledger?after_seq=` every few seconds (no push channel exists today; a streaming endpoint is a later option off serverless). A case started in a client's thread stays there through the officer's decision and back.

## 7. Questions to Squad

Free questions go to the engine's Copilot (`POST /copilot/ask`) scoped to the thread's client or the portfolio. Its guarantees are stricter than the demo's: figures must be stored facts or quotes found on their pages, one retry, then a refusal written by code. Each answer shows its sources and the figures code checked; a refusal offers the evidence or the client file.

## 8. Squad asks

A new work-item type `question`: the agent proposes options with evidence, the analyst chooses (and may tick "Remember"), the choice is recorded with her name, and a lesson is written when remembered. Used for mapping a new line, a doubtful figure, a held file, and judgement calls such as "ask the client first or recommend now".

## 9. Drafts and sending

Squad drafts emails and reminders to clients; only a person sends. In v2 "Send" records the message on the ledger and marks it sent; real email is a connector for later. Squad never sends to a client on its own.

## 10. Approvals and hand-offs

The analyst routes a case with her view (required). The officer sees the question as a decision, the analyst's view, the evidence, and a reason box (required); she can approve, reserve rights or return. A return comes back to the same thread with her reason; Squad gathers what was asked (for example the signed term sheet, attached as evidence); the analyst sends it back; the officer decides again. Two people always; the engine enforces it.

## 11. Teach once and track records

Track records per client and task (figures checked and right, corrections and when) come from the record, not from constants. Remembered habits show where they are used.

## 12. Backend additions

- `GET /me/briefing`
- `GET /threads/{borrower_id}` and `GET /ledger?after_seq=`
- `GET /cases/{work_item_id}/trail` (runs, calculations and checks behind a case)
- Work-item type `question` with options; `POST /work-items/{id}/answer`
- Drafts: create, edit, send (records only)
- `POST /lessons` (from a remembered answer or correction)
- Track record read model per borrower and task

## 13. Visual and interaction rules

Updates the cockpit rules where the demo proved better: ink primary buttons (ember only for needs-you), lavender for Squad and agent-written work, evidence documents always on paper-white in every look, confirmations in the presence line, drawer pushes content, text at least 3:1 contrast in every look (tested), widths 1000–1920 px, every route walked end to end before release.

## 14. Testing

Unit tests for the new endpoints; component tests; end-to-end journeys for every entry point of every client (home item, nav, portfolio row, Squad asks, officer screens); contrast scan in all looks; accessibility checks; the eval gate stays green.

## 15. Owner decisions (20 November 2026)

1. **Product name:** "Credit Squad" is the product name on screen as well as the presence label, for now; it may change after market research. (Squad remains how the agent refers to itself in conversation.)
2. **Client file:** the detail views are redesigned in this phase, not restyled versions of the cockpit screens.
3. **Default look:** Night for analysts, Warm paper for credit officers; anyone can switch.

# Redesign direction (brainstorm, 20 November 2026)

Working notes from the owner's brainstorm after colleagues' feedback on the cockpit ("good, but yet another sophisticated dashboard; overwhelming; the AI work is not visible"). Not a spec yet: the spec comes after the clickable prototype is tested. Mockups: the private Design canvas "Credit Agent Squad, home concepts" (rows B to G and the prototype storyboard).

## Decisions taken by the owner

| Topic | Decision |
|---|---|
| Thesis | "The best AI product is one you hardly need to open." |
| Primary user | The **commercial credit analyst**. The credit officer comes second, to approve waivers and credit actions. Design every flow from the analyst's side first. |
| Pilot portfolio | **Innovation banking**: venture-backed technology companies (the client type of a specialist innovation bank). The bank in the product stays fictional (Bank of Stoic); no real bank is named or imitated. Borrower names are invented startup names, screened before any external demo. |
| Interface | A standalone interface first; channels (email, team chat, phone, committee) later. |
| Agent presence | **One agent on the surface** ("Squad"), with the specialists and code shown in a collapsible **work trail** under each message: friendly on top, auditable underneath. |
| Disclosure | Chat-first with progressive disclosure: decision cards in the conversation; a drawer that opens only the evidence the question needs and closes when it is settled; today's screens remain as "detail screens". |
| Framing | Squad is a **wrapper over the Credit Agent Squad command centre, not a replacement**. The chat is the front door; the command centre screens stay as the detail behind it. Every Squad message card, evidence drawer and decision carries one consistent dive point, "Open in Command Centre"; individual figures do not (a figure already opens its source page). |
| Name and mark | **Squad** (chosen over C-Squad, Quorum, Assay and others: simple). Mark: the **closed ring**, eight specialist dots around one larger core ("many into one"); four dots below 32 px. Colour: **lavender** (ground #ECE8FF, dots #8F7BF0, core #4A35B8), the same family as the colour that marks agent-written work, so the mark and the agent's colour mean the same thing. No face, no character. Trademark and domain checks are still owed before anything external. |

## Direction being prototyped (Carly's morning)

Clickable demo: "Squad muse style demo" (`docs/product/prototype/carly-morning.html`). It is a prototype only and does not touch the live app. The live app's demo analyst (Priya Raman) is unchanged for now.

1. Squad greets the analyst with her work, not a dashboard.
2. Upload: the Intake Agent files what it can and holds what it cannot place, with one question.
3. Review in place, teach once: a doubtful figure beside its page; the confirmation becomes a remembered habit for that borrower.
4. Investigate: the work trail and the evidence drawer.
5. Prepare and route: the squad drafts the recommendation with sources; the analyst adds her view and routes it. An analyst cannot grant a waiver.
6. The credit officer decides, with a required reason, on the ledger.

## Behavioural design principles

- **Muse in tone and conversation, command centre in numbers and evidence.** Squad can be talked to, interrupted and asked why; it shows its work while it works and asks the analyst real questions. Every figure it says stays cold and cited: the demo answers free questions only from a fixed evidence pack, code checks every number against that pack, retries once, then refuses and opens the evidence.

- Design for **calibrated trust**, not engagement: make checking as easy as approving; keep deliberate friction where judgement is needed (reason required, second person); show the squad's measured accuracy per borrower and task.
- Triggers are rare and earned. The investment loop is teaching the squad (briefs, autonomy per borrower, learned habits), with autonomy earned from measured accuracy.

## Product change this implies (to plan in the redesign spec, not started)

The engine carries over unchanged (agents, guardrails, ledger, workflow, four-eyes). What changes for innovation banking:

- A new synthetic book of venture-backed companies: monthly financials, compliance certificates, MRR/ARR reports, funding events.
- Monthly cycles instead of quarterly.
- Venture-debt covenants: minimum unrestricted cash, months of runway, revenue or ARR against plan, investor-support conditions.
- SaaS spreading lines: deferred revenue, ARR, burn, capitalised software.

## Next steps

1. Clickable prototype of Carly's morning (estimate: two to three hours of build).
2. Test it with about five analysts and officers on three tasks: find what needs you, handle the covenant miss, check whether you trust the number. Watch whether they open the evidence before approving.
3. Field research at a month-end, if it can be arranged.
4. Then the redesign spec, including the innovation banking change above.

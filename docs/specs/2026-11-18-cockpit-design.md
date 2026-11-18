# Cockpit design: shell, command centre, inspection drawer, Copilot

Owner brief of 18 November 2026, with the decisions taken in the session that day. The aim: keep the warm stone base and the bank's authority, and replace static tables and grey boxes with a working cockpit in which every colour, tag and bar means something financial.

## Decisions the owner took

| Question | Decision |
|---|---|
| Pills | Coloured capsule tags only for severity and actionable status (Critical, Breach, Overdue, a gate that blocks the reader). Metadata (dates, ids, periods, routine roles) is plain text or small mono. Never "pills everywhere". |
| Selected row | A 3 px vertical bar on the row's left edge plus a soft warm tint. The bar uses the interactive blue already in the palette (cobalt), not a new indigo, so no sixth accent is added. |
| Purple (iris) | Agent output only. A human approval gate is never purple. |
| Switching person | "Switch demo user": signs in as another demonstration user. No role toggle on one identity. Shown only where demo users are enabled. |
| Colour | Meaning only. Stage bars use one ink ramp; exception categories use icons. |

## Colour and shape rules (replace the old "no pills, no side stripes" rule)

- Red: covenant breach or a critical item. Amber: needs attention, a high item, overdue, variance. Green: code-verified pass or recorded resolution. Iris: written by an agent. Cobalt: interactive, and the selected-row bar. Ink ramp: neutral quantity and progress.
- Capsule tag (`Tag`): severity and actionable status only. At most one coloured tag per table cell and two per row.
- Proportional bars (`StackedBar`, `Meter`) show plot positions only. Every number beside a bar is a stored figure or a count from the API.
- Still banned: coloured side stripes on cards (the selected-row bar is the one exception), more than two shadow steps, animation over 240 ms, any figure without its source, "AI thinks".

## Shared primitives (`frontend/src/design`)

| Primitive | Purpose |
|---|---|
| `Tag` | Capsule status tag: tones breach, attention, pass, agent, gate (dark neutral with a shield), neutral |
| `StackedBar` | Proportional horizontal bar with optional clickable segments |
| `Meter` | One value against a threshold (covenant headroom) |
| `Drawer` | Right slide-over, 520 px, not modal (the page behind stays usable), full-screen sheet below 640 px, Esc closes, 200 ms |
| `ChoiceCard` | A radio option as a selectable card |
| `Kbd` | Exists; used for every shortcut hint |

## Workspace drawer (`frontend/src/drawer`)

One drawer for the whole app, mounted in the shell, with a segmented header: **Exception & decision** and **◆ Copilot**.

- State lives in a context: `{ open, tab, itemId }`, with `openItem(id)`, `openCopilot(scope?)`, `close()`. The selected item is also in the URL (`?item=`) so a link reopens it.
- The command centre's below-the-table panel and the "Your decision is below" bar are removed.
- **Exception & decision tab**
  - Header: severity tag, borrower link, cycle and stage, mono reference.
  - Key-figures card: the figures the question turns on (calculated against threshold against reported; borrowings against the recalculated base), each a stored fact that opens its source. No card when the item has no such figures.
  - Evidence: each row expands in place to show the calculation's inputs or the review's lines, with "Open in full".
  - Decision: `ChoiceCard` options, reason, "Record decision". When the signed-in role lacks the permission, an **authority gate** replaces the italic note: who may decide, a "Route to <role> for sign-off" button (assigns the item to a person holding the permission; recorded in the ledger), and "Record decision" disabled.
  - "Ask Copilot about <borrower>'s <item>" switches to the Copilot tab scoped to the item.
- **Copilot tab**: see below.

## Shell

- **Rail**: expanded with labels (208 px) or collapsed to icons with tooltips (56 px); toggle button and `[`; choice remembered per browser. As built: from 1200 px the labelled rail sits beside the page (from 1400 px while the drawer is open); below that the rail stays 56 px and the toggle opens the labels over the page, because the screens are laid out for the narrow rail at those widths. Count beside Command centre; a still iris dot (nothing animates for longer than 240 ms) beside Agent activity while a run is in progress. Active item: raised surface, ink icon.
- **Top bar**: search trigger with `Ctrl K`; "As of" as a compact control with a clock icon and the freshness warning; user control with initials, name and role as text, and "Switch demo user"; "Ask Copilot" with an iris spark and `Ctrl J`.
- **Command palette**: borrower jump, queue filters, "Ask Copilot about…".
- **Phone**: bottom bar stays; the drawer is a full-screen sheet. No page scrolls sideways at any width from 360 px.

## Command centre

- Subtitle, computed: quarter and period end, number of exceptions awaiting sign-off, how many are within the reader's authority, and which roles the rest need (named from the real permission table).
- Four cards:
  1. **Active review cycles**: stacked ink-ramp bar by stage; each stage row filters the queue to that stage.
  2. **Exception breakdown**: category rows with icon and count; a click filters the queue and shows an active-filter chip with "Clear filter".
  3. **Q3 covenant compliance**: proportional bar, red (breach, breach reported compliant), amber (compliant with variance), green (compliant); rows link to the portfolio filtered by outcome.
  4. **Deliverables & signals**: overdue as an amber tag, received in the last 30 days, open signals linking to the portfolio.
- Queue: columns Severity, Borrower, Exception / finding, Routing, Due / SLA. Routing is computed from the permission the item needs: within the reader's authority (plain text), or a gate tag naming the role required; an agent recommendation, when there is one, is shown with the iris mark. No "verified" tag on an open exception.
- Keyboard: `J`/`K` or arrows move, Enter opens the drawer, Esc closes it.

## Copilot

- Scope switch in the header: whole portfolio, the borrower on screen, or the selected exception. Scope is sent to the server, which injects it; the model does not choose it.
- Empty state: four starter cards built from live data (the reader's name and role, real counts, the selected item). Off, with the reason, where no model is connected.
- Answers: each figure is a fact chip (formatted value, short fact id) that opens its source; each quotation carries a green "Quote verified by code, p. N" mark that opens the page.
- "Copy to decision reason" on an answer puts its text into the open item's reason field, followed by the Copilot run reference, so the ledger shows where the wording came from.
- Composer: Enter sends, Shift+Enter makes a new line; a link to the run under Agent activity. Footer: "Read-only. Grounded in verified filings and stored facts. Unverifiable claims are refused."

## Other routes

- **Portfolio, Borrowers**: headroom `Meter` per covenant, status tags for outcomes, a row opens a borrower tear-sheet in the drawer with a link to the full page.
- **Borrower Spreads**: document page beside the spread, with the selected figure highlighted on the page.
- **Review room**: stays the review meeting; same primitives and copy.
- **Agent activity**: runs as a timeline; the guardrail checks that actually ran shown as marks with their result; duration and tokens in mono.
- **Governance**: role by permission matrix for the six real roles, and the policy rules as tables.
- **Calendar**: overdue as amber tags; same table treatment.
- **Design system page**: documents the tokens, the colour rules above, and each new primitive live.

## Microcopy

Sentence case in running text, small capitals for card headers (ACTIVE REVIEW CYCLES, EXCEPTION BREAKDOWN, Q3 COVENANT COMPLIANCE, DELIVERABLES & SIGNALS). Figures and names in copy are always computed, never typed into the source. "Calculated by code; credit judgement is yours" on deterministic evidence. Identifiers are the first eight characters of the record's id.

## Phases, each deployed to the test link

1. Tokens, primitives, drawer, shell, command centre.
2. Copilot.
3. Other routes and the design page.

## What stays true

Agents reason, code calculates, guardrails verify, people decide. No figure without its source. A person cannot approve their own work. The ledger records every action, including routing and running a stage.

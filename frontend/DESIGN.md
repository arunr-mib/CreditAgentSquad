# Credit Agent Squad: design system

The visual identity and component vocabulary of the workspace. Tokens live in `src/design/tokens.css`, components in `src/design/`, live examples at `/design`. The design spec (`docs/specs/2026-11-17-credit-agent-squad-design.md`, section 15) is the contract, amended by the cockpit design (`docs/specs/2026-11-18-cockpit-design.md`); this file records how both are met.

**Direction.** A working cockpit on a warm stone base, with a bank's authority: quiet surfaces, ink type, hairline rules, figures that scan in columns, and every colour, tag and bar saying something financial. Agents appear as a colleague's annotations. People decide.

## Rules that do not bend

- **One typeface.** Inter for everything. JetBrains Mono only for identifiers (fact ids, calculation ids, record references), through the `.ident` class.
- **Figures** use tabular lining numerals (`.tnum`) and are never monospace. A quoted clause is prose.
- **Colour carries meaning only.** Red = covenant breach or a critical item. Amber = needs attention: a high item, overdue, variance. Green = a pass that code verified, or a recorded resolution, never a screen state. Iris = written by an agent, and nothing else: an approval a person must give is never iris. Cobalt = interactive, and the bar on the selected row. The ink ramp (`--ramp-1` to `--ramp-6`) = neutral quantity and progress in bars, never a status. Everything else is ink and neutrals. A colour with none of these meanings is a defect.
- **Capsule tags (`Tag`) are for severity and actionable status only**: Critical, Breach, Overdue, a failed run, a gate that blocks the reader. Dates, identifiers, periods and routine roles are plain text or small mono. At most one coloured tag in a table cell and two in a row. A state that asks nothing of the reader is a `StatusDot`: a dot and a word.
- **A check mark is never decorative.** It appears only for a check that ran, with the result that check recorded. A grant in the permission matrix is a dot, not a check.
- **The selected row** carries a 3 px cobalt bar on its left edge and a soft warm tint. It is the one coloured edge in the system.
- **Bars and meters show plot positions only** (`StackedBar`, `Meter`). Every number beside one is a stored figure or a count from the API.
- **Provenance is a glyph, not a colour.** Document, calculation, system of record, person. A fifth glyph, a seedling, marks a fact loaded from the synthetic book (demonstration data only): it is never shown as read from a document.
- **Every figure reaches its source.** A number is rendered by `Figure` and nothing else, and in the product a figure opens the source drawer. Counts of records (queue sizes) are not facts; they link to the list they count.
- **Banned:** coloured side stripes on cards or notices (the selected-row bar is the one exception); tags on everything; more than two shadow steps; animation longer than 240 ms; gradients as decoration; any figure without its source; a figure the interface worked out or typed itself.
- **Wording:** "Recommends resolve", never "Resolved". Never "AI thinks". Say "loan", not "facility". Plain words.
- **Density:** table rows 34 px (32 px compact), header 32 px. One clear next action per card.
- **Access:** every control is reachable by keyboard and shows the focus ring. WCAG AA contrast.

## Colour tokens

| Role | Token | Value | Use |
|---|---|---|---|
| Neutral | `--canvas` | `#f6f4ee` | Page background (warm off-white) |
| | `--surface` | `#fffefc` | Cards, tables, menus |
| | `--surface-sunken` | `#efece4` | Current nav item, skeletons, wells |
| | `--surface-hover` | `#f3f0e9` | Row and menu hover |
| | `--ink-900` | `#1b1a17` | Text, strong rules, selected segment |
| | `--ink-700` | `#45423b` | Secondary text |
| | `--ink-500` | `#5a564e` | Labels, glyphs (6.5:1 or better on every surface) |
| | `--ink-400` | `#8c877c` | Control borders, neutral dots (3:1, non-text only) |
| | `--hairline` | `#e3dfd5` | Row rules |
| | `--hairline-strong` | `#cfc9bc` | Card borders, dividers |
| Ink ramp | `--ramp-1` to `--ramp-6` | `#ddd8cb`, `#c2bcae`, `#a39d90`, `#827c71`, `#5a564e`, `#2f2d28` | Neutral quantity and progress in bars, light to dark; `--ramp-4` is the neutral meter. Never a status |
| Cobalt | `--cobalt` / `-strong` | `#1f47c4` / `#183aa6` | Links, primary button, focus ring, the selected-row bar; hover |
| | `--cobalt-bg` / `-border` | `#edf1fc` / `#b7c6f2` | Chosen option (`ChoiceCards`), selected cell, highlighted quote |
| Iris | `--iris` / `-mark` | `#5a3fa6` / `#6b4fc0` | Agent name; agent mark |
| | `--iris-bg` / `-border` | `#f3f0fa` / `#cfc5ec` | Agent note and agent tag ground and border |
| Red | `--red` / `-mark` | `#ae2018` / `#c8281e` | Breach or critical text; dot, bar fill |
| | `--red-bg` / `-border` | `#fbedeb` / `#efc2bd` | Breach tag ground and border |
| Amber | `--amber` / `-mark` | `#855400` / `#b87a00` | Attention text; dot, stage marker, bar fill |
| | `--amber-bg` / `-border` | `#faf1dc` / `#e9d29a` | Attention tag ground and border |
| Green | `--green` / `-mark` | `#1d6b41` / `#2a8553` | Pass text; pass dot, bar fill |
| | `--green-bg` / `-border` | `#e8f3ec` / `#b9dac6` | Pass tag ground and border |

Text tokens meet 4.5:1 on canvas, surface, sunken and hover; marks and control borders meet 3:1. `src/design/__tests__/tokens.test.ts` enforces both, plus the two-shadow and 240 ms limits. Tailwind's default palette is removed in `@theme`, so only these tokens can be used as utilities.

**One mark per severity, the same on every screen.** Critical is red, high is amber, medium is ink, low is hollow. Critical and high used to share amber so that red meant only a covenant breach; the owner's review (18 November 2026) found that two levels with one colour cannot be told apart, so red now means a covenant breach or a critical item. A covenant breach is still named in red where it occurs (the question, the outcome).

## Type

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `display` | 34 / 40 | 600 | One headline count per block |
| `page` | 26 / 32 | 600, tracking -0.018em | Page title |
| `heading` | 20 / 28 | 600 | Section headings, the figure in a source panel |
| `title` | 16 / 24 | 600 | Card titles, the question on a work item |
| `prose` | 14 / 22 | 400 | Agent notes, running text |
| `body` | 13 / 20 | 400 to 600 | Tables and controls: the working size |
| `caption` | 12 / 16 | 400 to 500 | Meta lines, hints, identifiers |
| `micro` | 11 / 16 | 600, caps, +0.06em | Eyebrows and column heads (`.eyebrow`) |

Weights: 400, 500, 600. Hierarchy comes from size and weight, not colour. Inter features `calt`, `cv05`, `cv08` are on. Fonts are self-hosted from `@fontsource-variable/*`; there are no external requests.

## Space, radius, shadow, motion

- **Space:** 4 px scale. `--space-1` to `--space-16` = 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Tailwind spacing is set to 4 px per unit.
- **Layout:** top bar 48 px; navigation 208 px, a 56 px icon rail below 1200 px, a bottom bar below 640 px; page gutter 24 px, smaller on a phone. Two-column work layouts from 1400 px; one column below. No minimum width: the page never scrolls sideways (checked from 360 px). Below 1024 px wide tables scroll inside their own frame with the name column pinned, or set each row out as a labelled list on a phone. Text that carries a decision (borrower, question, covenant, outcome) wraps and is never cut with an ellipsis.
- **Radius:** `--radius-xs` 2 px (marks, keys, highlighted quote, bars), `--radius-sm` 4 px (controls), `--radius-md` 6 px (cards, overlays). Fully round is for status dots, stage markers and the capsule tag only.
- **Shadow:** `--shadow-raised` (popover, menu, toast) and `--shadow-overlay` (dialog, command palette). Cards and tables are flat with a hairline border.
- **Motion:** `--motion-instant` 80 ms (hover, press), `--motion-fast` 140 ms (popover, tooltip, menu), `--motion-base` 200 ms (dialog, toast), `--motion-max` 240 ms (ceiling). Skeletons are still. `prefers-reduced-motion` removes the rest.
- **Focus:** a 2 px cobalt outline offset 2 px (inset on table rows). One treatment everywhere.

## Rules and tables

The ledger is the model. A table has a 1 px ink rule under its header and hairlines between rows; no vertical lines, no zebra. A computed line carries an ink rule above its figures and semibold type on a canvas band; a total adds a double rule below. Figures are right-aligned, the provenance glyph sits in a fixed slot to their right, and positive amounts reserve the width of a closing parenthesis so digits line up with accounting negatives. Money in tables is in USD thousands with the unit stated in the header; negatives are in parentheses; ratios end in `x`; percentages use a true minus. A line the statement does not print shows a dash and is recorded as absent, never as zero.

## Components (`src/design/`)

| Component | What it is for | Rule |
|---|---|---|
| `Button` | Actions. `primary`, `secondary`, `ghost`; 32 and 28 px | One primary per card or dialog |
| `IconButton` | Icon-only action | `label` is required: accessible name and tooltip |
| `Input`, `Select` | Fields | Always labelled. Validation is amber, not red |
| `Tabs` | Switch views | Ink underline. `tabClass` gives router links the same look |
| `Segmented` | Single-choice filter | Square shoulders |
| `Dialog`, `Popover`, `Tooltip` | Overlays | Two shadow steps; enter in 140 to 200 ms |
| `Toast` | Confirms something was recorded | Never the only record: the ledger is |
| `CommandPalette` | Ctrl-K or Cmd-K: go anywhere | Arrow keys move, Enter runs, Escape closes |
| `Card` | Flat surface with hairline border | No shadow, no coloured edge |
| `PageHeader` | Eyebrow, title, a line of facts, actions | The title is the page's `h1` |
| `DataTable` | Dense sortable table (TanStack Table) | Sticky header; nothing is ever clipped; Up, Down, Home, End move row focus; Enter activates; the selected row carries the cobalt bar and a warm tint |
| `StatusDot` | A state that asks nothing of the reader: a dot plus a word | Tones: breach, attention, pass, agent, neutral, muted. `emphasis` colours the word |
| `Tag` | Capsule tag for severity and actionable status | Tones: breach, attention, pass, agent, gate (dark, with a shield: an approval the reader cannot give; never iris), neutral. Never for a date, an identifier, a period or a routine role |
| `StackedBar` | Proportional horizontal bar, segments optionally clickable | Status fills where the parts are outcomes, the ink ramp where they are quantities. Widths only: the counts are text beside it |
| `Meter` | One quantity against its limit, as a short track | A plot position only; the figure is beside it, with its source |
| `ChoiceCards` | A single choice set out as cards (a radio group) | The chosen card is cobalt: it is the reader's own selection |
| `Drawer` | Right slide-over, 520 px | Not modal: the page behind stays in use. A full-screen sheet below 640 px. Esc closes; enters in 200 ms |
| `Figure` | A number, its unit, its glyph, its source | Opens a popover with document, page and quoted text, or formula and inputs; or selects into a side panel |
| `FactSource`, `Quote` | The source itself | A quote is prose with the printed figure highlighted in cobalt tint |
| `ProvenanceGlyph` | Document, calculation, system, person, synthetic book | 12 px, ink-500, never coloured |
| `AgentNote`, `AgentText` | Agent-written text | Iris ground with a hairline on all four sides and the agent mark. "Draft, not yet approved" until a person approves. `{{fact:<id>}}` renders as a `Figure`; an unknown reference is shown, not hidden |
| `GuardrailNotes` | What the guardrails checked and changed | Passed is green (a verified pass); changed, blocked or refused is amber; an action the list does not know is shown in its own words |
| `AgentMark` | The iris lozenge | Wherever an agent wrote something |
| `WorkItemCard` | A question for a person | One question, evidence links, one primary decision that stays in view; other decisions behind a menu |
| `Stepper` | Monitoring-cycle stages | Done is ink, not green. Amber marks the stage waiting for a person. `collapseLater` folds the stages still to come |
| `EmptyState` | Says what is absent and the one way forward | Plain words |
| `Skeleton` | Loading placeholder | Still, never shimmering |
| `Kbd` | A key hint | Every shortcut is shown with its key beside the control it works: `Ctrl K` search, `Ctrl J` Copilot, `[` the rail, `J` `K` or the arrows in a queue or timeline, `Enter` opens, `Esc` closes the drawer |

## Agents in the interface

- The agent mark and iris text name the author; the note's ground is iris tint. Nothing else is iris.
- Agent headlines are in the agent's voice: "Recommends escalate", "Recommends request", "Recommends resolve", "Abstains", "Drafted …". The decision buttons belong to the person.
- The agent never types a number. Its text carries `{{fact:<id>}}`; `AgentText` renders the stored fact with its glyph and source.
- Every forced change by a guardrail is listed under the note.

## Shell

Left navigation (Command centre, Portfolio, Borrowers, Calendar, Review room, Agent activity, Governance), top bar with the command-palette trigger, the Copilot, the simulated "as of" date read from the server's clock, and the user menu with the person's name, role and sign-out. The current navigation item is an ink label on a sunken ground; there is no coloured indicator. A skip link leads to the content. Signed out, only the sign-in screen is shown; a session that ends anywhere returns the person to it.

## The product on real data (`src/api`, `src/source`, `src/screens`)

| Piece | What it is for | Rule |
|---|---|---|
| `api/client.ts`, `api/hooks.ts` | The one way to `/api/v1`: cookie session, one TanStack Query hook per resource | Decimals stay strings. A refusal is shown in the server's own words |
| `source/SourceDrawer` | Answers "where did this number come from?" for every figure | Shows the rendered PDF page with the figure outlined, or the calculation with each input a link, or the clause, the system record or the person; then the fact's history. Inputs open in the same drawer; Back returns |
| `source/PdfPage` | One page of the stored PDF, drawn from the file, with citations outlined | The outline is cobalt (interactive context), never a status colour |
| `FactFigure`, `SourcedFigure`, `StaticFigure` | A stored fact; a figure that is a field of a record, a line of a calculation or a total; a line shown inside its own source | All three carry a glyph. The first two open the drawer |
| `CalculationBreakdown` | A calculation as code ran it | Lines built from several periods list those periods beneath them; named results carry a rule above; the result a double rule below |
| `AgentBody` | Agent text on real data | `{{fact:<id>}}` becomes a figure that opens the drawer; an unresolved reference is shown as unresolved |
| `WorkItemPanel` | One question for a person | Evidence rows open their sources; the decision is a choice, a reason and one primary button; a refusal from the server is named and quoted |
| `Load`, `Notice`, `EmptyCard` | Loading, error and empty states | Every screen goes through `Load`; a notice has a hairline on all four sides and a dot plus a word |
| `work/HeldFigures` | Repair of a held spread, on the work item | Each held figure in three labelled rows: On file (the line and the stored value, or "Nothing on file"), Read from the document (the label and figure as printed; it opens its page), Why it was held. One primary action whose label says what it does (File under the named line, Keep as read, Enter the figure, Reject this reading), the other choices as quiet links, a sentence before the click on what code will then do, and the API's recalculation summary after it. Two readings that look swapped get one action that files both. The decision that finishes the spread stays with the person, below |
| `repair/FigureForm`, `Refusal` | The value and the reason for changing a figure; a refusal beside the control that caused it | The value is entered as it is stored (whole dollars) and read back before it is sent. A reason is always required. A refusal is announced and quotes the server |
| `repair/RecalculationNote` | What code did after a figure changed, in words | Results retired, totals recalculated or the statements no longer foot, metrics, and each covenant whose outcome changed, before and after. Announced (`aria-live`). It restates the API's summary and claims nothing else |
| `source/ChangeFigure` | Correct or reject the figure in the source drawer | Only for a role that may confirm a spread. A calculated figure offers neither and says where the correction belongs |
| `review/Commentary`, `CommentaryEditor` | Write or edit a section of commentary in place | Figures are picked from the review sheet and stored as `{{fact:<id>}}`, never typed as references; the text is shown as it will read. The server's warnings are shown as given. Saving never approves |
| `borrower/UploadDocument` | File a PDF for the borrower | Only the fields the route takes (file, title). The answer is shown as the server gives it |
| `borrower/PackageSchedules` | Schedules where packages are listed: list, create, run what is due | "Prepared, not released": a run never releases. Creating and running need a role that may release |
| `screens/AgentActivity` | Agent runs as a timeline, newest first, by day (UTC) | The agent's name with the iris mark, the task in plain words, the borrower as a link. A tag only for a run that failed or was refused. One mark per guardrail check the run's own record names, with the result recorded there (passed is green with a check; changed or blocked is amber): a run that names no check gets no mark and says so. Duration (from the server), tokens and model in mono. The selected run's steps sit beside the timeline, or under its row below 1280 px. With no runs it says how one starts, that each is billable, and the server's reason where no model is connected |
| `screens/Governance` | Roles and permissions, policy rules, ledger, agent inventory, clock | The matrix is the six roles against every permission as `/governance/roles` returns them: a dot is a grant, a ringed dot a grant that never covers one's own work; below 1024 px each permission lists the roles that hold it. The policy rules are tables from `/governance/policy`: every setting is read by the server from the code that enforces it, and each row names that module. Nothing on either tab is typed into the page |

After a figure is confirmed, corrected, rejected or keyed, every query is read again, so each screen shows the figures on file.

A fact loaded from the synthetic book carries no page of its own. The source drawer and the document viewer show where **code located** the stored value on the period's document, and say so; this is never presented as an extraction.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test && pnpm build
pnpm e2e                              # five journeys against the running seeded stack (API on 8000, workspace on 5173)
node scripts/screenshots.mjs          # the real screens, signed in, 1440 x 900 at scale 2, into screenshots/ (--full adds full-page captures)
node scripts/a11y.mjs                 # axe-core on the same screens plus a keyboard focus-ring pass
pnpm e2e:repair                       # five repair journeys, with axe-core and focus checks; needs a database loaded by e2e/seed_repair.py
```

The last three need the seeded stack (see `docs/HANDOFF.md`). The officer journey records a real decision, so each `pnpm e2e` run takes one open covenant breach out of the queue; a fresh seed has four.

Before a screen ships, check it against: aligned figure columns; consistent row heights; no clipped or overlapping text; every figure has a glyph and a source; no banned pattern; colour only where it means something; a tag only for severity or actionable status; a check mark only for a check that ran; one primary action per card; focus ring on every control; `scrollWidth - clientWidth` is 0 at 360, 390, 820, 1024, 1280 and 1440 px, and one phone screenshot looked at.

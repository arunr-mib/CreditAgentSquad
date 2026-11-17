# Credit Agent Squad: design system

The visual identity and component vocabulary of the workspace. Tokens live in `src/design/tokens.css`, components in `src/design/`, live examples at `/design`. The design spec (`docs/specs/2026-11-17-creditfleet-design.md`, section 15) is the contract; this file records how it is met.

**Direction.** The calm of an institutional research terminal: quiet warm surfaces, ink type, hairline rules, figures that scan in columns. Agents appear as a colleague's annotations. People decide.

## Rules that do not bend

- **One typeface.** Inter for everything. JetBrains Mono only for identifiers (fact ids, calculation ids, record references), through the `.ident` class.
- **Figures** use tabular lining numerals (`.tnum`) and are never monospace. A quoted clause is prose.
- **Colour carries meaning only.** Red = covenant breach. Amber = needs attention. Green = verified pass or recorded resolution, never a screen state. Iris = written by an agent. Cobalt = interactive. Everything else is ink and neutrals. A colour with none of these meanings is a defect.
- **Provenance is a glyph, not a colour.** Document, calculation, system of record, person.
- **Every figure reaches its source.** A number is rendered by `Figure` and nothing else. Counts of records (queue sizes) are not facts; they link to the list they count.
- **Banned:** coloured side stripes on cards or notices; pill-shaped status tags; more than two shadow steps; animation longer than 240 ms; gradients as decoration.
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
| | `--ink-500` | `#66625a` | Labels, glyphs (AA on every surface) |
| | `--ink-400` | `#8c877c` | Control borders, neutral dots (3:1, non-text only) |
| | `--hairline` | `#e3dfd5` | Row rules |
| | `--hairline-strong` | `#cfc9bc` | Card borders, dividers |
| Cobalt | `--cobalt` / `-strong` | `#1f47c4` / `#183aa6` | Links, primary button, focus ring; hover |
| | `--cobalt-bg` / `-border` | `#edf1fc` / `#b7c6f2` | Selected row or cell, highlighted quote |
| Iris | `--iris` / `-mark` | `#5a3fa6` / `#6b4fc0` | Agent name; agent mark |
| | `--iris-bg` / `-border` | `#f3f0fa` / `#cfc5ec` | Agent note ground and border |
| Red | `--red` / `-mark` | `#ae2018` / `#c8281e` | Breach text; breach dot |
| | `--red-bg` / `-border` | `#fbedeb` / `#efc2bd` | Reserved tinted ground |
| Amber | `--amber` / `-mark` | `#855400` / `#b87a00` | Attention text; dot, stage marker |
| | `--amber-bg` / `-border` | `#faf1dc` / `#e9d29a` | Reserved tinted ground |
| Green | `--green` / `-mark` | `#1d6b41` / `#2a8553` | Pass text; pass dot |
| | `--green-bg` / `-border` | `#e8f3ec` / `#b9dac6` | Reserved tinted ground |

Text tokens meet 4.5:1 on canvas, surface, sunken and hover; marks and control borders meet 3:1. `src/design/__tests__/tokens.test.ts` enforces both, plus the two-shadow and 240 ms limits. Tailwind's default palette is removed in `@theme`, so only these tokens can be used as utilities.

**Severity is not red.** Critical and high are amber, medium is ink, low is hollow; one severity always looks the same. A covenant breach is marked in red where the breach is named (the question, the outcome), not on the severity.

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
- **Layout:** top bar 48 px; navigation 208 px, a 56 px icon rail below 1200 px; page gutter 24 px. Two-column work layouts from 1400 px; one column below. Minimum usable width 1024 px.
- **Radius:** `--radius-xs` 2 px (marks, keys, highlighted quote), `--radius-sm` 4 px (controls), `--radius-md` 6 px (cards, overlays). Round is for status dots and stage markers only.
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
| `Segmented` | Single-choice filter | Square shoulders, not pills |
| `Dialog`, `Popover`, `Tooltip` | Overlays | Two shadow steps; enter in 140 to 200 ms |
| `Toast` | Confirms something was recorded | Never the only record: the ledger is |
| `CommandPalette` | Ctrl-K or Cmd-K: go anywhere | Arrow keys move, Enter runs, Escape closes |
| `Card` | Flat surface with hairline border | No shadow, no coloured edge |
| `PageHeader` | Eyebrow, title, a line of facts, actions | The title is the page's `h1` |
| `DataTable` | Dense sortable table (TanStack Table) | Sticky header; nothing is ever clipped; Up, Down, Home, End move row focus; Enter activates |
| `StatusDot` | Status: a dot plus a word | Tones: breach, attention, pass, agent, neutral, muted. `emphasis` colours the word |
| `Figure` | A number, its unit, its glyph, its source | Opens a popover with document, page and quoted text, or formula and inputs; or selects into a side panel |
| `FactSource`, `Quote` | The source itself | A quote is prose with the printed figure highlighted in cobalt tint |
| `ProvenanceGlyph` | Document, calculation, system, person | 12 px, ink-500, never coloured |
| `AgentNote`, `AgentText` | Agent-written text | Iris ground with a hairline on all four sides and the agent mark. "Draft, not yet approved" until a person approves. `{{fact:<id>}}` renders as a `Figure`; an unknown reference is shown, not hidden |
| `GuardrailNotes` | What the guardrails checked and changed | Passed is green (a verified pass); changed or blocked is amber |
| `AgentMark` | The iris lozenge | Wherever an agent wrote something |
| `WorkItemCard` | A question for a person | One question, evidence links, one primary decision that stays in view; other decisions behind a menu |
| `Stepper` | Monitoring-cycle stages | Done is ink, not green. Amber marks the stage waiting for a person |
| `EmptyState` | Says what is absent and the one way forward | Plain words |
| `Skeleton` | Loading placeholder | Still, never shimmering |
| `Kbd` | A key hint | |

## Agents in the interface

- The agent mark and iris text name the author; the note's ground is iris tint. Nothing else is iris.
- Agent headlines are in the agent's voice: "Recommends escalate", "Recommends request", "Recommends resolve", "Abstains", "Drafted …". The decision buttons belong to the person.
- The agent never types a number. Its text carries `{{fact:<id>}}`; `AgentText` renders the stored fact with its glyph and source.
- Every forced change by a guardrail is listed under the note.

## Shell

Left navigation (Command centre, Portfolio, Borrowers, Calendar, Review room, Agent activity, Governance), top bar with the command-palette trigger, the simulated "as of" date and the user menu with role. The current navigation item is an ink label on a sunken ground; there is no coloured indicator. A skip link leads to the content.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test && pnpm build
node scripts/screenshots.mjs          # four PNGs at 1440 x 900, scale 2, into screenshots/ (--full adds full-page captures)
node scripts/a11y.mjs                 # axe-core on the four pages plus a keyboard focus-ring pass
```

Before a screen ships, check it against: aligned figure columns; consistent row heights; no clipped or overlapping text; every figure has a glyph and a source; no banned pattern; colour only where it means something; one primary action per card; focus ring on every control.

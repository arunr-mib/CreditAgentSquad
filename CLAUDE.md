# Credit Agent Squad

A fleet of AI agents for commercial lending. Slice one is the portfolio monitoring cycle. **Agents reason. Code calculates. Guardrails verify. People decide.**

**At the start of every session, read every file in `docs/lessons/`** (one lesson per file, summary on the first line). Record corrections and confirmed approaches there with the reason; update a lesson instead of duplicating it; delete lessons that prove wrong.

| | |
|---|---|
| Design spec (source of truth, owner-owned) | `docs/specs/2026-11-17-creditfleet-design.md` |
| Milestone plans | `docs/plans/` |
| Lessons | `docs/lessons/` |
| Current state and next steps | `docs/HANDOFF.md` |

## Hard constraints

- **The model never types a number.** Agent text uses `{{fact:<id>}}`; code renders figures. A figure that does not trace to a stored fact forces a retry, then an abstain.
- **`backend/app/calc/` and `backend/app/guardrails/` are pure.** No database, network, model or file access, and no imports from other `app` packages. Decimals only, never floats. Rounding only at the end of a formula, half-up.
- **A missing input is an error, never zero. An absent cap means uncapped. Unmeasured metrics are null, never zero.**
- **Facts are never edited.** A correction is a new fact that supersedes the old one.
- **Terms are versioned and approved by a second person.** A proposed version never governs a test. An amendment creates a new version; it never overwrites.
- **Scope is injected by code.** Tools take borrower, facility, period and cycle from the run's scope, never from the model.
- **The ledger is append-only.** No code path updates or deletes `ledger_events`.
- **Synthetic data only.** Every generated document carries `SYNTHETIC - FOR DEMONSTRATION`. Lender: Bank of Stoic. Borrower names are invented, never parodies of real companies. No bank or product names from the owner's reference slides.
- **Live model runs are billable.** Ask the owner first, with an estimate labelled as an estimate. Tests and CI use recorded responses only.
- **The synthetic generator computes expected values independently of `app/calc`.** If they disagree, investigate; never patch one to match the other.
- **`.env` is never committed.**

## Commands

```bash
uv sync                                   # install
uv run pytest                             # all Python tests
uv run pytest backend/tests/calc -q       # pure calculation tests
uv run ruff check .                       # lint
uv run python -m synthetic.generate       # build the synthetic book into synthetic/out/
service postgresql start                  # local Postgres 16 in the cloud container
cd frontend && pnpm install && pnpm dev   # workspace
```

## Design rules for the workspace

One typeface (Inter); JetBrains Mono only for identifiers; figures use tabular numerals. Colour carries meaning only: red breach, amber needs attention, green verified pass or recorded resolution, iris written by an agent, cobalt interactive. Provenance is a glyph, not a colour. Banned: coloured side stripes on cards, pill-shaped status tags, more than two shadow steps, animation over 240 ms, any figure without its source. Say "Recommends resolve", never "Resolved"; never "AI thinks".

## Working with the owner

- The owner owns the spec. Propose changes; do not rewrite it unasked.
- Plans run with worker agents; commit after every task with conventional prefixes (`feat(m2):`).
- Bullets over paragraphs, plain words, estimates labelled as estimates.
- Confirm before anything destructive, billable, or pushed to `main` or to another repository.
- Report only what a tool result in the session verified; say what is unverified.

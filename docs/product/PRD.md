# Product requirements: Credit Agent Squad

| | |
|---|---|
| Product | Credit Agent Squad: an AI agent squad for commercial lending |
| Slice covered | Slice one, the portfolio monitoring cycle |
| Status | Built and running on synthetic data; hosted test link live; not yet measured with a real model |
| Owner | Product owner (GitHub `arunr-mib`) |
| Date | 18 November 2026 |
| Related | `docs/specs/2026-11-17-credit-agent-squad-design.md` (system design), `docs/specs/2026-11-18-cockpit-design.md` (interface design), `docs/product/explainer.md` (plain-language guide), `docs/HANDOFF.md` (current state) |

## 1. Summary

Commercial credit teams spend most of a monitoring cycle on reading documents and redoing arithmetic. Credit Agent Squad gives that work to a set of narrow AI agents, keeps every calculation in code, checks everything an agent reads against the source page, and brings a person in only for judgement. The product's central promise is that no invented or wrong number reaches a person or a covenant test unnoticed, and that every action can be audited afterwards.

## 2. Goals and how success is measured

The owner's four success measures, with the measurement for each.

| # | Goal | Measured by | Current result |
|---|---|---|---|
| 1 | Agents handle the workflow; people step in only for judgement | Share of cycles that close without a person; every seeded problem raises exactly its expected exception and clean borrowers raise none | Stand-in reader, automatic path: 17 of 21 cycles closed, the other 4 resting on the exceptions their scenarios expect; 47.6% needed no person; exception precision and recall 100%. Not measured with a real model |
| 2 | No invented numbers; accurate calculations; sources cited | Extraction graded against ground truth; build fails on an invented number or a false "compliant"; tampering checks; every figure resolves to a stored fact | 2,677 of 2,677 facts with the stand-in reader; covenant outcomes 100%; 47 tampering checks, none slipped; three independent reviews found and closed 24 holes. Not measured with a real model |
| 3 | Every action traceable and auditable | Hash-chained ledger verifies; a person cannot approve their own work (tested); every figure in every Word, Excel and PowerPoint output traces to a fact | Ledger verifies on the hosted link (about 19,900 events); the application's database login there cannot alter the ledger; four-eyes tests pass; package verifier passes |
| 4 | Enterprise grade, visually superior, intuitive | Browser journeys with screenshots; no sideways scrolling from 360 px; accessibility checks; review by someone who has not seen the build | Cockpit redesign in progress (18 November 2026); zero sideways overflow measured at 360 to 1280 px before the redesign; to be re-measured after it |

Non-goals for slice one: underwriting and credit memos, risk rating scorecards, problem-loan workout, real connectors to bank systems, single sign-on, multiple tenants, commercial real estate.

## 3. Users

| Role in the product | What they do here | What they may decide |
|---|---|---|
| Credit analyst | Works the exception queue, confirms held figures, prepares terms and commentary, runs agents | Spreading and intake questions, general exceptions; not breaches |
| Portfolio manager | Reviews the book, approves commentary, releases packages, runs agents | General exceptions, commentary approval, package release |
| Credit officer | Decides breaches and over-advances, approves terms and commentary | Breach responses, terms approval |
| Credit administration | Boards and approves terms, handles documents | Terms, general exceptions |
| Credit review | Independent review of the trail | Records findings; read-only otherwise |
| Administrator | Users, policy, the demonstration clock | Everything; for set-up, not for daily credit work |

A person cannot approve work they prepared. Roles are enforced by the server, not only by the interface.

## 4. Principles the product must hold

1. Agents reason, code calculates, guardrails verify, people decide.
2. The model never types a number. Agent text refers to stored facts; code renders the figure.
3. Every number is a stored fact with provenance: read from a document (page and position), calculated (formula and inputs), from a system of record, or entered by a person.
4. The model never chooses the evidence it is checked against. Code injects the borrower, loan and period, and code locates every figure on its page.
5. Abstain over guess. A failed check holds the figure and raises one specific question with a way to repair it.
6. Terms are versioned, effective-dated and approved by a second person.
7. Every action is on an append-only, hash-chained ledger.
8. Autonomy is earned per task from measured accuracy; the default is that a person confirms every document reading.
9. Synthetic data only in this phase.

## 5. Scope: the monitoring cycle

### 5.1 Stages and requirements

| Stage | Requirement | Acceptance |
|---|---|---|
| Compliance tracking | Read covenants, definitions (including add-backs and caps) and reporting requirements from the agreement and amendments, each with its clause citation; build a calendar of what is due | Proposed terms never govern a test; an amendment creates a new version; a contradiction between a proposed covenant and its clause is flagged |
| Package collection | Classify each received document, find its period, match it to an obligation, chase what is late | A document that does not name the borrower, or whose period looks like the comparative column, is not filed without a person; a chaser is drafted, never sent automatically |
| Spreading | Read statements into the template with a citation per figure; verify each against its page; foot and tie the statements | A figure that cannot be found on its page, sits under the wrong label or column, has the wrong sign or scale, or is used twice is held; statements that do not foot store no totals and raise a question |
| Covenant monitoring | Calculate each covenant from approved terms; read the certificate; compare; investigate a difference | Outcomes: compliant, compliant with variance, breach, breach reported compliant, cannot test. A missing input is "cannot test", never a pass |
| Borrowing base | Recalculate eligibility, ineligibles, advance rates and availability from the agings and the certificate | Every line of the certificate is compared; a line not reported is flagged; an over-advance raises a critical exception |
| Early warning | Compute signals by rule; have an agent explain and rank them | Signals carry the facts they were computed from; an explanation with a typed figure is dropped |
| Portfolio review | Draft commentary per borrower from stored facts; support the meeting before, during and after | Commentary needs approval by a second person; a section whose text fails the number check is withheld |
| Credit actions | Actions with owner and due date; items can be routed to the person who may decide | Routing and decisions are on the ledger |
| Package delivery | Word, Excel (live formulas and a sources sheet) and PowerPoint from templates; scheduled or on demand | A verifier confirms every figure in the output traces to a fact; each delivery is a frozen snapshot |

### 5.2 Agents

Nine agents, each with a versioned prompt, a fixed tool list, a step cap and a strict output schema: Intake, Terms, Spreading, Certificate, Covenant, Collateral (borrowing base), Early Warning, Review, Copilot. All run on Claude Opus 5.5 by default, configurable per agent. Agents are inventoried in the product (name, version, model, purpose) for model-risk review.

### 5.3 Guardrails

| Layer | What it enforces |
|---|---|
| Schema | Output matches the agent's schema or the run fails |
| Quote and cell | A quoted clause or a printed figure must be on the cited page; code derives the row label, column, units and sign from the page |
| Label | A figure may be filed under a template line only if the printed label names that line, or a person confirmed that label for that borrower |
| Number | Every digit in agent prose must be inside a fact reference or one of a narrow set of date and reference forms; number words are allowed only as plain counts |
| Scope | Tools take borrower, loan, period and cycle from the run, never from the model |
| Terms | A test uses the approved version in force; a proposed version never governs |
| Policy | Decisions are limited to those allowed for the item and the role |

### 5.4 Human gates

Exceptions are typed. Each carries one question, its evidence, the allowed decisions and the permission needed. Examples: a figure could not be verified; statements do not foot; a breach; a breach the certificate reports as compliant; a borrowing base over-advance; an amendment on file but not in the approved terms; reporting past due; a stage that failed. Every held item has a repair path (confirm, replace, reject, enter by hand, request a new document), and a correction recalculates everything downstream.

## 6. Interface requirements

Set out in full in `docs/specs/2026-11-18-cockpit-design.md`. In brief:

- **Command centre**: four summary cards with proportional bars that filter the exception queue; the queue shows severity, borrower, finding, routing and due date; keyboard navigation.
- **One drawer** beside the queue for the selected exception (key figures, evidence, decision, authority gate with one-press routing) and the Copilot.
- **Copilot**: scope chosen by the reader and injected by the server; starter questions built from live data; figures as fact chips; quotations marked as verified by code; copy an answer into a decision's reason with its run reference.
- **Source drawer**: any figure opens its document page with the figure highlighted, or its calculation with every input.
- **Borrower pages**: summary, loans and terms, documents, spreads, covenants, borrowing base, signals, reviews, packages, timeline.
- **Governance**: ledger explorer with chain verification, agent inventory, role and permission matrix, policy settings, the demonstration clock.
- **Colour carries meaning only**: red breach or critical; amber attention; green code-verified; purple written by an agent; blue interactive. Capsule tags only for severity and actionable status.
- Usable from 360 px wide; no page scrolls sideways.

## 7. Non-functional requirements

| Area | Requirement | State |
|---|---|---|
| Audit | Append-only, hash-chained ledger; application role cannot update or delete it | Met on the hosted link; local development uses one database role |
| Access | Role-based permissions enforced by the server; second-person rule; sign-in lockout; session cookie HTTPS-only outside local development | Met; lockout is per account and can be used to lock someone out |
| Accuracy | Decimal arithmetic; rounding only at the end of a formula; missing input is an error | Met |
| Reproducibility | Tests and CI use recorded or scripted model responses; nothing billable runs without the owner's go-ahead | Met |
| Deployment | Runs as a static workspace plus one API; PostgreSQL 16 or later; no dependency on a hosted agent service | Hosted test: Vercel and Supabase. No background worker there: a person runs a cycle one stage at a time |
| Model use | Works with a direct key today; the model client is a single module so a bank can substitute its own cloud provider | Direct key only so far |
| Data | Synthetic only; every generated document is marked as synthetic | Met |

## 8. Evaluation

- **Synthetic bank**: 21 borrowers over 8 quarters, 360 documents, with seeded situations (a breach hidden behind a compliant certificate, an add-back over its cap, an unapproved amendment, a thousands-against-units trap, a restated prior period, a missing page, an image-only document, late reporting, a miscounted ineligible) plus clean performers. Expected values are computed independently of the product's calculation code.
- **Grading**: deterministic. The gate fails on any invented number, any false "compliant", or any tampering check that slips.
- **Tampering checks**: 47 mutations of a reading or an answer; each must be refused by the product or recovered by code.
- **Independent review**: a fresh reviewer is given only the promise and asked to break it. Three rounds so far.
- **Live measurement (owed)**: the first runs with a real model, graded the same way, starting with three borrowers.

## 9. Risks and open questions

| Risk or question | Position |
|---|---|
| Accuracy with a real model is unmeasured | First live runs are the next step; default autonomy stays "assisted" until measured |
| A fourth review will probably find another hole | Run it after the first live measurement, briefed with what has been found |
| Real statement layouts differ from synthetic ones | Unfamiliar layouts are held for a person; plan to remember a confirmed layout per borrower so later periods need fewer touches |
| The oracle of expected answers has not been signed by the owner | 76 rows awaiting sign-off |
| A database owner can still rewrite the ledger | Keep a copy of the chain's head outside the database; a scheduled export is not yet built |
| A long stage holds the ledger lock, so other writes wait | Acceptable for a test deployment; needs a shorter transaction around model calls before real use |
| Cost per cycle | Estimated at about one US dollar per borrower cycle with the default model; unmeasured |

## 10. Roadmap

1. **Now**: finish the cockpit interface; first live runs on the hosted link; measure and publish the scorecard.
2. **Next in slice one**: fourth independent review; remembered layouts per borrower; export of the ledger head on a schedule; boarding terms by hand in the interface.
3. **Slice two, underwriting**: tax return spreading, global cash flow, risk rating scorecard, credit memo, approval routing and delegated authority, policy exceptions. Reuses spreading, ratios and the fact store.
4. **Slice three, problem loans.**
5. **Slice four, bank integration**: real connectors (origination, core, document management), single sign-on, deployment hardening.
6. **Slice five, multiple banks**: separate tenants.

## 11. Glossary

See the explainer (`docs/product/explainer.md`, "Words used").

# Credit Agent Squad design

Date: 2026-11-17. Status: approved in outline by the owner; this document is the detailed design and the source of truth. The owner owns it: propose changes, do not rewrite it unasked.

## 1. Purpose

Credit Agent Squad runs commercial lending work end to end for a mid-sized US bank. Agents handle the workflow; a person steps in only where credit judgement is needed. Phase one is a working pilot foundation on synthetic data. Slice one is the portfolio monitoring cycle for commercial and industrial loans, including borrowing-base lines.

Success measures:

1. People step in only for judgement.
2. No invented numbers; calculations are exact; every figure cites its source.
3. Every action is traceable and auditable.
4. Enterprise grade, visually excellent, intuitive.

## 2. Rules

1. Agents reason, code calculates, guardrails verify, people decide.
2. The model never types a number. Agents write commentary with fact references (`{{fact:<id>}}`); code renders the figure. A digit in agent text that does not match a fact in scope forces one retry, then an abstain.
3. Every number is a stored fact with provenance (section 6).
4. The model never chooses the evidence it is checked against. Code injects borrower, facility, period and cycle into every tool call, and code gathers the evidence used for verification.
5. Abstain over guess. Every exception carries one specific question and a repair path.
6. Terms and methods are versioned, effective-dated and approved by a person. Nothing is overwritten.
7. Every action is written to an append-only, hash-chained ledger. Where policy requires two people, the approver must be a different authenticated user from the preparer.
8. Autonomy is earned: each task type runs at a level set by policy (section 9).
9. Synthetic data only. Every generated document carries `SYNTHETIC - FOR DEMONSTRATION`. Lender: "Bank of Stoic". Borrower names are invented and are not parodies of real companies.
10. A missing input is an error, never zero. An absent cap means uncapped. Unmeasured metrics are null, never zero.

## 3. Architecture

```
Workspace (React)   -> API (FastAPI) -> Workflow (cycle state machine, jobs, scheduler)
                                      -> Agent runtime -> Agents -> Tool gateway -> Services
                                      -> Guardrails (pure code)
Services (code only): calc, terms, spreading, borrowing base, signals, calendar,
                      documents, facts, ledger, publishing, connectors
Data: PostgreSQL 16, file store
```

- The workflow is code. An agent never decides which stage comes next; inside a task it decides what evidence to read.
- Agents run on the Claude Messages API with our own tool loop (`anthropic` SDK), so the product can run inside a bank's environment, move to Bedrock, replay recorded responses in tests, and log every step.
- `backend/app/calc/` and `backend/app/guardrails/` are pure: no database, no network, no model, no imports from other app packages except each other's types. They are the only places a number is produced or a figure is cleared.

### Repository layout

```
CLAUDE.md
docs/specs/  docs/plans/  docs/lessons/
backend/
  pyproject.toml
  app/core/         config, db, security, roles, ledger, clock
  app/calc/         decimal helpers, expression engine, template, metrics, covenants, borrowing base, signals
  app/guardrails/   numbers, quotes, narrative, terms drift, policy
  app/domain/       models and services per area
  app/agents/       runtime, llm client, tool gateway, specs/, one module per agent
  app/connectors/   interface and simulated systems
  app/api/          routers, schemas
  migrations/
  tests/
synthetic/          generator package, scenarios, renderers; output in synthetic/out/ (git-ignored except truth and oracle)
evals/              cases, recordings, grader, scorecard data
frontend/           src/design, src/screens, src/api
```

## 4. Spreading template `ci-1`

Values are stored in whole US dollars as decimals. Each line has a key, label, statement, `computed` flag and `presentation_sign`. Stored value = `presentation_sign` x printed value, where a printed figure in parentheses is negative. Expenses and outflows are stored positive.

Income statement (flow, fiscal year to date):

| Key | Label | Notes |
|---|---|---|
| is.revenue | Net revenue | |
| is.cogs | Cost of goods sold | |
| is.gross_profit | Gross profit | computed: revenue - cogs |
| is.sga | Selling, general and administrative | |
| is.depreciation_amortization | Depreciation and amortization | |
| is.other_operating_expense | Other operating expense | |
| is.nonrecurring_expense | Restructuring and other non-recurring charges | |
| is.operating_income | Operating income | computed: gross_profit - sga - depreciation_amortization - other_operating_expense - nonrecurring_expense |
| is.interest_expense | Interest expense | |
| is.other_income_net | Other income (expense), net | income positive |
| is.pretax_income | Income before taxes | computed: operating_income - interest_expense + other_income_net |
| is.income_tax_expense | Income tax expense | |
| is.net_income | Net income | computed: pretax_income - income_tax_expense |

Balance sheet (point in time):

| Key | Label | Notes |
|---|---|---|
| bs.cash | Cash and equivalents | |
| bs.accounts_receivable | Accounts receivable, net | |
| bs.inventory | Inventory | |
| bs.other_current_assets | Other current assets | |
| bs.total_current_assets | Total current assets | computed |
| bs.net_ppe | Property and equipment, net | |
| bs.intangibles | Goodwill and intangibles | |
| bs.other_noncurrent_assets | Other assets | |
| bs.total_assets | Total assets | computed |
| bs.accounts_payable | Accounts payable | |
| bs.accrued_liabilities | Accrued liabilities | |
| bs.revolver | Line of credit | |
| bs.cpltd | Current portion of long-term debt | |
| bs.other_current_liabilities | Other current liabilities | |
| bs.total_current_liabilities | Total current liabilities | computed |
| bs.long_term_debt | Long-term debt, net of current portion | |
| bs.subordinated_debt | Subordinated debt | |
| bs.other_noncurrent_liabilities | Other liabilities | |
| bs.total_liabilities | Total liabilities | computed |
| bs.total_equity | Total equity | input, as stated |
| bs.total_liabilities_and_equity | Total liabilities and equity | computed |

Cash flow (flow, fiscal year to date, indirect):

| Key | Label | Notes |
|---|---|---|
| cf.net_income | Net income | must equal is.net_income |
| cf.depreciation_amortization | Depreciation and amortization | must equal is.depreciation_amortization |
| cf.change_in_working_capital | Changes in working capital | signed, source of cash positive |
| cf.other_operating | Other operating items | signed |
| cf.cfo | Net cash from operating activities | computed: sum of the four above |
| cf.capex | Purchases of property and equipment | presentation_sign -1; stored positive |
| cf.other_investing | Other investing | signed |
| cf.cfi | Net cash from investing | computed: -capex + other_investing |
| cf.revolver_net | Net borrowings on line of credit | signed |
| cf.term_debt_proceeds | Proceeds from long-term debt | |
| cf.term_debt_repayments | Repayments of long-term debt | presentation_sign -1; stored positive |
| cf.distributions | Distributions to owners | presentation_sign -1; stored positive |
| cf.other_financing | Other financing | signed |
| cf.cff | Net cash from financing | computed: revolver_net + term_debt_proceeds - term_debt_repayments - distributions + other_financing |
| cf.net_change_in_cash | Net change in cash | computed: cfo + cfi + cff |

Supplemental (from the notes page):

| Key | Label |
|---|---|
| sup.cash_interest_paid | Cash paid for interest |
| sup.cash_taxes_paid | Cash paid for income taxes |
| sup.scheduled_principal | Scheduled principal payments on term debt |
| sup.financed_capex | Capital expenditures financed with purchase-money debt |

Stated totals. For every computed line the statement prints, the printed total is also extracted as `stated.<key>` (for example `stated.bs.total_assets`). Checks (tolerance: 1 dollar x number of components x scale):

- each computed line equals its stated total (footing);
- `bs.total_assets = bs.total_liabilities_and_equity`;
- `cf.net_income = is.net_income`, `cf.depreciation_amortization = is.depreciation_amortization`;
- `cf.net_change_in_cash = bs.cash(period end) - bs.cash(prior fiscal year end)`;
- a prior-period comparative column, where present, equals the previously confirmed spread, otherwise a restatement exception.

Absent lines. A statement that has no line for a template input is recorded as `absent` (value zero) only when the footing checks for its section pass. If footing fails, the section raises an exception. This is how "missing is never zero" is kept while real statements omit empty lines.

Periods. A period is `(period_end, months, basis)` with `months` in 3, 6, 9, 12 and basis `ytd`. Interim statements present fiscal year to date. Trailing twelve months for a flow line at an interim date = YTD(current) + FY(prior) - YTD(same period, prior year). At a fiscal year end, TTM = FY. Fiscal year end month is per borrower (the synthetic book uses December throughout).

Statement quality: `audited`, `reviewed`, `compiled`, `internal`, `tax_return` (slice two). Scale as reported (1 or 1000) is recorded per document; values are stored unscaled.

## 5. Calculation engine

`app/calc/expr.py` evaluates an expression tree over decimals and returns the value plus a trace of every node, so a calculation record can name each input fact.

Nodes (JSON):

```
{"op":"line","key":"is.net_income","period":"ttm"}      period: ttm | ytd | point | fy
{"op":"const","value":"1.25"}
{"op":"add","args":[...]}  {"op":"sub","args":[a,b,...]}  {"op":"mul","args":[...]}
{"op":"div","num":a,"den":b}                              den <= 0 is an error
{"op":"min","args":[...]}  {"op":"max","args":[...]}
{"op":"named","name":"ebitda"}                            reference to a definition
{"op":"addback","name":"restructuring","source":<node>,"cap":null | {"type":"amount","value":"500000"} | {"type":"pct_of","value":"0.10","of":<node>}}
```

Rules: decimals only; rounding only at the end, per formula (`{"dp":2,"mode":"half_up"}` for ratios, 0 dp for dollars); missing input returns an error naming the line and period; unknown key or duplicate component is an error; `calc_id` is supplied by the caller; engine version is recorded.

Metric library (`app/calc/metrics.py`, versioned as `metrics-1`): ebitda (net income + interest expense + income tax expense + depreciation and amortization), total_debt (revolver + cpltd + long_term_debt + subordinated_debt), senior_debt (total_debt - subordinated_debt), tangible_net_worth (total_equity - intangibles), working_capital, current_ratio, quick_ratio, leverage (total_debt / ebitda ttm), senior_leverage, interest_coverage (ebitda ttm / interest expense ttm), dscr, fccr, debt_to_tnw, gross_margin, ebitda_margin, net_margin, dso (accounts_receivable / revenue ttm x 365), dio (inventory / cogs ttm x 365), dpo (accounts_payable / cogs ttm x 365), revenue_growth_yoy, liquidity (cash + availability).

## 6. Facts and lineage

`facts`: id, borrower_id, facility_id (nullable), key, period_end, months, value numeric(24,6), unit (usd, ratio, days, pct, count), kind, status, and provenance by kind:

| Kind | Provenance fields |
|---|---|
| extracted | document_id, page, bbox, quote (text as printed), label_text, scale_as_reported, agent_run_id |
| calculated | calc_run_id |
| system | connector, record_ref, as_of |
| manual | entered_by, reason |
| seeded | note: loaded from synthetic ground truth, not extracted |

Status: proposed, verified (code found the quote on the page and the parsed number matches), confirmed (a person accepted it), rejected, superseded. A fact is never edited; a correction creates a new fact with `supersedes_fact_id`.

`calc_runs`: id, formula_key, formula_version, terms_version_id (nullable), inputs (name, fact_id, value), outputs, trace, engine_version, created_by, created_at.

Every figure shown in the workspace or in a published file carries its fact id. Selecting it opens the source page with the quote highlighted, or the calculation with its inputs.

## 7. Terms

A `terms_version` belongs to a facility: version, status (proposed, approved, superseded), effective_from, effective_to, approved_by, approved_at, prepared_by, warnings (null = never checked, [] = checked and clean), source documents, and a `terms` JSON document:

```
{
  "definitions": {"ebitda": {"base":"ebitda","addbacks":[{"name","source_key","cap","citation"}]}},
  "covenants": [{
     "id":"fccr", "name":"Fixed Charge Coverage Ratio", "archetype":"coverage",
     "params": {...archetype parameters...},
     "test": {"operator":">=", "threshold":"1.20", "steps":[{"from":"2026-01-01","value":"1.25"}], "unit":"ratio"},
     "measurement": {"basis":"ttm", "frequency":"quarterly"},
     "rounding": {"dp":2,"mode":"half_up"},
     "citations":[{"field","document_id","section","page","quote"}]
  }],
  "reporting_requirements": [{"id","document_type","frequency","due_days_after_period_end","quality","citation"}],
  "borrowing_base": null | {
     "commitment":"5000000",
     "components":[
       {"collateral":"accounts_receivable","advance_rate":"0.85","eligibility":{"max_age_days":90,"cross_aging_pct":"0.50","concentration_limit_pct":"0.25","exclude":["intercompany","foreign","government","contra"]}},
       {"collateral":"inventory","advance_rate":"0.50","sublimit":"1500000","eligibility":{"exclude":["work_in_process","consigned"]}}],
     "reserves":[{"name","amount"}], "frequency":"monthly", "citation":{...}}
}
```

Archetypes (`app/calc/covenants.py` compiles parameters to an expression tree; unknown keys are rejected, nothing is defaulted):

| Archetype | Parameters | Formula |
|---|---|---|
| coverage | numerator_base (ebitda or adjusted_ebitda), deductions subset of [unfinanced_capex, cash_taxes, distributions], denominator subset of [cash_interest, interest_expense, scheduled_principal] (at least one) | (base - deductions) / denominator, all TTM. unfinanced_capex = cf.capex - sup.financed_capex |
| leverage | debt (total_debt or senior_debt), ebitda (ebitda or adjusted_ebitda) | debt (point) / ebitda (TTM) |
| current_ratio | none | total current assets / total current liabilities |
| min_tangible_net_worth | step_up_pct_of_net_income (nullable) | tangible net worth; threshold may step up |
| min_liquidity | include_availability (bool) | cash (+ availability) |
| max_capex | none | cf.capex for the fiscal year (TTM at interim) |
| debt_to_tnw | none | total liabilities / tangible net worth |
| custom | expression tree written by a person | as written |

`adjusted_ebitda` = ebitda + add-backs from `definitions.ebitda.addbacks`, each capped as specified.

Approval. Extraction produces a proposed version. Before approval, code checks that every number in the terms appears in its cited quote on the cited page, that thresholds are stated in the right unit, and records warnings (`amendment_not_cited`, `clause_amended`, `addback_not_in_terms`, `definition_not_located`, `definition_conflict`, `definition_superseded`). Approval supersedes the previous version by setting its `effective_to` to the day before; the old terms are never rewritten. Only one approved open-ended version per facility. The version in force for a test is the approved or superseded version whose dates contain the period end. A proposed version never governs. Approver must differ from preparer.

Terms drift. If a calculation used terms that differ from the approved version, each difference must be backed by a quote from an agreement or amendment; an unbacked difference turns a "resolve" into "escalate".

## 8. Monitoring cycle

A cycle is one borrower and one period end. Stages: `awaiting_package`, `intake`, `spreading`, `covenant_testing`, `borrowing_base` (if the facility has one), `signals`, `review_prep`, `in_review`, `actions_open`, `closed`. Stage status: pending, running, needs_person, done, skipped, failed. A background worker advances cycles; each stage is one or more jobs on a Postgres queue (`FOR UPDATE SKIP LOCKED`). A simulated clock lets the demo advance time.

Covenant test outcomes (computed by code for every covenant in force, every period):

| Outcome | Meaning | Next |
|---|---|---|
| compliant | computed passes and agrees with the certificate | none |
| compliant_variance | passes, but differs from the certificate beyond tolerance | logged |
| breach | computed fails | exception, Covenant Agent investigates |
| breach_reported_compliant | computed fails and the certificate claims compliance | critical exception |
| cannot_test | missing input or no terms in force | exception with the missing item named |

Covenant Agent recommendation on an exception: `resolve` (explained and compliant under terms that are on file, with evidence), `escalate` (true breach or unverified), `request` (a named document is needed), `abstain`. Policy overrides in code: prohibited phrasing (waive, amend, contact borrower) escalates; margin worse than the policy floor escalates; step cap reached on a resolve abstains; an abstain is never promoted.

Exceptions (`work_items`): type, severity, borrower, cycle, stage, question, allowed decisions, evidence (fact ids, document pages), status (open, decided, dismissed), decision (who, what, reason, when), requires_second_person. Types in slice one: `intake.missing_document`, `intake.unclassified`, `spread.value_unverified`, `spread.does_not_foot`, `spread.restatement`, `spread.image_only`, `terms.approval_needed`, `terms.unapproved_amendment`, `covenant.breach`, `covenant.reported_mismatch`, `covenant.cannot_test`, `bb.over_advance`, `bb.certificate_mismatch`, `signal.high`, `review.commentary_approval`, `package.release`.

Borrowing base. Code recalculates eligible receivables (age, cross-aging, concentration, exclusions), eligible inventory (exclusions, sublimit), reserves, borrowing base, availability = min(base, commitment) - outstanding - letters of credit, and reconciles each line to the borrower's certificate.

Signals (`signals-1`, code): covenant headroom below 10 percent; headroom falling two periods running; revenue TTM down more than 10 percent year on year; EBITDA margin down more than 3 points; DSO up more than 10 days; DPO up more than 15 days; leverage up more than 0.5x; net loss TTM; cash down more than 30 percent; line usage above 90 percent; availability below 10 percent of commitment; reporting more than 15 days late; payment past due more than 10 days; auditor opinion qualified or going concern (agent-detected, quoted). Each signal stores rule id, severity, and the facts behind it. The Early Warning Agent explains and ranks; it cannot create or suppress a signal.

Reviews. A review sheet per borrower per cycle: facility summary, covenant table, trends, signals, borrowing base, commentary (versioned; agent draft marked as such until a person approves), changes since last review, open actions. A review meeting groups sheets; decisions and actions are recorded during the meeting; a snapshot freezes all facts and files at release.

## 9. Autonomy policy

| Task | Default level | A person is required when |
|---|---|---|
| Classify and match documents | automatic | a document cannot be classified or matched |
| Spread statements | automatic with exceptions | a value is unverified, a section does not foot, a restatement is found, the page is image-only |
| Extract terms | assisted | always: terms govern only after approval by a second person |
| Test covenants | automatic | never for the calculation; always for the response to a breach |
| Borrowing base | automatic with exceptions | over-advance or certificate mismatch |
| Signals | automatic | high severity is acknowledged by a person |
| Review commentary | assisted | always: commentary is approved by a person |
| Release a package | assisted | always |

Levels: shadow (agent output recorded, not used), assisted (a person confirms), automatic with exceptions, automatic. Changes to policy are ledger events.

## 10. Agent runtime

- `AgentSpec`: name, version, model (`claude-opus-5-5`), effort, max_steps, max_output_tokens, system prompt file, tool names, output schema. Specs live in `app/agents/specs/` and are registered in `agent_specs` with a content hash.
- `Scope`: borrower_id, facility_id, period_end, cycle_id, allowed document ids. The tool gateway overwrites scope fields in every tool input, validates inputs against the tool's schema, returns refusals as `{error}` evidence, and records each call as an `agent_steps` row and a ledger event.
- `LLMClient` protocol with three implementations: live (Anthropic SDK), recording (wraps live, writes responses), recorded (replays by request hash; used in tests and CI). Adaptive thinking; effort set explicitly; structured output via strict schemas; refusal stop reason handled with server-side fallbacks; prompt caching on stable prefixes; streaming for long outputs.
- Step cap and token budget per run. A stalled run fails; a failure never reads as a recommendation.
- Guardrail pipeline after every agent answer: parse; validate shape (one retry with no tools); gather evidence in code; quote verified on the page; figures traceable; terms drift; policy; single conditional write. Every forced change is a note `{layer, check, action, detail}` shown to the user.
- Lessons: when a person overrides an agent, their written reason is stored and retrieved for similar later cases. Only a person's reasoning counts as precedent.

Agents: Intake, Terms, Spreading, Covenant, Borrowing Base, Early Warning, Review, Copilot. The Copilot has read-only tools.

Extraction contract. The model receives the PDF and returns, per value: template key, page, printed text of the figure, printed label, period column. Code locates the printed text on that page (PyMuPDF words and boxes), parses the number itself (parentheses negative, commas, currency symbols, scale), applies scale and presentation sign, and stores the fact as verified only if found and equal. The model's own number is never stored.

## 11. Number guardrail

Ported from CreditScout with its tests. Normalisation: accounting negatives, currency symbols and commas stripped, scale suffixes (k, m, mm, bn) only when attached, `x` as ratio. Stripped before extraction: ids, ISO dates, month-day forms, version numbers, section and exhibit references, bare years, quarter labels. "N to 1" drops the 1.00 only when N is a known ratio. Match tolerance: `|a-b| <= 1e-6 x max(1,|a|,|b|)`. Each rule has a positive and a negative test. Known traps are recorded in `docs/lessons/`.

## 12. Ledger, access, security

- `ledger_events`: seq, id, ts, actor_type (user, agent, system), actor_id, action, entity_type, entity_id, payload, prev_hash, hash = sha256(prev_hash + canonical JSON). Updates and deletes are blocked by a database trigger. A command verifies the chain.
- Roles: analyst, portfolio_manager, credit_officer, credit_admin, credit_review (read and QA findings), admin. Server-side sessions, argon2 password hashing, role checks in one place. Single sign-on is a later slice; the user model is ready for it.
- Borrower documents are untrusted input: text from documents is never treated as instructions; agents have no tools that send data out.
- Secrets only in environment variables; `.env` is git-ignored.

## 13. Connectors

`Connector` interface per system: origination, spreading system, core loan accounting, CRM, accounting, email. Phase one ships simulated implementations fed by the synthetic book. Email is an outbox of drafts; nothing is sent.

## 14. Synthetic book

`synthetic/` generates about 20 borrowers over 8 quarters from a seeded ground-truth model and renders PDFs with a real text layer. Ground truth and the oracle are JSON; decimals are strings.

`synthetic/out/truth/<borrower_id>.json`:

```
{"borrower": {...}, "facilities": [...], "terms_versions": [...],
 "periods": [{"period_end","months","fiscal_year","quarter","quality","scale","values":{key: "decimal"}}],
 "certificates": [{"period_end","reported":{covenant_id:{"value","threshold","in_compliance"}}}],
 "borrowing_base": [{"period_end","ar_aging":[...],"inventory":[...],"certificate":{...},"outstanding","letters_of_credit"}],
 "system_of_record": [{"date","revolver_outstanding","commitment","past_due_days"}],
 "documents": [{"id","type","period_end","path","pages","title","received_date"}],
 "scenario": {"code","description"},
 "expected": {"covenant_tests":[...], "borrowing_base":[...], "signals":[...], "exceptions":[...]}}
```

The generator computes `expected` with its own simple arithmetic, independent of `app/calc`. The calculation engine must reproduce it exactly; a disagreement is investigated, not patched. `synthetic/oracle.csv` lists expected outcomes with an `owner_signed_off` column; live evaluations refuse unsigned rows.

Scenarios: clean performer; breach behind a compliant certificate; amendment on file but not approved into terms; add-back over its cap; deteriorating trend; late reporting; miscounted ineligible receivable; over-advance; scale trap; restated prior period; missing page; image-only document; step-up threshold; several clean borrowers so the book is not all exceptions.

## 15. Workspace

Screens: Command centre (work queue by risk and due date), Portfolio (exposure, covenant status, signals, trends), Borrower 360 (summary, facilities, documents, spreads, covenants, borrowing base, signals, reviews, timeline), Calendar (requirements, due, received, overdue), Spread grid (multi-period, provenance per cell), Covenant workspace (test, calculation, certificate comparison, investigation), Terms review (extracted terms beside the source clause), Document viewer (page with highlighted citations), Review room (before, during, after), Agent activity (runs, steps, guardrail notes), Governance (ledger, agent versions, method versions, scorecard, policy), Copilot panel.

Visual identity (new; rules kept from CreditScout):

- One typeface, Inter; JetBrains Mono only for identifiers. Figures use tabular numerals and are never monospace. A quoted clause is prose.
- Colour carries meaning only: red = breach, amber = needs attention, green = verified pass or recorded resolution, iris = written by an agent, cobalt = interactive. Everything else is ink and neutrals on a warm off-white canvas.
- Provenance is shown by a small glyph beside a figure (document, calculation, system, person), not by colour.
- Banned: coloured side stripes on cards, pill-shaped status tags (use a dot and a word), more than two shadow steps, animation over 240 ms, any figure without its source.
- Wording: "Recommends resolve", never "Resolved"; never "AI thinks".
- Dense tables (32 to 36 px rows), one clear next action per card, keyboard navigation and a command palette, WCAG AA contrast.

## 16. Verification

- Unit tests for calc and guardrails (pure, fast). API tests against Postgres with savepoint isolation.
- The calculation engine reproduces the synthetic `expected` values exactly.
- Evaluations: deterministic grader with named failures (`invented-number`, `false-compliant`, `false-breach`, `wrong-abstain`, `missed-abstain`, `wrong-citation`, `stale-terms`, `missed-exception`, `false-exception`). CI runs recorded responses only. The build fails on any `invented-number` or `false-compliant`. Live runs are billable, need the owner's go-ahead, and are reported as they come out.
- Playwright journeys with screenshots and accessibility checks.
- After each milestone, a worker with fresh context checks the result against the four success measures.

## 17. Out of scope for slice one

Underwriting, tax returns, global cash flow, risk rating scorecard, credit memo, approval routing, problem loans, real connectors, single sign-on, separate tenants, commercial real estate, scanned-document recognition, fiscal years other than calendar in the synthetic book, dark theme.

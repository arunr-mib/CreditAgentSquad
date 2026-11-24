# app.calc: the calculation core of Credit Agent Squad

The only place a number is calculated. Pure: no database, network, files, model or clock, and no
imports from other `app` packages. Versions: engine `calc-1`, template `ci-1`, `metrics-1`, `signals-1`.

- `decimal.Decimal` only. Floats are refused (TypeError at constructors, an error result inside trees).
- Rounding happens once, at the end of a formula, half-up. Arithmetic runs at 50 digits.
- A missing input is an error naming line and period, never zero. A denominator <= 0 is an error.
- Bad data comes back as `CalcError(code, message, key, period_end, months, detail)`, not an exception;
  codes are constants in `errors.py`. Dates are passed in; period ends must be month-end `date`s.

## What you supply: a fact provider
```python
get(key: str, period_end: date, months: int) -> FactValue | None    # FactValue(value: Decimal, fact_id: str | None)
```
`months` is fiscal-year-to-date months (3, 6, 9, 12). Balance sheet lines are asked for with the YTD
months of their date (cash at 30 June, December year end: `("bs.cash", 2025-06-30, 6)`); the database
stores point-in-time facts with months = 0 and the service's provider translates the lookup. The provider
must also serve computed template lines (`is.net_income`, `bs.total_current_assets`, ...): store the
output of `compute_statement` as calculated facts. `bb.availability` is the one non-template key: store
`BorrowingBaseResult.availability` under it, or `unused_availability(commitment, outstanding, lcs)` for a
line with no borrowing base. `periods.provider_from_facts({(key, end, months): value})` is for tests.

## template.py
- `LINES`, `LINE_BY_KEY`: `TemplateLine(key, label, statement, computed, presentation_sign, flow, formula)`.
  `stored_value(key, printed)` = presentation_sign x printed value.
- `compute_statement(inputs, *, absent=(), statements=None) -> StatementResult(values, computed, errors)`.
- `check_statement(inputs, *, scale, prior_fye_cash, absent=(), statements=None) -> CheckReport(values,
  computed, checks, errors)`. `inputs` holds input lines plus `stated.<key>` printed totals. Checks:
  footing, balance, the two cash-flow ties, cash roll. `CheckResult(check, key, status, actual, expected,
  difference, tolerance)`, status `pass | fail | not_checked`. Every failed check is also an error
  (`does_not_foot`, `does_not_balance`, `does_not_tie`, `cash_roll_mismatch`). Tolerance = 1 dollar x
  components x scale: footing counts the total's formula terms; balance and ties count 1; cash roll 2.
- Absent lines: pass their keys in `absent`. One stands (as zero) only if a stated total depending on it
  was checked and every footing check of its statement passed; otherwise `absent_not_verified`.
  Supplemental lines have no totals, so they can never be absent: extract them, or enter zero by hand.
- `check_comparative(comparative, confirmed, *, scale) -> list[CheckResult]`: `fail` = restated.

## periods.py
- `resolve_line(key, mode, period_end, provider, *, fye_month=12) -> LineResolution(value, inputs, errors)`,
  mode `ttm | ytd | point | fy`. Interim TTM = YTD + prior FY - prior-year YTD; at a year end TTM = FY.
  Flow lines take ttm/ytd/fy, balance sheet lines take point; `fy` away from a year end is an error.
- `TraceInput(key, period_end, months, value, fact_id, sign)`; sign is -1 for the prior-year YTD.

## expr.py
```python
evaluate(node, period_end, provider, *, definitions=None, rounding=None, fye_month=12, calc_id=None) -> EvalResult
validate_node(node, definitions=None) -> list[CalcError]        # structure only, reads no facts
```
`EvalResult(value, rounded, trace, errors, calc_id, engine_version)`; `value` is None when there are errors.
`Trace.inputs`: every fact read, once, in order. `Trace.addbacks`: `AddbackTrace(name, raw, cap_type,
cap_value, cap_limit, applied, capped, period_end)`. `Trace.steps`: every node's value in evaluation order.
Nodes are those of spec section 5 plus one extension, `{"op":"shift","months":-12,"arg":node}`, used for
year-on-year metrics. `cap` absent or null = uncapped; a zero cap must be written. A line key outside the
template, an unknown node key, a component or add-back used twice in a sum, and a negative cap are errors.

## metrics.py
`METRICS[name] -> MetricDef(name, expr, unit, rounding)`; `metric_definitions()`; `compute_metrics`;
`compute_metric(name, period_end, provider, *, fye_month=12, calc_id=None) -> EvalResult`. Rounding: usd 0 dp,
ratio 2, days 1, pct as a fraction to 4 (0.1282 = 12.82%). quick_ratio, dscr and fccr: see the module docstring.

## terms.py
Pydantic v2 models, `extra="forbid"` throughout: `Terms`, `Definition`, `Addback`, `Covenant`,
`CovenantTest`, `Step`, `Measurement`, `Rounding`, `Citation`, `ReportingRequirement`, `BorrowingBase`,
`Component`, `Eligibility`, `Reserve`, `TermsVersion`. Decimals are strings in JSON; floats are rejected.
Only these may be absent: add-back `cap` (uncapped), `sublimit` and eligibility limits (no limit), `steps`,
citations, `quality`. `Covenant.typed_params` is the archetype's parameter model; cap `of` is a metric name
or an expression tree; the measurement basis must fit the archetype (`BASIS_BY_ARCHETYPE`).
- `threshold_in_force(test, period_end)`: the latest step with `from <= period_end`, else the base threshold.
- `terms_in_force(versions, period_end) -> TermsInForce(version, error)`: the approved or superseded version
  whose dates contain the period end. Proposed never governs. None or several is an error.
- `compare_terms(used, approved, *, include_citations=False) -> list[TermsDifference(path, kind, used,
  approved)]`: kind `changed | added | removed`, path like `covenants[fccr].test.threshold`.

## covenants.py
```python
test_covenant(covenant, period_end, provider, definitions, *, fye_month=12, step_up_from=None, calc_id=None)
determine_outcome(test_result, certificate_entry, tolerance) -> Outcome(outcome, variances, errors, certificate_compared)
```
`definitions` is the governing `terms.definitions`. `CovenantTestResult(covenant_id, period_end, value,
raw_value, threshold, operator, unit, passed, headroom, headroom_pct, trace, errors, expression, calc_id,
engine_version)`. The rounded `value` is what is compared with the threshold. Headroom is positive when
there is cushion, for every operator; `headroom_pct` = headroom / |threshold| as a fraction to 4 dp.
`passed` is None when the test could not run. Also: `compile_covenant`, `build_definitions`, `is_test_date`,
`untested(covenant_id, period_end, errors)` (for no terms in force), `CertificateEntry.from_mapping`.
Outcomes: `compliant`, `compliant_variance`, `breach`, `breach_reported_compliant`, `cannot_test`.
`step_up_from` (the closing date) is needed only for min_tangible_net_worth with a step-up percentage:
each fiscal year ended after it adds pct x positive net income to the threshold.

## borrowing_base.py
```python
compute_borrowing_base(ar_rows, inventory_rows, terms_bb, outstanding, letters_of_credit) -> BorrowingBaseResult
reconcile(computed, certificate, tolerance) -> list[LineDifference(line, computed, certificate, difference, status)]
```
`ArRow(customer, current, days_1_30, days_31_60, days_61_90, over_90, flags, contra)`, `InventoryRow(
category, amount)`; both have `from_mapping`. Result: `lines` (names in `LINE_NAMES`, whole dollars),
`customers` (exact per-customer split), `excluded_by_flag`, `inventory_ineligible_by_category`,
`reserves_by_name`, `availability` (negative when over-advanced), `over_advance`, `is_over_advance`,
`errors`. Ineligibles per customer, in order, each on what the last left: excluded flags (whole balance),
over-age buckets, cross-aging (the rest, when the aged share is strictly above the percentage), contra
(the customer's contra amount, only if the terms exclude "contra"), concentration (excess over pct x
receivables left across all customers). Each line is rounded once. Reconcile status: `match | mismatch |
unknown_line | not_computed`; difference = computed - certificate.

## signals.py
```python
evaluate_signals(period_end, series, *, system_rows=(), reporting=(), opinions=(), as_of=None, rules=RULES) -> SignalEvaluation
compute_signal_inputs(period_end, provider, *, fye_month=12) -> SignalInputs(values, errors, traces)
```
`series`: `PeriodMetrics(period_end, months, metrics, headroom)`; metric names are `revenue_ttm`,
`ebitda_margin`, `dso`, `dpo`, `leverage`, `net_income_ttm`, `cash` (UNROUNDED, straight from
`compute_signal_inputs`) and `availability` (borrowing base lines only; leave None otherwise); `headroom`
maps covenant id to `headroom_pct`. Also `SystemRow`, `ReportingItem`, `AuditorOpinion`,
`reporting_due_date`. `Signal(rule_id, severity, period_end, subject, basis)`: no prose; the basis holds
the values compared with their period keys and fact ids. Each rule rounds its figure once and fires when
the rounded figure is strictly beyond the trigger. An unmeasured value never fires: the rule is listed in
`not_evaluated(rule_id, subject, reason, detail)`. Changes are year on year; `reporting_late` raises one
signal per late requirement. Ids, severities, triggers and the comparison basis are data in `RULES`.
`backend/tests/calc/test_synthetic_truth.py` regenerates the synthetic book and holds this package to it.

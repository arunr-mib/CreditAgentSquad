# Phase 1: Lending Layer for Innovation Banking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the engine what venture-backed borrowers need — a second spreading template (`vc-1`), a trailing-three-months period basis, runway / unrestricted-cash / revenue-vs-plan covenants, startup signals, monthly document handling, funding events and a "teach once" write path — without changing anything the C&I book relies on.

**Architecture:** Pure calculation changes live in `backend/app/calc/` (no I/O, Decimals only). A template registry replaces the single `ci-1` table; `line_info` still answers for any known key, and each borrower names its template. New archetypes compile to the existing expression engine. Domain and API additions (borrower template, funding events, lessons) go through one new Alembic migration. The legacy 21-borrower C&I book and every existing test stay green throughout.

**Tech Stack:** Python 3.13, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL 16, pytest (`uv run pytest`), ruff.

**Spec:** `docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md` (sections 4–9, 12). Owner's source of truth: `docs/specs/2026-11-17-credit-agent-squad-design.md`.

## Global Constraints

- `backend/app/calc/` and `backend/app/guardrails/` are pure: no database, network, model or file access, no imports from other `app` packages (enforced by `backend/tests/calc/test_purity.py`).
- Decimals only, never floats. Rounding only at the end of a formula, half-up.
- A missing input is an error, never zero. An absent cap means uncapped. Unmeasured metrics are null, never zero.
- A ratio whose denominator is zero or negative is never computed; RML with average net burn ≤ 0 is "not meaningful: cash-flow positive" (spec 5).
- Plan figures for revenue-vs-plan are approved terms data, never read from a budget column (spec 5).
- Facts are never edited; the ledger is append-only.
- Every existing test passes after every task (`uv run pytest` from the repo root; start Postgres first with `service postgresql start`).
- Owner defaults taken where the spec left questions open (owner approved the spec without answering them; each can be overruled): the four extra innovation names stay; revenue-vs-plan floor is a terms parameter (synthetic book will use 0.80 of plan on trailing-three-months revenue); RML watch level is a terms/signal parameter defaulting to 12 months; the kept C&I four stay quarterly.

## Review Focus

1. **Cash-flow-positive borrower (burn ≤ 0):** RML must come back "not meaningful", the covenant compliant with that note — never a division error, never a negative runway.
2. **Trailing three months across a fiscal year end** (e.g. period end January with a December year end): the sum must use the prior fiscal year's figures, not treat missing months as zero.
3. **A `ci-1` borrower must be untouched:** no `vc-1` line accepted in its spread, `net_loss` still fires for it, quarterly cycles unchanged.
4. **Revenue-vs-plan with a missing plan month:** cannot test, naming the missing month — never compare against a partial plan.
5. **Monthly statement period phrases** ("one month ended", "ten months ended October 31") must be recognised by intake and by the quote guardrail; quarterly phrases must still work.

Each line above has its test in the owning task (Tasks 2, 3, 1, 4 and 7).

---

## File map

| File | Change |
|---|---|
| `backend/app/calc/template.py` | Template registry: `TEMPLATES`, `template_lines(template_id)`; `vc-1` lines; `compute_statement`/`check_statement` take `template_id` |
| `backend/app/calc/periods.py` | Mode `t3m` (trailing three months) |
| `backend/app/calc/terms.py` | Archetypes `min_unrestricted_cash`, `min_runway_months`, `revenue_vs_plan`; unit `months`; basis `t3m` |
| `backend/app/calc/metrics.py` | Metrics `unrestricted_cash`, `net_burn_t3m`, `rml` |
| `backend/app/calc/covenants.py` | Compile the new archetypes; RML not-meaningful path; result `note` |
| `backend/app/calc/signals.py` | Rules `runway_below_watch`, `runway_falling`, `burn_rising`, `revenue_below_plan`; per-template applicability |
| `backend/app/guardrails/quotes.py` | Monthly period phrases |
| `backend/app/agents/intake.py` | Monthly statements and new document types |
| `backend/migrations/versions/0004_innovation_banking.py` | `borrowers.template_id`, `funding_events` table |
| `backend/app/domain/credit.py` | `Borrower.template_id` |
| `backend/app/domain/funding.py` (new) | `FundingEvent` model + `check_funding_events()` |
| `backend/app/domain/lessons.py` (new) | `record_lesson()` |
| `backend/app/api/routes_credit.py` | `GET/POST /borrowers/{id}/funding-events`, `POST /lessons` |
| `backend/app/domain/stages.py`, `domain/signals_service.py` | Monthly cycles and month-based signal history for `vc-1` borrowers |
| `backend/app/agents/specs/spreading.md`, `intake.md` | Template-aware line list; new document types |
| Tests | `backend/tests/calc/test_template_vc.py`, `test_periods_t3m.py`, `test_covenants_vc.py`, `test_signals_vc.py`; `backend/tests/guardrails/test_quotes_monthly.py`; `backend/tests/agents/test_intake_monthly.py`; `backend/tests/test_funding.py`; `backend/tests/test_lessons.py`; `backend/tests/test_monthly_cycles.py` |

---

### Task 1: Template registry and the `vc-1` template

**Files:**
- Modify: `backend/app/calc/template.py`
- Test: `backend/tests/calc/test_template_vc.py`

**Interfaces:**
- Produces: `TEMPLATES: dict[str, tuple[TemplateLine, ...]]`; `template_lines(template_id: str) -> tuple[TemplateLine, ...]` (raises `ValueError` for an unknown id); `line_info(key)` unchanged in signature, now searching every template; `compute_statement(inputs, *, absent=(), statements=None, template_id="ci-1")`; `check_statement(..., template_id="ci-1")`; `in_template(key: str, template_id: str) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/calc/test_template_vc.py
from decimal import Decimal as D

import pytest

from app.calc.template import TEMPLATES, compute_statement, in_template, line_info, template_lines

VC_KEYS = {
    "is.subscription_revenue", "is.services_revenue", "is.total_revenue", "is.cost_of_revenue",
    "is.vc_gross_profit", "is.rnd", "is.sales_marketing", "is.gna", "is.vc_operating_loss",
    "is.vc_interest", "is.vc_other_income", "is.vc_net_loss",
    "bs.cash_unrestricted", "bs.cash_restricted", "bs.vc_total_cash", "bs.short_term_investments",
    "bs.capitalised_software", "bs.deferred_revenue_current", "bs.deferred_revenue_noncurrent",
    "bs.venture_debt_current", "bs.venture_debt_noncurrent", "bs.convertible_notes", "bs.safes",
    "bs.preferred_equity", "bs.common_equity",
    "cf.vc_operating_cash_flow", "cf.vc_capex", "cf.capitalised_software_spend", "cf.equity_raised",
    "cf.debt_raised", "cf.vc_net_change_in_cash",
    "saas.mrr", "saas.arr", "saas.customers",
}


def test_both_templates_registered():
    assert set(TEMPLATES) == {"ci-1", "vc-1"}
    assert VC_KEYS <= {line.key for line in template_lines("vc-1")}


def test_unknown_template_is_an_error():
    with pytest.raises(ValueError):
        template_lines("xx-9")


def test_template_membership_is_separate():
    # Review focus 3: a ci-1 borrower must not accept vc-1 lines, and vice versa
    assert in_template("bs.cash", "ci-1") and not in_template("bs.cash", "vc-1")
    assert in_template("bs.cash_unrestricted", "vc-1") and not in_template("bs.cash_unrestricted", "ci-1")


def test_shared_keys_have_identical_definitions():
    ci = {line.key: line for line in template_lines("ci-1")}
    vc = {line.key: line for line in template_lines("vc-1")}
    for key in ci.keys() & vc.keys():
        assert ci[key] == vc[key], key


def test_line_info_finds_keys_in_either_template():
    assert line_info("is.revenue").label == "Net revenue"
    assert line_info("bs.cash_unrestricted").flow is False
    assert line_info("saas.arr").flow is False  # ARR is a point-in-time run rate
    assert line_info("cf.vc_capex").flow is True


def test_vc_total_cash_is_unrestricted_plus_restricted():
    result = compute_statement(
        {"bs.cash_unrestricted": D("4600000"), "bs.cash_restricted": D("700000")},
        statements=["bs"], template_id="vc-1",
        absent=[k for k in (l.key for l in template_lines("vc-1"))
                if k.startswith("bs.") and not line_info(k).computed
                and k not in ("bs.cash_unrestricted", "bs.cash_restricted")],
    )
    assert result.values["bs.vc_total_cash"] == D("5300000")


def test_ci_statement_unchanged_by_default():
    result = compute_statement({"is.revenue": D("10"), "is.cogs": D("4")}, statements=["is"],
                               absent=["is.sga", "is.depreciation_amortization", "is.other_operating_expense",
                                       "is.nonrecurring_expense", "is.interest_expense", "is.other_income_net",
                                       "is.income_tax_expense"])
    assert result.values["is.gross_profit"] == D("6")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest backend/tests/calc/test_template_vc.py -v`
Expected: FAIL — `ImportError: cannot import name 'TEMPLATES'`.

- [ ] **Step 3: Implement**

In `backend/app/calc/template.py`:
1. Rename the existing tuple `LINES` to `CI_LINES` and keep `LINES = CI_LINES` as an alias so every existing import keeps working.
2. Add the `saas` statement: `STATEMENTS = ("is", "bs", "cf", "sup", "saas")`. In `_line`, a `saas.*` line is point-in-time: `flow=statement not in ("bs", "saas")`. Apply the same rule in `_total`.
3. Add the `vc-1` lines:

```python
VC_LINES: tuple[TemplateLine, ...] = (
    # Income statement (flow, fiscal year to date; monthly reporters file every month)
    _line("is.subscription_revenue", "Subscription revenue"),
    _line("is.services_revenue", "Services revenue"),
    _total("is.total_revenue", "Total revenue", "is.subscription_revenue", "is.services_revenue"),
    _line("is.cost_of_revenue", "Cost of revenue"),
    _total("is.vc_gross_profit", "Gross profit", "is.total_revenue", "-is.cost_of_revenue"),
    _line("is.rnd", "Research and development"),
    _line("is.sales_marketing", "Sales and marketing"),
    _line("is.gna", "General and administrative"),
    _total("is.vc_operating_loss", "Operating income (loss)",
           "is.vc_gross_profit", "-is.rnd", "-is.sales_marketing", "-is.gna"),
    _line("is.vc_interest", "Interest expense"),
    _line("is.vc_other_income", "Other income (expense), net"),
    _total("is.vc_net_loss", "Net income (loss)", "is.vc_operating_loss", "-is.vc_interest", "is.vc_other_income"),
    # Balance sheet (point in time)
    _line("bs.cash_unrestricted", "Cash in operating accounts"),
    _line("bs.cash_restricted", "Cash pledged or restricted"),
    _total("bs.vc_total_cash", "Total cash", "bs.cash_unrestricted", "bs.cash_restricted"),
    _line("bs.short_term_investments", "Short-term investments"),
    _line("bs.accounts_receivable", "Accounts receivable, net"),
    _line("bs.other_current_assets", "Other current assets"),
    _line("bs.capitalised_software", "Capitalised software, net"),
    _line("bs.vc_other_intangibles", "Other intangibles, net"),
    _line("bs.other_noncurrent_assets", "Other assets"),
    _total("bs.vc_total_assets", "Total assets",
           "bs.vc_total_cash", "bs.short_term_investments", "bs.accounts_receivable",
           "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles",
           "bs.other_noncurrent_assets"),
    _line("bs.accounts_payable", "Accounts payable"),
    _line("bs.accrued_liabilities", "Accrued liabilities"),
    _line("bs.deferred_revenue_current", "Deferred revenue, current"),
    _line("bs.deferred_revenue_noncurrent", "Deferred revenue, non-current"),
    _line("bs.venture_debt_current", "Venture debt, current portion"),
    _line("bs.venture_debt_noncurrent", "Venture debt, net of current portion"),
    _line("bs.convertible_notes", "Convertible notes"),
    _line("bs.safes", "SAFEs"),
    _line("bs.vc_other_liabilities", "Other liabilities"),
    _total("bs.vc_total_liabilities", "Total liabilities",
           "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current",
           "bs.deferred_revenue_noncurrent", "bs.venture_debt_current", "bs.venture_debt_noncurrent",
           "bs.convertible_notes", "bs.safes", "bs.vc_other_liabilities"),
    _line("bs.preferred_equity", "Preferred stock"),
    _line("bs.common_equity", "Common stock and accumulated deficit"),
    _total("bs.vc_total_equity", "Total stockholders' equity", "bs.preferred_equity", "bs.common_equity"),
    _total("bs.vc_total_liabilities_and_equity", "Total liabilities and stockholders' equity",
           "bs.vc_total_liabilities", "bs.vc_total_equity"),
    # Cash flow (flow)
    _line("cf.vc_operating_cash_flow", "Net cash used in operating activities"),
    _line("cf.vc_capex", "Purchases of property and equipment", sign=-1),
    _line("cf.capitalised_software_spend", "Capitalised software development", sign=-1),
    _line("cf.equity_raised", "Proceeds from issuance of preferred stock"),
    _line("cf.debt_raised", "Proceeds from venture debt"),
    _line("cf.vc_other_financing", "Other financing"),
    _total("cf.vc_net_change_in_cash", "Net change in cash",
           "cf.vc_operating_cash_flow", "-cf.vc_capex", "-cf.capitalised_software_spend",
           "cf.equity_raised", "cf.debt_raised", "cf.vc_other_financing"),
    # SaaS metrics (point in time, from the MRR/ARR report)
    _line("saas.mrr", "Monthly recurring revenue"),
    _line("saas.arr", "Annual recurring revenue"),
    _line("saas.customers", "Customers"),
)

TEMPLATES: dict[str, tuple[TemplateLine, ...]] = {"ci-1": CI_LINES, "vc-1": VC_LINES}
_TEMPLATE_KEYS = {tid: frozenset(line.key for line in lines) for tid, lines in TEMPLATES.items()}


def template_lines(template_id: str) -> tuple[TemplateLine, ...]:
    if template_id not in TEMPLATES:
        raise ValueError(f"unknown template {template_id!r}")
    return TEMPLATES[template_id]


def in_template(key: str, template_id: str) -> bool:
    return key in _TEMPLATE_KEYS.get(template_id, frozenset())


LINE_BY_KEY: dict[str, TemplateLine] = {}
for _lines in TEMPLATES.values():
    for _l in _lines:
        if _l.key in LINE_BY_KEY and LINE_BY_KEY[_l.key] != _l:
            raise RuntimeError(f"line {_l.key} differs between templates")
        LINE_BY_KEY[_l.key] = _l
```

4. Extend `NEVER_NEGATIVE` with the `vc-1` positive lines: `is.subscription_revenue`, `is.services_revenue`, `is.cost_of_revenue`, `is.rnd`, `is.sales_marketing`, `is.gna`, `bs.cash_unrestricted`, `bs.cash_restricted`, `bs.capitalised_software`, `bs.deferred_revenue_current`, `bs.deferred_revenue_noncurrent`, `cf.vc_capex`, `cf.capitalised_software_spend`, `saas.mrr`, `saas.arr`, `saas.customers`.
5. Add `SYNONYMS` for `vc-1`: `"bs.deferred_revenue_current": ("Contract liabilities, current", "Deferred revenue")` is **not** added — mapping "contract liabilities" stays a question to a person (spec 4); add only unambiguous ones: `"is.rnd": ("Research and development expense", "R&D")`, `"is.gna": ("General and administrative expense",)`, `"cf.capitalised_software_spend": ("Capitalized software development costs",)`.
7. **Standard-spread reference (owner request, 20 Nov):** add `backend/app/calc/TEMPLATES.md` mapping every `ci-1` and `vc-1` line to the conventional sections of a bank spreading template of the kind used by industry spreading tools such as Moody's MMAS (Sales / Cost of Sales / Gross Profit / Operating Expenses / Operating Profit / Interest / Net Profit; Current Assets / Non-current Assets / Current Liabilities / Long-term Debt / Equity; UCA-style cash flow: operating, investing, financing). Use only public, generic section names; copy nothing proprietary, and name no product in code. Add `TemplateLine.section: str` (one of the section names in that file) to every line, and a test that every line has a section from the documented list.
8. `compute_statement` and `check_statement` gain `template_id: str = "ci-1"`; every place they iterate `LINES` or check membership in `LINE_BY_KEY` for absent/stated lines uses `template_lines(template_id)` / `in_template(key, template_id)` instead, and the error text names the template. `_TIES` (cash-flow ties) apply only to `ci-1`; for `vc-1` there are no ties yet.

- [ ] **Step 4: Run tests**

Run: `uv run pytest backend/tests/calc -q`
Expected: all pass, including the existing `test_template.py` line-count assertions (they count `CI_LINES` through the `LINES` alias).

- [ ] **Step 5: Commit**

```bash
git add backend/app/calc/template.py backend/tests/calc/test_template_vc.py
git commit -m "feat(p1): template registry and the vc-1 spreading template"
```

---

### Task 2: Trailing-three-months period basis (`t3m`)

**Files:**
- Modify: `backend/app/calc/periods.py`, `backend/app/calc/terms.py` (`Basis`)
- Test: `backend/tests/calc/test_periods_t3m.py`

**Interfaces:**
- Consumes: `resolve_line`, `ytd_months`, `prior_fiscal_year_end` (periods.py).
- Produces: `MODES = ("ttm", "ytd", "point", "fy", "t3m")`; `resolve_line(key, "t3m", period_end, provider, fye_month=12)` returning the flow over the three months ending at `period_end`; `Basis` includes `"t3m"`.

Definition: let `m = ytd_months(period_end)`. If `m >= 3`: `YTD(m) − YTD(m−3)` where `YTD(0)` does not exist and `m == 3` means `YTD(3)` alone. If `m < 3`: `YTD(m) + FY(prior) − YTD(prior year, 12 − (3 − m))`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/calc/test_periods_t3m.py
from datetime import date
from decimal import Decimal as D

from app.calc.periods import provider_from_facts, resolve_line

K = "cf.vc_operating_cash_flow"


def test_within_the_fiscal_year():
    facts = {(K, date(2026, 10, 31), 10): D("-6500"), (K, date(2026, 7, 31), 7): D("-4550")}
    res = resolve_line(K, "t3m", date(2026, 10, 31), provider_from_facts(facts))
    assert res.errors == [] and res.value == D("-1950")


def test_exactly_three_months_into_the_year():
    facts = {(K, date(2026, 3, 31), 3): D("-1800")}
    res = resolve_line(K, "t3m", date(2026, 3, 31), provider_from_facts(facts))
    assert res.value == D("-1800")


def test_across_the_fiscal_year_end():
    # Review focus 2: January with a December year end uses November and December of the prior year
    facts = {
        (K, date(2026, 1, 31), 1): D("-600"),
        (K, date(2025, 12, 31), 12): D("-7000"),
        (K, date(2025, 10, 31), 10): D("-5800"),
    }
    res = resolve_line(K, "t3m", date(2026, 1, 31), provider_from_facts(facts))
    assert res.value == D("-1800")  # -600 + (-7000) - (-5800)


def test_missing_month_is_an_error_not_zero():
    facts = {(K, date(2026, 10, 31), 10): D("-6500")}
    res = resolve_line(K, "t3m", date(2026, 10, 31), provider_from_facts(facts))
    assert res.value is None and res.errors[0].code == "missing_input"


def test_point_lines_cannot_be_t3m():
    res = resolve_line("bs.cash_unrestricted", "t3m", date(2026, 10, 31), provider_from_facts({}))
    assert res.value is None and res.errors[0].code == "invalid_period_mode"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest backend/tests/calc/test_periods_t3m.py -v`
Expected: FAIL — unknown period mode `t3m`.

- [ ] **Step 3: Implement**

In `periods.py` set `MODES = ("ttm", "ytd", "point", "fy", "t3m")` and, in `resolve_line`, before the existing `if mode in ("point", "ytd", "fy") or at_year_end:` branch, add:

```python
    if mode == "t3m":
        if months >= 3:
            current = _fetch(res, provider, key, period_end, months, 1)
            if months == 3:
                res.value = current
                return res
            earlier = _fetch(res, provider, key, _months_before(period_end, 3), months - 3, -1)
            if current is not None and earlier is not None:
                res.value = CALC_CONTEXT.subtract(current, earlier)
            return res
        current = _fetch(res, provider, key, period_end, months, 1)
        prior_fy_end = prior_fiscal_year_end(period_end, fye_month)
        prior_fy = _fetch(res, provider, key, prior_fy_end, 12, 1)
        cut_months = 12 - (3 - months)
        cut_end = _months_before(prior_fy_end, 3 - months)
        cut = _fetch(res, provider, key, cut_end, cut_months, -1)
        if None not in (current, prior_fy, cut):
            res.value = CALC_CONTEXT.subtract(CALC_CONTEXT.add(current, prior_fy), cut)
        return res
```

and add the helper it uses:

```python
def _months_before(period_end: date, months: int) -> date:
    index = period_end.year * 12 + (period_end.month - 1) - months
    return month_end(index // 12, index % 12 + 1)
```

Mode/flow validation already rejects `t3m` on point lines because `line.flow == (mode == "point")` is false for a point line with `t3m` — add an explicit check: `if mode == "t3m" and not line.flow:` → `INVALID_PERIOD_MODE`. In `terms.py` add `"t3m"` to `Basis`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest backend/tests/calc -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/calc/periods.py backend/app/calc/terms.py backend/tests/calc/test_periods_t3m.py
git commit -m "feat(p1): trailing-three-months period basis"
```

---

### Task 3: Runway, unrestricted cash and revenue-vs-plan covenants

**Files:**
- Modify: `backend/app/calc/terms.py`, `backend/app/calc/metrics.py`, `backend/app/calc/covenants.py`
- Test: `backend/tests/calc/test_covenants_vc.py`

**Interfaces:**
- Consumes: `t3m` mode (Task 2); `vc-1` lines (Task 1).
- Produces:
  - `Archetype` adds `"min_unrestricted_cash"`, `"min_runway_months"`, `"revenue_vs_plan"`; `Unit` adds `"months"`.
  - `RevenueVsPlanParams(metric: Literal["revenue", "arr"], plan: list[PlanMonth])`, `PlanMonth(period_end: Day, amount: NonNegDec)`.
  - Metrics: `unrestricted_cash = point("bs.cash_unrestricted")`; `net_burn_t3m = sub(add(t3m("cf.vc_capex"), t3m("cf.capitalised_software_spend")), t3m("cf.vc_operating_cash_flow"))`; `avg_net_burn = div(named("net_burn_t3m"), const("3"))`. RML is not a metric node (it needs the not-meaningful rule) — it is computed by `compute_rml(period_end, provider, fye_month) -> RmlResult(value: Decimal | None, burn: Decimal | None, not_meaningful: bool, errors)`.
  - `CovenantTestResult.note: str | None` (`"not_meaningful_cash_flow_positive"` for RML with burn ≤ 0).
  - `compile_covenant(covenant, period_end: date | None = None)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/calc/test_covenants_vc.py
from datetime import date
from decimal import Decimal as D

import pytest

from app.calc.covenants import compute_rml, test_covenant
from app.calc.periods import provider_from_facts
from app.calc.terms import Covenant

OCT = date(2026, 10, 31)


def _cov(archetype, params, threshold, unit, operator=">=", basis="point"):
    return Covenant.model_validate({
        "id": archetype, "name": archetype, "archetype": archetype, "params": params,
        "test": {"operator": operator, "threshold": str(threshold), "unit": unit, "steps": []},
        "measurement": {"basis": basis, "frequency": "monthly"},
        "rounding": {"dp": 1 if unit == "months" else 0, "mode": "half_up"},
    })


def _dataflake():
    # unrestricted 4.6M; operating cash flow -1.95M over Aug-Oct (YTD Oct -6.5M, YTD Jul -4.55M); no capex
    return provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("4600000"),
        ("bs.cash_restricted", OCT, 10): D("700000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("-6500000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("-4550000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })


def test_min_unrestricted_cash_excludes_pledged_cash():
    result = test_covenant(_cov("min_unrestricted_cash", {}, 5000000, "usd"), OCT, _dataflake())
    assert result.value == D("4600000") and result.passed is False


def test_rml_is_cash_over_average_three_month_burn():
    rml = compute_rml(OCT, _dataflake())
    assert rml.burn == D("650000") and rml.value.quantize(D("0.1")) == D("7.1") and not rml.not_meaningful


def test_rml_covenant_breach_below_threshold():
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, _dataflake())
    assert result.value == D("7.1") and result.passed is False and result.note is None


def test_rml_not_meaningful_when_cash_flow_positive():
    # Review focus 1: burn <= 0 never divides
    provider = provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("9000000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("300000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("100000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, provider)
    assert result.passed is True and result.value is None
    assert result.note == "not_meaningful_cash_flow_positive" and result.errors == []


def _plan(months):
    return {"metric": "revenue", "plan": [{"period_end": d.isoformat(), "amount": "1000000"} for d in months]}


def test_revenue_vs_plan_ratio():
    provider = provider_from_facts({
        ("is.subscription_revenue", OCT, 10): D("7700000"),
        ("is.subscription_revenue", date(2026, 7, 31), 7): D("5300000"),
        ("is.services_revenue", OCT, 10): D("0"), ("is.services_revenue", date(2026, 7, 31), 7): D("0"),
    })
    cov = _cov("revenue_vs_plan", _plan([date(2026, 8, 31), date(2026, 9, 30), OCT]), "0.80", "ratio", basis="t3m")
    cov = cov.model_copy(update={"rounding": cov.rounding.model_copy(update={"dp": 2})})
    result = test_covenant(cov, OCT, provider)
    assert result.value == D("0.80") and result.passed is True  # 2.4M of 3.0M plan


def test_revenue_vs_plan_missing_plan_month_cannot_test():
    # Review focus 4
    cov = _cov("revenue_vs_plan", _plan([date(2026, 9, 30), OCT]), "0.80", "ratio", basis="t3m")
    result = test_covenant(cov, OCT, provider_from_facts({}))
    assert result.passed is None
    assert any(e.code == "missing_parameter" and "2026-08-31" in e.message for e in result.errors)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest backend/tests/calc/test_covenants_vc.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_rml'`.

- [ ] **Step 3: Implement**

`terms.py`:

```python
Unit = Literal["ratio", "usd", "pct", "days", "count", "months"]
Archetype = Literal[
    "coverage", "leverage", "current_ratio", "min_tangible_net_worth", "min_liquidity", "max_capex",
    "debt_to_tnw", "min_unrestricted_cash", "min_runway_months", "revenue_vs_plan", "custom",
]


class PlanMonth(_Model):
    period_end: Day
    amount: NonNegDec


class RevenueVsPlanParams(_Model):
    metric: Literal["revenue", "arr"]
    plan: list[PlanMonth] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "RevenueVsPlanParams":
        _no_duplicates((p.period_end for p in self.plan), "plan month")
        return self
```

Register in `PARAMS_BY_ARCHETYPE`: `"min_unrestricted_cash": NoParams, "min_runway_months": NoParams, "revenue_vs_plan": RevenueVsPlanParams`; in `BASIS_BY_ARCHETYPE`: `"min_unrestricted_cash": ("point",), "min_runway_months": ("t3m",)`, `"revenue_vs_plan": ("t3m", "point")` (`min_runway_months` uses `t3m` because its burn is a trailing-three-months average; ARR plan tests use `point`).

`metrics.py`: add a `t3m(key)` helper next to `ttm`/`point` (`{"op": "line", "key": key, "period": "t3m"}`) and the three definitions listed under Interfaces in `metric_definitions()`.

`covenants.py`:

```python
@dataclass
class RmlResult:
    value: Decimal | None
    burn: Decimal | None  # average monthly net burn over the last three months
    not_meaningful: bool
    errors: list[CalcError]
    trace: Trace


def compute_rml(period_end: date, provider: Provider, fye_month: int = 12) -> RmlResult:
    """RML = unrestricted cash / average monthly net burn (last 3 months). Burn <= 0: not meaningful."""
    defs = metric_definitions()
    burn = evaluate(named("avg_net_burn"), period_end, provider, definitions=defs, fye_month=fye_month)
    cash = evaluate(named("unrestricted_cash"), period_end, provider, definitions=defs, fye_month=fye_month)
    trace = Trace(inputs=cash.trace.inputs + burn.trace.inputs, steps=cash.trace.steps + burn.trace.steps)
    errors = burn.errors + cash.errors
    if errors:
        return RmlResult(None, burn.value, False, errors, trace)
    if burn.value <= ZERO:
        return RmlResult(None, burn.value, True, [], trace)
    return RmlResult(cash.value / burn.value, burn.value, False, [], trace)
```

In `compile_covenant(covenant, period_end=None)` add:

```python
    if archetype == "min_unrestricted_cash":
        return named("unrestricted_cash")
    if archetype == "revenue_vs_plan":
        if params.metric == "arr":
            measured, months = point("saas.arr"), [period_end]
        else:
            measured = add(t3m("is.subscription_revenue"), t3m("is.services_revenue"))
            months = [shift_period_end(period_end, -2), shift_period_end(period_end, -1), period_end]
        plan = {p.period_end: p.amount for p in params.plan}
        missing = [m for m in months if m not in plan]
        if missing:
            raise PlanMissing(missing)
        total = sum((plan[m] for m in months), ZERO)
        return div(measured, {"op": "const", "value": str(total)})
```

with `class PlanMissing(Exception): months: list[date]` defined in `covenants.py`. In `test_covenant`, (a) for `min_runway_months` call `compute_rml` and build the result directly: value = `round_half_up(rml.value, dp)` and pass/fail against the threshold when meaningful; `note="not_meaningful_cash_flow_positive"`, `passed=True`, `value=None` when not meaningful; errors carried when missing; (b) wrap `compile_covenant(covenant, period_end)` and turn `PlanMissing` into a `CalcError(E.MISSING_PARAMETER, f"no approved plan figure for {', '.join(m.isoformat() for m in exc.months)}")` with `passed=None`. Add `note: str | None = None` to `CovenantTestResult`, and pass it through `determine_outcome` unchanged (a not-meaningful RML maps to `compliant`).

- [ ] **Step 4: Run tests**

Run: `uv run pytest backend/tests/calc -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/calc/terms.py backend/app/calc/metrics.py backend/app/calc/covenants.py backend/tests/calc/test_covenants_vc.py
git commit -m "feat(p1): runway, unrestricted cash and revenue-vs-plan covenants"
```

---

### Task 3b: Debt service coverage (DSCR) for venture borrowers (owner request, 20 Nov)

**Files:**
- Modify: `backend/app/calc/template.py` (add to `vc-1`: `is.vc_depreciation_amortization` "Depreciation and amortization", and the existing `sup.cash_interest_paid`, `sup.scheduled_principal` lines shared with `ci-1`; include D&A in `is.vc_operating_loss`'s formula as a deduction), `backend/app/calc/metrics.py` (`vc_ebitda = is.vc_operating_loss + is.vc_depreciation_amortization` on a `ttm` basis), `backend/app/calc/covenants.py` (`coverage` archetype picks `vc_ebitda` for a `vc-1` borrower when `numerator_base` is `ebitda`)
- Test: `backend/tests/calc/test_covenants_vc.py` (add tests)

**Interfaces:**
- Consumes: Task 1 template registry; Task 3 `compile_covenant(covenant, period_end=None)`.
- Produces: `compile_covenant(covenant, period_end=None, template_id="ci-1")`; `test_covenant(..., template_id="ci-1")` passes it through; DSCR = (EBITDA − unfinanced capex) ÷ (cash interest + scheduled principal), the same formula the `coverage` archetype already uses for `ci-1`.

- [ ] **Step 1: Failing tests:** (a) a `vc-1` borrower with TTM operating loss −1,000,000, D&A 200,000, cash interest 300,000, scheduled principal 500,000 has DSCR −1.00 (negative EBITDA is a real breach, not "not meaningful": only the denominator must be positive); (b) a `vc-1` borrower with no debt service (interest 0, principal 0) cannot be tested, with the existing `non_positive_denominator` error; (c) the existing `ci-1` coverage tests still pass unchanged.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** as listed; `unfinanced_capex` for `vc-1` = `cf.vc_capex` TTM (no purchase-money financing line in `vc-1`).
- [ ] **Step 4: Run** `uv run pytest backend/tests/calc -q` → all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(p1): DSCR for venture borrowers"`

---

### Task 4: Startup signals and per-template rules

**Files:**
- Modify: `backend/app/calc/signals.py`
- Test: `backend/tests/calc/test_signals_vc.py`

**Interfaces:**
- Consumes: `compute_rml` (Task 3).
- Produces: `SignalRule.templates: frozenset[str]` (default `{"ci-1"}` for every existing rule, so C&I behaviour is unchanged; `reporting_late`, `payment_past_due`, `covenant_headroom_low`, `covenant_headroom_falling` apply to both); new rules applying to `{"vc-1"}`: `runway_below_watch` (kind `rml_below`, params `{"watch": D("12"), "high_below": D("9")}`), `runway_falling` (kind `rml_falling`, `{"periods": 3}`), `burn_rising` (kind `pct_increase`, `{"metric": "avg_net_burn", "threshold": D("0.20"), "compare_months": 3}`), `revenue_below_plan` (kind `plan_ratio_below`, `{"threshold": D("1.00")}`); `evaluate_signals(..., template_id: str = "ci-1")` filters by `templates`; `compute_signal_inputs(period_end, provider, *, fye_month=12, template_id="ci-1", history_months=None)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/calc/test_signals_vc.py
from app.calc.signals import RULES


def test_net_loss_does_not_apply_to_venture_template():
    net_loss = next(r for r in RULES if r.name == "net_loss")
    assert "vc-1" not in net_loss.templates and "ci-1" in net_loss.templates   # review focus 3


def test_startup_rules_exist_for_vc_only():
    names = {r.name: r for r in RULES}
    for name in ("runway_below_watch", "runway_falling", "burn_rising", "revenue_below_plan"):
        assert names[name].templates == frozenset({"vc-1"})
    assert {"vc-1", "ci-1"} <= names["reporting_late"].templates
```

plus one behavioural test per new kind against an in-memory provider (RML 7.1 → `runway_below_watch` high; RML 10 → medium; RML 13 → none; three falling months → `runway_falling`; burn 0.65M vs prior 0.50M → `burn_rising`), written with the same provider style as Task 3's tests and asserting `evaluate_signals(..., template_id="vc-1")` returns exactly the expected signal names.

- [ ] **Step 2: Run to verify they fail** — `uv run pytest backend/tests/calc/test_signals_vc.py -v` → FAIL (`SignalRule` has no `templates`).

- [ ] **Step 3: Implement** — add the `templates` field and the four rule kinds in `_KINDS` (each a pure function over `SignalInputs`, following the shape of the existing `below`/`pct_decrease` handlers); `compute_signal_inputs` for `vc-1` builds monthly history (`history_months`, default 6) of `rml`, `avg_net_burn` and plan ratio instead of quarterly C&I metrics. Existing rule tuples gain `templates=frozenset({"ci-1"})` or both, as listed above.

- [ ] **Step 4: Run** — `uv run pytest backend/tests/calc -q` → all pass (existing `test_signals.py` unchanged).

- [ ] **Step 5: Commit** — `git commit -m "feat(p1): startup signals; net loss off for the venture template"`

---

### Task 5: Borrower template and funding events (migration and models)

**Files:**
- Create: `backend/migrations/versions/0004_innovation_banking.py`, `backend/app/domain/funding.py`
- Modify: `backend/app/domain/credit.py`, `backend/app/domain/__init__.py` (export), `backend/app/api/routes_credit.py`
- Test: `backend/tests/test_funding.py`

**Interfaces:**
- Produces: `Borrower.template_id: str` (`String(8)`, server default `'ci-1'`, check constraint `template_id IN ('ci-1','vc-1')`); `FundingEvent` (table `funding_events`: `id`, `borrower_id`, `kind` in `equity_round|extension|milestone_tranche|venture_debt`, `amount` Numeric(20,2), `expected_close` Date, `status` in `expected|signed|closed|slipped`, `evidence_document_ids` JSON list, `created_at`); `check_funding_events(session, as_of: date) -> list[FundingEvent]` marks every `expected`/`signed` event whose `expected_close < as_of` as `slipped`, writes ledger action `funding_event.slipped`, and raises a work item of type `funding_slipped` (high) once per event; `GET /api/v1/borrowers/{id}/funding-events`, `POST /api/v1/borrowers/{id}/funding-events` (permission `PREPARE_TERMS`), each write recorded on the ledger as `funding_event.recorded`.

- [ ] **Step 1: Write the failing tests** (`backend/tests/test_funding.py`, using the existing `db_session` and `make_borrower` fixtures from `backend/tests/conftest.py`):

```python
from datetime import date
from decimal import Decimal as D

from app.domain.funding import FundingEvent, check_funding_events


def test_new_borrowers_default_to_ci_template(db_session, make_borrower):
    assert make_borrower().template_id == "ci-1"


def test_slipped_funding_raises_one_work_item(db_session, make_borrower):
    b = make_borrower(template_id="vc-1")
    db_session.add(FundingEvent(borrower_id=b.id, kind="extension", amount=D("8000000"),
                                expected_close=date(2026, 12, 12), status="signed"))
    db_session.flush()
    assert check_funding_events(db_session, date(2026, 12, 10)) == []
    slipped = check_funding_events(db_session, date(2026, 12, 13))
    assert [e.status for e in slipped] == ["slipped"]
    assert check_funding_events(db_session, date(2026, 12, 14)) == []  # not raised twice
```

(If `make_borrower` does not accept `template_id`, extend the fixture in the same commit.)

- [ ] **Step 2: Run** — `uv run pytest backend/tests/test_funding.py -v` → FAIL (`ModuleNotFoundError: app.domain.funding`).
- [ ] **Step 3: Implement** the migration (`op.add_column("borrowers", sa.Column("template_id", sa.String(8), server_default="ci-1", nullable=False))`, the check constraint, and `op.create_table("funding_events", ...)` with the columns above), the model, the service and the two routes; follow `routes_credit.py`'s existing patterns for permission (`deps.require`) and ledger writes (`core.ledger.record`).
- [ ] **Step 4: Run** — `uv run alembic -c backend/alembic.ini upgrade head` against the test database, then `uv run pytest backend/tests -q` → all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(p1): borrower template and funding events"`

---

### Task 6: Teach once — the lessons write path

**Files:**
- Create: `backend/app/domain/lessons.py`
- Modify: `backend/app/api/routes_credit.py` (route), `backend/app/agents/covenant_tools.py` (no change in reading; confirm it reads the new rows)
- Test: `backend/tests/test_lessons.py`

**Interfaces:**
- Produces: `record_lesson(session, *, borrower_id, topic: str, text: str, written_by, work_item_id=None, tag=None) -> Lesson` — refuses empty text (`ValueError("a lesson is a person's own words")`), refuses `written_by` that is not a user (only people's reasoning becomes precedent, owner spec), writes ledger action `lesson.recorded`. `POST /api/v1/lessons {borrower_id, topic, text, work_item_id?, tag?}` (permission `DECIDE_WORK_ITEM`).

- [ ] **Step 1: Failing tests:** a recorded lesson is returned by the same query `covenant_tools.py:386` uses for that borrower and topic; empty text is refused; the ledger has one `lesson.recorded` event.
- [ ] **Step 2: Run** → FAIL (no module).
- [ ] **Step 3: Implement** the service and route.
- [ ] **Step 4: Run** `uv run pytest backend/tests -q` → all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(p1): record lessons from people's own words"`

---

### Task 7: Monthly statements in the quote guardrail and intake

**Files:**
- Modify: `backend/app/guardrails/quotes.py` (period phrases, lines ~126–134), `backend/app/agents/intake.py` (statement recogniser, line ~43; document types), `backend/app/agents/specs/intake.md`
- Test: `backend/tests/guardrails/test_quotes_monthly.py`, `backend/tests/agents/test_intake_monthly.py`

**Interfaces:**
- Produces: period phrases recognise `one month ended`, `two months ended` … `eleven months ended`, `month ended`, `for the month of October 2026`, each mapped to the right `months` value (with the fiscal-year-to-date rule unchanged); intake document types add `monthly_financials`, `mrr_report`, `bank_statement`, `term_sheet`, `investor_update` (monthly compliance certificate reuses `compliance_certificate` with monthly frequency).

- [ ] **Step 1: Failing tests** (review focus 5):

```python
# backend/tests/guardrails/test_quotes_monthly.py
import pytest

from app.guardrails.quotes import period_months_from_heading

@pytest.mark.parametrize("heading,months", [
    ("For the ten months ended October 31, 2026", 10),
    ("One month ended October 31, 2026", 1),
    ("For the month ended October 31, 2026", 1),
    ("Nine months ended September 30, 2026", 9),     # quarterly phrases still work
    ("Three months ended September 30, 2026", 3),
    ("Year ended December 31, 2025", 12),
])
def test_period_phrases(heading, months):
    assert period_months_from_heading(heading) == months
```

(If the guardrail's existing function has another name, the test imports that name; the recogniser lives where the current "three/six/nine/twelve" phrases are parsed.) Intake test: a synthetic monthly statement page reading "For the ten months ended October 31, 2026" is classified `monthly_financials` with period 2026-10-31; an MRR export naming no company is held with the question "Which client is this, and which month?".

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — extend the number-word table to one…twelve, accept "month ended"/"for the month of", and add the document types and their recognisers.
- [ ] **Step 4: Run** `uv run pytest backend/tests -q` → all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(p1): monthly statements in intake and the quote guardrail"`

---

### Task 8: Monthly cycles and template-aware agents

**Files:**
- Modify: `backend/app/domain/stages.py` (annual vs interim at line ~110; `quarter_months` at ~285), `backend/app/domain/signals_service.py` (`HISTORY_QUARTERS`, `quarter_ends`), `backend/app/seed_book.py` (one cycle per period by the borrower's reporting frequency; `months` from `ytd_months`, not `9`), `backend/app/agents/specs/spreading.md` and `agents/spreading.py` (line list from `template_lines(borrower.template_id)`)
- Test: `backend/tests/test_monthly_cycles.py`

**Interfaces:**
- Consumes: `Borrower.template_id` (Task 5), `template_lines` (Task 1), `evaluate_signals(..., template_id)` (Task 4).
- Produces: `period_ends_for(borrower, from_date, to_date) -> list[date]` (monthly for `vc-1`, quarterly for `ci-1`), used by seeding and signals; spreading tools refuse a line not `in_template(key, borrower.template_id)` with a question to the analyst.

- [ ] **Step 1: Failing tests:** a `vc-1` borrower gets monthly cycles (Aug, Sep, Oct 2026) and its signals history steps one month at a time; a `ci-1` borrower still gets quarterly cycles and `months=9` at 30 September; the spreading tool refuses `is.revenue` for a `vc-1` borrower and `bs.cash_unrestricted` for a `ci-1` borrower.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** as above; the frequency comes from the borrower's approved reporting requirements (`ReportingRequirement.frequency`), falling back to the template default (`vc-1` monthly, `ci-1` quarterly).
- [ ] **Step 4: Run** the whole suite: `uv run pytest -q` and `uv run ruff check .` → all pass, and `uv run python -m evals.run --mode standin` → gate passes on the legacy book.
- [ ] **Step 5: Commit** — `git commit -m "feat(p1): monthly cycles and template-aware spreading"`

---

### Task 9: Phase close — independent review and handoff

**Files:**
- Modify: `docs/HANDOFF.md` (Phase 1 state; the oracle row count is now correct: 75 rows, all signed), `docs/lessons/` (any lesson learned)

- [ ] **Step 1:** Run everything: `service postgresql start && uv run pytest -q && uv run ruff check . && uv run python -m evals.run --mode standin` — all green; record the counts.
- [ ] **Step 2:** Dispatch a fresh reviewer (no prior context) with the spec, this plan and the diff since the plan's first commit; it checks correctness against the spec's sections 4–9, the five Review Focus items, and that `calc/` and `guardrails/` stay pure.
- [ ] **Step 3:** Fix what the review finds, one commit per finding.
- [ ] **Step 4:** Update `docs/HANDOFF.md`; commit `docs(p1): phase 1 handoff`; push the branch.

---

## Self-review notes

- Spec coverage: §4 template → Task 1; §5 covenants + `avg_last_3m` (implemented as `t3m` sum ÷ 3) → Tasks 2–3; §6 funding events → Task 5; §7 signals → Tasks 4 and 5 (`funding_slipped` is domain-level); §8 documents and intake → Task 7; §9 teach once → Task 6; §3 cadence → Task 8; §12 hosting is Phase 5, not here; §10 scenarios and §11 evals are Phases 2 and 3.
- Interfaces are consistent: `template_id`, `in_template`, `template_lines`, `t3m`, `compute_rml`, `note`, `PlanMissing`, `check_funding_events`, `record_lesson`.

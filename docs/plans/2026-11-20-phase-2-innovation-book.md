# Phase 2: The Innovation-Banking Synthetic Book — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 20-borrower synthetic book for Credit Squad v2 (16 venture-backed innovation clients on a monthly cadence plus the four kept C&I borrowers), with every scenario of the spec self-verifying, expected values computed independently of the engine, an unsigned answer key for the owner, and a seed that loads either book (innovation by default).

**Architecture:** The frozen v1 generator (`synthetic/`) stays exactly as it is and is pinned by digest. The new book lives beside it in `synthetic/books/innovation/`: a monthly truth model back-solved from the owner's 31 October 2026 figures, an independent expected-values module, terms and agreement text, a document planner, and a generator CLI that builds the four kept borrowers by calling the frozen v1 code with the v1 seed (so their truth, documents and signed answer-key rows are byte-identical). Renderers for the new document types sit in `synthetic/render/innovation.py` and reuse the shared page template, legal-document renderer and auditor's report. The backend gains a seed that reads either book, funding events, held files and the revenue plan from approved terms; a cross-check test runs the generated truth through `app.calc`.

**Tech Stack:** Python 3.13, `Decimal`/`int` (no floats), reportlab and PyMuPDF (PDF), openpyxl (the xlsx export), pytest (`uv run pytest`), ruff, PostgreSQL 16 for the seed tests.

**Spec:** `docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md` (sections 2, 3, 10 and 11 are this phase; 4–9 were built in Phase 1 — plan `docs/plans/2026-11-20-phase-1-lending-layer.md`). Owner decisions and defaults: `docs/owner-questions.md`. Owner's source of truth: `docs/specs/2026-11-17-credit-agent-squad-design.md`.

## Global Constraints

- **The model never types a number; the generator computes expected values independently of `app/calc`.** Nothing under `synthetic/` imports from `backend/app`, and `synthetic/tests` never import it. If the engine and the generator disagree, investigate; never patch one to match the other (CLAUDE.md). The cross-check lives in `backend/tests/calc/` and reads only the generator's JSON.
- **The v1 book is frozen (spec 2.3).** No legacy Python source, `synthetic/out/` file or `synthetic/oracle.csv` is edited, regenerated or changed (only `synthetic/README.md` gains a section). `synthetic/tests/test_legacy_frozen.py` pins every legacy source file and the four kept truth files by sha256. The existing engine tests keep running on `synthetic.generate`.
- **Bank of Stoic only.** Lender is "Bank of Stoic"; every document carries `SYNTHETIC - FOR DEMONSTRATION` on every page (the xlsx in a footer and a cell); no real bank or product name anywhere (a test scans every page). All names are invented, and none is searched on the web here — the owner checks them (Task 10).
- **Decimals and whole dollars only, never floats.** The innovation truth is whole dollars (`int`); ratios use `Decimal`, rounded half-up once at the end. A missing input is an error, never zero; an unmeasured metric is `None`, never zero; a ratio whose denominator is zero or negative is never computed — runway with average net burn ≤ 0 is "not meaningful: cash-flow positive" and the test is compliant with that note (spec 5, owner rule 10 proposal).
- **Spec 2.1 figures at 31 October 2026 are exact:** the twelve demo clients keep unrestricted cash, average monthly net burn (August–October 2026) and RML to the dollar and the decimal. Net burn = capex + capitalised software spend − operating cash flow (spec 5), financing excluded.
- **Spec 3 cadence:** as-of Thursday 19 November 2026; current period 31 October 2026 for innovation clients (30 September 2026 for the kept four); 18 monthly periods May 2025 to October 2026; monthly financials within 30 days of month end, monthly compliance certificate, MRR/ARR report and bank statements monthly, audited annual within 180 days of year end.
- **Plan figures are approved terms data** (`revenue_vs_plan.params.plan`), never read from a budget column of a borrower document; the covenant is `revenue_vs_plan` at **0.80** of plan on **trailing-three-months revenue** (owner default).
- **RML watch level is 12 months** for everyone and is a signal parameter, not a term (owner default); the covenant floor is 6.0 months. The kept four stay quarterly (owner default).
- **`Borrower.code` ≤ 32 characters; the hosted ledger is not touched** (hosting is Phase 5).
- **Answer key:** new rows arrive with `owner_signed_off = no`; rows for the kept four keep `yes` through `_keep_sign_off` against the v1 oracle; a regenerated row whose values changed comes back unsigned (lesson `docs/lessons/a-rule-change-moves-the-product-and-the-answer-key-together.md`).
- **Commands and style:** `uv run pytest` from the repo root with Postgres started (`service postgresql start`); `uv run ruff check .` clean (line length 110). Every existing test passes after every task. Commit after every task with a `feat(p2):` prefix.
- **Concurrent work in `backend/`:** another agent is editing `backend/` (at plan time, uncommitted changes in `seed_book.py`, `signals_service.py`, `funding.py`, `worker.py` and others). Backend steps in Tasks 7–9 are edits by exact anchor text, never whole-file rewrites; re-read each file first, and if an anchor has moved apply the same change by hand.

## Review Focus

Spec silent or thin; each line has its test in the owning task.

1. **Pledged or escrowed cash on a certificate.** A certificate that adds a pledged (Dataflake) or newly restricted (Tidewell) account to unrestricted cash must produce the true figure from the bank statements and a breach / variance, never a pass on the borrower's word; the clause is quoted from §1.1 of the agreement. Tests: Task 3 (accounts tie to the balance sheet), Task 5, Task 6 (the pages say it), Task 8 (seeded outcome `breach_reported_compliant`), Task 9 (engine agrees).
2. **A plan that stops short of the test month.** The approved plan runs to October 2026 (the book's last month); November must come back "cannot test: no approved plan figure for 2026-11-30", never a comparison against a partial plan. Test: Task 9.
3. **Cash-flow-positive client.** Ferrogate's average net burn is negative: runway is "not meaningful", the covenant is compliant with the note, the certificate's own runway figure is ignored, no runway signal fires and nothing divides. Tests: Tasks 2, 5, 6, 8, 9.
4. **Trailing three months across the fiscal year end.** January 2026's trailing three months are November and December 2025 and January, never zero for the missing months; the engine's YTD-difference arithmetic must equal the generator's discrete-month sum. Tests: Task 2 (identity), Task 9 (every month January–March 2026 agrees with `app.calc`).
5. **A file that names no company and shows the wrong year.** Stripple's `mrr_export.xlsx` is held unclassified, not filed against an obligation and not guessed; the seed ingests PDFs only, so the workbook is skipped and its PDF print is the held file. Tests: Task 6 (the workbook and print), Task 8 (held, `doc_type` None, no obligation matched).

## Rulings made in this plan (the spec was silent; overrule any)

| # | Ruling | Why |
|---|---|---|
| 1 | The four extra clients' cash, burn and runway: Corvane $8.4M / $0.60M / 14.0, Nimbusfield $3.3M / $0.40M / 8.3 (under 9: high signal), Tidewell $4.3M after the new restricted account / $0.35M / 12.3, Ferrogate $16.0M / −$0.25M / not meaningful | spec 2.1 gives situations only |
| 2 | Due days: financials 30 and certificate 30 (spec 3), MRR report 15, bank statements 7 | "October reporting 12 days late" at an as-of of 19 November only works for a 7-day item (due 7 November) |
| 3 | Lumora's package is the bank statements (12 days late) and the MRR report (4 days late); financials and certificate are not yet due. 12 days is under the 15-day `reporting_late` threshold, so the exception is the missing-document chaser, not a signal | follows from ruling 2 and the Phase 1 rule |
| 4 | October covenant tests for Lumora are `cannot_test` with `after_repair`, signals unmeasured (the v1 pattern for a late package) | the spread is blocked until the package arrives |
| 5 | Corvane's plan miss is a breach (`covenant.breach`, high) in September and October, honestly reported; August (87%) passes | spec says "two months running" and "Covenant breach" |
| 6 | Tidewell's cash mismatch is `compliant_variance` in the calculation (both figures pass) and the exception `cash.statement_mismatch` — a new type for a statements-to-certificate reconciliation that Phase 3 builds. It is pinned as "pending" in the cross-check and seed tests so the suite fails the day either side moves | the current engine records a passing variance on the ledger only |
| 7 | Stripple's three problems are two exceptions in the key: `intake.unclassified` (the held file) and one `spread.value_unverified` for the statements (new line plus the capitalised software doubt). The seed raises stand-in items for them (the v1 pattern); live behaviour is Phase 3 | the spreading agent groups mapping doubts into one item |
| 8 | `mrr_export.xlsx` is the real workbook and `mrr_export.pdf` is its print, because intake accepts PDFs only | `ingest_pdf` refuses anything else |
| 9 | **Controller amendment (overrules the draft):** the owner asked for DSCR in the covenant set ("covenants - have DSCR as well"). Ferrogate (the only client with positive EBITDA) gets a DSCR covenant (TTM basis, minimum 1.25x) in a terms version with `effective_from` 2026-05-31, so tests exist only from May 2026 and no earlier `cannot_test` rows appear; the earlier terms version carries no DSCR. The expected values and oracle rows for those months are produced by the independent generator like every other test. Requires the Phase 1 fix that passes the borrower's template into `test_covenant` (done in the Phase 1 close) | Owner instruction; spec 5 "DSCR only where sensible" |
| 10 | Tests run from August 2025 (15 monthly tests per client, 720 in all): a trailing three months needs the month before them, so May–July 2025 cannot be tested from published periods. The simulation runs from January 2025 so year-to-date figures are right | publishing starts May 2025 |
| 11 | Funding events: Dataflake `extension` $8M `signed` (term sheet signed), closing 12 December 2026; Halcyon `equity_round` $12M `expected` 31 March 2027; Kelvra `milestone_tranche` $4M `expected` 26 February 2027; Nimbusfield `equity_round` $15M `expected` 6 November 2026 (the date the bank was told), which has passed, so the check marks it `slipped` | spec 2.1 and 10 |
| 12 | The kept four keep their v1 truth, so their `as_of` stays 17 November; the book's as-of is 19 November. The seed uses the latest `as_of` for the demonstration clock | byte-identical kept borrowers |
| 13 | Fiscal 2024 (the comparative column of the audited statements) is fiscal 2025 scaled by 0.62, recorded as derived in its memo; the December 2024 balance sheet is the opening balance sheet | the simulation starts January 2025 |
| 14 | Every client has a Bank of Stoic venture term loan, drawn in full (Veridia drew $5M of an $8M facility in April 2026); every balance sheet carries it | the terms attach to a facility |

**Found while reading Phase 1 (not changed here):** `run_covenant_tests` does not pass the borrower's template to `test_covenant`, so a `vc-1` DSCR would be tested with `ci-1` formulas (matters only when ruling 9 is reversed); the runway and plan signals store no source facts (`signals_service._source_facts` only covers rules with a `metric` parameter), so the "every signal figure has a stored fact" check that v1's seed test makes is not repeated for them in Task 8.

---

## File map

| File | Change |
|---|---|
| `synthetic/books/__init__.py`, `synthetic/books/innovation/__init__.py` | new packages |
| `synthetic/books/innovation/roster.py` | `ClientSpec`, the 16 clients (spec 2.1 figures), scenarios, constants |
| `synthetic/books/innovation/names.py` | every invented name, with what to check first |
| `synthetic/books/innovation/model.py` | monthly truth model, identities, periods, comparative |
| `synthetic/books/innovation/expected.py` | independent expected values: plan, covenant rows, outcomes, signals |
| `synthetic/books/innovation/terms.py` | agreement text (`LegalDoc`), terms version, facility |
| `synthetic/books/innovation/reports.py` | certificates, bank accounts, MRR bridge, software roll |
| `synthetic/books/innovation/layout.py` | printed layout and labels of the vc-1 statements |
| `synthetic/render/innovation.py` | renderers: monthly and annual statements, MRR report, bank statement, certificate, notices, export |
| `synthetic/books/innovation/documents.py` | which documents exist, dates, payloads |
| `synthetic/books/innovation/book.py` | `ClientBook`, assembly, scenario verification |
| `synthetic/books/innovation/kept.py` | the four kept C&I borrowers via the frozen v1 code |
| `synthetic/books/innovation/generate.py` | CLI: truth, documents, manifest, oracle |
| `synthetic/books/innovation/out/{truth,manifest.json}`, `synthetic/books/innovation/oracle.csv` | generated, committed (documents are git-ignored) |
| `synthetic/tests/test_legacy_frozen.py`; `synthetic/tests/innovation/*` | new tests |
| `synthetic/README.md`, `.gitignore`, `CLAUDE.md`, `docker-compose.yml`, `docs/owner-questions.md`, `docs/HANDOFF.md` | documentation |
| `backend/app/domain/documents.py` | monthly document types |
| `backend/app/domain/signals_service.py` | `approved_plan`; plan passed to the venture signal inputs |
| `backend/app/seed_book.py` | `BOOKS`, `--book`, funding events, held files, non-PDF skip, stand-ins, latest as-of |
| `backend/tests/domain/test_document_types.py`, `test_approved_plan.py`; `backend/tests/test_seed_innovation.py`; `backend/tests/calc/test_synthetic_innovation_truth.py` | new tests |

---

### Task 1: Scaffolding, the frozen-legacy guard, the roster and the names list

**Files:**
- Create: `synthetic/books/__init__.py` (empty), `synthetic/books/innovation/__init__.py`, `synthetic/books/innovation/roster.py`, `synthetic/books/innovation/names.py`
- Create: `synthetic/tests/test_legacy_frozen.py`, `synthetic/tests/innovation/test_roster.py`

**Interfaces:**
- Consumes: `synthetic.scenarios.RMS`, `ANALYSTS`, `AUDITORS`, `ROSTER` (frozen v1).
- Produces: `LENDER`, `AS_OF` (2026-11-19), `CURRENT_PERIOD` (2026-10-31), `DEFAULT_SEED` (20261120), `LEGACY_SEED` (20261117), `KEPT_IDS`, `SCENARIOS: dict[str, str]`, `FundingSpec(kind, amount, expected_close, status, note)`, `ClientSpec` (frozen dataclass: `id, name, sector, stage, city, state, cash, burn, rml, mrr, growth, gross_margin, customers, pledged, venture_debt, min_cash, scenario, shape, rm, analyst, cfo, auditor, closing_date, risk_rating, sti, history, funding, min_rml, plan_floor, capsw_frac, legal_form, extra`), `CLIENTS: tuple[ClientSpec, ...]` (16), `BY_ID`; `invented_names() -> list[dict]` (`kind`, `name`, `sector`, `watch`).

- [ ] **Step 1: Write the failing tests**

`synthetic/tests/test_legacy_frozen.py`

```python
"""The v1 book is frozen (design spec 2.3): the existing engine tests run on it, and the kept four rest on it.

A failure here means a legacy generator file changed. If that was deliberate, say so in the commit, regenerate
`synthetic/out`, have the owner re-sign what moved, and update the digests below; never edit the key to make it pass."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "book.py": "df0bcbab44f214b92a72b4b17d7dad6e5b8df155d202f0c0545b65ed7672e674",
    "certificates.py": "b0983ffc3002f73585ed40159266c0fa4fa13fa0dc99646016afb1f0fab55177",
    "collateral.py": "3b8eead1e2e44b7768d81c18f1df38b571b234e044d93fcda69d1f05745e14c7",
    "expected.py": "50538df6a5cb1d322ebec8dec62d53b435d5045ebe32644136820348cdcf421a",
    "generate.py": "b31db0b252a2f3c2e1b3dee44c0a7871c8195cd3be122f83ff056c058fb36588",
    "model.py": "34c97762adce57b51766fb7387e9c587d2e1df96f353c3638d7c20f9e482087d",
    "scenarios.py": "401832e5c62e8e65e7f333fc982fd1866e9815c70f88fbb8d65d31b1aad97d47",
    "terms.py": "b14b53d5d12237ef9ef71509603efa62401524c885a466e4af75d5d156abe832",
    "render/__init__.py": "809d3245e0ac45db447987b20af07c15101fd4373c6084202a8f7ff9b2712550",
    "render/certificates.py": "5f46348d615eb03d1498f65cabbf924f36b97e0e575c05ada45e158f0b97ab53",
    "render/common.py": "42a797bceb6f12b96f2ebf49e010c4edb3327c0a24494bd07852a573ade4a668",
    "render/legal.py": "5950ae6a3db6290a810f672a47411c9027cc21e943cfb9beec4f3e48105ad388",
    "render/statements.py": "4d95875ce13e5492a4d261006a979842a48f4bf02b89891e9dc1dabd7082a2cc",
}  # fmt: skip
TRUTH = {
    "kestrel-bay-packaging": "9d08a6c314ecee174eddc578885efd213de7b859bf22a9358f9eb6e543e23b10",
    "harrowgate-precision": "7244c3d51b3c1bfc7882997c407902d45b5a25698431cdbc1758b172eb4809c1",
    "briarstone-beverage": "4931dc641fdd5836a1228f68546ce075706d75e99f0144fda044bdb434525e3a",
    "pellham-grain": "eca053369d10b150700ac45e41eb5c2fa570cac412843210c6bd7f99b65d19fe",
}  # fmt: skip


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_legacy_source_is_unchanged(name):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == SOURCES[name], f"synthetic/{name} changed"


@pytest.mark.parametrize("borrower_id", sorted(TRUTH))
def test_kept_truth_files_are_unchanged(borrower_id):
    path = ROOT / "out" / "truth" / f"{borrower_id}.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == TRUTH[borrower_id]
```

`synthetic/tests/innovation/test_roster.py`

```python
"""The roster is the owner's (design spec 2.1), and every invented name is listed for checking."""

from __future__ import annotations

import re

from synthetic.books.innovation.names import invented_names
from synthetic.books.innovation.roster import (
    AS_OF,
    BY_ID,
    CLIENTS,
    CURRENT_PERIOD,
    KEPT_IDS,
    LEGACY_SEED,
    SCENARIOS,
)
from synthetic.scenarios import ROSTER

# spec 2.1, as the owner wrote it: unrestricted cash, average monthly net burn over the last three months, RML
OWNER = {
    "dataflake": (4_600_000, 650_000, "7.1"), "lumora-health": (4_000_000, 420_000, "9.5"),
    "brightvane-energy": (5_500_000, 450_000, "12.2"), "mosswell-robotics": (7_800_000, 600_000, "13.0"),
    "halcyon-grid": (2_600_000, 200_000, "13.0"), "quillon-ai": (12_000_000, 800_000, "15.0"),
    "kelvra-bio": (9_200_000, 500_000, "18.4"), "orbitline-systems": (3_900_000, 210_000, "18.6"),
    "stripple-tech": (6_600_000, 300_000, "22.0"), "veridia-payments": (14_000_000, 550_000, "25.5"),
    "tessaract-labs": (11_000_000, 400_000, "27.5"), "pellucid-sensors": (6_300_000, 220_000, "28.6"),
}  # fmt: skip
REAL_BANKS = ("JPMorgan", "Chase", "Wells Fargo", "Citibank", "Citigroup", "Silicon Valley Bank", "SVB",
              "Bank of America", "HSBC", "Goldman", "Morgan Stanley", "First Republic", "Signature Bank", "Comerica",
              "Capital One")  # fmt: skip


def test_sixteen_clients_with_distinct_short_ids_and_the_owners_twelve_exactly():
    assert len(CLIENTS) == 16 == len({c.id for c in CLIENTS}) == len({c.name for c in CLIENTS})
    assert all(len(c.id) <= 32 for c in CLIENTS)  # Borrower.code is at most 32 characters
    for client_id, (cash, burn, rml) in OWNER.items():
        spec = BY_ID[client_id]
        assert (spec.cash, spec.burn, spec.rml) == (cash, burn, rml), client_id
    assert {c.id for c in CLIENTS} - set(OWNER) == {
        "corvane-analytics", "nimbusfield-security", "tidewell-medical", "ferrogate-cloud"}
    assert BY_ID["ferrogate-cloud"].rml is None and BY_ID["ferrogate-cloud"].burn < 0


def test_every_scenario_is_declared_and_the_kept_four_are_in_the_v1_roster():
    assert {c.scenario for c in CLIENTS} == set(SCENARIOS)
    v1 = {spec.id: spec for spec in ROSTER}
    assert set(KEPT_IDS) <= set(v1) and len(KEPT_IDS) == 4
    assert {v1[i].scenario for i in KEPT_IDS} == {"hidden_breach", "clean", "over_advance", "reported_breach"}
    assert LEGACY_SEED == 20261117  # the v1 seed: the kept four are built with it


def test_the_dates_are_a_thursday_in_mid_november_and_a_month_end():
    assert AS_OF.strftime("%A") == "Thursday" and (AS_OF.year, AS_OF.month) == (2026, 11)
    assert (CURRENT_PERIOD.year, CURRENT_PERIOD.month, CURRENT_PERIOD.day) == (2026, 10, 31)


def test_the_invented_names_are_listed_for_the_owner_to_check():
    rows = invented_names()
    assert len(rows) == 32 and len({r["name"] for r in rows}) == 32
    assert [r["name"] for r in rows if r["kind"] == "company"] == [c.name for c in CLIENTS]
    assert any(r["watch"] for r in rows)
    assert not [r for r in rows for bank in REAL_BANKS if re.search(rf"\b{re.escape(bank)}\b", r["name"])]
```

- [ ] **Step 2: Run to verify the roster tests fail and the freeze guard passes**

Run: `uv run pytest synthetic/tests/test_legacy_frozen.py synthetic/tests/innovation/test_roster.py -v`
Expected: the freeze tests PASS (they pin the tree as it stands — if any fails, stop and tell the owner: the legacy tree differs from the digests recorded when this plan was written); `test_roster.py` fails at collection with `ModuleNotFoundError: No module named 'synthetic.books'`.

- [ ] **Step 3: Implement**

`synthetic/books/innovation/__init__.py`

```python
"""The innovation-banking book: 16 venture-backed clients (monthly, template vc-1) and the four kept C&I borrowers."""
```

`synthetic/books/innovation/roster.py`

```python
"""The 16 innovation clients (spec 2.1) and the constants of the book. Figures marked (spec) are the owner's."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from synthetic.scenarios import ANALYSTS, AUDITORS, RMS

LENDER = "Bank of Stoic"
AS_OF = date(2026, 11, 19)  # a Thursday
CURRENT_PERIOD = date(2026, 10, 31)
DEFAULT_SEED = 20261120
LEGACY_SEED = 20261117  # the kept four are built with the v1 seed so that they stay byte-identical
KEPT_IDS = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")

SCENARIOS: dict[str, str] = {
    "clean": "Clean performer: covenants pass with room, documents complete and on time, no loud signal.",
    "pledged_cash": (
        "Pledged cash counted: the certificate adds cash pledged to a lease letter of credit to unrestricted cash "
        "and claims compliance; true unrestricted cash is below the minimum."
    ),
    "late_package": (
        "Late monthly package: the October bank statements and MRR report have not arrived, 12 and 4 days "
        "after their due dates; October cannot be tested yet."
    ),
    "runway_falling": "Runway falling: burn is rising and runway has fallen three months running, still above 12 months.",
    "funding_expected": "Clean book with an expected funding event the bank is tracking.",
    "stripple_package": (
        "Awkward October package: a new balance-sheet line (contract liabilities), capitalised software that can be "
        "misread as spending, and an MRR export with no company name and the wrong year."
    ),
    "plan_miss": (
        "Plan miss: trailing-three-months revenue is under 80 percent of the approved plan in September and October."
    ),
    "funding_slipped": (
        "Funding slipped: the round the bank was told would close on 6 November has not closed; runway is under "
        "9 months."
    ),
    "restricted_account": (
        "Restricted account: a new escrow collateral account was opened in October; the certificate counts it as "
        "unrestricted cash while the bank statements show it restricted."
    ),
    "cash_flow_positive": "Cash-flow positive: average net burn is negative, so runway is not meaningful (and not a division).",
}


@dataclass(frozen=True)
class FundingSpec:
    kind: str  # equity_round | extension | milestone_tranche | venture_debt
    amount: int
    expected_close: date
    status: str  # expected | signed
    note: str


@dataclass(frozen=True)
class ClientSpec:
    id: str
    name: str
    sector: str
    stage: str
    city: str
    state: str
    cash: int  # unrestricted cash at 2026-10-31 (spec)
    burn: int  # average monthly net burn, Aug-Oct 2026 (spec); negative means cash generative
    rml: str | None  # runway in months at 2026-10-31, one decimal (spec); None when not meaningful
    mrr: int  # MRR at 2026-10-31
    growth: str  # monthly MRR growth
    gross_margin: str
    customers: int  # customers at 2026-10-31
    pledged: int  # cash pledged or restricted at 2026-10-31
    venture_debt: int  # drawn from Bank of Stoic at 2026-10-31
    min_cash: int  # minimum unrestricted cash covenant
    scenario: str
    shape: str  # burn shape: steady | dip | rising | positive
    rm: str
    analyst: str
    cfo: str
    auditor: str
    closing_date: date
    risk_rating: int = 5
    sti: int = 0  # short-term investments, which are not cash for the covenants
    history: tuple[tuple[str, str, int], ...] = ()  # (YYYY-MM, "equity" | "debt", amount) inside the 22 months
    funding: tuple[FundingSpec, ...] = ()
    min_rml: str = "6.0"
    plan_floor: str = "0.80"
    capsw_frac: str = "0.07"  # capitalised software spend as a share of revenue
    legal_form: str = "corporation"
    extra: dict = field(default_factory=dict)


def _c(**kw) -> ClientSpec:
    return ClientSpec(**kw)


CLIENTS: tuple[ClientSpec, ...] = (
    _c(id="dataflake", name="Dataflake Inc", sector="Data infrastructure", stage="Series A", city="Austin",
       state="TX", cash=4_600_000, burn=650_000, rml="7.1", mrr=640_000, growth="0.030", gross_margin="0.70",
       customers=140, pledged=1_500_000, venture_debt=2_000_000, min_cash=5_000_000, scenario="pledged_cash",
       shape="steady", rm=RMS[0], analyst=ANALYSTS[0], cfo="Imogen Farrow", auditor=AUDITORS[0],
       closing_date=date(2024, 9, 12), risk_rating=6,
       funding=(FundingSpec("extension", 8_000_000, date(2026, 12, 12), "signed",
                            "Series B extension, term sheet signed, closing 12 December"),),
       extra={"pledged_note": "pledged to secure a hosting lease letter of credit"}),
    _c(id="lumora-health", name="Lumora Health", sector="Digital health", stage="Series B", city="Boston",
       state="MA", cash=4_000_000, burn=420_000, rml="9.5", mrr=470_000, growth="0.028", gross_margin="0.68",
       customers=96, pledged=400_000, venture_debt=2_000_000, min_cash=2_500_000, scenario="late_package",
       shape="steady", rm=RMS[1], analyst=ANALYSTS[1], cfo="Tobias Wenlock", auditor=AUDITORS[1],
       closing_date=date(2024, 6, 20), risk_rating=5),
    _c(id="brightvane-energy", name="Brightvane Energy", sector="Climate hardware", stage="Series A",
       city="Denver", state="CO", cash=5_500_000, burn=450_000, rml="12.2", mrr=380_000, growth="0.025",
       gross_margin="0.55", customers=62, pledged=600_000, venture_debt=1_500_000, min_cash=3_000_000,
       scenario="runway_falling", shape="rising", rm=RMS[2], analyst=ANALYSTS[2], cfo="Odalys Prentiss",
       auditor=AUDITORS[2], closing_date=date(2024, 11, 4), risk_rating=5),
    _c(id="mosswell-robotics", name="Mosswell Robotics", sector="Robotics", stage="Series A", city="Pittsburgh",
       state="PA", cash=7_800_000, burn=600_000, rml="13.0", mrr=700_000, growth="0.020", gross_margin="0.62",
       customers=85, pledged=500_000, venture_debt=2_500_000, min_cash=4_000_000, scenario="clean", shape="dip",
       rm=RMS[3], analyst=ANALYSTS[0], cfo="Reuben Castellane", auditor=AUDITORS[3],
       closing_date=date(2024, 3, 15), risk_rating=4),
    _c(id="halcyon-grid", name="Halcyon Grid", sector="Energy software", stage="Seed+", city="Portland",
       state="OR", cash=2_600_000, burn=200_000, rml="13.0", mrr=160_000, growth="0.035", gross_margin="0.74",
       customers=41, pledged=150_000, venture_debt=1_000_000, min_cash=1_500_000, scenario="funding_expected",
       shape="dip", rm=RMS[0], analyst=ANALYSTS[1], cfo="Marguerite Oyelowo", auditor=AUDITORS[0],
       closing_date=date(2025, 2, 10), risk_rating=5,
       funding=(FundingSpec("equity_round", 12_000_000, date(2027, 3, 31), "expected",
                            "Series A expected in the first quarter of 2027"),)),
    _c(id="quillon-ai", name="Quillon AI", sector="Applied AI", stage="Series B", city="San Francisco",
       state="CA", cash=12_000_000, burn=800_000, rml="15.0", mrr=1_150_000, growth="0.030", gross_margin="0.75",
       customers=210, pledged=800_000, venture_debt=5_000_000, min_cash=6_000_000, scenario="clean", shape="dip",
       rm=RMS[1], analyst=ANALYSTS[2], cfo="Sunniva Hartigan", auditor=AUDITORS[1],
       closing_date=date(2024, 1, 25), risk_rating=4, sti=3_000_000),
    _c(id="kelvra-bio", name="Kelvra Bio", sector="Biotech tools", stage="Series B", city="San Diego",
       state="CA", cash=9_200_000, burn=500_000, rml="18.4", mrr=520_000, growth="0.020", gross_margin="0.66",
       customers=74, pledged=400_000, venture_debt=3_000_000, min_cash=3_500_000, scenario="funding_expected",
       shape="dip", rm=RMS[2], analyst=ANALYSTS[0], cfo="Lysander Boateng", auditor=AUDITORS[2],
       closing_date=date(2024, 8, 8), risk_rating=4, history=(("2026-01", "equity", 10_000_000),),
       funding=(FundingSpec("milestone_tranche", 4_000_000, date(2027, 2, 26), "expected",
                            "Milestone tranche, expected in February 2027"),)),
    _c(id="orbitline-systems", name="Orbitline Systems", sector="Space software", stage="Series A",
       city="Huntsville", state="AL", cash=3_900_000, burn=210_000, rml="18.6", mrr=260_000, growth="0.030",
       gross_margin="0.70", customers=38, pledged=250_000, venture_debt=1_500_000, min_cash=2_000_000,
       scenario="clean", shape="dip", rm=RMS[3], analyst=ANALYSTS[1], cfo="Evander Pruitt", auditor=AUDITORS[3],
       closing_date=date(2025, 1, 17), risk_rating=4),
    _c(id="stripple-tech", name="Stripple Tech", sector="Fintech infrastructure", stage="Series B",
       city="Chicago", state="IL", cash=6_600_000, burn=300_000, rml="22.0", mrr=1_350_000, growth="0.025",
       gross_margin="0.78", customers=175, pledged=500_000, venture_debt=4_000_000, min_cash=3_500_000,
       scenario="stripple_package", shape="dip", rm=RMS[0], analyst=ANALYSTS[2], cfo="Cosima Aldridge",
       auditor=AUDITORS[0], closing_date=date(2024, 5, 30), risk_rating=5, capsw_frac="0.10"),
    _c(id="veridia-payments", name="Veridia Payments", sector="Payments", stage="Series C", city="Atlanta",
       state="GA", cash=14_000_000, burn=550_000, rml="25.5", mrr=2_400_000, growth="0.018", gross_margin="0.70",
       customers=390, pledged=1_200_000, venture_debt=8_000_000, min_cash=7_000_000, scenario="clean",
       shape="dip", rm=RMS[1], analyst=ANALYSTS[0], cfo="Anselm Okonkwo-Reyes", auditor=AUDITORS[1],
       closing_date=date(2023, 10, 19), risk_rating=4, sti=3_000_000, history=(("2026-04", "debt", 5_000_000),)),
    _c(id="tessaract-labs", name="Tessaract Labs", sector="Developer tools", stage="Series B", city="Seattle",
       state="WA", cash=11_000_000, burn=400_000, rml="27.5", mrr=1_050_000, growth="0.020", gross_margin="0.80",
       customers=520, pledged=600_000, venture_debt=4_000_000, min_cash=5_500_000, scenario="clean",
       shape="dip", rm=RMS[2], analyst=ANALYSTS[2], cfo="Philippa Strand", auditor=AUDITORS[2],
       closing_date=date(2024, 2, 2), risk_rating=4, sti=2_000_000),
    _c(id="pellucid-sensors", name="Pellucid Sensors", sector="Industrial IoT", stage="Series A",
       city="Minneapolis", state="MN", cash=6_300_000, burn=220_000, rml="28.6", mrr=330_000, growth="0.022",
       gross_margin="0.58", customers=54, pledged=300_000, venture_debt=1_000_000, min_cash=3_000_000,
       scenario="clean", shape="dip", rm=RMS[3], analyst=ANALYSTS[1], cfo="Garrick Lindahl", auditor=AUDITORS[3],
       closing_date=date(2024, 12, 5), risk_rating=4),
    _c(id="corvane-analytics", name="Corvane Analytics", sector="B2B SaaS", stage="Series B", city="Raleigh",
       state="NC", cash=8_400_000, burn=600_000, rml="14.0", mrr=801_000, growth="0.030", gross_margin="0.74",
       customers=118, pledged=500_000, venture_debt=3_000_000, min_cash=4_000_000, scenario="plan_miss",
       shape="dip", rm=RMS[0], analyst=ANALYSTS[2], cfo="Henrietta Voss", auditor=AUDITORS[0],
       closing_date=date(2024, 7, 11), risk_rating=6,
       extra={"jun_mrr": 900_000, "after_june": ["0.98", "0.95", "0.92", "0.89"], "plan_growth": "1.12"}),
    _c(id="nimbusfield-security", name="Nimbusfield Security", sector="Cybersecurity", stage="Series A",
       city="Reston", state="VA", cash=3_300_000, burn=400_000, rml="8.3", mrr=300_000, growth="0.030",
       gross_margin="0.72", customers=66, pledged=250_000, venture_debt=2_000_000, min_cash=2_000_000,
       scenario="funding_slipped", shape="steady", rm=RMS[1], analyst=ANALYSTS[0], cfo="Wilhelmina Achterberg",
       auditor=AUDITORS[1], closing_date=date(2025, 3, 6), risk_rating=6,
       funding=(FundingSpec("equity_round", 15_000_000, date(2026, 11, 6), "expected",
                            "Series A-2; the bank was told it would close on 6 November"),)),
    _c(id="tidewell-medical", name="Tidewell Medical", sector="Medical devices", stage="Series B",
       city="Nashville", state="TN", cash=4_300_000, burn=350_000, rml="12.3", mrr=540_000, growth="0.022",
       gross_margin="0.64", customers=88, pledged=1_100_000, venture_debt=2_500_000, min_cash=3_000_000,
       scenario="restricted_account", shape="steady", rm=RMS[2], analyst=ANALYSTS[1], cfo="Barnaby Ekwueme",
       auditor=AUDITORS[2], closing_date=date(2024, 4, 18), risk_rating=5,
       extra={"newly_restricted": 1_000_000, "restricted_before": 100_000}),
    _c(id="ferrogate-cloud", name="Ferrogate Cloud", sector="Cloud infrastructure", stage="Series C",
       city="Dallas", state="TX", cash=16_000_000, burn=-250_000, rml=None, mrr=3_000_000, growth="0.015",
       gross_margin="0.80", customers=300, pledged=700_000, venture_debt=6_000_000, min_cash=8_000_000,
       scenario="cash_flow_positive", shape="positive", rm=RMS[3], analyst=ANALYSTS[2], cfo="Ignatius Valcourt",
       auditor=AUDITORS[3], closing_date=date(2023, 12, 14), risk_rating=3, sti=4_000_000),
)
BY_ID: dict[str, ClientSpec] = {c.id: c for c in CLIENTS}
```

`synthetic/books/innovation/names.py`

```python
"""Every invented name in the innovation book, for the owner to check before anything is shown outside the team.

    uv run python -m synthetic.books.innovation.names

No web search is done here: the list says what to check, not what was found. Names reused from the v1 book (the
relationship managers, analysts, credit officers, auditors and the kept four) were checked with v1."""

from __future__ import annotations

from synthetic.books.innovation.roster import CLIENTS

LOOKS_LIKE = {
    "stripple-tech": "close in sound to a well-known payments company",
    "tessaract-labs": "a spelling variant of a common word used by many products",
    "dataflake": "data-infrastructure names are crowded",
    "veridia-payments": "close to 'Veridian', used by several companies",
    "halcyon-grid": "a common word used by many companies",
    "quillon-ai": "close to other 'Quill' product names",
}


def invented_names() -> list[dict]:
    rows = []
    for spec in CLIENTS:
        rows.append({"kind": "company", "name": spec.name, "sector": spec.sector, "watch": LOOKS_LIKE.get(spec.id, "")})
    for spec in CLIENTS:
        rows.append({"kind": "person", "name": spec.cfo, "sector": f"chief financial officer, {spec.name}", "watch": ""})
    return rows


def main() -> None:
    print("| Kind | Name | Where | Check first because |\n|---|---|---|---|")
    for row in invented_names():
        print(f"| {row['kind']} | {row['name']} | {row['sector']} | {row['watch'] or '-'} |")


if __name__ == "__main__":
    main()
```

Also create the empty `synthetic/books/__init__.py`.

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest synthetic/tests/test_legacy_frozen.py synthetic/tests/innovation/test_roster.py -v && uv run ruff check synthetic`
Expected: PASS (22 tests: 14 legacy source digests, 4 kept truth digests, 4 roster tests), ruff clean.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books synthetic/tests/test_legacy_frozen.py synthetic/tests/innovation/test_roster.py
git commit -m "feat(p2): innovation roster, frozen-legacy guard and the names list"
```

---

### Task 2: The monthly truth model and the independent expected values

**Files:**
- Create: `synthetic/books/innovation/model.py`, `synthetic/books/innovation/expected.py`
- Create: `synthetic/tests/innovation/conftest.py`, `synthetic/tests/innovation/test_model.py`, `synthetic/tests/innovation/test_expected.py`

**Interfaces:**
- Consumes: `ClientSpec`, `CLIENTS`, `DEFAULT_SEED` (Task 1).
- Produces (`model`): `MONTHS` (22 month ends, Jan 2025–Oct 2026), `N`, `LAST`, `PUBLISHED_FROM` (4), `OPENING_END`, `month_end(y, m)`, `rnd`, `ALL_KEYS` (the vc-1 keys), `FORMULAS`, `apply_formulas(values)`, `Month(end, flows, balances, memo)`, `Period(period_end, months, fiscal_year, quality, values, memo)`, `simulate(spec, seed) -> (opening: Month, months: list[Month])`, `build_periods(months) -> list[Period]` (year-to-date flows), `comparative_fy2024(opening, fy2025) -> Period`, `check_periods(opening, periods) -> list[str]`.
- Produces (`expected`): `Series(months)` with `flow3`, `net_burn3`, `avg_burn`, `cash`, `rml` (None when not meaningful), `revenue`, `revenue3`; `FIRST_TEST` (7), `DUE_DAYS`, `COVENANTS`, `TOLERANCE`, `EXCEPTION_SEVERITY`, `q(value, dp)`, `build_plan(spec, series) -> dict[date, int]`, `plan_ratio(series, plan, i)`, `cert_months(spec)`, `cert_cash`, `cert_entry`, `classify(...)`, `covenant_rows(spec, series, plan, version_id, facility_id) -> list[dict]`, `compute_signals(series, plan, rows, i, days_late) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

The conftest starts with the `sims` fixture only (Tasks 5 and 6 extend it).

`synthetic/tests/innovation/conftest.py`

```python
"""Fixtures for the innovation book: every client simulated, nothing else built."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.expected import Series
from synthetic.books.innovation.roster import CLIENTS, ClientSpec


@dataclass
class Sim:
    """One client simulated, with nothing else built."""

    spec: ClientSpec
    opening: model.Month
    months: list[model.Month]
    periods: list[model.Period]
    series: Series


@pytest.fixture(scope="session")
def sims() -> dict[str, Sim]:
    out = {}
    for spec in CLIENTS:
        opening, months = model.simulate(spec)
        out[spec.id] = Sim(spec, opening, months, model.build_periods(months), Series(months))
    return out
```

`synthetic/tests/innovation/test_model.py`

```python
"""The monthly truth model and its expected arithmetic: the owner's October figures exactly, and every statement balances and ties."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.expected import Series, q
from synthetic.books.innovation.roster import BY_ID

# spec 2.1, as the owner wrote it: unrestricted cash, average monthly net burn over the last three months, RML
OWNER = {
    "dataflake": (4_600_000, 650_000, "7.1"), "lumora-health": (4_000_000, 420_000, "9.5"),
    "brightvane-energy": (5_500_000, 450_000, "12.2"), "mosswell-robotics": (7_800_000, 600_000, "13.0"),
    "halcyon-grid": (2_600_000, 200_000, "13.0"), "quillon-ai": (12_000_000, 800_000, "15.0"),
    "kelvra-bio": (9_200_000, 500_000, "18.4"), "orbitline-systems": (3_900_000, 210_000, "18.6"),
    "stripple-tech": (6_600_000, 300_000, "22.0"), "veridia-payments": (14_000_000, 550_000, "25.5"),
    "tessaract-labs": (11_000_000, 400_000, "27.5"), "pellucid-sensors": (6_300_000, 220_000, "28.6"),
}  # fmt: skip


@pytest.mark.parametrize("client_id", sorted(OWNER))
def test_the_owners_october_figures_exactly(sims, client_id):
    cash, burn, rml = OWNER[client_id]
    series = sims[client_id].series
    assert series.cash(model.LAST) == cash
    assert series.avg_burn(model.LAST) == burn  # the mean of August, September and October, to the dollar
    assert q(series.rml(model.LAST), 1) == D(rml)


def test_every_statement_balances_foots_and_ties(sims):
    for book in sims.values():
        assert model.check_periods(book.opening, book.periods) == [], book.spec.id


def test_eighteen_months_are_published_from_may_2025(sims):
    book = sims["dataflake"]
    published = book.periods[model.PUBLISHED_FROM :]
    assert published[0].period_end == date(2025, 5, 31) and published[-1].period_end == date(2026, 10, 31)
    assert len(published) == 18 and len(book.periods) == 22


def test_the_vc1_lines_are_the_template_lines(sims):
    assert "saas.mrr" in model.ALL_KEYS and "cf.capitalised_software_spend" in model.ALL_KEYS
    assert len(model.ALL_KEYS) == len(set(model.ALL_KEYS))
    p = sims["quillon-ai"].periods[-1]
    assert set(p.values) == set(model.ALL_KEYS)
    assert p.values["saas.arr"] == 12 * p.values["saas.mrr"]


def test_financing_inflows_are_not_burn(sims):
    """Kelvra raised 10 million in January 2026 and Veridia drew 5 million of venture debt in April: cash jumps
    that month, net burn does not move."""
    kelvra, veridia = sims["kelvra-bio"], sims["veridia-payments"]
    jan = model.MONTHS.index(date(2026, 1, 31))
    assert kelvra.months[jan].flows["cf.equity_raised"] == 10_000_000
    change = kelvra.months[jan].flows["cf.vc_net_change_in_cash"]
    assert change > 9_000_000
    assert abs(kelvra.series.avg_burn(jan) - 500_000) < 150_000
    apr = model.MONTHS.index(date(2026, 4, 30))
    assert veridia.months[apr].flows["cf.debt_raised"] == 5_000_000
    assert veridia.months[apr].balances["bs.venture_debt_current"] + veridia.months[apr].balances[
        "bs.venture_debt_noncurrent"] == 8_000_000


def test_net_burn_is_capex_plus_capitalised_software_less_operating_cash_flow(sims):
    month = sims["stripple-tech"].months[model.LAST]
    f = month.flows
    burn = f["cf.vc_capex"] + f["cf.capitalised_software_spend"] - f["cf.vc_operating_cash_flow"]
    assert f["cf.vc_net_change_in_cash"] == -burn  # no financing that month


def test_trailing_three_months_across_a_fiscal_year_end(sims):
    """Review focus: January's trailing three months use November and December of the prior year, not zeros."""
    book = sims["mosswell-robotics"]
    jan = model.MONTHS.index(date(2026, 1, 31))
    key = "cf.vc_operating_cash_flow"
    direct = book.series.flow3(key, jan)
    nov, dec = book.months[jan - 2].flows[key], book.months[jan - 1].flows[key]
    assert direct == nov + dec + book.months[jan].flows[key] and nov != 0 and dec != 0
    # the identity the engine relies on: YTD(Jan) + FY2025 - YTD(October 2025)
    ytd = {p.period_end: p.values[key] for p in book.periods}
    assert ytd[date(2026, 1, 31)] + ytd[date(2025, 12, 31)] - ytd[date(2025, 10, 31)] == direct


def test_ferrogate_generates_cash_and_runway_is_not_meaningful(sims):
    series = sims["ferrogate-cloud"].series
    assert series.avg_burn(model.LAST) == -250_000 and series.rml(model.LAST) is None


def test_clean_clients_do_not_trip_runway_falling_and_brightvane_does(sims):
    def falling(series: Series) -> bool:
        points = [series.rml(i) for i in range(model.LAST - 3, model.LAST + 1)]
        return all(b < a for a, b in zip(points, points[1:], strict=False))

    for client_id in ("mosswell-robotics", "quillon-ai", "orbitline-systems", "veridia-payments", "tessaract-labs",
                      "pellucid-sensors", "halcyon-grid", "kelvra-bio", "stripple-tech", "corvane-analytics"):
        assert not falling(sims[client_id].series), client_id
    assert falling(sims["brightvane-energy"].series)


def test_same_seed_same_truth_and_a_new_seed_keeps_the_owners_figures():
    spec = BY_ID["dataflake"]
    a, b = model.simulate(spec, 1), model.simulate(spec, 1)
    assert [m.flows for m in a[1]] == [m.flows for m in b[1]]
    other = model.simulate(spec, 2)
    assert [m.flows for m in other[1]] != [m.flows for m in a[1]]
    assert Series(other[1]).cash(model.LAST) == spec.cash and Series(other[1]).net_burn3(model.LAST) == 3 * spec.burn
```

`synthetic/tests/innovation/test_expected.py`

```python
"""The expected arithmetic: plan, covenant rows, outcomes against the certificate, and the startup signals."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from synthetic.books.innovation import model
from synthetic.books.innovation.expected import (
    FIRST_TEST,
    build_plan,
    classify,
    compute_signals,
    covenant_rows,
    plan_ratio,
    q,
)  # fmt: skip

LAST = model.LAST
CURRENT = date(2026, 10, 31)


def rows_for(sim):
    plan = build_plan(sim.spec, sim.series)
    return plan, covenant_rows(sim.spec, sim.series, plan, "tv", "f")


def test_fifteen_tested_months_three_covenants_each_from_august_2025(sims):
    plan, rows = rows_for(sims["dataflake"])
    assert len(rows) == 15 * 3 == 3 * (model.N - FIRST_TEST)
    assert rows[0]["period_end"] == date(2025, 8, 31) and rows[-1]["period_end"] == CURRENT
    assert [r["covenant_id"] for r in rows[:3]] == ["min_unrestricted_cash", "min_runway_months", "revenue_vs_plan"]
    assert len(plan) == 18 and all(v % 1000 == 0 for v in plan.values())  # May 2025 to October 2026, to the thousand


def test_clean_clients_beat_plan_by_about_five_percent(sims):
    for client_id in ("mosswell-robotics", "quillon-ai", "pellucid-sensors"):
        sim = sims[client_id]
        plan = build_plan(sim.spec, sim.series)
        assert all(D("1.04") < plan_ratio(sim.series, plan, i) < D("1.06") for i in range(FIRST_TEST, model.N))


def test_corvane_falls_under_the_floor_in_september_and_october_only(sims):
    sim = sims["corvane-analytics"]
    plan = build_plan(sim.spec, sim.series)
    ratio = {i: plan_ratio(sim.series, plan, i) for i in (LAST - 3, LAST - 2, LAST - 1, LAST)}
    assert ratio[LAST - 3] > D("0.95") and ratio[LAST - 2] >= D("0.84")
    assert ratio[LAST - 1] <= D("0.77") and ratio[LAST] <= D("0.77")


def test_a_cash_flow_positive_runway_is_not_meaningful_and_never_divides(sims):
    sim = sims["ferrogate-cloud"]
    plan, rows = rows_for(sim)
    row = next(r for r in rows if r["covenant_id"] == "min_runway_months" and r["period_end"] == CURRENT)
    assert (row["value"], row["pass"], row["headroom"], row["note"]) == (
        None, True, None, "not_meaningful_cash_flow_positive")
    assert (row["reported_value"], row["reported_in_compliance"], row["outcome"]) == (None, True, "compliant")


def test_outcome_table():
    unit = "usd"
    assert classify(False, D(1), True, D(2), True, unit) == "breach_reported_compliant"
    assert classify(False, D(1), True, D(1), False, unit) == "breach"
    assert classify(False, D(1), False, None, None, unit) == "breach"
    assert classify(True, D(5000), True, D(5000), True, unit) == "compliant"
    assert classify(True, D(5000), True, D(9000), True, unit) == "compliant_variance"
    assert classify(True, D(5000), False, None, None, unit) == "compliant"
    assert classify(True, None, True, None, False, "months") == "compliant_variance"  # n/m, certificate says no


def test_dataflakes_certificate_counts_pledged_cash_and_the_covenant_breaches(sims):
    _, rows = rows_for(sims["dataflake"])
    cash = next(r for r in rows if r["covenant_id"] == "min_unrestricted_cash" and r["period_end"] == CURRENT)
    assert (cash["value"], cash["reported_value"], cash["outcome"]) == (
        D(4_600_000), D(6_100_000), "breach_reported_compliant")
    runway = next(r for r in rows if r["covenant_id"] == "min_runway_months" and r["period_end"] == CURRENT)
    assert (runway["value"], runway["reported_value"], runway["outcome"]) == (D("7.1"), D("9.4"), "compliant_variance")
    assert all(r["outcome"] == "compliant" for r in rows if r["period_end"] != CURRENT)


def test_signals_follow_spec_7(sims):
    def current(client_id):
        sim = sims[client_id]
        plan, rows = rows_for(sim)
        return {(s["rule"], s["severity"]) for s in compute_signals(sim.series, plan, rows, LAST, [])}

    assert ("runway_below_watch", "high") in current("dataflake")  # 7.1 months is under 9
    assert ("runway_below_watch", "medium") in current("lumora-health")  # 9.5 is under 12 and not under 9
    assert ("runway_falling", "medium") in current("brightvane-energy")
    assert not any(rule.startswith("runway") or rule == "burn_rising" for rule, _ in current("mosswell-robotics"))
    assert ("revenue_below_plan", "medium") in current("corvane-analytics")
    assert q(sims["nimbusfield-security"].series.rml(LAST), 2) < 9


def test_reporting_lateness_over_fifteen_days_is_a_high_signal(sims):
    sim = sims["lumora-health"]
    plan, rows = rows_for(sim)
    quiet = compute_signals(sim.series, plan, rows, LAST, [("bank_statements", 12)])
    loud = compute_signals(sim.series, plan, rows, LAST, [("bank_statements", 16)])
    assert not [s for s in quiet if s["rule"] == "reporting_late"]
    assert [s["severity"] for s in loud if s["rule"] == "reporting_late"] == ["high"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest synthetic/tests/innovation/test_model.py synthetic/tests/innovation/test_expected.py -v`
Expected: collection fails with `ModuleNotFoundError: No module named 'synthetic.books.innovation.model'`.

- [ ] **Step 3: Implement**

The model works backwards from the owner's October figures: net burn is chosen first (one heavy July 2026 for clean clients so October runway is not lower than September's; steady 5 percent growth for Brightvane; a switch to cash generation in March 2026 for Ferrogate), cash is walked back from October, operating cash flow follows from the net burn formula, working-capital balances drive net income, and operating expenses are what make net income hold. The balance sheet balances by construction.

`synthetic/books/innovation/model.py`

```python
"""Monthly truth model for a venture-backed SaaS client (template vc-1).

Twenty-two months are simulated (January 2025 to October 2026) from an opening balance sheet at 2024-12-31; the
last eighteen (May 2025 to October 2026) are published. Everything is whole dollars (`int`), so every printed
figure is exactly derivable from the truth.

Construction runs backwards from the owner's October 2026 figures:

* net burn is chosen first (`burn_path`), with the last three months summing to exactly three times the target;
* net burn = capex + capitalised software spend - operating cash flow (spec 5), so operating cash flow follows;
* total cash is walked back from October 2026 (cash moves by -net burn plus financing inflows); unrestricted cash
  is total cash less the restricted balance;
* working-capital balances are drivers of revenue; net income is then what makes the cash flow identity hold,
  operating expenses are what make net income hold, and accumulated deficit rolls with net income.

The balance sheet therefore balances by construction; `check_periods` re-verifies it from the published figures.
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from synthetic.books.innovation.roster import DEFAULT_SEED, ClientSpec

D = Decimal


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


MONTHS: tuple[date, ...] = tuple(month_end(2025, m) for m in range(1, 13)) + tuple(
    month_end(2026, m) for m in range(1, 11)
)
N = len(MONTHS)  # 22 simulated months
LAST = N - 1  # October 2026
PUBLISHED_FROM = 4  # May 2025
OPENING_END = date(2024, 12, 31)
JULY_2026 = MONTHS.index(month_end(2026, 7))
JUNE_2026 = MONTHS.index(month_end(2026, 6))


def rnd(x) -> int:
    return int(D(x).quantize(D(1), rounding=ROUND_HALF_UP))


IS_IN = (
    "is.subscription_revenue", "is.services_revenue", "is.cost_of_revenue", "is.rnd", "is.sales_marketing",
    "is.gna", "is.vc_depreciation_amortization", "is.vc_interest", "is.vc_other_income",
)  # fmt: skip
CF_IN = (
    "cf.vc_operating_cash_flow", "cf.vc_capex", "cf.capitalised_software_spend", "cf.equity_raised",
    "cf.debt_raised", "cf.vc_other_financing",
)  # fmt: skip
SUP = ("sup.cash_interest_paid", "sup.scheduled_principal")
BS_IN = (
    "bs.cash_unrestricted", "bs.cash_restricted", "bs.short_term_investments", "bs.accounts_receivable",
    "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles", "bs.other_noncurrent_assets",
    "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current", "bs.deferred_revenue_noncurrent",
    "bs.venture_debt_current", "bs.venture_debt_noncurrent", "bs.convertible_notes", "bs.safes",
    "bs.vc_other_liabilities", "bs.preferred_equity", "bs.common_equity",
)  # fmt: skip
SAAS = ("saas.mrr", "saas.arr", "saas.customers")
# Subtotals in dependency order: key -> ((sign, component), ...). The generator's own copy of the vc-1 identities.
FORMULAS: dict[str, tuple[tuple[int, str], ...]] = {
    "is.total_revenue": ((1, "is.subscription_revenue"), (1, "is.services_revenue")),
    "is.vc_gross_profit": ((1, "is.total_revenue"), (-1, "is.cost_of_revenue")),
    "is.vc_operating_loss": (
        (1, "is.vc_gross_profit"), (-1, "is.rnd"), (-1, "is.sales_marketing"), (-1, "is.gna"),
        (-1, "is.vc_depreciation_amortization"),
    ),  # fmt: skip
    "is.vc_net_loss": ((1, "is.vc_operating_loss"), (-1, "is.vc_interest"), (1, "is.vc_other_income")),
    "bs.vc_total_cash": ((1, "bs.cash_unrestricted"), (1, "bs.cash_restricted")),
    "bs.vc_total_assets": (
        (1, "bs.vc_total_cash"), (1, "bs.short_term_investments"), (1, "bs.accounts_receivable"),
        (1, "bs.other_current_assets"), (1, "bs.capitalised_software"), (1, "bs.vc_other_intangibles"),
        (1, "bs.other_noncurrent_assets"),
    ),  # fmt: skip
    "bs.vc_total_liabilities": (
        (1, "bs.accounts_payable"), (1, "bs.accrued_liabilities"), (1, "bs.deferred_revenue_current"),
        (1, "bs.deferred_revenue_noncurrent"), (1, "bs.venture_debt_current"), (1, "bs.venture_debt_noncurrent"),
        (1, "bs.convertible_notes"), (1, "bs.safes"), (1, "bs.vc_other_liabilities"),
    ),  # fmt: skip
    "bs.vc_total_equity": ((1, "bs.preferred_equity"), (1, "bs.common_equity")),
    "bs.vc_total_liabilities_and_equity": ((1, "bs.vc_total_liabilities"), (1, "bs.vc_total_equity")),
    "cf.vc_net_change_in_cash": (
        (1, "cf.vc_operating_cash_flow"), (-1, "cf.vc_capex"), (-1, "cf.capitalised_software_spend"),
        (1, "cf.equity_raised"), (1, "cf.debt_raised"), (1, "cf.vc_other_financing"),
    ),  # fmt: skip
}
ALL_KEYS = (
    IS_IN + ("is.total_revenue", "is.vc_gross_profit", "is.vc_operating_loss", "is.vc_net_loss") + BS_IN
    + ("bs.vc_total_cash", "bs.vc_total_assets", "bs.vc_total_liabilities", "bs.vc_total_equity",
       "bs.vc_total_liabilities_and_equity") + CF_IN + ("cf.vc_net_change_in_cash",) + SUP + SAAS
)  # fmt: skip


def is_flow(key: str) -> bool:
    return key.startswith(("is.", "cf.", "sup."))


def apply_formulas(values: dict[str, int]) -> None:
    """Fill every subtotal whose components are all present (the formulas are in dependency order)."""
    for key, parts in FORMULAS.items():
        if all(component in values for _, component in parts):
            values[key] = sum(sign * values[component] for sign, component in parts)


@dataclass
class Month:
    end: date
    flows: dict[str, int]  # the discrete month: input and subtotal flow lines
    balances: dict[str, int]  # month end: balance lines, subtotals and SaaS metrics
    memo: dict[str, object]


@dataclass
class Period:
    period_end: date
    months: int  # fiscal-year-to-date months
    fiscal_year: int
    quality: str
    values: dict[str, int]  # flows are year to date; balances and SaaS metrics are at the period end
    memo: dict[str, object]


def burn_path(spec: ClientSpec, rng: random.Random) -> list[int]:
    """Monthly net burn for the 22 months; the last three sum to exactly three times the target."""
    burn = D(spec.burn)
    base = [D(1)] * N
    if spec.shape == "dip":
        # One heavy month (July 2026): the average then drops out of the October window, so October runway is
        # not lower than September's and a clean client does not trip `runway_falling`.
        base[JULY_2026] = 1 + D(3) / (D(spec.cash) / burn) + D("0.30")
    elif spec.shape == "rising":
        base = [D("1.05") ** (i - LAST) for i in range(N)]
        scale = D(3) / sum(base[LAST - 2 :])
        base = [x * scale for x in base]
    elif spec.shape == "positive":
        base = [D("-1.25") if i < 14 else D(1) for i in range(N)]  # burning until February 2026, then generating
    wobble = [D(rng.randint(-40, 40)) / 1000 for _ in range(N)]
    net_burn = [rnd(burn * base[i] * (1 + wobble[i])) for i in range(N)]
    net_burn[LAST] = 3 * spec.burn - net_burn[LAST - 2] - net_burn[LAST - 1]
    return net_burn


def simulate(spec: ClientSpec, seed: int = DEFAULT_SEED) -> tuple[Month, list[Month]]:
    """The opening month (December 2024) and the 22 simulated months."""
    rng = random.Random(f"{seed}:{spec.id}:innovation")
    growth, margin = D(spec.growth), D(spec.gross_margin)
    net_burn = burn_path(spec, rng)
    equity, debt = [0] * N, [0] * N
    for ym, kind, amount in spec.history:
        i = MONTHS.index(month_end(int(ym[:4]), int(ym[5:])))
        (equity if kind == "equity" else debt)[i] += amount

    def mrr_at(i: int) -> int:
        if spec.scenario == "plan_miss":  # grows to June, then loses customers
            if i <= JUNE_2026:
                return rnd(D(spec.extra["jun_mrr"]) / (1 + growth) ** (JUNE_2026 - i))
            return rnd(D(spec.extra["jun_mrr"]) * D(spec.extra["after_june"][i - JUNE_2026 - 1]))
        return rnd(D(spec.mrr) / (1 + growth) ** (LAST - i))

    def customers_at(i: int) -> int:
        return rnd(D(spec.customers) / (1 + growth * D("0.6")) ** (LAST - i))

    idx = range(-1, N)  # index -1 is the opening month
    mrr = {i: mrr_at(i) for i in idx}
    svc = {i: rnd(D("0.06") * mrr[i]) for i in idx}
    rev = {i: mrr[i] + svc[i] for i in idx}  # subscription revenue is the month's MRR
    cor = {i: rnd(rev[i] * (1 - margin)) for i in idx}
    capex = {i: rnd(D("0.012") * rev[i]) for i in idx}
    capsw = {i: rnd(D(spec.capsw_frac) * rev[i]) for i in idx}

    restricted = {i: spec.pledged for i in idx}
    if spec.scenario == "restricted_account":
        restricted.update({i: spec.extra["restricted_before"] for i in range(-1, LAST)})
    total = {LAST: spec.cash + restricted[LAST]}
    for i in range(LAST, -1, -1):  # cash moves by -net burn plus financing inflows
        total[i - 1] = total[i] + net_burn[i] - equity[i] - debt[i]
    cash = {i: total[i] - restricted[i] for i in idx}

    venture = {-1: spec.venture_debt - sum(debt)}
    for i in range(N):
        venture[i] = venture[i - 1] + debt[i]
    interest = {i: rnd(D(venture[i - 1]) * D("0.105") / 12) for i in range(N)}
    other_income = {i: rnd((D(spec.sti) * D("0.04") + D(cash[i - 1]) * D("0.035")) / 12) for i in range(N)}
    receivable = {i: rnd(D(rev[i]) * 38 / 30) for i in idx}
    prepaid = {i: rnd(D("0.30") * rev[i]) for i in idx}
    payable = {i: rnd(D("0.45") * cor[i]) for i in idx}
    accrued = {i: rnd(D("0.35") * rev[i]) for i in idx}
    deferred_current = {i: rnd(D("1.6") * mrr[i]) for i in idx}
    deferred_long = {i: rnd(D("0.25") * mrr[i]) for i in idx}
    software = {-1: 12 * capsw[-1]}
    other_assets = {-1: 8 * capex[-1] + 150_000}
    amortisation, depreciation = {}, {}
    for i in range(N):
        amortisation[i] = rnd(D(software[i - 1]) / 36)
        depreciation[i] = rnd(D(other_assets[i - 1]) / 48)
        software[i] = software[i - 1] + capsw[i] - amortisation[i]
        other_assets[i] = other_assets[i - 1] + capex[i] - depreciation[i]
    intangibles = 0 if spec.id == "stripple-tech" else 120_000
    convertible = 1_000_000 if spec.id == "nimbusfield-security" else 0
    safes = 1_500_000 if spec.id == "halcyon-grid" else 0
    preferred = {-1: 30_000_000}
    for i in range(N):
        preferred[i] = preferred[i - 1] + equity[i]

    def balances(i: int) -> dict[str, int]:
        current = rnd(D(venture[i]) * D("0.25"))
        return {
            "bs.cash_unrestricted": cash[i], "bs.cash_restricted": restricted[i],
            "bs.short_term_investments": spec.sti, "bs.accounts_receivable": receivable[i],
            "bs.other_current_assets": prepaid[i], "bs.capitalised_software": software[i],
            "bs.vc_other_intangibles": intangibles, "bs.other_noncurrent_assets": other_assets[i],
            "bs.accounts_payable": payable[i], "bs.accrued_liabilities": accrued[i],
            "bs.deferred_revenue_current": deferred_current[i], "bs.deferred_revenue_noncurrent": deferred_long[i],
            "bs.venture_debt_current": current, "bs.venture_debt_noncurrent": venture[i] - current,
            "bs.convertible_notes": convertible, "bs.safes": safes, "bs.vc_other_liabilities": 80_000,
            "bs.preferred_equity": preferred[i],
        }  # fmt: skip

    opening_bal = balances(-1)
    assets = sum(opening_bal[k] for k in (
        "bs.cash_unrestricted", "bs.cash_restricted", "bs.short_term_investments", "bs.accounts_receivable",
        "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles",
        "bs.other_noncurrent_assets"))  # fmt: skip
    liabilities = sum(opening_bal[k] for k in (
        "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current",
        "bs.deferred_revenue_noncurrent", "bs.venture_debt_current", "bs.venture_debt_noncurrent",
        "bs.convertible_notes", "bs.safes", "bs.vc_other_liabilities"))  # fmt: skip
    common = {-1: assets - liabilities - opening_bal["bs.preferred_equity"]}  # the opening accumulated deficit
    opening_bal["bs.common_equity"] = common[-1]
    apply_formulas(opening_bal)
    opening = Month(OPENING_END, {}, {**opening_bal, "saas.mrr": mrr[-1], "saas.arr": 12 * mrr[-1],
                                       "saas.customers": customers_at(-1)}, {})  # fmt: skip

    months: list[Month] = []
    for i in range(N):
        cfo = capex[i] + capsw[i] - net_burn[i]
        d_and_a = amortisation[i] + depreciation[i]
        working_capital = (
            (payable[i] - payable[i - 1]) + (accrued[i] - accrued[i - 1])
            + (deferred_current[i] - deferred_current[i - 1]) + (deferred_long[i] - deferred_long[i - 1])
            - (receivable[i] - receivable[i - 1]) - (prepaid[i] - prepaid[i - 1])
        )  # fmt: skip
        net_income = cfo - d_and_a - working_capital
        operating_income = net_income + interest[i] - other_income[i]
        opex = rev[i] - cor[i] - d_and_a - operating_income
        if opex <= 0:
            raise ValueError(f"{spec.id} {MONTHS[i]}: operating expenses are not positive")
        r_and_d, selling = rnd(D("0.36") * opex), rnd(D("0.41") * opex)
        common[i] = common[i - 1] + net_income
        bal = balances(i)
        bal["bs.common_equity"] = common[i]
        bal.update({"saas.mrr": mrr[i], "saas.arr": 12 * mrr[i], "saas.customers": customers_at(i)})
        flows = {
            "is.subscription_revenue": mrr[i], "is.services_revenue": svc[i], "is.cost_of_revenue": cor[i],
            "is.rnd": r_and_d, "is.sales_marketing": selling, "is.gna": opex - r_and_d - selling,
            "is.vc_depreciation_amortization": d_and_a, "is.vc_interest": interest[i],
            "is.vc_other_income": other_income[i], "cf.vc_operating_cash_flow": cfo, "cf.vc_capex": capex[i],
            "cf.capitalised_software_spend": capsw[i], "cf.equity_raised": equity[i], "cf.debt_raised": debt[i],
            "cf.vc_other_financing": 0, "sup.cash_interest_paid": interest[i], "sup.scheduled_principal": 0,
        }  # fmt: skip
        apply_formulas(flows)
        apply_formulas(bal)
        memo = {
            "saas.net_new_arr": 12 * (mrr[i] - mrr[i - 1]),
            "saas.nrr_percent": 104 + (rng.randint(0, 14) if i else 0),
            "software.amortisation": amortisation[i],
        }
        months.append(Month(MONTHS[i], flows, bal, memo))
    return opening, months


def build_periods(months: list[Month]) -> list[Period]:
    """Fiscal-year-to-date periods (all 22; the first four are not published)."""
    periods: list[Period] = []
    ytd: dict[str, int] = {}
    for m in months:
        if m.end.month == 1:
            ytd = dict.fromkeys(m.flows, 0)
        for key, amount in m.flows.items():
            ytd[key] += amount
        values = {**ytd, **m.balances}
        apply_formulas(values)
        quality = "audited" if m.end == date(2025, 12, 31) else "internal"
        periods.append(Period(m.end, m.end.month, m.end.year, quality, {k: values[k] for k in ALL_KEYS}, dict(m.memo)))
    return periods


def comparative_fy2024(opening: Month, fy2025: Period) -> Period:
    """Fiscal 2024, for the comparative column of the audited statements. The simulation starts in January 2025,
    so the 2024 flows are the 2025 flows scaled by 0.62 (a company that grew about 60 percent); the December 2024
    balance sheet is the opening balance sheet."""
    values = {k: rnd(D(v) * D("0.62")) for k, v in fy2025.values.items() if is_flow(k) and k in IS_IN + CF_IN + SUP}
    values.update({k: v for k, v in opening.balances.items() if k in BS_IN + SAAS})
    apply_formulas(values)
    return Period(OPENING_END, 12, 2024, "audited", {k: values[k] for k in ALL_KEYS},
                  {"derived": "fiscal 2024 flows are fiscal 2025 flows scaled by 0.62"})


def check_periods(opening: Month, periods: list[Period]) -> list[str]:
    """Verify the identities from the published figures only. Returns a list of failures."""
    problems: list[str] = []
    by_end = {p.period_end: p for p in periods}
    start_cash = {2025: opening.balances["bs.vc_total_cash"], 2026: by_end[date(2025, 12, 31)].values["bs.vc_total_cash"]}
    for p in periods:
        v, tag = p.values, p.period_end.isoformat()
        for key, parts in FORMULAS.items():
            if v[key] != sum(sign * v[component] for sign, component in parts):
                problems.append(f"{tag}: {key} does not foot")
        if v["bs.vc_total_assets"] != v["bs.vc_total_liabilities_and_equity"]:
            problems.append(f"{tag}: balance sheet does not balance")
        if v["cf.vc_net_change_in_cash"] != v["bs.vc_total_cash"] - start_cash[p.fiscal_year]:
            problems.append(f"{tag}: cash flow does not tie to the change in cash")
        if v["saas.arr"] != 12 * v["saas.mrr"]:
            problems.append(f"{tag}: ARR is not twelve times MRR")
        for key in ("bs.cash_unrestricted", "bs.accounts_receivable", "bs.accounts_payable", "saas.mrr"):
            if v[key] < 0:
                problems.append(f"{tag}: {key} is negative")
    return problems
```

`synthetic/books/innovation/expected.py`

```python
"""Expected results for an innovation client, in plain arithmetic.

This module never imports from backend/app. The engine has to reach the same numbers by its own route; if it does not,
investigate, and never patch either side to match.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from synthetic.books.innovation.model import JUNE_2026, LAST, MONTHS, Month, N
from synthetic.books.innovation.roster import ClientSpec

D = Decimal
FIRST_TEST = 7  # August 2025: the first month whose trailing three months all lie in the published periods
PLAN_FIRST = 4  # the approved plan covers May 2025 to October 2026
SIGNAL_SEVERITY = {
    "covenant_headroom_low": "medium", "covenant_headroom_falling": "low", "runway_below_watch": "medium",
    "runway_falling": "medium", "burn_rising": "medium", "revenue_below_plan": "medium", "reporting_late": "high",
}  # fmt: skip
SIGNAL_TRIGGER = {
    "covenant_headroom_low": "0.10", "runway_below_watch": "12", "burn_rising": "0.20", "revenue_below_plan": "1.00",
    "reporting_late": "15",
}  # fmt: skip
EXCEPTION_SEVERITY = {
    "covenant.reported_mismatch": "critical", "covenant.breach": "high", "signal.high": "high",
    "intake.missing_document": "medium", "funding_slipped": "high", "intake.unclassified": "medium",
    "spread.value_unverified": "medium", "cash.statement_mismatch": "high",
}  # fmt: skip
# A certificate figure is either exact or far from the engine's own tolerance (usd 1, months 0, pct 0.0005), so the
# two sides cannot disagree about "agrees with the certificate".
TOLERANCE = {"usd": D(1000), "months": D("0.05"), "pct": D("0.001")}
DUE_DAYS = {"bank_statement": 7, "mrr_report": 15, "monthly_financials": 30, "compliance_certificate": 30}
COVENANTS = (
    ("min_unrestricted_cash", "Minimum Unrestricted Cash", "usd"),
    ("min_runway_months", "Minimum Runway", "months"),
    ("revenue_vs_plan", "Revenue to Plan", "pct"),
)


def q(value: Decimal, dp: int) -> Decimal:
    return value.quantize(D(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def thousands(value: Decimal) -> int:
    return int((value / 1000).quantize(D(1), rounding=ROUND_HALF_UP)) * 1000


class Series:
    """Discrete monthly figures for one client, indexed like MONTHS."""

    def __init__(self, months: list[Month]):
        self.months = months

    def flow3(self, key: str, i: int) -> int:
        return sum(self.months[j].flows[key] for j in range(i - 2, i + 1))

    def net_burn3(self, i: int) -> int:
        """Capex plus capitalised software spend, less operating cash flow, over the three months ending at i."""
        return (self.flow3("cf.vc_capex", i) + self.flow3("cf.capitalised_software_spend", i)
                - self.flow3("cf.vc_operating_cash_flow", i))  # fmt: skip

    def avg_burn(self, i: int) -> Decimal:
        return D(self.net_burn3(i)) / 3

    def cash(self, i: int) -> int:
        return self.months[i].balances["bs.cash_unrestricted"]

    def rml(self, i: int) -> Decimal | None:
        """Unrestricted cash over average monthly net burn; None (not meaningful) when the burn is zero or negative."""
        burn = self.avg_burn(i)
        return None if burn <= 0 else D(self.cash(i)) / burn

    def revenue(self, i: int) -> int:
        return self.months[i].flows["is.subscription_revenue"] + self.months[i].flows["is.services_revenue"]

    def revenue3(self, i: int) -> int:
        return sum(self.revenue(j) for j in range(i - 2, i + 1))


def build_plan(spec: ClientSpec, series: Series) -> dict[date, int]:
    """Approved plan figures (monthly revenue, May 2025 to October 2026). Clean clients beat plan by about 5 percent;
    Corvane's plan runs away from its revenue after June 2026."""
    plan: dict[date, int] = {}
    for i in range(PLAN_FIRST, N):
        if spec.scenario == "plan_miss" and i >= JUNE_2026:
            value = D(series.revenue(JUNE_2026)) * D(spec.extra["plan_growth"]) ** (i - JUNE_2026)
        else:
            value = D(series.revenue(i)) * D("0.95")
        plan[MONTHS[i]] = thousands(value)
    return plan


def plan_ratio(series: Series, plan: dict[date, int], i: int) -> Decimal:
    planned = sum(plan[MONTHS[j]] for j in range(i - 2, i + 1))
    return D(series.revenue3(i)) / D(planned)


def cert_months(spec: ClientSpec) -> set[int]:
    """Months with a certificate on file: the last three, except Lumora's October (not yet delivered)."""
    months = {LAST - 2, LAST - 1, LAST}
    if spec.scenario == "late_package":
        months.discard(LAST)
    return months


def cert_cash(spec: ClientSpec, series: Series, i: int) -> int:
    """The cash the borrower's certificate shows. Dataflake counts its pledged account; Tidewell counts its new escrow
    account. Both are wrong in October only."""
    cash = series.cash(i)
    if i == LAST and spec.scenario == "pledged_cash":
        cash += spec.pledged
    if i == LAST and spec.scenario == "restricted_account":
        cash += spec.extra["newly_restricted"]
    return cash


def cert_entry(spec: ClientSpec, series: Series, plan: dict[date, int], i: int, covenant_id: str):
    """What the certificate reports for one covenant at month i: (value, in_compliance). A cash-flow-positive client
    reports no runway figure."""
    if covenant_id == "min_unrestricted_cash":
        cash = D(cert_cash(spec, series, i))
        return cash, cash >= spec.min_cash
    if covenant_id == "min_runway_months":
        burn = series.avg_burn(i)
        if burn <= 0:
            return None, True
        value = q(D(cert_cash(spec, series, i)) / burn, 1)
        return value, value >= D(spec.min_rml)
    ratio = q(plan_ratio(series, plan, i), 4)
    return ratio, ratio >= D(spec.plan_floor)


def classify(passed: bool, value: Decimal | None, reported: bool, rep_value: Decimal | None, rep_flag: bool | None,
             unit: str) -> str:
    """Outcome of a covenant test against the borrower's certificate (spec section 8 of the design)."""
    if not passed:
        return "breach_reported_compliant" if reported and rep_flag else "breach"
    if not reported:
        return "compliant"
    if value is None:  # not meaningful: the certificate's own figure is ignored; its flag is still compared
        return "compliant" if rep_flag else "compliant_variance"
    agrees = rep_value is not None and abs(rep_value - value) <= TOLERANCE[unit] and bool(rep_flag)
    return "compliant" if agrees else "compliant_variance"


def covenant_rows(spec: ClientSpec, series: Series, plan: dict[date, int], version_id: str, facility_id: str) -> list[dict]:
    """One row per covenant per month from August 2025."""
    rows: list[dict] = []
    certified = cert_months(spec)
    for i in range(FIRST_TEST, N):
        for covenant_id, name, unit in COVENANTS:
            threshold = {"usd": D(spec.min_cash), "months": D(spec.min_rml), "pct": D(spec.plan_floor)}[unit]
            note = None
            if covenant_id == "min_unrestricted_cash":
                value: Decimal | None = D(series.cash(i))
            elif covenant_id == "min_runway_months":
                raw = series.rml(i)
                value = None if raw is None else q(raw, 1)
                note = "not_meaningful_cash_flow_positive" if raw is None else None
            else:
                value = q(plan_ratio(series, plan, i), 4)
            passed = True if value is None else value >= threshold
            headroom = None if value is None else q((value - threshold) / abs(threshold), 4)
            reported = i in certified
            rep_value, rep_flag = cert_entry(spec, series, plan, i, covenant_id) if reported else (None, None)
            rows.append({
                "period_end": MONTHS[i], "covenant_id": covenant_id, "covenant_name": name, "archetype": covenant_id,
                "facility_id": facility_id, "terms_version_id": version_id, "terms_version": 1, "unit": unit,
                "operator": ">=", "threshold": threshold, "value": value, "pass": passed, "headroom": headroom,
                "note": note, "reported_value": rep_value, "reported_threshold": threshold if reported else None,
                "reported_in_compliance": rep_flag,
                "outcome": classify(passed, value, reported, rep_value, rep_flag, unit),
            })  # fmt: skip
    return rows


def compute_signals(series: Series, plan: dict[date, int], rows: list[dict], i: int,
                    days_late: list[tuple[str, int]]) -> list[dict]:
    """Signals for month i under rule set `signals-1` (the startup rules of spec section 7)."""
    end = MONTHS[i]
    out: list[dict] = []

    def add(rule: str, value, severity: str | None = None, **detail) -> None:
        out.append({"rule": rule, "period_end": end, "severity": severity or SIGNAL_SEVERITY[rule], "value": value,
                    "trigger": SIGNAL_TRIGGER.get(rule), "detail": detail})  # fmt: skip

    headroom: dict[str, dict[int, Decimal | None]] = {}
    for row in rows:
        headroom.setdefault(row["covenant_id"], {})[MONTHS.index(row["period_end"])] = row["headroom"]
    for covenant_id, per_month in sorted(headroom.items()):
        now = per_month.get(i)
        if now is None:
            continue
        if now < D("0.10"):
            add("covenant_headroom_low", now, covenant_id=covenant_id)
        window = [per_month.get(j) for j in (i - 2, i - 1, i)]
        if None not in window and window[2] < window[1] < window[0]:
            add("covenant_headroom_falling", now, covenant_id=covenant_id)
    runway = series.rml(i)
    if runway is not None and runway < 12:
        add("runway_below_watch", q(runway, 2), "high" if runway < 9 else "medium")
    points = [series.rml(j) for j in range(i - 3, i + 1)]
    if None not in points and all(later < earlier for earlier, later in zip(points, points[1:], strict=False)):
        add("runway_falling", q(runway, 2))
    prior = series.avg_burn(i - 3)
    if prior > 0:
        change = q((series.avg_burn(i) - prior) / prior, 4)
        if change > D("0.20"):
            add("burn_rising", change)
    ratio = q(plan_ratio(series, plan, i), 4)
    if ratio < D("1.00"):
        add("revenue_below_plan", ratio)
    for requirement, late in days_late:
        if late > 15:
            add("reporting_late", D(late), requirement=requirement)
    return out
```

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest synthetic/tests/innovation -v && uv run ruff check synthetic`
Expected: PASS, ruff clean. If an October figure differs from the owner's by even a dollar, the model is wrong: fix the model, never the roster.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books/innovation/model.py synthetic/books/innovation/expected.py synthetic/tests/innovation
git commit -m "feat(p2): monthly truth model and independent expected values"
```

---

### Task 3: Terms, the agreement text, and what each client reports

> **Controller amendment:** besides what follows, give Ferrogate a second terms version effective 2026-05-31 adding a `dscr` covenant (TTM, minimum 1.25x), with independent expected values in Task 2's expected module and oracle rows in Task 6. See ruling 9.

**Files:**
- Create: `synthetic/books/innovation/terms.py`, `synthetic/books/innovation/reports.py`, `synthetic/tests/innovation/test_terms_and_reports.py`

**Interfaces:**
- Consumes: `model` and `expected` (Task 2); the frozen `synthetic.terms` document structures (`LegalDoc`, `Article`, `Section`, `Para`, `money`, `long_date`) and `synthetic.render.legal.render_legal`; `synthetic.scenarios.CREDIT_OFFICERS`.
- Produces (`terms`): `SLUG` ("credit-agreement"), `ClientTerms(agreement, version, facility, clause_index)`, `build_agreement(spec) -> LegalDoc`, `covenants_json(spec, plan)`, `build_terms(spec, plan) -> ClientTerms` (citations are `{"field", "_anchor": (slug, anchor)}` placeholders resolved at generation time).
- Produces (`reports`): `build_certificates(spec, series, plan) -> list[dict]`, `format_actual(unit, value)`, `format_required(unit, threshold)`, `bank_accounts(spec, months, i)`, `bank_notes(spec, i)`, `mrr_bridge(months, i)`, `software_roll(months, i)`, `misread_runway(series, i)`.

- [ ] **Step 1: Write the failing test**

`synthetic/tests/innovation/test_terms_and_reports.py`

```python
"""Terms, the agreement text, and what each client reports and sends (certificates, accounts, MRR, software)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from synthetic.books.innovation import model, reports
from synthetic.books.innovation.expected import DUE_DAYS, build_plan, cert_months
from synthetic.books.innovation.terms import build_terms
from synthetic.render import common
from synthetic.render.legal import render_legal

LAST = model.LAST


def terms_for(sim):
    return build_terms(sim.spec, build_plan(sim.spec, sim.series))


def test_agreement_cites_every_number_in_the_terms_on_the_page_it_prints(sims, tmp_path):
    sim = sims["dataflake"]
    terms = terms_for(sim)
    result = render_legal(tmp_path / "ca.pdf", terms.agreement, sim.spec.name)
    pages = common.page_texts(tmp_path / "ca.pdf")
    cites = terms.agreement.cites
    for anchor, cite in cites.items():
        assert common.squash(cite["quote"]) in common.squash(pages[result["anchor_pages"][anchor] - 1]), anchor
    assert "$5,000,000" in cites["cov_cash"]["quote"] and "6.0 months" in cites["cov_runway"]["quote"]
    assert "80%" in cites["cov_plan"]["quote"]
    assert "excluding any cash that is pledged, escrowed or otherwise restricted" in cites["def_unrestricted_cash"]["quote"]
    assert cites["def_unrestricted_cash"]["section"] == "1.1"
    for anchor, days in (("rep_monthly", 30), ("rep_certificate", 30), ("rep_mrr", 15), ("rep_bank", 7), ("rep_annual", 180)):
        assert f"{days} days" in cites[anchor]["quote"]


def test_every_client_has_the_three_covenants_and_five_reporting_requirements(sims):
    for sim in sims.values():
        spec, plan = sim.spec, build_plan(sim.spec, sim.series)
        terms = terms_for(sim)
        covenants = terms.version["terms"]["covenants"]
        assert [c["id"] for c in covenants] == ["min_unrestricted_cash", "min_runway_months", "revenue_vs_plan"]
        assert [c["test"]["unit"] for c in covenants] == ["usd", "months", "pct"]
        assert [c["measurement"]["basis"] for c in covenants] == ["point", "t3m", "t3m"]
        assert {c["measurement"]["frequency"] for c in covenants} == {"monthly"}
        assert [c["test"]["threshold"] for c in covenants] == [str(spec.min_cash), "6.0", "0.80"]
        assert [(p["period_end"], int(p["amount"])) for p in covenants[2]["params"]["plan"]] == [
            (m.isoformat(), plan[m]) for m in sorted(plan)]
        requirements = {r["id"]: r for r in terms.version["terms"]["reporting_requirements"]}
        assert {k: v["due_days_after_period_end"] for k, v in requirements.items()} == {
            "monthly_financials": 30, "compliance_certificate": 30, "mrr_report": 15, "bank_statements": 7,
            "annual_statements": 180}
        assert DUE_DAYS["bank_statement"] == 7 and all(r["frequency"] == "monthly" for k, r in requirements.items()
                                                       if k != "annual_statements")
        anchors = {c["citation"]["_anchor"][1] for c in requirements.values()}
        assert anchors <= set(terms.agreement.cites)
        assert terms.facility["commitment"] == str(spec.venture_debt) and terms.facility["borrowing_base"] is False
        assert terms.version["status"] == "approved" and terms.version["terms"]["borrowing_base"] is None


def test_watch_levels_are_not_in_the_terms_they_are_signal_parameters(sims):
    """Owner default: the 12-month watch level is a signal parameter, the covenant floor is 6.0 months."""
    terms = terms_for(sims["dataflake"])
    assert "watch" not in str(terms.version["terms"]) and terms.version["terms"]["covenants"][1]["test"]["threshold"] == "6.0"


def test_certificates_are_honest_except_the_two_designed_distortions(sims):
    for sim in sims.values():
        plan = build_plan(sim.spec, sim.series)
        certificates = reports.build_certificates(sim.spec, sim.series, plan)
        assert sorted(model.MONTHS.index(c["period_end"]) for c in certificates) == sorted(cert_months(sim.spec))
    dataflake = reports.build_certificates(sims["dataflake"].spec, sims["dataflake"].series, {m: 1 for m in model.MONTHS})
    october = dataflake[-1]["reported"]["min_unrestricted_cash"]
    assert october["value"] == D(6_100_000) and october["in_compliance"] is True
    assert {"Cash held in the pledged collateral account": 1_500_000}.items() <= {
        line["label"]: line["amount"] for line in october["calculation"]}.items()
    september = dataflake[-2]["reported"]["min_unrestricted_cash"]
    assert september["value"] == D(sims["dataflake"].series.cash(LAST - 1))
    ferrogate = reports.build_certificates(sims["ferrogate-cloud"].spec, sims["ferrogate-cloud"].series,
                                           {m: 1 for m in model.MONTHS})[-1]["reported"]["min_runway_months"]
    assert ferrogate["value"] is None and ferrogate["in_compliance"] is True
    assert not [c for c in reports.build_certificates(sims["lumora-health"].spec, sims["lumora-health"].series,
                                                      {m: 1 for m in model.MONTHS}) if c["period_end"] == date(2026, 10, 31)]


def test_bank_accounts_tie_to_the_balance_sheet_and_roll_from_month_to_month(sims):
    for sim in sims.values():
        for i in (LAST - 2, LAST - 1, LAST):
            accounts = reports.bank_accounts(sim.spec, sim.months, i)
            balances = sim.months[i].balances
            assert sum(a["closing"] for a in accounts if not a["restricted"]) == balances["bs.cash_unrestricted"]
            assert sum(a["closing"] for a in accounts if a["restricted"]) == balances["bs.cash_restricted"]
            assert all(a["credits"] >= 0 and a["debits"] >= 0 for a in accounts)
            assert all(a["opening"] + a["credits"] - a["debits"] == a["closing"] for a in accounts), sim.spec.id
        before = {a["tail"]: a["closing"] for a in reports.bank_accounts(sim.spec, sim.months, LAST - 1)}
        after = {a["tail"]: a["opening"] for a in reports.bank_accounts(sim.spec, sim.months, LAST) if a["tail"] in before}
        assert before == after, sim.spec.id
    tidewell = reports.bank_accounts(sims["tidewell-medical"].spec, sims["tidewell-medical"].months, LAST)
    assert [(a["tail"], a["closing"]) for a in tidewell if a["restricted"]] == [("9001", 100_000), ("9002", 1_000_000)]


def test_the_mrr_bridge_adds_up_and_the_software_roll_ties(sims):
    for sim in sims.values():
        for i in range(LAST - 5, LAST + 1):
            bridge = reports.mrr_bridge(sim.months, i)
            assert bridge["opening"] + bridge["new"] + bridge["expansion"] - bridge["contraction"] - bridge["churn"] == bridge["mrr"]
            assert min(bridge["new"], bridge["churn"]) >= 0 and bridge["arr"] == 12 * bridge["mrr"], (sim.spec.id, i)
            roll = reports.software_roll(sim.months, i)
            assert roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"], (sim.spec.id, i)
    assert len(reports.mrr_bridge(sims["dataflake"].months, LAST)["trend"]) == 6


def test_printed_certificate_figures():
    assert reports.format_actual("usd", D(6_100_000)) == "$6,100,000"
    assert reports.format_actual("months", D("9.4")) == "9.4 months"
    assert reports.format_actual("pct", D("1.0530")) == "105.30%"
    assert reports.format_actual("months", None) == "Not meaningful (cash-flow positive)"
    assert reports.format_required("pct", D("0.80")) == "Not less than 80.00% of plan"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest synthetic/tests/innovation/test_terms_and_reports.py -v`
Expected: collection fails with `ModuleNotFoundError: No module named 'synthetic.books.innovation.terms'`.

- [ ] **Step 3: Implement**

Each covenant sentence in the agreement is written so the product's provenance check passes: the threshold appears in the quote in a form it reads (`$5,000,000`, `6.0 months`, `80%`), the sentence names the covenant, and a floor is worded as a floor ("shall not be less than"). The `Unrestricted Cash` definition (section 1.1) excludes pledged, escrowed or restricted cash — it is the clause Dataflake's certificate ignores.

`synthetic/books/innovation/terms.py`

```python
"""Terms for an innovation client: the venture loan agreement (as a LegalDoc), the terms version with citation
placeholders, and the facility. The approved plan figures are terms data entered by a person (spec 5), so the
`revenue_vs_plan` covenant carries them in its parameters and the agreement only names the 80 percent floor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from synthetic.books.innovation.expected import DUE_DAYS
from synthetic.books.innovation.model import MONTHS
from synthetic.books.innovation.roster import LENDER, ClientSpec
from synthetic.scenarios import CREDIT_OFFICERS
from synthetic.terms import Article, LegalDoc, Para, Section, long_date, money

D = Decimal
SLUG = "credit-agreement"
PLAN_MONTHS = MONTHS[4:]


@dataclass
class ClientTerms:
    agreement: LegalDoc
    version: dict  # citations still carry "_anchor": (slug, anchor)
    facility: dict
    clause_index: list[dict]


def build_agreement(spec: ClientSpec) -> LegalDoc:
    """The agreement text. Every cited sentence is kept whole on one page, and the page is recorded at render time."""
    doc = LegalDoc(
        slug=SLUG, doc_type="credit_agreement", title="VENTURE LOAN AND SECURITY AGREEMENT",
        subtitle=f"Dated as of {long_date(spec.closing_date)}", doc_date=spec.closing_date,
        borrower_name=spec.name, preamble=[], articles=[], signature_blocks=[], toc=True,
    )  # fmt: skip
    cite = doc.cite
    doc.preamble = [Para(
        f"This Venture Loan and Security Agreement is entered into as of {long_date(spec.closing_date)} between "
        f"{spec.name}, a Delaware corporation (the Borrower), and {LENDER} (the Lender)."
    )]
    doc.articles = [
        Article("1", "DEFINITIONS", [Section("1.1", "Defined Terms", [
            Para(cite("def_unrestricted_cash", "1.1",
                      '"Unrestricted Cash" means cash held in deposit accounts of the Borrower with the Lender, '
                      "excluding any cash that is pledged, escrowed or otherwise restricted."),
                 ("def_unrestricted_cash",)),
            Para(cite("def_net_burn", "1.1",
                      '"Net Burn" means, for any month, capital expenditures plus capitalized software development '
                      "spend, less net cash from operating activities, and excludes the proceeds of equity and debt "
                      "financing."), ("def_net_burn",)),
            Para(cite("def_runway", "1.1",
                      '"Runway" means Unrestricted Cash divided by the average monthly Net Burn for the three months '
                      "then ended; if that average is zero or negative, Runway is not meaningful and the covenant is "
                      "satisfied."), ("def_runway",)),
            Para('"Approved Plan" means the monthly revenue plan approved by the Lender and recorded in the Lender\'s '
                 "credit file, as updated by written agreement of the Lender and the Borrower."),
        ])]),  # fmt: skip
        Article("2", "THE LOAN", [Section("2.1", "Venture Term Loan", [
            Para(cite("facility", "2.1",
                      f"The Lender has made a venture term loan to the Borrower in the aggregate principal amount of "
                      f"{money(spec.venture_debt)}, bearing interest at the rate of Prime plus 3.50 percent."),
                 ("facility",))])]),  # fmt: skip
        Article("5", "REPORTING", [Section("5.1", "Financial Statements and Certificates", [
            Para(cite("rep_annual", "5.1(a)",
                      "Within 180 days after the end of each fiscal year, the Borrower shall deliver audited financial "
                      "statements with an unqualified opinion."), ("rep_annual",)),
            Para(cite("rep_monthly", "5.1(b)",
                      "Within 30 days after the end of each month, the Borrower shall deliver management financial "
                      "statements for that month and the year to date."), ("rep_monthly",)),
            Para(cite("rep_certificate", "5.1(c)",
                      "Within 30 days after the end of each month, the Borrower shall deliver a compliance certificate "
                      "signed by its chief financial officer."), ("rep_certificate",)),
            Para(cite("rep_mrr", "5.1(d)",
                      "Within 15 days after the end of each month, the Borrower shall deliver a monthly recurring "
                      "revenue report."), ("rep_mrr",)),
            Para(cite("rep_bank", "5.1(e)",
                      "Within 7 days after the end of each month, the Borrower shall deliver its bank account "
                      "statements for that month."), ("rep_bank",)),
        ])]),  # fmt: skip
        Article("6", "FINANCIAL COVENANTS", [
            Section("6.1", "Minimum Unrestricted Cash", [Para(cite(
                "cov_cash", "6.1",
                f"Unrestricted Cash shall not be less than {money(spec.min_cash)} at any month end."), ("cov_cash",))]),
            Section("6.2", "Minimum Runway", [Para(cite(
                "cov_runway", "6.2",
                f"Runway shall not be less than {spec.min_rml} months at any month end."), ("cov_runway",))]),
            Section("6.3", "Revenue to Plan", [Para(cite(
                "cov_plan", "6.3",
                "Revenue for any three-month period shall not be less than 80% of the Approved Plan for the same "
                "three months."), ("cov_plan",))]),
        ]),  # fmt: skip
    ]
    doc.signature_blocks = [(spec.name, spec.cfo, "Chief Financial Officer"),
                            (LENDER, CREDIT_OFFICERS[len(spec.id) % 2], "Credit Officer")]  # fmt: skip
    return doc


def _requirement(rid: str, document_type: str, frequency: str, due_days: int, quality: str | None, anchor: str) -> dict:
    return {
        "id": rid, "document_type": document_type, "frequency": frequency, "due_days_after_period_end": due_days,
        "quality": quality, "citation": {"field": f"reporting_requirements.{rid}", "_anchor": (SLUG, anchor)},
    }  # fmt: skip


def covenants_json(spec: ClientSpec, plan: dict[date, int]) -> list[dict]:
    def covenant(cid, name, params, operator_threshold, unit, basis, dp, anchors) -> dict:
        return {
            "id": cid, "name": name, "archetype": cid, "params": params,
            "test": {"operator": ">=", "threshold": operator_threshold, "steps": [], "unit": unit},
            "measurement": {"basis": basis, "frequency": "monthly"}, "rounding": {"dp": dp, "mode": "half_up"},
            "citations": [{"field": field, "_anchor": (SLUG, anchor)} for field, anchor in anchors],
        }  # fmt: skip

    return [
        covenant("min_unrestricted_cash", "Minimum Unrestricted Cash", {}, str(spec.min_cash), "usd", "point", 0,
                 (("test.threshold", "cov_cash"), ("definition", "def_unrestricted_cash"))),
        covenant("min_runway_months", "Minimum Runway", {}, spec.min_rml, "months", "t3m", 1,
                 (("test.threshold", "cov_runway"), ("definition", "def_runway"), ("definition", "def_net_burn"))),
        covenant("revenue_vs_plan", "Revenue to Plan",
                 {"metric": "revenue", "plan": [{"period_end": m.isoformat(), "amount": str(plan[m])} for m in PLAN_MONTHS]},
                 spec.plan_floor, "pct", "t3m", 4, (("test.threshold", "cov_plan"),)),
    ]  # fmt: skip


def build_terms(spec: ClientSpec, plan: dict[date, int]) -> ClientTerms:
    agreement = build_agreement(spec)
    facility_id = f"{spec.id}-vl"
    facility = {
        "id": facility_id, "borrower_id": spec.id, "type": "term_loan", "name": "Venture Term Loan",
        "commitment": str(spec.venture_debt), "original_amount": str(spec.venture_debt),
        "closing_date": spec.closing_date.isoformat(),
        "maturity_date": (spec.closing_date + timedelta(days=4 * 365)).isoformat(),
        "interest_rate": "Prime + 3.50%", "borrowing_base": False,
    }  # fmt: skip
    terms = {
        "definitions": {},
        "covenants": covenants_json(spec, plan),
        "reporting_requirements": [
            _requirement("monthly_financials", "monthly_financials", "monthly", DUE_DAYS["monthly_financials"],
                         "internal", "rep_monthly"),
            _requirement("compliance_certificate", "compliance_certificate", "monthly",
                         DUE_DAYS["compliance_certificate"], None, "rep_certificate"),
            _requirement("mrr_report", "mrr_report", "monthly", DUE_DAYS["mrr_report"], None, "rep_mrr"),
            _requirement("bank_statements", "bank_statement", "monthly", DUE_DAYS["bank_statement"], None, "rep_bank"),
            _requirement("annual_statements", "annual_financial_statements", "annual", 180, "audited", "rep_annual"),
        ],
        "borrowing_base": None,
    }  # fmt: skip
    version = {
        "id": f"tv-{spec.id}-1", "facility_id": facility_id, "version": 1, "status": "approved",
        "effective_from": spec.closing_date.isoformat(), "effective_to": None, "prepared_by": spec.analyst,
        "approved_by": CREDIT_OFFICERS[len(spec.id) % 2],
        "approved_at": (spec.closing_date + timedelta(days=6)).isoformat(), "warnings": [],
        "source_documents": [f"{spec.id}.{SLUG}"], "terms": terms,
    }  # fmt: skip
    clause_index = [{"field": "facilities.venture_term_loan.commitment", "_anchor": (SLUG, "facility")}]
    return ClientTerms(agreement, version, facility, clause_index)
```

`synthetic/books/innovation/reports.py`

```python
"""What the client reports and sends: certificates, bank account balances, the MRR bridge, the software roll."""

from __future__ import annotations

from decimal import Decimal

from synthetic.books.innovation.expected import COVENANTS, Series, cert_cash, cert_entry, cert_months, q
from synthetic.books.innovation.model import LAST, MONTHS, Month, rnd
from synthetic.books.innovation.roster import ClientSpec

D = Decimal


def build_certificates(spec: ClientSpec, series: Series, plan: dict) -> list[dict]:
    """Monthly compliance certificates for the last three months, as the client delivered them."""
    certificates = []
    for i in sorted(cert_months(spec)):
        threshold = {"usd": D(spec.min_cash), "months": D(spec.min_rml), "pct": D(spec.plan_floor)}
        reported = {}
        for covenant_id, _, unit in COVENANTS:
            value, flag = cert_entry(spec, series, plan, i, covenant_id)
            cash = [{"label": "Cash in operating accounts", "amount": series.cash(i)}]
            if i == LAST and spec.scenario == "pledged_cash":
                cash.append({"label": "Cash held in the pledged collateral account", "amount": spec.pledged})
            if i == LAST and spec.scenario == "restricted_account":
                cash.append({"label": "Cash in the escrow collateral account opened October 14, 2026",
                             "amount": spec.extra["newly_restricted"]})  # fmt: skip
            if covenant_id == "min_unrestricted_cash":
                lines = [*cash, {"label": "Unrestricted Cash", "amount": cert_cash(spec, series, i)}]
            elif covenant_id == "min_runway_months":
                lines = [{"label": "Unrestricted Cash (as above)", "amount": cert_cash(spec, series, i)},
                         {"label": "Net Burn for the three months ended", "amount": series.net_burn3(i)},
                         {"label": "Average monthly Net Burn", "amount": q(series.avg_burn(i), 0)}]  # fmt: skip
            else:
                planned = sum(plan[MONTHS[j]] for j in range(i - 2, i + 1))
                lines = [{"label": "Revenue for the three months ended", "amount": series.revenue3(i)},
                         {"label": "Approved Plan for the same three months", "amount": planned}]  # fmt: skip
            reported[covenant_id] = {"value": value, "threshold": threshold[unit], "in_compliance": flag,
                                     "unit": unit, "calculation": lines}  # fmt: skip
        certificates.append({"period_end": MONTHS[i], "scale": 1, "signed_by": spec.cfo, "reported": reported})
    return certificates


def format_actual(unit: str, value: Decimal | None) -> str:
    if value is None:
        return "Not meaningful (cash-flow positive)"
    if unit == "usd":
        return f"${int(value):,}"
    if unit == "months":
        return f"{value:.1f} months"
    return f"{value * 100:.2f}%"


def format_required(unit: str, threshold: Decimal) -> str:
    if unit == "usd":
        return f"Not less than ${int(threshold):,}"
    if unit == "months":
        return f"Not less than {threshold:.1f} months"
    return f"Not less than {threshold * 100:.2f}% of plan"


def bank_accounts(spec: ClientSpec, months: list[Month], i: int) -> list[dict]:
    """Account balances for month i. Operating balances sum to unrestricted cash and the pledged accounts to
    restricted cash, so the statement ties to the balance sheet exactly."""

    def split(cash: int) -> list[int]:
        operating, payroll = rnd(D("0.70") * cash), rnd(D("0.12") * cash)
        return [operating, payroll, cash - operating - payroll]

    now, before = months[i], months[i - 1]
    closing, opening = split(now.balances["bs.cash_unrestricted"]), split(before.balances["bs.cash_unrestricted"])
    inflow = now.flows["is.subscription_revenue"] + now.flows["is.services_revenue"]
    credits = [rnd(D("1.02") * inflow) + now.flows["cf.equity_raised"] + now.flows["cf.debt_raised"]]
    credits += [abs(closing[k] - opening[k]) + rnd(D("0.25") * opening[k]) for k in (1, 2)]
    accounts = []
    for k, (name, tail) in enumerate((("Operating account", "4417"), ("Payroll account", "4425"),
                                      ("Treasury money market account", "4433"))):  # fmt: skip
        accounts.append({"name": name, "tail": tail, "restricted": False, "opening": opening[k],
                         "credits": credits[k], "debits": credits[k] - (closing[k] - opening[k]),
                         "closing": closing[k]})  # fmt: skip
    first = spec.extra.get("restricted_before", spec.pledged)
    accounts.append({"name": "Collateral account", "tail": "9001", "restricted": True, "opening": first,
                     "credits": 0, "debits": 0, "closing": first})  # fmt: skip
    if spec.scenario == "restricted_account" and i == LAST:
        accounts.append({"name": "Escrow collateral account", "tail": "9002", "restricted": True, "opening": 0,
                         "credits": spec.extra["newly_restricted"], "debits": 0,
                         "closing": spec.extra["newly_restricted"]})  # fmt: skip
    return accounts


def bank_notes(spec: ClientSpec, i: int) -> list[str]:
    note = spec.extra.get("pledged_note", "pledged as collateral under the venture loan agreement")
    notes = [f"The collateral account is {note}. Balances in restricted accounts are not available for withdrawal."]
    if spec.scenario == "restricted_account" and i == LAST:
        notes.append("The account ending 9002 was opened on October 14, 2026 as a cash collateral account under an "
                     "escrow arrangement. It is restricted.")  # fmt: skip
    return notes


def mrr_bridge(months: list[Month], i: int) -> dict:
    """The MRR movement for month i: opening, new, expansion, contraction, churn, closing."""
    opening, closing = months[i - 1].balances["saas.mrr"], months[i].balances["saas.mrr"]
    expansion, contraction, churn = rnd(D("0.012") * opening), rnd(D("0.004") * opening), rnd(D("0.008") * opening)
    residual = closing - opening - (expansion - contraction - churn)
    new = max(residual, 0)
    churn += max(-residual, 0)
    return {"opening": opening, "new": new, "expansion": expansion, "contraction": contraction, "churn": churn,
            "mrr": closing, "arr": months[i].balances["saas.arr"], "net_new_arr": months[i].memo["saas.net_new_arr"],
            "customers": months[i].balances["saas.customers"], "nrr": months[i].memo["saas.nrr_percent"],
            "trend": [(MONTHS[j].strftime("%B %Y"), months[j].balances["saas.mrr"], months[j].balances["saas.customers"])
                      for j in range(i - 5, i + 1)]}  # fmt: skip


def software_roll(months: list[Month], i: int) -> dict:
    return {"opening": months[i - 1].balances["bs.capitalised_software"],
            "additions": months[i].flows["cf.capitalised_software_spend"],
            "amortisation": months[i].memo["software.amortisation"],
            "closing": months[i].balances["bs.capitalised_software"]}  # fmt: skip


def misread_runway(series: Series, i: int) -> Decimal | None:
    """Runway if the capitalised software balance were read as the month's spend (the Stripple trap)."""
    wrong = (series.flow3("cf.vc_capex", i) + series.months[i].balances["bs.capitalised_software"]
             - series.flow3("cf.vc_operating_cash_flow", i))  # fmt: skip
    burn = D(wrong) / 3
    return None if burn <= 0 else D(series.cash(i)) / burn
```

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest synthetic/tests/innovation -v && uv run ruff check synthetic`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books/innovation/terms.py synthetic/books/innovation/reports.py synthetic/tests/innovation/test_terms_and_reports.py
git commit -m "feat(p2): innovation terms, agreement text and client reports"
```

---

### Task 4: Renderers for the new document types

**Files:**
- Create: `synthetic/books/innovation/layout.py`, `synthetic/render/innovation.py`, `synthetic/tests/innovation/test_render.py`

**Interfaces:**
- Consumes: `synthetic.render.common` (page template, marker, `accounting`, `page_texts`), `synthetic.render.statements._auditor_report` (reused for the audited annual), `reports.software_roll` (Task 3).
- Produces (`render`): `render_monthly_financials(path, spec, payload, title)`, `render_annual_statements(...)`, `render_mrr_report(...)`, `render_bank_statement(...)`, `render_monthly_certificate(...)`, `render_notice(...)` (term sheet and investor update), `render_export_print(path, rows)`, `write_export_workbook(path, rows) -> str`. Every renderer returns `{"pages": int, "extra": {...}}`; statements and reports put `page_map` and `figures` (`key -> {"page", "label", "printed"}`) in `extra`, which is what a stand-in reader grades against.

- [ ] **Step 1: Write the failing test**

`synthetic/tests/innovation/test_render.py`

```python
"""The renderers for the new document types print what they are given, on pages marked synthetic."""

from __future__ import annotations

from datetime import date

from synthetic.books.innovation import reports
from synthetic.books.innovation.model import LAST
from synthetic.render import common
from synthetic.render import innovation as render

END = date(2026, 10, 31)
SPEC = type("Spec", (), {"name": "Dataflake Inc", "auditor": "Wexley Arnault LLP", "city": "Austin", "state": "TX",
                         "legal_form": "corporation"})  # fmt: skip


def text(path) -> str:
    pages = common.page_texts(path)
    assert all(common.MARKER in page for page in pages)
    return "\n".join(pages)


def test_management_financials_print_the_figures_and_the_period_phrases(sims, tmp_path):
    sim = sims["stripple-tech"]
    month, i = sim.months[LAST], LAST
    payload = {"end": END, "months": 10, "prior_end": date(2025, 12, 31), "balances": month.balances,
               "prior": sim.months[11].balances, "ytd": sim.periods[i].values, "month": {**month.flows, **month.balances},
               "labels": {"bs.deferred_revenue_current": "Contract liabilities"},
               "software_roll": reports.software_roll(sim.months, i)}  # fmt: skip
    result = render.render_monthly_financials(tmp_path / "mf.pdf", sim.spec, payload, "mf")
    body = text(tmp_path / "mf.pdf")
    assert "Ten months ended" in body and "One month ended" in body and "month ended October 31, 2026" in body
    assert "Contract liabilities" in body and "Deferred revenue, current" not in body
    figure = result["extra"]["figures"]["bs.cash_unrestricted"]
    assert figure["printed"] == f"{month.balances['bs.cash_unrestricted']:,}" and figure["page"] == 1
    assert result["extra"]["figures"]["cf.vc_capex"]["printed"].startswith("(")  # an outflow prints in brackets


def test_bank_statement_prints_restricted_accounts_and_ties_the_totals(tmp_path):
    accounts = [
        {"name": "Operating account", "tail": "4417", "restricted": False, "opening": 3_000_000, "credits": 800_000,
         "debits": 1_100_000, "closing": 2_700_000},
        {"name": "Collateral account", "tail": "9001", "restricted": True, "opening": 1_500_000, "credits": 0,
         "debits": 0, "closing": 1_500_000},
    ]  # fmt: skip
    result = render.render_bank_statement(tmp_path / "bank.pdf", SPEC, {"end": END, "accounts": accounts,
                                                                        "notes": ["Restricted."]}, "bank")
    body = text(tmp_path / "bank.pdf")
    assert "STATEMENT OF ACCOUNT" in body and "RESTRICTED" in body and "Bank of Stoic" in body
    assert result["extra"]["figures"]["bs.cash_unrestricted"]["printed"] == "$2,700,000"
    assert result["extra"]["figures"]["bs.cash_restricted"]["printed"] == "$1,500,000"


def test_certificate_mrr_report_and_notices(tmp_path):
    reported = {"min_unrestricted_cash": {"required_text": "Not less than $5,000,000", "actual_text": "$6,100,000",
                                          "in_compliance": True, "calculation": [("Unrestricted Cash", "$6,100,000")]}}
    render.render_monthly_certificate(tmp_path / "cc.pdf", SPEC, {
        "end": END, "document_date": date(2026, 11, 12), "signed_by": "Imogen Farrow", "reported": reported,
        "names": {"min_unrestricted_cash": "Minimum Unrestricted Cash"}}, "cc")
    assert "MONTHLY COMPLIANCE CERTIFICATE" in text(tmp_path / "cc.pdf") and "$6,100,000" in text(tmp_path / "cc.pdf")
    render.render_mrr_report(tmp_path / "mrr.pdf", SPEC, {
        "end": END, "mrr": 640_000, "arr": 7_680_000, "net_new_arr": 240_000, "customers": 140, "nrr": 108,
        "opening": 620_000, "new": 20_000, "expansion": 7_000, "contraction": 2_000, "churn": 5_000,
        "trend": [("May 2026", 500_000, 120)]}, "mrr")
    assert "MONTHLY RECURRING REVENUE REPORT" in text(tmp_path / "mrr.pdf")
    render.render_notice(tmp_path / "ts.pdf", SPEC, {
        "heading": "SUMMARY OF TERMS (TERM SHEET)", "subheading": "Series B extension",
        "sections": [("Amount", "$8,000,000")], "table": [["Term", "Summary"], ["Amount", "$8,000,000"]],
        "closing": "Non-binding.", "footer": "Term sheet"}, "ts")
    assert "TERM SHEET" in text(tmp_path / "ts.pdf")


def test_the_export_has_no_company_name_and_carries_the_marker(tmp_path):
    rows = [("2025-01", 800_000, 120), ("2025-02", 820_000, 121)]
    cells = render.write_export_workbook(tmp_path / "mrr_export.xlsx", rows)
    printed = render.render_export_print(tmp_path / "mrr_export.pdf", rows)
    assert "month,mrr_usd,customers" in cells and "SYNTHETIC - FOR DEMONSTRATION" in cells
    assert printed["extra"]["intake_form"] == "pdf_print_of_xlsx"
    assert "Stripple" not in text(tmp_path / "mrr_export.pdf") and "2025-01" in text(tmp_path / "mrr_export.pdf")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest synthetic/tests/innovation/test_render.py -v`
Expected: collection fails with `ModuleNotFoundError: No module named 'synthetic.render.innovation'`.

- [ ] **Step 3: Implement**

The monthly statements print two columns for income and cash flow ("Ten months ended" year to date, and "One month ended"), balances at the month end and the prior fiscal year end, and a capitalised software roll-forward note. The period phrases are the ones intake and the quote guardrail recognise ("month ended", "ten months ended"). Printed labels can be overridden per document (Stripple's October package).

`synthetic/books/innovation/layout.py`

```python
"""Printed layout of the vc-1 statements: label, kind and order of every line. Own copy; never read from backend/app."""
from __future__ import annotations

# (kind, key or heading). kind: head | line | total | grand
INCOME = (
    ("head", "Revenue"), ("line", "is.subscription_revenue"), ("line", "is.services_revenue"), ("total", "is.total_revenue"),
    ("line", "is.cost_of_revenue"), ("total", "is.vc_gross_profit"),
    ("head", "Operating expenses"), ("line", "is.rnd"), ("line", "is.sales_marketing"), ("line", "is.gna"),
    ("line", "is.vc_depreciation_amortization"), ("total", "is.vc_operating_loss"),
    ("line", "is.vc_interest"), ("line", "is.vc_other_income"), ("grand", "is.vc_net_loss"),
)
BALANCE = (
    ("head", "Assets"), ("line", "bs.cash_unrestricted"), ("line", "bs.cash_restricted"), ("total", "bs.vc_total_cash"),
    ("line", "bs.short_term_investments"), ("line", "bs.accounts_receivable"), ("line", "bs.other_current_assets"),
    ("line", "bs.capitalised_software"), ("line", "bs.vc_other_intangibles"), ("line", "bs.other_noncurrent_assets"),
    ("grand", "bs.vc_total_assets"),
    ("head", "Liabilities"), ("line", "bs.accounts_payable"), ("line", "bs.accrued_liabilities"),
    ("line", "bs.deferred_revenue_current"), ("line", "bs.deferred_revenue_noncurrent"),
    ("line", "bs.venture_debt_current"), ("line", "bs.venture_debt_noncurrent"), ("line", "bs.convertible_notes"),
    ("line", "bs.safes"), ("line", "bs.vc_other_liabilities"), ("total", "bs.vc_total_liabilities"),
    ("head", "Stockholders' equity"), ("line", "bs.preferred_equity"), ("line", "bs.common_equity"),
    ("total", "bs.vc_total_equity"), ("grand", "bs.vc_total_liabilities_and_equity"),
)
CASHFLOW = (
    ("head", "Operating activities"), ("line", "cf.vc_operating_cash_flow"),
    ("head", "Investing activities"), ("line", "cf.vc_capex"), ("line", "cf.capitalised_software_spend"),
    ("head", "Financing activities"), ("line", "cf.equity_raised"), ("line", "cf.debt_raised"),
    ("line", "cf.vc_other_financing"), ("grand", "cf.vc_net_change_in_cash"),
)
LABELS = {
    "is.subscription_revenue": "Subscription revenue", "is.services_revenue": "Services revenue",
    "is.total_revenue": "Total revenue", "is.cost_of_revenue": "Cost of revenue", "is.vc_gross_profit": "Gross profit",
    "is.rnd": "Research and development", "is.sales_marketing": "Sales and marketing",
    "is.gna": "General and administrative", "is.vc_depreciation_amortization": "Depreciation and amortization",
    "is.vc_operating_loss": "Operating income (loss)", "is.vc_interest": "Interest expense",
    "is.vc_other_income": "Other income (expense), net", "is.vc_net_loss": "Net income (loss)",
    "bs.cash_unrestricted": "Cash in operating accounts", "bs.cash_restricted": "Cash pledged or restricted",
    "bs.vc_total_cash": "Total cash", "bs.short_term_investments": "Short-term investments",
    "bs.accounts_receivable": "Accounts receivable, net", "bs.other_current_assets": "Other current assets",
    "bs.capitalised_software": "Capitalised software, net", "bs.vc_other_intangibles": "Other intangibles, net",
    "bs.other_noncurrent_assets": "Other assets", "bs.vc_total_assets": "Total assets",
    "bs.accounts_payable": "Accounts payable", "bs.accrued_liabilities": "Accrued liabilities",
    "bs.deferred_revenue_current": "Deferred revenue, current", "bs.deferred_revenue_noncurrent": "Deferred revenue, non-current",
    "bs.venture_debt_current": "Venture debt, current portion", "bs.venture_debt_noncurrent": "Venture debt, net of current portion",
    "bs.convertible_notes": "Convertible notes", "bs.safes": "SAFEs", "bs.vc_other_liabilities": "Other liabilities",
    "bs.vc_total_liabilities": "Total liabilities", "bs.preferred_equity": "Preferred stock",
    "bs.common_equity": "Common stock and accumulated deficit", "bs.vc_total_equity": "Total stockholders' equity",
    "bs.vc_total_liabilities_and_equity": "Total liabilities and stockholders' equity",
    "cf.vc_operating_cash_flow": "Net cash used in operating activities", "cf.vc_capex": "Purchases of property and equipment",
    "cf.capitalised_software_spend": "Capitalised software development", "cf.equity_raised": "Proceeds from issuance of preferred stock",
    "cf.debt_raised": "Proceeds from venture debt", "cf.vc_other_financing": "Other financing",
    "cf.vc_net_change_in_cash": "Net change in cash",
}
OUTFLOWS = frozenset({"cf.vc_capex", "cf.capitalised_software_spend"})  # stored positive, printed in brackets
```

`synthetic/render/innovation.py`

```python
"""Renderers for the innovation book's documents. Reuses the shared page template in synthetic.render.common."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Spacer, Table, TableStyle

from synthetic.books.innovation.layout import BALANCE, CASHFLOW, INCOME, LABELS, OUTFLOWS
from synthetic.render import common
from synthetic.render.common import (
    COVER_LINE,
    COVER_TITLE,
    HEADING,
    RULE,
    SMALL,
    SUBTITLE,
    TITLE,
    Mark,
    accounting,
    para,
)
from synthetic.render.statements import _auditor_report

D = Decimal
LENDER = "Bank of Stoic"
WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
         11: "Eleven", 12: "Twelve"}


def long_date(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def usd(value) -> str:
    v = int(value)
    return f"(${abs(v):,})" if v < 0 else f"${v:,}"


def _grid(total_rows=(), header=True, size=9):
    styles = [("FONT", (0, 0), (-1, -1), "Helvetica", size), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
              ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("TOPPADDING", (0, 0), (-1, -1), 2.4),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6)]
    if header:
        styles += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE)]
    for r in total_rows:
        styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", size), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
    return styles


def _table(rows, widths, total_rows=(), header=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle(_grid(total_rows, header)))
    return t


class _Sheet:
    """Builds statement tables and remembers what was printed where."""

    def __init__(self, labels: dict[str, str]):
        self.labels, self.marks, self.keys = labels, {}, {}

    def table(self, section: str, layout, headers, now: dict, before: dict) -> list:
        data, styles = [["", *headers]], []
        printed = self.keys.setdefault(section, {})
        for kind, key in layout:
            r = len(data)
            if kind == "head":
                data.append([key, "", ""])
                styles += [("FONT", (0, r), (0, r), "Helvetica-Bold", 9.5), ("TOPPADDING", (0, r), (-1, r), 7)]
                continue
            sign = -1 if key in OUTFLOWS else 1
            a, b = accounting(D(now[key] * sign)), accounting(D(before[key] * sign))
            label = self.labels.get(key, LABELS[key])
            data.append([label, a, b])
            printed[key] = (label, a, b)
            if kind == "line":
                styles.append(("LEFTPADDING", (0, r), (0, r), 16))
            else:
                styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", 9.5), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
        t = Table(data, colWidths=[3.95 * inch, 1.3 * inch, 1.3 * inch], hAlign="LEFT")
        t.setStyle(TableStyle(_grid(header=True, size=9.5) + styles))
        return [Mark(self.marks, section), t]

    def figures(self) -> dict:
        return {k: {"page": self.marks[s], "label": lab, "printed": a}
                for s, keys in self.keys.items() for k, (lab, a, _) in keys.items()}


def _head(spec_name: str, statement: str, line: str) -> list:
    return [para(spec_name, TITLE), para(statement, SUBTITLE), para(line, SUBTITLE),
            para("(in U.S. dollars)", SMALL), Spacer(1, 8)]


def render_monthly_financials(path: Path, spec, payload: dict, title: str) -> dict:
    end, months = payload["end"], payload["months"]
    sheet = _Sheet(payload.get("labels", {}))
    ytd_head = f"{WORDS[months]} month{'s' if months > 1 else ''} ended\n{long_date(end)}"
    month_head = f"One month ended\n{long_date(end)}"
    point_head = (f"{long_date(end)}", f"{long_date(payload['prior_end'])}")
    line = f"For the month ended {long_date(end)}, with year to date"
    story = [*_head(spec.name, "Management Financial Statements (Unaudited)", line)]
    story += [para("Balance Sheet", HEADING)] + sheet.table("balance_sheet", BALANCE, point_head, payload["balances"], payload["prior"])
    story.append(PageBreak())
    story += _head(spec.name, "Statement of Operations", line)
    story += sheet.table("income_statement", INCOME, (ytd_head, month_head), payload["ytd"], payload["month"])
    story.append(PageBreak())
    story += _head(spec.name, "Statement of Cash Flows", line)
    story += sheet.table("cash_flow", CASHFLOW, (ytd_head, month_head), payload["ytd"], payload["month"])
    story.append(PageBreak())
    roll = payload["software_roll"]
    story += _head(spec.name, "Note 1 - Capitalised software", line)
    story += [_table([["", "Month ended"], ["Balance at start of month", usd(roll["opening"])],
                      ["Additions (capitalised development)", usd(roll["additions"])],
                      ["Amortisation", usd(-roll["amortisation"])], ["Balance at end of month", usd(roll["closing"])]],
                     [3.95 * inch, 1.3 * inch], total_rows=(4,)), Spacer(1, 8)]
    story.append(para("Prepared by management from the books of the Company. Not audited or reviewed. Amounts are in "
                      "whole U.S. dollars.", SMALL))
    pages = common.build_pdf(path, title, f"{spec.name} | Management financials {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "page_map": dict(sheet.marks), "figures": sheet.figures(),
                                      "months": months, "period_basis": "fiscal_year_to_date"}}


def render_annual_statements(path: Path, spec, payload: dict, title: str) -> dict:
    end, prior = payload["end"], payload["prior_end"]
    sheet = _Sheet({})
    head = (f"Year ended\n{long_date(end)}", f"Year ended\n{long_date(prior)}")
    point = (long_date(end), long_date(prior))
    line = f"For the years ended December 31, {end.year} and {prior.year}"
    story = [Spacer(1, 1.6 * inch), para(spec.name, COVER_TITLE), para("Audited Financial Statements", COVER_LINE),
             para(f"December 31, {end.year} and {prior.year}", COVER_LINE),
             para(f"With Independent Auditor's Report of {spec.auditor}", COVER_LINE), PageBreak()]
    story += _auditor_report(spec, end, prior) + [PageBreak()]
    story += _head(spec.name, "Balance Sheets", line) + sheet.table("balance_sheet", BALANCE, point, payload["balances"], payload["prior_balances"])
    story.append(PageBreak())
    story += _head(spec.name, "Statements of Operations", line) + sheet.table("income_statement", INCOME, head, payload["flows"], payload["prior_flows"])
    story.append(PageBreak())
    story += _head(spec.name, "Statements of Cash Flows", line) + sheet.table("cash_flow", CASHFLOW, head, payload["flows"], payload["prior_flows"])
    pages = common.build_pdf(path, title, f"{spec.name} | FY{end.year}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "quality": "audited", "page_map": dict(sheet.marks),
                                      "figures": sheet.figures(), "comparative_period_end": prior}}


def render_mrr_report(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    w = [3.4 * inch, 1.6 * inch]
    summary = [["Metric", f"As of {long_date(end)}"], ["Monthly recurring revenue (MRR)", usd(payload["mrr"])],
               ["Annual recurring revenue (ARR)", usd(payload["arr"])], ["Net new ARR in the month", usd(payload["net_new_arr"])],
               ["Customers", f"{payload['customers']:,}"], ["Net revenue retention, trailing 12 months", f"{payload['nrr']}%"]]
    bridge = [["MRR bridge", "Month ended"], ["Opening MRR", usd(payload["opening"])], ["New customers", usd(payload["new"])],
              ["Expansion", usd(payload["expansion"])], ["Contraction", usd(-payload["contraction"])],
              ["Churn", usd(-payload["churn"])], ["Closing MRR", usd(payload["mrr"])]]
    trend = [["Month", "MRR", "Customers"]] + [[m, usd(v), f"{c:,}"] for m, v, c in payload["trend"]]
    story = [Mark(marks, "summary"), para("MONTHLY RECURRING REVENUE REPORT", TITLE), para(spec.name, SUBTITLE),
             para(f"For the month ended {long_date(end)}", SUBTITLE), Spacer(1, 8), _table(summary, w), Spacer(1, 10),
             Mark(marks, "bridge"), _table(bridge, w, total_rows=(6,)), Spacer(1, 10), Mark(marks, "trend"),
             para("Trailing six months", HEADING), _table(trend, [2.0 * inch, 1.5 * inch, 1.1 * inch]),
             Spacer(1, 8), para("MRR is the contracted monthly subscription charge for active customers at month end. "
                                "ARR is twelve times MRR.", SMALL)]
    pages = common.build_pdf(path, title, f"{spec.name} | MRR report {end.isoformat()}", spec.name, story)
    figs = {"saas.mrr": {"page": marks["summary"], "label": "Monthly recurring revenue (MRR)", "printed": usd(payload["mrr"])},
            "saas.arr": {"page": marks["summary"], "label": "Annual recurring revenue (ARR)", "printed": usd(payload["arr"])},
            "saas.customers": {"page": marks["summary"], "label": "Customers", "printed": f"{payload['customers']:,}"}}
    return {"pages": pages, "extra": {"page_map": marks, "figures": figs}}


def render_bank_statement(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    first = date(end.year, end.month, 1)
    rows = [["Account", "Opening", "Credits", "Debits", "Closing"]]
    for a in payload["accounts"]:
        rows.append([f"{a['name']} (ending {a['tail']})" + (" - RESTRICTED" if a["restricted"] else ""),
                     usd(a["opening"]), usd(a["credits"]), usd(-a["debits"]), usd(a["closing"])])
    free = sum(a["closing"] for a in payload["accounts"] if not a["restricted"])
    held = sum(a["closing"] for a in payload["accounts"] if a["restricted"])
    totals = [["Total operating accounts (unrestricted)", usd(free)], ["Total pledged and restricted accounts", usd(held)],
              ["Total balances on deposit", usd(free + held)]]
    story = [Mark(marks, "summary"), para("STATEMENT OF ACCOUNT", TITLE), para(f"{LENDER} - Business Banking", SUBTITLE),
             para(f"Account holder: {spec.name}", SUBTITLE),
             para(f"Statement period: {long_date(first)} to {long_date(end)}", SUBTITLE), Spacer(1, 8),
             Table(rows, colWidths=[2.9 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch], hAlign="LEFT",
                   style=TableStyle(_grid(size=8.5))), Spacer(1, 10), Mark(marks, "totals"),
             _table([["Summary", ""], *totals], [3.4 * inch, 1.6 * inch], total_rows=(3,), header=True)]
    for note in payload["notes"]:
        story += [Spacer(1, 8), para(note, SMALL)]
    pages = common.build_pdf(path, title, f"{spec.name} | Account statement {end.isoformat()}", LENDER, story)
    figs = {"bs.cash_unrestricted": {"page": marks["totals"], "label": "Total operating accounts (unrestricted)", "printed": usd(free)},
            "bs.cash_restricted": {"page": marks["totals"], "label": "Total pledged and restricted accounts", "printed": usd(held)}}
    return {"pages": pages, "extra": {"page_map": marks, "figures": figs}}


def render_monthly_certificate(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    reported = payload["reported"]
    failing = [payload["names"][c] for c, r in reported.items() if not r["in_compliance"]]
    statement = (f"As of {long_date(end)}, the Borrower was not in compliance with: {', '.join(failing)}. The Borrower "
                 "was in compliance with each other financial covenant." if failing else
                 f"As of {long_date(end)}, the Borrower was in compliance with each of the financial covenants set "
                 "forth in Article 6 of the Credit Agreement.")
    rows = [["Covenant", "Section", "Required", "Actual", "In compliance"]]
    for i, (cid, r) in enumerate(reported.items(), start=1):
        rows.append([payload["names"][cid], f"6.{i}", r["required_text"], r["actual_text"], "Yes" if r["in_compliance"] else "No"])
    story = [Mark(marks, "summary"), para("MONTHLY COMPLIANCE CERTIFICATE", TITLE), para(spec.name, SUBTITLE),
             para(f"For the month ended {long_date(end)}", SUBTITLE), Spacer(1, 8), para(f"To: {LENDER}"),
             para(f"Date: {long_date(payload['document_date'])}"),
             para("This certificate is delivered under Section 5.1(c) of the Credit Agreement. The undersigned, the chief "
                  "financial officer of the Borrower, certifies that the covenant calculations in Schedule 1 are true and correct."),
             para(statement), Spacer(1, 6),
             Table(rows, colWidths=[2.0 * inch, 0.65 * inch, 1.65 * inch, 1.45 * inch, 0.95 * inch], hAlign="LEFT",
                   style=TableStyle(_grid(size=8.5))), Spacer(1, 16), para(spec.name.upper()),
             para(f"By: /s/ {payload['signed_by']}"), para("Title: Chief Financial Officer"), PageBreak(),
             Mark(marks, "calculations"), para("Schedule 1 - Covenant Calculations", TITLE),
             para(f"{spec.name} - as of and for the month ended {long_date(end)}", SUBTITLE), Spacer(1, 6)]
    for i, (cid, r) in enumerate(reported.items(), start=1):
        calc = [[label, text] for label, text in r["calculation"]]
        calc += [[payload["names"][cid], r["actual_text"]], ["Requirement", r["required_text"]],
                 ["In compliance", "Yes" if r["in_compliance"] else "No"]]
        story.append(KeepTogether([para(f"Section 6.{i} - {payload['names'][cid]}", HEADING),
                                   _table(calc, [4.4 * inch, 1.9 * inch], total_rows=(len(calc) - 3,), header=False), Spacer(1, 6)]))
    pages = common.build_pdf(path, title, f"{spec.name} | Compliance certificate {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "page_map": marks}}


def render_notice(path: Path, spec, payload: dict, title: str) -> dict:
    """Term sheet and investor update: titled paragraphs and an optional table."""
    marks: dict = {}
    story = [Mark(marks, "start"), para(payload["heading"], TITLE), para(spec.name, SUBTITLE),
             para(payload["subheading"], SUBTITLE), Spacer(1, 8)]
    for head, text in payload["sections"]:
        story += [para(head, HEADING), para(text)]
    if payload.get("table"):
        story += [Spacer(1, 6), _table(payload["table"], [3.0 * inch, 1.8 * inch])]
    story.append(para(payload["closing"], SMALL))
    pages = common.build_pdf(path, title, f"{spec.name} | {payload['footer']}", spec.name, story)
    return {"pages": pages, "extra": {"page_map": marks}}


def render_export_print(path: Path, rows: list[tuple[str, int, int]]) -> dict:
    """A print of mrr_export.xlsx: no company name, no title, the sheet as it came."""
    data = [["month", "mrr_usd", "customers"]] + [[m, f"{v:,}", f"{c:,}"] for m, v, c in rows]
    story = [_table(data, [1.6 * inch, 1.4 * inch, 1.2 * inch])]
    pages = common.build_pdf(path, "mrr_export", "mrr_export.xlsx | sheet: export", "", story)
    return {"pages": pages, "extra": {"intake_form": "pdf_print_of_xlsx"}}


def write_export_workbook(path: Path, rows: list[tuple[str, int, int]]) -> str:
    """The real mrr_export.xlsx. Returns the text of its cells (hashed for the manifest)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "export"
    ws.append(["month", "mrr_usd", "customers"])
    for row in rows:
        ws.append(list(row))
    ws.append([])
    ws.append(["SYNTHETIC - FOR DEMONSTRATION"])
    ws.oddFooter.center.text = "SYNTHETIC - FOR DEMONSTRATION"
    wb.properties.creator = ""
    wb.properties.title = "export"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return "\n".join(",".join(str(c) for c in r) for r in ([["month", "mrr_usd", "customers"], *rows, [], ["SYNTHETIC - FOR DEMONSTRATION"]]))
```

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest synthetic/tests/innovation -v && uv run ruff check synthetic`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books/innovation/layout.py synthetic/render/innovation.py synthetic/tests/innovation/test_render.py
git commit -m "feat(p2): renderers for monthly financials, MRR report, bank statement, certificate and notices"
```

---

### Task 5: The document plan, client assembly, and the scenarios verifying themselves

**Files:**
- Create: `synthetic/books/innovation/documents.py`, `synthetic/books/innovation/book.py`, `synthetic/tests/innovation/test_scenarios.py`
- Modify: `synthetic/tests/innovation/conftest.py` (add the `clients` fixture)

**Interfaces:**
- Consumes: Tasks 1–4; the frozen `synthetic.book.DocPlan`.
- Produces (`documents`): `plan_documents(spec, opening, months, periods, fy2024, series, certificates, terms, rng) -> list[DocPlan]`, `certificate_payload(spec, doc, names)`, `notice_documents(spec, series, months, rng)`, `stripple_export(spec, months) -> (DocPlan, rows)`, `package_due(doc_type, period_end)`, `usd(value)`, `month_name(end)`.
- Produces (`book`): `ClientBook` (dataclass: `spec, opening, months, periods, comparative, series, plan, terms, certificates, documents, funding_events, expected, scenario_details`; property `published`), `build_client(spec, seed) -> ClientBook`, `build_clients(seed) -> list[ClientBook]`, `scenario_record(book)`, `verify(book)` (raises `AssertionError` naming the client and scenario), `PENDING` ("cash.statement_mismatch").

- [ ] **Step 1: Write the failing test**

Replace the conftest with the version that also builds the clients:

`synthetic/tests/innovation/conftest.py`

```python
"""Fixtures for the innovation book: every client simulated, and every client built."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.book import ClientBook, build_clients
from synthetic.books.innovation.expected import Series
from synthetic.books.innovation.roster import CLIENTS, ClientSpec


@dataclass
class Sim:
    """One client simulated, with nothing else built."""

    spec: ClientSpec
    opening: model.Month
    months: list[model.Month]
    periods: list[model.Period]
    series: Series


@pytest.fixture(scope="session")
def sims() -> dict[str, Sim]:
    out = {}
    for spec in CLIENTS:
        opening, months = model.simulate(spec)
        out[spec.id] = Sim(spec, opening, months, model.build_periods(months), Series(months))
    return out


@pytest.fixture(scope="session")
def clients() -> dict[str, ClientBook]:
    return {book.spec.id: book for book in build_clients()}
```

`synthetic/tests/innovation/test_scenarios.py`

```python
"""Every scenario of design spec section 10 makes the book say what it should, and the generator checks itself."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from synthetic.books.innovation import model, reports
from synthetic.books.innovation.book import verify
from synthetic.books.innovation.expected import q
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, SCENARIOS

LAST = model.LAST


def exceptions(book) -> list[str]:
    return sorted(e["type"] for e in book.expected["exceptions"])


def current(book) -> dict[str, dict]:
    return {r["covenant_id"]: r for r in book.expected["covenant_tests"] if r["period_end"] == CURRENT_PERIOD}


def current_signals(book) -> list[dict]:
    return [s for s in book.expected["signals"] if s["period_end"] == CURRENT_PERIOD]


def test_every_client_has_a_known_scenario_and_every_scenario_a_client(clients):
    assert {b.spec.scenario for b in clients.values()} == set(SCENARIOS)
    assert len(clients) == 16


def test_the_generator_verifies_itself_and_fails_loudly(clients):
    for book in clients.values():
        verify(book)
    broken = clients["dataflake"]
    original = broken.spec.min_cash
    object.__setattr__(broken.spec, "min_cash", 4_000_000)  # cash would then pass: the scenario is gone
    try:
        with pytest.raises(AssertionError, match="dataflake"):
            verify(broken)
    finally:
        object.__setattr__(broken.spec, "min_cash", original)


def test_the_owners_figures_hold_in_the_assembled_book(clients):
    assert clients["dataflake"].series.cash(LAST) == 4_600_000 and clients["lumora-health"].series.cash(LAST) == 4_000_000
    assert q(clients["tessaract-labs"].series.rml(LAST), 1) == D("27.5")


def test_clean_clients_raise_nothing_and_carry_no_loud_signal(clients):
    for client_id in ("mosswell-robotics", "quillon-ai", "orbitline-systems", "veridia-payments", "tessaract-labs",
                      "pellucid-sensors", "halcyon-grid", "kelvra-bio", "brightvane-energy", "ferrogate-cloud"):
        book = clients[client_id]
        assert exceptions(book) == [], client_id
        loud = [s["rule"] for s in current_signals(book) if s["severity"] != "low" and s["rule"] != "runway_falling"]
        assert loud == [], client_id


def test_dataflake_certificate_counts_pledged_cash_and_claims_compliance(clients):
    book = clients["dataflake"]
    row = current(book)["min_unrestricted_cash"]
    assert row["value"] == D(4_600_000) < row["threshold"] == D(5_000_000)
    assert row["reported_value"] == D(6_100_000) and row["reported_in_compliance"] is True
    assert row["outcome"] == "breach_reported_compliant"
    assert exceptions(book) == ["covenant.reported_mismatch", "signal.high"]
    assert book.scenario_details["definition_clause"] == {"_anchor": ("credit-agreement", "def_unrestricted_cash")}


def test_dataflakes_extension_is_a_signed_term_sheet_closing_on_12_december(clients):
    events = clients["dataflake"].funding_events
    assert [(e["kind"], e["amount"], e["expected_close"], e["status"]) for e in events] == [
        ("extension", 8_000_000, date(2026, 12, 12), "signed")]
    assert events[0]["evidence_document_ids"] == ["dataflake.term-sheet-2026-11-10"]


def test_lumora_october_package_is_12_days_late(clients):
    book = clients["lumora-health"]
    assert max(i["days_late"] for i in book.scenario_details["reporting"]) == 12
    assert (AS_OF - date(2026, 11, 7)).days == 12  # bank statements are due 7 days after month end
    assert exceptions(book) == ["intake.missing_document"] * 2
    assert not [d for d in book.documents if d.period_end == CURRENT_PERIOD]
    assert all(r["outcome"] == "cannot_test" and r["after_repair"]["pass"] for r in current(book).values())
    assert not current_signals(book)
    assert [d.id for d in book.documents if d.period_end == date(2026, 9, 30)][:1] == ["lumora-health.bank-2026-09-30"]


def test_brightvane_runway_falls_three_months_running_and_stays_above_the_watch_level(clients):
    book = clients["brightvane-energy"]
    points = [book.series.rml(i) for i in range(LAST - 3, LAST + 1)]
    assert all(b < a for a, b in zip(points, points[1:], strict=False)) and points[-1] >= 12
    rules = {s["rule"] for s in current_signals(book)}
    assert "runway_falling" in rules and "burn_rising" not in rules and "runway_below_watch" not in rules


def test_corvane_misses_plan_two_months_running_against_figures_in_the_terms(clients):
    book = clients["corvane-analytics"]
    rows = {(r["period_end"], r["covenant_id"]): r for r in book.expected["covenant_tests"]}
    sep, oct_ = rows[(date(2026, 9, 30), "revenue_vs_plan")], rows[(CURRENT_PERIOD, "revenue_vs_plan")]
    aug = rows[(date(2026, 8, 31), "revenue_vs_plan")]
    assert aug["outcome"] == "compliant" and sep["outcome"] == "breach" and oct_["outcome"] == "breach"
    assert exceptions(book) == ["covenant.breach"]
    covenant = book.terms.version["terms"]["covenants"][2]
    assert covenant["test"]["threshold"] == "0.80" and covenant["measurement"]["basis"] == "t3m"
    assert len(covenant["params"]["plan"]) == 18  # plan figures are terms data, 18 months


def test_nimbusfield_funding_slipped_and_runway_is_under_nine_months(clients):
    book = clients["nimbusfield-security"]
    assert book.funding_events[0]["expected_close"] < AS_OF and book.funding_events[0]["status"] == "expected"
    assert book.series.rml(LAST) < 9
    assert exceptions(book) == ["funding_slipped", "signal.high"]


def test_tidewell_certificate_counts_a_restricted_account(clients):
    book = clients["tidewell-medical"]
    assert book.series.cash(LAST) == 4_300_000
    cash = current(book)["min_unrestricted_cash"]
    assert cash["outcome"] == "compliant_variance" and cash["reported_value"] - cash["value"] == 1_000_000
    assert exceptions(book) == ["cash.statement_mismatch"]
    assert sum(a["closing"] for a in reports.bank_accounts(book.spec, book.months, LAST) if a["restricted"]) == 1_100_000


def test_ferrogate_is_cash_flow_positive_and_runway_is_not_meaningful(clients):
    book = clients["ferrogate-cloud"]
    row = current(book)["min_runway_months"]
    assert (row["value"], row["pass"], row["note"], row["outcome"]) == (
        None, True, "not_meaningful_cash_flow_positive", "compliant")
    assert row["reported_value"] is None and row["reported_in_compliance"] is True
    assert not [s for s in current_signals(book) if s["rule"].startswith("runway")]


def test_stripple_roll_ties_and_misreading_it_changes_runway_a_lot(clients):
    book = clients["stripple-tech"]
    details = book.scenario_details["capitalised_software"]
    roll = reports.software_roll(book.months, LAST)
    assert roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"]
    assert details["balance"] > 10 * details["month_spend"]
    assert reports.misread_runway(book.series, LAST) < book.series.rml(LAST) * D("0.7")
    assert q(reports.misread_runway(book.series, LAST), 2) == details["misread_runway"]
    assert exceptions(book) == ["intake.unclassified", "spread.value_unverified"]
    assert book.scenario_details["new_line"]["belongs_to"] == "bs.deferred_revenue_current"
    export = next(d for d in book.documents if d.id == "stripple-tech.mrr-export")
    assert export.extra["held"] is True and export.period_end is None and len(export.payload["rows"]) == 10


def test_funding_events_cover_dataflake_halcyon_kelvra_and_nimbusfield(clients):
    events = {cid: b.funding_events for cid, b in clients.items() if b.funding_events}
    assert sorted(events) == ["dataflake", "halcyon-grid", "kelvra-bio", "nimbusfield-security"]
    assert (events["halcyon-grid"][0]["kind"], events["halcyon-grid"][0]["expected_close"]) == (
        "equity_round", date(2027, 3, 31))
    assert (events["kelvra-bio"][0]["kind"], events["kelvra-bio"][0]["expected_close"]) == (
        "milestone_tranche", date(2027, 2, 26))
    for cid, rows in events.items():
        ids = {d.id for d in clients[cid].documents}
        assert all(rows_[0] for rows_ in [e["evidence_document_ids"] for e in rows]), cid
        assert all(set(e["evidence_document_ids"]) <= ids for e in rows), cid
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest synthetic/tests/innovation/test_scenarios.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'synthetic.books.innovation.book'`.

- [ ] **Step 3: Implement**

`verify` is the generator checking itself: the owner's October figures exactly; no test within a margin of its threshold; every earlier test compliant (Corvane's September is the designed exception); a certificate figure is exact or far outside every tolerance; and one block per scenario of spec 10. A change to the roster or model that breaks a scenario stops generation with a message naming the client.

`synthetic/books/innovation/documents.py`

```python
"""The documents each client sends: which exist, when they arrived, and what is printed on them."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from synthetic.book import DocPlan
from synthetic.books.innovation import reports
from synthetic.books.innovation.expected import DUE_DAYS, Series
from synthetic.books.innovation.model import LAST, MONTHS, Month, Period
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, ClientSpec
from synthetic.books.innovation.terms import SLUG, ClientTerms

D = Decimal
PACKAGE_MONTHS = (LAST - 2, LAST - 1, LAST)  # the three months with documents on file
STRIPPLE_LABELS = {
    "bs.deferred_revenue_current": "Contract liabilities",
    "bs.capitalised_software": "Capitalised software development costs",
    "cf.capitalised_software_spend": "Software development costs",
}


def month_name(end: date) -> str:
    return end.strftime("%B %Y")


def usd(value) -> str:
    return f"${int(value):,}"


def _received(rng: random.Random, end: date, low: int, high: int) -> date:
    return min(end + timedelta(days=rng.randint(low, high)), AS_OF - timedelta(days=1))


def plan_documents(spec: ClientSpec, opening: Month, months: list[Month], periods: list[Period], fy2024: Period,
                   series: Series, certificates: list[dict], terms: ClientTerms, rng: random.Random) -> list[DocPlan]:
    """All documents on file for a client at the as-of date."""
    docs: list[DocPlan] = []
    by_end = {c["period_end"]: c for c in certificates}

    def add(slug: str, doc_type: str, title: str, period_end: date | None, received: date, payload: dict) -> DocPlan:
        doc = DocPlan(f"{spec.id}.{slug}", slug, doc_type, title, period_end, received, received, payload)
        docs.append(doc)
        return doc

    add(SLUG, "credit_agreement", f"Venture Loan and Security Agreement between {spec.name} and Bank of Stoic", None,
        spec.closing_date, {"legal": terms.agreement})
    fy2025 = periods[11]
    add("afs-2025", "annual_financial_statements", "Audited financial statements, fiscal 2025", fy2025.period_end,
        date(2026, 4, 3) + timedelta(days=rng.randint(0, 24)),
        {"end": fy2025.period_end, "prior_end": fy2024.period_end, "balances": months[11].balances,
         "prior_balances": opening.balances, "flows": fy2025.values, "prior_flows": fy2024.values})  # fmt: skip
    for i in PACKAGE_MONTHS:
        end, month = MONTHS[i], months[i]
        if spec.scenario == "late_package" and i == LAST:
            continue  # the October package has not arrived
        labels = STRIPPLE_LABELS if spec.scenario == "stripple_package" and i == LAST else {}
        add(f"bank-{end.isoformat()}", "bank_statement", f"Account statement, {month_name(end)}", end,
            _received(rng, end, 2, 6),
            {"end": end, "accounts": reports.bank_accounts(spec, months, i), "notes": reports.bank_notes(spec, i)})
        add(f"mrr-{end.isoformat()}", "mrr_report", f"MRR report, {month_name(end)}", end, _received(rng, end, 4, 10),
            {"end": end, **reports.mrr_bridge(months, i)})
        add(f"mf-{end.isoformat()}", "monthly_financials", f"Management financial statements, {month_name(end)}", end,
            _received(rng, end, 10, 18),
            {"end": end, "months": end.month, "prior_end": date(2025, 12, 31), "balances": month.balances,
             "prior": months[11].balances, "ytd": periods[i].values, "month": {**month.flows, **month.balances},
             "labels": dict(labels), "software_roll": reports.software_roll(months, i)})  # fmt: skip
        cert = by_end[end]
        add(f"mcc-{end.isoformat()}", "compliance_certificate", f"Monthly compliance certificate, {month_name(end)}",
            end, _received(rng, end, 11, 18), {"certificate": cert, "end": end})
    return docs


def certificate_payload(spec: ClientSpec, doc: DocPlan, names: dict[str, str]) -> dict:
    """The renderer's view of a certificate: figures as printed."""
    cert = doc.payload["certificate"]
    reported = {}
    for covenant_id, entry in cert["reported"].items():
        reported[covenant_id] = {
            "in_compliance": entry["in_compliance"],
            "required_text": reports.format_required(entry["unit"], entry["threshold"]),
            "actual_text": reports.format_actual(entry["unit"], entry["value"]),
            "calculation": [(line["label"], usd(line["amount"])) for line in entry["calculation"]],
        }
    return {"end": cert["period_end"], "document_date": doc.document_date, "signed_by": cert["signed_by"],
            "reported": reported, "names": names}  # fmt: skip


def notice_documents(spec: ClientSpec, series: Series, months: list[Month], rng: random.Random) -> list[DocPlan]:
    """Term sheets and investor updates for the clients with a funding event the bank is tracking."""
    docs: list[DocPlan] = []
    oct_month = months[LAST]
    for event in spec.funding:
        close = event.expected_close
        if spec.id in ("dataflake", "nimbusfield-security"):
            signed = spec.id == "dataflake"
            doc_date = date(2026, 11, 10) if signed else date(2026, 9, 24)
            round_name = "Series B extension" if signed else "Series A-2 preferred stock financing"
            payload = {
                "heading": "SUMMARY OF TERMS (TERM SHEET)", "subheading": f"{round_name} - dated {doc_date:%B} {doc_date.day}, {doc_date.year}",
                "sections": [
                    ("Issuer", f"{spec.name}, a Delaware corporation."),
                    ("Transaction", f"Sale of {usd(event.amount)} of preferred stock to the lead investor and existing "
                                    "investors, as the " + round_name + "."),
                    ("Expected closing", f"On or about {close:%B} {close.day}, {close.year}, subject to the conditions below."),
                    ("Conditions", "Completion of confirmatory diligence, definitive documents, and the Lender's "
                                   "consent where the loan agreement requires it."),
                ],
                "table": [["Term", "Summary"], ["Amount", usd(event.amount)], ["Security", "Preferred stock"],
                          ["Expected closing", f"{close:%B} {close.day}, {close.year}"]],
                "closing": "This summary is non-binding except for confidentiality. " + ("Signed by the Company and the "
                           "lead investor." if signed else "Not yet signed by all parties."),
                "footer": "Term sheet",
            }  # fmt: skip
            docs.append(DocPlan(f"{spec.id}.term-sheet-{doc_date.isoformat()}", f"term-sheet-{doc_date.isoformat()}",
                                "term_sheet", f"Term sheet, {round_name}", None, doc_date,
                                doc_date + timedelta(days=1 if not signed else 2), {"notice": payload}))
    if spec.funding:
        update = {
            "heading": "INVESTOR UPDATE", "subheading": f"{month_name(CURRENT_PERIOD)}",
            "sections": [
                ("Highlights", f"Monthly recurring revenue closed the month at {usd(oct_month.balances['saas.mrr'])} "
                               f"({usd(oct_month.balances['saas.arr'])} annualised) across "
                               f"{oct_month.balances['saas.customers']:,} customers."),
                ("Cash and runway", f"Cash in operating accounts was {usd(series.cash(LAST))} at month end."),
                ("Financing", spec.funding[0].note + "."),
            ],
            "table": [["Metric", month_name(CURRENT_PERIOD)], ["MRR", usd(oct_month.balances["saas.mrr"])],
                      ["Customers", f"{oct_month.balances['saas.customers']:,}"],
                      ["Cash in operating accounts", usd(series.cash(LAST))]],
            "closing": "Sent to the Company's investors. Figures are management's and unaudited.",
            "footer": "Investor update",
        }  # fmt: skip
        received = date(2026, 11, 9) + timedelta(days=rng.randint(0, 4))
        docs.append(DocPlan(f"{spec.id}.investor-update-{CURRENT_PERIOD.isoformat()}",
                            f"investor-update-{CURRENT_PERIOD.isoformat()}", "investor_update",
                            f"Investor update, {month_name(CURRENT_PERIOD)}", CURRENT_PERIOD, received, received,
                            {"notice": update}))
    return docs


def stripple_export(spec: ClientSpec, months: list[Month]) -> tuple[DocPlan, list[tuple[str, int, int]]]:
    """The stray MRR export: ten months of 2025 (the wrong year), no company name anywhere."""
    rows = [(MONTHS[i].strftime("%Y-%m"), months[i].balances["saas.mrr"], months[i].balances["saas.customers"])
            for i in range(10)]  # fmt: skip
    doc = DocPlan(f"{spec.id}.mrr-export", "mrr_export", "unclassified", "mrr_export", None, date(2026, 11, 5),
                  date(2026, 11, 5), {"rows": rows}, extra={"held": True})
    return doc, rows


def package_due(doc_type: str, period_end: date = CURRENT_PERIOD) -> date:
    return period_end + timedelta(days=DUE_DAYS[doc_type])
```

`synthetic/books/innovation/book.py`

```python
"""Assemble one innovation client (data only; nothing is rendered here), compute what the engine should reach, and
check that the scenario came out exactly as designed."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from synthetic.book import DocPlan
from synthetic.books.innovation import documents, model, reports
from synthetic.books.innovation.expected import (
    EXCEPTION_SEVERITY,
    FIRST_TEST,
    TOLERANCE,
    Series,
    build_plan,
    compute_signals,
    covenant_rows,
    plan_ratio,
    q,
)  # fmt: skip
from synthetic.books.innovation.model import LAST, MONTHS, Month, N, Period
from synthetic.books.innovation.roster import (
    AS_OF,
    CLIENTS,
    CURRENT_PERIOD,
    DEFAULT_SEED,
    SCENARIOS,
    ClientSpec,
)  # fmt: skip
from synthetic.books.innovation.terms import SLUG, ClientTerms, build_terms

D = Decimal
MARGIN = {"usd": D(50_000), "months": D("0.5"), "pct": D("0.03")}  # no test sits closer to its threshold than this
PENDING = "cash.statement_mismatch"  # raised by the statements-to-certificate reconciliation (Phase 3)
REQUIREMENTS = (("bank_statements", "bank_statement"), ("mrr_report", "mrr_report"),
                ("monthly_financials", "monthly_financials"), ("compliance_certificate", "compliance_certificate"))  # fmt: skip


@dataclass
class ClientBook:
    spec: ClientSpec
    opening: Month
    months: list[Month]
    periods: list[Period]  # all 22; `published` is what is printed
    comparative: Period
    series: Series
    plan: dict[date, int]
    terms: ClientTerms
    certificates: list[dict]
    documents: list[DocPlan]
    funding_events: list[dict]
    expected: dict
    scenario_details: dict

    @property
    def published(self) -> list[Period]:
        return self.periods[model.PUBLISHED_FROM :]


def _funding_events(spec: ClientSpec, docs: list[DocPlan]) -> list[dict]:
    events = []
    for event in spec.funding:
        evidence = [d.id for d in docs if d.type == "term_sheet"] if event.kind == "extension" or spec.id == "nimbusfield-security" \
            else [d.id for d in docs if d.type == "investor_update"]  # fmt: skip
        events.append({"kind": event.kind, "amount": event.amount, "expected_close": event.expected_close,
                       "status": event.status, "note": event.note, "evidence_document_ids": evidence})  # fmt: skip
    return events


def _reporting_items(docs: list[DocPlan]) -> list[dict]:
    items = []
    for requirement, doc_type in REQUIREMENTS:
        due = documents.package_due(doc_type)
        doc = next((d for d in docs if d.type == doc_type and d.period_end == CURRENT_PERIOD), None)
        reference = doc.received_date if doc else AS_OF
        items.append({"requirement": requirement, "document_type": doc_type, "due_date": due,
                      "received_date": doc.received_date if doc else None, "days_late": (reference - due).days})  # fmt: skip
    return items


def _expected(spec: ClientSpec, series: Series, plan: dict, terms: ClientTerms, docs: list[DocPlan],
              events: list[dict], details: dict) -> dict:
    rows = covenant_rows(spec, series, plan, terms.version["id"], terms.facility["id"])
    halted = spec.scenario == "late_package"
    items = _reporting_items(docs)
    if halted:  # the October package has not arrived: October cannot be tested yet
        for row in rows:
            if row["period_end"] == CURRENT_PERIOD:
                row["after_repair"] = {"value": row["value"], "pass": row["pass"], "headroom": row["headroom"],
                                       "outcome": row["outcome"]}  # fmt: skip
                row.update(value=None, headroom=None, outcome="cannot_test", note=None, missing="package_not_received")
                row["pass"] = None
    visible = [r for r in rows if r["outcome"] != "cannot_test"]
    signals: list[dict] = []
    for i in range(FIRST_TEST + 3, N):
        if halted and i == LAST:
            continue  # financial signals are unmeasured while the spread is blocked
        late = [(it["requirement"], it["days_late"]) for it in items] if i == LAST else []
        signals += compute_signals(series, plan, visible, i, late)

    exceptions: list[dict] = []

    def raise_exception(kind: str, subject: str, summary: str) -> None:
        exceptions.append({"type": kind, "severity": EXCEPTION_SEVERITY[kind], "period_end": CURRENT_PERIOD,
                           "subject": subject, "summary": summary})  # fmt: skip

    for it in items:
        if it["received_date"] is None and it["days_late"] > 0:
            raise_exception("intake.missing_document", f"requirement:{it['requirement']}",
                            f"{it['document_type']} for {CURRENT_PERIOD.isoformat()} was due "
                            f"{it['due_date'].isoformat()} and has not been received.")
    chasing = any(e["type"] == "intake.missing_document" for e in exceptions)
    if spec.scenario == "stripple_package":
        raise_exception("intake.unclassified", f"document:{spec.id}.mrr-export",
                        "mrr_export.xlsx names no company and shows 2025, not October 2026: which client and month?")
        raise_exception("spread.value_unverified", f"document:{spec.id}.mf-{CURRENT_PERIOD.isoformat()}",
                        "'Contract liabilities' is not a template line, and the capitalised software figure may be "
                        "the balance rather than the month's spending.")
    if spec.scenario == "restricted_account":
        raise_exception(PENDING, f"cash:{CURRENT_PERIOD.isoformat()}",
                        "Bank statements show the escrow collateral account as restricted; the certificate counts it "
                        "as unrestricted cash.")
    for event in events:
        if event["status"] in ("expected", "signed") and event["expected_close"] < AS_OF:
            raise_exception("funding_slipped", f"funding_event:{event['kind']}:{event['expected_close'].isoformat()}",
                            f"The {event['kind'].replace('_', ' ')} expected to close on "
                            f"{event['expected_close'].isoformat()} has not closed.")
    for row in rows:
        if row["period_end"] != CURRENT_PERIOD:
            continue
        if row["outcome"] == "breach":
            raise_exception("covenant.breach", f"covenant:{row['covenant_id']}", f"{row['covenant_name']} fails its threshold.")
        elif row["outcome"] == "breach_reported_compliant":
            raise_exception("covenant.reported_mismatch", f"covenant:{row['covenant_id']}",
                            f"{row['covenant_name']} fails its threshold while the certificate claims compliance.")
    for signal in signals:
        if signal["period_end"] == CURRENT_PERIOD and signal["severity"] == "high":
            if signal["rule"] == "reporting_late" and chasing:
                continue  # one late filing is one question for a person
            raise_exception("signal.high", f"signal:{signal['rule']}", f"High-severity signal {signal['rule']}.")
    details["reporting"] = items
    return {"covenant_tests": rows, "borrowing_base": [], "signals": signals, "exceptions": exceptions}


def _details(spec: ClientSpec, series: Series, plan: dict, docs: list[DocPlan], events: list[dict]) -> dict:
    """Facts a grader needs that are not obvious from the rest of the file."""
    if spec.scenario == "pledged_cash":
        return {"covenant_id": "min_unrestricted_cash", "true_unrestricted_cash": series.cash(LAST),
                "pledged_cash_counted": spec.pledged, "certificate_cash": series.cash(LAST) + spec.pledged,
                "threshold": spec.min_cash, "definition_clause": {"_anchor": (SLUG, "def_unrestricted_cash")}}  # fmt: skip
    if spec.scenario == "late_package":
        return {"missing_requirements": ["bank_statements", "mrr_report"], "days_late": 12}
    if spec.scenario == "runway_falling":
        return {"rml_by_month": {MONTHS[i].isoformat(): q(series.rml(i), 2) for i in range(LAST - 3, LAST + 1)}}
    if spec.scenario == "plan_miss":
        return {"plan_ratio_by_month": {MONTHS[i].isoformat(): q(plan_ratio(series, plan, i), 4)
                                        for i in range(LAST - 3, LAST + 1)}}  # fmt: skip
    if spec.scenario == "funding_slipped":
        event = events[0]
        return {"event": {k: event[k] for k in ("kind", "amount", "expected_close")},
                "days_past_expected_close": (AS_OF - event["expected_close"]).days,
                "rml": q(series.rml(LAST), 2)}  # fmt: skip
    if spec.scenario == "restricted_account":
        return {"newly_restricted": spec.extra["newly_restricted"], "certificate_cash": series.cash(LAST) + spec.extra["newly_restricted"],
                "statement_unrestricted_cash": series.cash(LAST)}  # fmt: skip
    if spec.scenario == "cash_flow_positive":
        return {"avg_net_burn": q(series.avg_burn(LAST), 2)}
    if spec.scenario == "stripple_package":
        return {
            "new_line": {"printed_label": "Contract liabilities", "belongs_to": "bs.deferred_revenue_current",
                         "document_id": f"{spec.id}.mf-{CURRENT_PERIOD.isoformat()}"},
            "capitalised_software": {"balance_key": "bs.capitalised_software", "spend_key": "cf.capitalised_software_spend",
                                     "balance": series.months[LAST].balances["bs.capitalised_software"],
                                     "month_spend": series.months[LAST].flows["cf.capitalised_software_spend"],
                                     "misread_runway": q(reports.misread_runway(series, LAST), 2),
                                     "true_runway": q(series.rml(LAST), 2)},
            "held_file": {"document_id": f"{spec.id}.mrr-export", "reason": "no company name; rows are 2025, not 2026"},
        }  # fmt: skip
    return {}


def build_client(spec: ClientSpec, seed: int = DEFAULT_SEED) -> ClientBook:
    opening, months = model.simulate(spec, seed)
    periods = model.build_periods(months)
    problems = model.check_periods(opening, periods)
    if problems:
        raise AssertionError(f"{spec.id}: {problems[:3]}")
    comparative = model.comparative_fy2024(opening, periods[11])
    series = Series(months)
    plan = build_plan(spec, series)
    terms = build_terms(spec, plan)
    certificates = reports.build_certificates(spec, series, plan)
    rng = random.Random(f"{seed}:{spec.id}:documents")
    docs = documents.plan_documents(spec, opening, months, periods, comparative, series, certificates, terms, rng)
    docs += documents.notice_documents(spec, series, months, rng)
    if spec.scenario == "stripple_package":
        docs.append(documents.stripple_export(spec, months)[0])
    events = _funding_events(spec, docs)
    details = _details(spec, series, plan, docs, events)
    result = _expected(spec, series, plan, terms, docs, events, details)
    book = ClientBook(spec, opening, months, periods, comparative, series, plan, terms, certificates, docs, events,
                      result, details)
    verify(book)
    return book


def build_clients(seed: int = DEFAULT_SEED) -> list[ClientBook]:
    return [build_client(spec, seed) for spec in CLIENTS]


def scenario_record(book: ClientBook) -> dict:
    return {"code": book.spec.scenario, "description": SCENARIOS[book.spec.scenario], "details": book.scenario_details}


def verify(book: ClientBook) -> None:
    """Fail loudly if the client's figures are not the owner's, or its scenario is not what it is meant to produce."""
    spec, series, result = book.spec, book.series, book.expected
    rows = result["covenant_tests"]
    current = {r["covenant_id"]: r for r in rows if r["period_end"] == CURRENT_PERIOD}
    earlier = [r for r in rows if r["period_end"] != CURRENT_PERIOD]
    kinds = sorted(e["type"] for e in result["exceptions"])
    now_signals = [s for s in result["signals"] if s["period_end"] == CURRENT_PERIOD]

    def need(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(f"{spec.id} ({spec.scenario}): {message}")

    # the owner's October figures (spec 2.1), exactly
    need(series.cash(LAST) == spec.cash, "unrestricted cash at 31 October is not the owner's")
    need(series.net_burn3(LAST) == 3 * spec.burn, "three-month net burn is not three times the owner's average")
    if spec.rml is None:
        need(series.rml(LAST) is None, "runway should not be meaningful")
    else:
        need(q(series.rml(LAST), 1) == D(spec.rml), f"runway is {q(series.rml(LAST), 1)}, the owner's is {spec.rml}")
    need(book.months[LAST].balances["saas.mrr"] == spec.mrr, "MRR at 31 October is not the sized MRR")
    need(book.months[LAST].balances["saas.customers"] == spec.customers, "customers at 31 October")
    need(book.months[LAST].balances["bs.cash_restricted"] == spec.pledged, "pledged cash at 31 October")
    # no test sits on its threshold; every earlier test passes (Corvane's September is the designed exception)
    for r in rows:
        if r["value"] is not None:
            need(abs(r["value"] - r["threshold"]) >= MARGIN[r["unit"]], f"{r['covenant_id']} sits on its threshold")
    allowed = {("2026-09-30", "revenue_vs_plan")} if spec.scenario == "plan_miss" else set()
    for r in earlier:
        if r["outcome"] == "cannot_test":
            continue
        need(r["outcome"] == "compliant" or (r["period_end"].isoformat(), r["covenant_id"]) in allowed,
             f"{r['covenant_id']} {r['period_end']} is {r['outcome']}")
    # a certificate figure is exact, or far outside every tolerance
    for r in rows:
        if r["reported_value"] is not None and r["value"] is not None:
            gap = abs(r["reported_value"] - r["value"])
            need(gap == 0 or gap >= 20 * TOLERANCE[r["unit"]], f"{r['covenant_id']} certificate is within tolerance")
    wanted = {
        "clean": [], "funding_expected": [], "runway_falling": [], "cash_flow_positive": [],
        "pledged_cash": ["covenant.reported_mismatch", "signal.high"],
        "late_package": ["intake.missing_document", "intake.missing_document"],
        "stripple_package": ["intake.unclassified", "spread.value_unverified"],
        "plan_miss": ["covenant.breach"],
        "funding_slipped": ["funding_slipped", "signal.high"],
        "restricted_account": [PENDING],
    }[spec.scenario]
    need(kinds == sorted(wanted), f"exceptions are {kinds}")
    if spec.scenario in ("clean", "funding_expected", "cash_flow_positive", "runway_falling"):
        loud = [s["rule"] for s in now_signals if s["severity"] != "low" and s["rule"] != "runway_falling"]
        need(not loud, f"has loud signals {loud}")
        need(all(r["outcome"] == "compliant" for r in current.values()), "covenants should all pass")
    if spec.scenario in ("clean", "funding_expected"):
        need(not any(s["rule"] == "runway_falling" for s in now_signals), "clean client trips runway_falling")
    if spec.scenario == "pledged_cash":
        cash = current["min_unrestricted_cash"]
        need(cash["outcome"] == "breach_reported_compliant" and cash["reported_value"] > spec.min_cash > cash["value"],
             "certificate should count pledged cash and claim compliance while true cash breaches")
        need(cash["reported_value"] - cash["value"] == spec.pledged, "the difference should be the pledged account")
    if spec.scenario == "late_package":
        need(sorted(e["subject"] for e in result["exceptions"])
             == ["requirement:bank_statements", "requirement:mrr_report"], "wrong requirements missing")
        need(max(i["days_late"] for i in book.scenario_details["reporting"]) == 12, "worst lateness should be 12 days")
        need(all(r["outcome"] == "cannot_test" for r in current.values()), "October should not be testable")
        need(not any(d.period_end == CURRENT_PERIOD for d in book.documents), "no October document should exist")
    if spec.scenario == "runway_falling":
        points = [series.rml(i) for i in range(LAST - 3, LAST + 1)]
        need(all(b < a for a, b in zip(points, points[1:], strict=False)), "runway should fall three months running")
        need(points[-1] >= 12, "runway should still be above the watch level")
        need(any(s["rule"] == "runway_falling" for s in now_signals), "runway_falling should fire")
        need(not any(s["rule"] == "burn_rising" for s in now_signals), "burn_rising should not fire")
    if spec.scenario == "plan_miss":
        ratio = {i: plan_ratio(series, book.plan, i) for i in (LAST - 2, LAST - 1, LAST)}
        need(ratio[LAST - 2] >= D("0.84"), "August should still be above 84 percent of plan")
        need(ratio[LAST - 1] <= D("0.77") and ratio[LAST] <= D("0.77"), "September and October should be under plan")
        need(current["revenue_vs_plan"]["outcome"] == "breach", "plan miss should be a breach")
        need(len(book.terms.version["terms"]["covenants"][2]["params"]["plan"]) == 18, "plan should have 18 months")
    if spec.scenario == "funding_slipped":
        need(book.funding_events[0]["expected_close"] < AS_OF, "the round should be past its date")
        need(series.rml(LAST) < 9, "runway should be under 9 months")
    if spec.scenario == "restricted_account":
        accounts = reports.bank_accounts(spec, book.months, LAST)
        held = sum(a["closing"] for a in accounts if a["restricted"])
        need(held == spec.pledged == spec.extra["newly_restricted"] + spec.extra["restricted_before"],
             "restricted balances should add to the pledged figure")
        need(all(r["outcome"] == "compliant_variance" for r in current.values() if r["covenant_id"] != "revenue_vs_plan"),
             "cash and runway should differ from the certificate but both pass")
    if spec.scenario == "cash_flow_positive":
        need(series.avg_burn(LAST) <= 0, "average net burn should be zero or negative")
        run = current["min_runway_months"]
        need(run["value"] is None and run["pass"] and run["note"] == "not_meaningful_cash_flow_positive",
             "runway should be not meaningful and compliant")
    if spec.scenario == "stripple_package":
        roll = reports.software_roll(book.months, LAST)
        need(roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"], "software roll does not tie")
        need(roll["closing"] > 10 * roll["additions"], "balance should dwarf the month's spending")
        need(reports.misread_runway(series, LAST) < series.rml(LAST) * D("0.7"), "the misread should change runway a lot")
    for event in book.funding_events:
        need(event["kind"] in ("equity_round", "extension", "milestone_tranche", "venture_debt"), "funding kind")
    need(len(spec.id) <= 32, "borrower code is longer than 32 characters")
```

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest synthetic/tests/innovation -v && uv run ruff check synthetic`
Expected: PASS, ruff clean. A scenario assertion that fails here means the design drifted — fix the model or roster parameters, not the assertion.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books/innovation/documents.py synthetic/books/innovation/book.py synthetic/tests/innovation
git commit -m "feat(p2): innovation client assembly with self-verifying scenarios"
```

---

### Task 6: The generator, the four kept borrowers and the answer key

**Files:**
- Create: `synthetic/books/innovation/kept.py`, `synthetic/books/innovation/generate.py`
- Create: `synthetic/tests/innovation/test_scenario_documents.py`, `synthetic/tests/innovation/test_documents.py`, `synthetic/tests/innovation/test_kept_and_oracle.py`
- Modify: `synthetic/tests/innovation/conftest.py` (add `generated`), `.gitignore`, `synthetic/README.md`
- Generate and commit: `synthetic/books/innovation/out/truth/*.json`, `synthetic/books/innovation/out/manifest.json`, `synthetic/books/innovation/oracle.csv`

**Interfaces:**
- Consumes: Tasks 1–5; frozen `synthetic.generate` helpers `_render`, `_truth`, `_oracle_rows`, `_keep_sign_off`, `_resolve_citations`, `plain`, `ORACLE_COLUMNS`; `synthetic.book.build_borrower`.
- Produces: `kept.build_kept(seed=LEGACY_SEED) -> list[BorrowerBook]`; `generate.generate(out, seed=DEFAULT_SEED, oracle=None, legacy_oracle=LEGACY_ORACLE) -> dict` (the manifest) and the CLI `python -m synthetic.books.innovation.generate [--out DIR] [--seed N] [--oracle FILE]`; truth schema `synthetic-truth-2` (innovation clients) beside the unchanged `synthetic-truth-1` (kept four). The innovation truth adds `borrower.template_id = "vc-1"`, `borrower.stage`, `funding_events`, `documents[*].figures`/`page_map`, `scenario.details`, and expected-exception types `funding_slipped`, `intake.unclassified`, `spread.value_unverified`, `cash.statement_mismatch`.

- [ ] **Step 1: Write the failing tests**

Replace the conftest with the final version (adds the `generated` fixture, a full generation into a temporary directory):

`synthetic/tests/innovation/conftest.py`

```python
"""Fixtures for the innovation book: clients simulated, clients built, and one full generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.book import ClientBook, build_clients
from synthetic.books.innovation.expected import Series
from synthetic.books.innovation.generate import generate
from synthetic.books.innovation.roster import CLIENTS, ClientSpec


@dataclass
class Sim:
    """One client simulated, with nothing else built."""

    spec: ClientSpec
    opening: model.Month
    months: list[model.Month]
    periods: list[model.Period]
    series: Series


@pytest.fixture(scope="session")
def sims() -> dict[str, Sim]:
    out = {}
    for spec in CLIENTS:
        opening, months = model.simulate(spec)
        out[spec.id] = Sim(spec, opening, months, model.build_periods(months), Series(months))
    return out


@pytest.fixture(scope="session")
def clients() -> dict[str, ClientBook]:
    return {book.spec.id: book for book in build_clients()}


@dataclass
class Generated:
    out: Path
    oracle: Path
    manifest: dict
    truths: dict[str, dict]

    def text(self, document_id: str) -> list[str]:
        from synthetic.render import common

        doc = next(d for d in self.manifest["documents"] if d["id"] == document_id)
        return common.page_texts(self.out / doc["path"])


@pytest.fixture(scope="session")
def generated(tmp_path_factory) -> Generated:
    root = tmp_path_factory.mktemp("innovation-book")
    out = root / "out"
    manifest = generate(out, oracle=root / "oracle.csv")
    truths = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "truth").glob("*.json"))}
    return Generated(out, root / "oracle.csv", manifest, truths)
```

`synthetic/tests/innovation/test_scenario_documents.py`

```python
"""The scenarios as the documents show them: what an analyst would read on the pages."""

from __future__ import annotations

import openpyxl

from synthetic.books.innovation.roster import CURRENT_PERIOD


def test_dataflake_documents_show_the_inflated_certificate_the_pledged_account_and_clause_1_1(generated):
    certificate = "\n".join(generated.text("dataflake.mcc-2026-10-31"))
    assert "$6,100,000" in certificate and "pledged collateral account" in certificate and "Yes" in certificate
    clause = generated.truths["dataflake"]["scenario"]["details"]["definition_clause"]
    assert clause["section"] == "1.1" and "excluding any cash that is pledged" in clause["quote"]
    page = generated.text("dataflake.credit-agreement")[clause["page"] - 1]
    assert " ".join(clause["quote"].split()) in " ".join(page.split())
    statement = "\n".join(generated.text("dataflake.bank-2026-10-31"))
    assert "$4,600,000" in statement and "$1,500,000" in statement and "RESTRICTED" in statement


def test_dataflakes_term_sheet_names_the_amount_and_the_closing_date(generated):
    sheet = "\n".join(generated.text("dataflake.term-sheet-2026-11-10"))
    assert "$8,000,000" in sheet and "December 12, 2026" in sheet and "TERM SHEET" in sheet


def test_lumoras_october_package_is_absent_and_september_is_there(generated):
    ids = {d["id"] for d in generated.manifest["documents"] if d["borrower_id"] == "lumora-health"}
    assert not [i for i in ids if i.endswith(CURRENT_PERIOD.isoformat())]
    assert {"lumora-health.bank-2026-09-30", "lumora-health.mf-2026-09-30"} <= ids


def test_tidewells_october_statement_shows_the_new_restricted_account_and_the_certificate_counts_it(generated):
    october = "\n".join(generated.text("tidewell-medical.bank-2026-10-31"))
    september = "\n".join(generated.text("tidewell-medical.bank-2026-09-30"))
    certificate = "\n".join(generated.text("tidewell-medical.mcc-2026-10-31"))
    assert "9002" in october and "RESTRICTED" in october and "$1,000,000" in october and "9002" not in september
    assert "$5,300,000" in certificate and "$4,300,000" in october


def test_ferrogates_certificate_says_runway_is_not_meaningful(generated):
    assert "Not meaningful" in "\n".join(generated.text("ferrogate-cloud.mcc-2026-10-31"))


def test_stripples_october_package_has_a_new_line_a_confusable_software_label_and_a_stray_export(generated):
    october = "\n".join(generated.text("stripple-tech.mf-2026-10-31"))
    september = "\n".join(generated.text("stripple-tech.mf-2026-09-30"))
    assert "Contract liabilities" in october and "Contract liabilities" not in september
    assert "Deferred revenue, current" in september and "Software development costs" in october
    workbook = openpyxl.load_workbook(generated.out / "documents" / "stripple-tech" / "mrr_export.xlsx")
    cells = [str(c.value) for row in workbook.active.iter_rows() for c in row if c.value is not None]
    assert not any("Stripple" in c for c in cells), "the export must name no company"
    assert any(c.startswith("2025-") for c in cells) and not any(c.startswith("2026-") for c in cells)
    assert "SYNTHETIC - FOR DEMONSTRATION" in cells
    printed = "\n".join(generated.text("stripple-tech.mrr-export"))
    assert "Stripple" not in printed and "mrr_export.xlsx" in printed
    held = next(d for d in generated.truths["stripple-tech"]["documents"] if d["id"] == "stripple-tech.mrr-export")
    assert held["held"] is True and held["period_end"] is None and held["type"] == "unclassified"
    details = generated.truths["stripple-tech"]["scenario"]["details"]
    assert details["new_line"]["page"] == 1 and details["capitalised_software"]["page"] == 1


def test_funding_events_are_in_the_truth_files_with_evidence_documents(generated):
    events = {cid: t["funding_events"] for cid, t in generated.truths.items() if t.get("funding_events")}
    assert sorted(events) == ["dataflake", "halcyon-grid", "kelvra-bio", "nimbusfield-security"]
    for cid, rows in events.items():
        ids = {d["id"] for d in generated.truths[cid]["documents"]}
        assert all(e["evidence_document_ids"] and set(e["evidence_document_ids"]) <= ids for e in rows), cid
    assert events["halcyon-grid"][0]["expected_close"] == "2027-03-31"
    assert events["kelvra-bio"][0]["expected_close"] == "2027-02-26"
```

`synthetic/tests/innovation/test_documents.py`

```python
"""The documents: every one is marked synthetic, names its client, and prints exactly what the truth says."""

from __future__ import annotations

import re
from decimal import Decimal as D

from synthetic.books.innovation.layout import OUTFLOWS
from synthetic.books.innovation.roster import LENDER
from synthetic.render import common

REAL_BANKS = ("JPMorgan", "Chase", "Wells Fargo", "Citibank", "Citigroup", "Silicon Valley Bank", "SVB", "Bank of America",
              "HSBC", "Goldman", "Morgan Stanley", "First Republic", "Signature Bank", "Comerica", "Capital One")
WORDS = {8: "Eight", 9: "Nine", 10: "Ten"}
MONTHLY = ("monthly_financials", "mrr_report", "bank_statement", "compliance_certificate")


def real_banks_in(text: str) -> list[str]:
    """Proper names only, as whole words: "Purchases of property" must not match "Chase"."""
    return [bank for bank in REAL_BANKS if re.search(rf"\b{re.escape(bank)}\b", text)]


def innovation_docs(generated):
    kept = {"kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain"}
    return [d for d in generated.manifest["documents"] if d["borrower_id"] not in kept and d["path"].endswith(".pdf")]


def test_book_size_and_the_lender(generated):
    assert generated.manifest["counts"]["borrowers"] == 20
    assert len(generated.truths) == 20
    assert {t["borrower"]["lender"] for t in generated.truths.values()} == {LENDER}
    assert sum(1 for t in generated.truths.values() if t["borrower"].get("template_id") == "vc-1") == 16


def test_every_page_of_every_document_carries_the_marker_and_no_real_bank_appears(generated):
    for doc in innovation_docs(generated):
        pages = common.page_texts(generated.out / doc["path"])
        assert all(common.MARKER in page for page in pages), doc["id"]
        joined = "\n".join(pages)
        assert not real_banks_in(joined), doc["id"]
    assert any(d["path"].endswith(".xlsx") for d in generated.manifest["documents"])


def test_every_document_but_the_stray_export_names_its_client_in_the_first_pages(generated):
    names = {t["borrower"]["id"]: t["borrower"]["name"] for t in generated.truths.values()}
    for doc in innovation_docs(generated):
        if doc["id"] == "stripple-tech.mrr-export":
            continue
        head = "\n".join(common.page_texts(generated.out / doc["path"])[:2])
        assert names[doc["borrower_id"]] in head, doc["id"]


def printed(key: str, value: int) -> str:
    return common.accounting(D(-value if key in OUTFLOWS else value))


def test_monthly_financials_print_exactly_the_truth(generated):
    checked = 0
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "monthly_financials"):
            values = periods[doc["period_end"]]["values"]
            pages = generated.text(doc["id"])
            for key, figure in doc["figures"].items():
                assert figure["printed"] == printed(key, values[key]), (doc["id"], key)
                assert figure["printed"] in pages[figure["page"] - 1], (doc["id"], key)
                checked += 1
            head = "\n".join(pages)
            assert "month ended" in head.lower() and f"{WORDS[doc['months']]} months ended" in head, doc["id"]
    assert checked > 16 * 3 * 40


def test_bank_statements_tie_to_the_balance_sheet(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "bank_statement"):
            values = periods[doc["period_end"]]["values"]
            assert doc["figures"]["bs.cash_unrestricted"]["printed"] == f"${values['bs.cash_unrestricted']:,}", doc["id"]
            assert doc["figures"]["bs.cash_restricted"]["printed"] == f"${values['bs.cash_restricted']:,}", doc["id"]


def test_mrr_reports_print_the_saas_lines(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "mrr_report"):
            values = periods[doc["period_end"]]["values"]
            assert doc["figures"]["saas.mrr"]["printed"] == f"${values['saas.mrr']:,}", doc["id"]
            assert doc["figures"]["saas.customers"]["printed"] == f"{values['saas.customers']:,}", doc["id"]


def test_certificates_print_what_the_truth_reports(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        by_end = {c["period_end"]: c for c in truth["certificates"]}
        for doc in (d for d in truth["documents"] if d["type"] == "compliance_certificate"):
            text = "\n".join(generated.text(doc["id"]))
            reported = by_end[doc["period_end"]]["reported"]
            assert text.count("Yes") >= sum(1 for r in reported.values() if r["in_compliance"]), doc["id"]
            for entry in reported.values():
                if entry["unit"] == "usd":
                    assert f"${int(D(entry['value'])):,}" in text, doc["id"]


def test_each_client_has_the_documents_the_agreement_requires(generated):
    for cid, truth in generated.truths.items():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        by_type = {}
        for d in truth["documents"]:
            by_type.setdefault(d["type"], []).append(d)
        assert len(by_type["credit_agreement"]) == 1 and len(by_type["annual_financial_statements"]) == 1
        counts = {t: len(by_type.get(t, [])) for t in MONTHLY}
        assert counts == dict.fromkeys(MONTHLY, 2 if cid == "lumora-health" else 3), cid  # three months on file
        for d in by_type["monthly_financials"]:
            assert d["received_date"] <= truth["as_of"]
```

`synthetic/tests/innovation/test_kept_and_oracle.py`

```python
"""The kept four are the v1 book, and the answer key is the owner's to sign."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from synthetic.books.innovation.roster import KEPT_IDS

LEGACY = Path(__file__).resolve().parents[2] / "out"
LEGACY_ORACLE = Path(__file__).resolve().parents[2] / "oracle.csv"


def test_the_four_kept_borrowers_are_byte_identical_to_the_v1_truth(generated):
    for borrower_id in KEPT_IDS:
        mine = (generated.out / "truth" / f"{borrower_id}.json").read_bytes()
        assert mine == (LEGACY / "truth" / f"{borrower_id}.json").read_bytes(), borrower_id


def test_their_documents_are_the_v1_documents(generated):
    legacy = {d["id"]: d["text_sha256"] for d in json.loads((LEGACY / "manifest.json").read_text())["documents"]
              if d["borrower_id"] in KEPT_IDS}
    mine = {d["id"]: d["text_sha256"] for d in generated.manifest["documents"] if d["borrower_id"] in KEPT_IDS}
    assert mine == legacy and len(mine) == 73


def test_kept_rows_stay_signed_and_new_rows_come_unsigned(generated):
    rows = list(csv.DictReader(generated.oracle.open(newline="")))
    kept = [r for r in rows if r["borrower_id"] in KEPT_IDS]
    new = [r for r in rows if r["borrower_id"] not in KEPT_IDS]
    legacy = [r for r in csv.DictReader(LEGACY_ORACLE.open(newline="")) if r["borrower_id"] in KEPT_IDS]
    def key(row):
        return (row["borrower_id"], row["kind"], row["item"])

    assert sorted(kept, key=key) == sorted(legacy, key=key) and all(r["owner_signed_off"] == "yes" for r in kept)
    assert len({r["borrower_id"] for r in new}) == 16 and all(r["owner_signed_off"] == "no" for r in new)
    assert {r["kind"] for r in new} == {"covenant_test", "funding_event", "exception"}


def test_regenerating_keeps_an_owner_signature_only_while_the_row_is_unchanged(tmp_path):
    from synthetic.books.innovation.generate import generate

    out, oracle = tmp_path / "out", tmp_path / "oracle.csv"
    generate(out, oracle=oracle)
    rows = list(csv.DictReader(oracle.open(newline="")))
    target = next(r for r in rows if r["borrower_id"] == "dataflake" and r["item"] == "min_unrestricted_cash")
    target["owner_signed_off"] = "yes"
    with oracle.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    generate(out, oracle=oracle)
    again = {(r["borrower_id"], r["kind"], r["item"]): r["owner_signed_off"] for r in csv.DictReader(oracle.open(newline=""))}
    assert again[("dataflake", "covenant_test", "min_unrestricted_cash")] == "yes"
    assert sum(1 for v in again.values() if v == "yes") == 1 + 16  # the signed row and the kept four's
    generate(out, seed=7, oracle=oracle)  # a different seed changes values: the signature does not survive
    changed = {(r["borrower_id"], r["kind"], r["item"]): r["owner_signed_off"] for r in csv.DictReader(oracle.open(newline=""))}
    assert changed[("dataflake", "covenant_test", "min_unrestricted_cash")] == "yes"  # the October figures are fixed
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest synthetic/tests/innovation/test_scenario_documents.py synthetic/tests/innovation/test_documents.py synthetic/tests/innovation/test_kept_and_oracle.py -v`
Expected: errors importing `synthetic.books.innovation.generate`.

- [ ] **Step 3: Implement**

The kept four are built by the frozen v1 code with the v1 seed and written with v1's own `_truth`, so `synthetic/books/innovation/out/truth/<kept>.json` equals `synthetic/out/truth/<kept>.json` byte for byte. Their oracle rows come from v1's `_oracle_rows` and keep their sign-off against `synthetic/oracle.csv`; innovation rows are unsigned unless the new oracle already holds an unchanged signed row.

`synthetic/books/innovation/kept.py`

```python
"""The four C&I borrowers kept from the v1 book: same truth, terms, documents and answer-key rows.

They are built by the frozen v1 modules with the v1 seed, so they stay byte-identical to `synthetic/out`, and the
recordings and signed oracle rows that rest on them stay valid."""

from __future__ import annotations

from synthetic.book import BorrowerBook, build_borrower
from synthetic.books.innovation.roster import KEPT_IDS, LEGACY_SEED
from synthetic.scenarios import ROSTER


def build_kept(seed: int = LEGACY_SEED) -> list[BorrowerBook]:
    by_id = {spec.id: spec for spec in ROSTER}
    return [build_borrower(by_id[borrower_id], seed) for borrower_id in KEPT_IDS]
```

`synthetic/books/innovation/generate.py`

```python
"""Build the innovation book: 16 venture-backed clients and the four kept C&I borrowers.

    uv run python -m synthetic.books.innovation.generate [--out synthetic/books/innovation/out] [--seed 20261120]

The same seed gives byte-identical truth files and identical PDF text. The kept four are produced by the frozen v1
generator with the v1 seed, so their truth files equal those in `synthetic/out`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
from pathlib import Path

from synthetic import generate as legacy
from synthetic.book import DocPlan
from synthetic.books.innovation import documents
from synthetic.books.innovation.book import ClientBook, build_clients, scenario_record
from synthetic.books.innovation.expected import COVENANTS
from synthetic.books.innovation.kept import build_kept
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, DEFAULT_SEED, LEGACY_SEED, LENDER
from synthetic.render import common
from synthetic.render import innovation as render
from synthetic.render.legal import render_legal

HERE = Path(__file__).resolve().parent
LEGACY_ORACLE = HERE.parents[1] / "oracle.csv"
SCHEMA = "synthetic-truth-2"
NAMES = {cid: name for cid, name, _ in COVENANTS}


def _render_client_doc(book: ClientBook, doc: DocPlan, folder: Path) -> dict:
    spec, path, payload = book.spec, folder / doc.filename, doc.payload
    if doc.type == "credit_agreement":
        return render_legal(path, payload["legal"], spec.name)
    if doc.type == "annual_financial_statements":
        return render.render_annual_statements(path, spec, payload, doc.title)
    if doc.type == "monthly_financials":
        return render.render_monthly_financials(path, spec, payload, doc.title)
    if doc.type == "mrr_report":
        return render.render_mrr_report(path, spec, payload, doc.title)
    if doc.type == "bank_statement":
        return render.render_bank_statement(path, spec, payload, doc.title)
    if doc.type == "compliance_certificate":
        return render.render_monthly_certificate(path, spec, documents.certificate_payload(spec, doc, NAMES), doc.title)
    if doc.type in ("term_sheet", "investor_update"):
        return render.render_notice(path, spec, payload["notice"], doc.title)
    if doc.type == "unclassified":  # the stray MRR export: the real workbook, and the print of it the PDF-only intake takes
        xlsx = folder / "mrr_export.xlsx"
        cells = render.write_export_workbook(xlsx, payload["rows"])
        result = render.render_export_print(path, payload["rows"])
        result["extra"]["workbook"] = {"path": f"documents/{spec.id}/mrr_export.xlsx",
                                       "cells_sha256": hashlib.sha256(cells.encode("utf-8")).hexdigest()}  # fmt: skip
        return result
    raise ValueError(doc.type)


def _period_record(p) -> dict:
    return {"period_end": p.period_end, "months": p.months, "fiscal_year": p.fiscal_year, "quality": p.quality,
            "scale": 1, "values": p.values, "memo": p.memo}  # fmt: skip


def _client_truth(book: ClientBook, rendered: dict[str, dict], texts: dict[str, list[str]], seed: int) -> dict:
    spec = book.spec

    def lookup(anchor_ref: tuple[str, str]) -> dict:
        slug, anchor = anchor_ref
        doc_id = f"{spec.id}.{slug}"
        cite = book.terms.agreement.cites[anchor]
        page = rendered[doc_id]["anchor_pages"][anchor]
        if common.squash(cite["quote"]) not in common.squash(texts[doc_id][page - 1]):
            raise AssertionError(f"{doc_id}: quote for {anchor} is not on page {page}")
        return {"document_id": doc_id, "section": cite["section"], "page": page, "quote": cite["quote"]}

    version = legacy._resolve_citations(book.terms.version, lookup)
    version["clause_index"] = legacy._resolve_citations(book.terms.clause_index, lookup)
    scenario = scenario_record(book)
    scenario["details"] = legacy._resolve_citations(scenario["details"], lookup)
    if spec.scenario == "stripple_package":  # pages are known only after rendering
        figures = rendered[f"{spec.id}.mf-{CURRENT_PERIOD.isoformat()}"]["extra"]["figures"]
        scenario["details"]["new_line"]["page"] = figures["bs.deferred_revenue_current"]["page"]
        scenario["details"]["capitalised_software"]["page"] = figures["bs.capitalised_software"]["page"]
    docs = [
        {"id": d.id, "type": d.type, "period_end": d.period_end, "path": f"documents/{spec.id}/{d.filename}",
         "pages": d.pages, "title": d.title, "received_date": d.received_date, "document_date": d.document_date,
         **d.extra}
        for d in book.documents
    ]  # fmt: skip
    truth = {
        "schema": SCHEMA, "seed": seed, "as_of": AS_OF, "current_period": CURRENT_PERIOD,
        "borrower": {
            "id": spec.id, "name": spec.name, "legal_form": spec.legal_form, "industry": spec.sector,
            "stage": spec.stage, "city": spec.city, "state": spec.state, "fiscal_year_end_month": 12,
            "lender": LENDER, "relationship_manager": spec.rm, "analyst": spec.analyst,
            "risk_rating": spec.risk_rating, "statement_scale": 1, "chief_financial_officer": spec.cfo,
            "auditor": spec.auditor, "template_id": "vc-1",
        },
        "facilities": [book.terms.facility], "terms_versions": [version],
        "periods": [_period_record(p) for p in book.published], "comparative_periods": [_period_record(book.comparative)],
        "certificates": book.certificates, "borrowing_base": [], "system_of_record": [], "funding_events": book.funding_events,
        "documents": docs, "scenario": scenario, "expected": book.expected,
    }  # fmt: skip
    return legacy.plain(truth)


def _client_oracle_rows(book: ClientBook) -> list[dict]:
    spec = book.spec
    base = {"borrower_id": spec.id, "borrower_name": spec.name, "period_end": CURRENT_PERIOD.isoformat(),
            "scenario": spec.scenario, "owner_signed_off": "no", "threshold": "", "terms_version": "",
            "expected_value": ""}  # fmt: skip
    rows = []
    for test in book.expected["covenant_tests"]:
        if test["period_end"] != CURRENT_PERIOD:
            continue
        outcome = test["outcome"] + ("+not_meaningful" if test.get("note") else "")
        rows.append({**base, "kind": "covenant_test", "item": test["covenant_id"],
                     "expected_value": "" if test["value"] is None else format(test["value"], "f"),
                     "threshold": f"{test['operator']} {format(test['threshold'], 'f')}", "expected_outcome": outcome,
                     "terms_version": test["terms_version_id"]})  # fmt: skip
    for event in book.funding_events:
        past = event["status"] in ("expected", "signed") and event["expected_close"] < AS_OF
        rows.append({**base, "kind": "funding_event", "item": f"{event['kind']}:{event['expected_close'].isoformat()}",
                     "expected_value": str(event["amount"]), "expected_outcome": "slipped" if past else event["status"]})
    for exception in book.expected["exceptions"]:
        rows.append({**base, "kind": "exception", "item": exception["subject"], "expected_outcome": exception["type"]})
    return rows


def _write_truth(out: Path, borrower_id: str, truth: dict) -> None:
    text = json.dumps(truth, indent=1, ensure_ascii=False) + "\n"
    (out / "truth" / f"{borrower_id}.json").write_text(text, encoding="utf-8")


def _render_all(borrower_id: str, plans: list[DocPlan], render_one, folder: Path, manifest: list[dict]):
    rendered: dict[str, dict] = {}
    texts: dict[str, list[str]] = {}
    for doc in plans:
        result = render_one(doc, folder)
        doc.pages = result["pages"]
        doc.extra = {**doc.extra, **result.get("extra", {})}
        rendered[doc.id] = result
        pages = common.page_texts(folder / doc.filename)
        texts[doc.id] = pages
        if len(pages) != doc.pages:
            raise AssertionError(f"{doc.id}: page count mismatch")
        if not any(common.MARKER in text for text in pages):
            raise AssertionError(f"{doc.id}: synthetic marker missing")
        manifest.append({"id": doc.id, "borrower_id": borrower_id, "type": doc.type,
                         "period_end": doc.period_end.isoformat() if doc.period_end else None,
                         "path": f"documents/{borrower_id}/{doc.filename}", "pages": doc.pages,
                         "text_sha256": hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()})  # fmt: skip
        if "workbook" in result.get("extra", {}):
            manifest.append({"id": f"{doc.id}-xlsx", "borrower_id": borrower_id, "type": "unclassified", "period_end": None,
                             "path": result["extra"]["workbook"]["path"], "pages": 0,
                             "text_sha256": result["extra"]["workbook"]["cells_sha256"]})  # fmt: skip
    return rendered, texts


def generate(out: Path, seed: int = DEFAULT_SEED, oracle: Path | None = None, legacy_oracle: Path = LEGACY_ORACLE) -> dict:
    """Generate the whole book under `out`. Returns the manifest."""
    out = Path(out)
    oracle = Path(oracle) if oracle else out.parent / "oracle.csv"
    for stale in (out / "documents", out / "truth"):
        if stale.exists():
            shutil.rmtree(stale)
    (out / "truth").mkdir(parents=True, exist_ok=True)
    manifest_docs: list[dict] = []
    innovation_rows: list[dict] = []
    kept_rows: list[dict] = []
    clients = build_clients(seed)
    for book in clients:
        folder = out / "documents" / book.spec.id
        rendered, texts = _render_all(book.spec.id, book.documents, lambda d, f, b=book: _render_client_doc(b, d, f),
                                      folder, manifest_docs)  # fmt: skip
        _write_truth(out, book.spec.id, _client_truth(book, rendered, texts, seed))
        innovation_rows += _client_oracle_rows(book)
    kept = build_kept(LEGACY_SEED)
    for book in kept:
        folder = out / "documents" / book.spec.id
        rendered, texts = _render_all(book.spec.id, book.documents, lambda d, f, b=book: legacy._render(b, d, f), folder,
                                      manifest_docs)  # fmt: skip
        _write_truth(out, book.spec.id, legacy._truth(book, rendered, texts, LEGACY_SEED))
        kept_rows += legacy._oracle_rows(book)
    names = [(b.spec.id, b.spec.name, b.spec.scenario) for b in clients] + [(b.spec.id, b.spec.name, b.spec.scenario) for b in kept]
    manifest = {
        "schema": "synthetic-manifest-2", "seed": seed, "legacy_seed": LEGACY_SEED, "as_of": AS_OF.isoformat(),
        "lender": LENDER,
        "counts": {"borrowers": len(names), "documents": len(manifest_docs), "pages": sum(d["pages"] for d in manifest_docs)},
        "borrowers": [{"id": i, "name": n, "scenario": s} for i, n, s in names], "documents": manifest_docs,
    }  # fmt: skip
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    rows = innovation_rows + kept_rows
    legacy._keep_sign_off(legacy_oracle, kept_rows)  # the kept four keep the owner's sign-off
    legacy._keep_sign_off(oracle, innovation_rows)  # a regenerated innovation row stays signed only if unchanged
    with oracle.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=legacy.ORACLE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the innovation-banking book.")
    parser.add_argument("--out", default=str(HERE / "out"), help="output directory")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--oracle", default=None, help="oracle CSV path (default: beside the output directory)")
    args = parser.parse_args()
    started = time.monotonic()
    manifest = generate(Path(args.out), args.seed, args.oracle)
    counts = manifest["counts"]
    print(f"{counts['borrowers']} borrowers, {counts['documents']} documents, {counts['pages']} pages written to "
          f"{args.out} in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
```

Add to `.gitignore` after the `synthetic/out/documents/` line:

```
synthetic/books/innovation/out/documents/
```

Add to `synthetic/README.md`, directly under the opening paragraph (before "## Regenerate"):

```markdown
## Two books

| Book | Where | What | Regenerate |
|---|---|---|---|
| Innovation (v2 default) | `synthetic/books/innovation/` | 20 borrowers: 16 venture-backed clients (monthly, template `vc-1`, current period 31 October 2026) and the 4 kept C&I borrowers | `uv run python -m synthetic.books.innovation.generate` |
| Legacy C&I (v1, frozen) | `synthetic/` (this folder) | 21 quarterly borrowers; existing engine tests run on it | `uv run python -m synthetic.generate` |

The legacy generator is frozen: `synthetic/tests/test_legacy_frozen.py` pins every source file and the four kept truth files by digest. The kept four (`kestrel-bay-packaging`, `harrowgate-precision`, `briarstone-beverage`, `pellham-grain`) are built by the legacy code with the legacy seed, so their truth, documents and signed answer-key rows are identical in both books. The innovation answer key is `synthetic/books/innovation/oracle.csv`: its rows for the 16 innovation clients are unsigned until the owner signs them.

Innovation conventions the spec left open: tests run from August 2025 (a trailing three months needs published months before it); due days are financials and certificate 30, MRR report 15, bank statements 7; the approved revenue plan covers May 2025 to October 2026; DSCR only for Ferrogate from May 2026 (terms version); `mrr_export.xlsx` is delivered with a PDF print (`mrr_export.pdf`) because intake takes PDFs only; the exception `cash.statement_mismatch` is raised by a reconciliation the engine does not do yet.
```

- [ ] **Step 4: Generate the book, run all synthetic tests and lint**

Run:

```bash
uv run python -m synthetic.books.innovation.generate
git status --short synthetic/out synthetic/oracle.csv
uv run pytest synthetic/tests -v
uv run ruff check .
```

Expected: `20 borrowers, 301 documents, 854 pages written to synthetic/books/innovation/out in ~4s`; `git status` shows nothing under `synthetic/out` or `synthetic/oracle.csv` (the v1 book is untouched); the whole synthetic suite passes (about 127 tests, including every legacy test); ruff clean. Open `synthetic/books/innovation/oracle.csv`: 16 rows `yes` (the kept four), 62 rows `no`.

- [ ] **Step 5: Commit**

```bash
git add synthetic/books .gitignore synthetic/README.md synthetic/tests
git commit -m "feat(p2): innovation book generator, kept borrowers and unsigned answer key"
```

---

### Task 7: Monthly document types, and the revenue plan from approved terms

Phase 1 left the revenue-below-plan signal calling with no plan (`compute_signal_inputs(..., plan=None)`), and `ingest_pdf` refuses the monthly document types that intake and the seed use. Both are wired here.

**Files:**
- Modify: `backend/app/domain/documents.py` (document types), `backend/app/domain/signals_service.py` (`approved_plan`, plan passed to the venture inputs)
- Create: `backend/tests/domain/test_document_types.py`, `backend/tests/domain/test_approved_plan.py`

**Interfaces:**
- Consumes: `covenant_service.governing_terms(db, facility, period_end) -> (row | None, parsed version | error)` and `fact_provider`; `calc.signals.compute_signal_inputs(..., plan=...)` (Phase 1); `calc.terms.RevenueVsPlanParams`.
- Produces: `DOCUMENT_TYPES` gains `monthly_financials`, `mrr_report`, `bank_statement`, `term_sheet`, `investor_update`; `signals_service.approved_plan(db, borrower, period_end) -> dict[date, Decimal] | None` — the monthly revenue plan of the approved terms in force (a covenant of archetype `revenue_vs_plan` with metric `revenue`), `None` when there is none. A proposed version never counts.

- [ ] **Step 1: Write the failing tests**

`backend/tests/domain/test_document_types.py`

```python
"""A venture client's monthly documents can be filed (the book's seed and intake both need these types)."""
import pymupdf
from app.domain.credit import Borrower
from app.domain.documents import DOCUMENT_TYPES
from app.domain.documents_service import ingest_pdf

NEW = ("monthly_financials", "mrr_report", "bank_statement", "term_sheet", "investor_update")


def tiny_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Management financial statements for the month ended October 31, 2026")
    return doc.tobytes()


def test_the_monthly_types_are_document_types():
    assert set(NEW) <= set(DOCUMENT_TYPES) and "compliance_certificate" in DOCUMENT_TYPES


def test_a_monthly_document_can_be_filed_by_type(db):
    b = Borrower(code="DOC1", name="Mosswell Robotics", template_id="vc-1")
    db.add(b)
    db.flush()
    for doc_type in NEW:
        doc = ingest_pdf(db, borrower_id=b.id, data=tiny_pdf(), file_name=f"{doc_type}.pdf", doc_type=doc_type,
                         doc_type_source="system", source="seed", actor=("system", "seed"))
        assert doc.doc_type == doc_type
```

`backend/tests/domain/test_approved_plan.py`

```python
"""The revenue plan behind `revenue_below_plan` comes from approved terms, and only from approved terms."""
from datetime import UTC, date, datetime

from app.domain.credit import Borrower, Facility
from app.domain.org import User
from app.domain.signals_service import approved_plan
from app.domain.terms import TermsVersion

OCT = date(2026, 10, 31)


def covenant(amounts: dict[str, str], metric: str = "revenue") -> dict:
    return {"id": "revenue_vs_plan", "name": "Revenue to Plan", "archetype": "revenue_vs_plan",
            "params": {"metric": metric, "plan": [{"period_end": k, "amount": v} for k, v in amounts.items()]},
            "test": {"operator": ">=", "threshold": "0.80", "steps": [], "unit": "pct"},
            "measurement": {"basis": "t3m", "frequency": "monthly"}, "rounding": {"dp": 4, "mode": "half_up"},
            "citations": []}


def setup(db, code, versions):
    """versions: [(status, covenant dict)] in version order, all effective from 2025-01-01."""
    b = Borrower(code=code, name="Corvane Analytics", template_id="vc-1")
    db.add(b)
    user = User(email=f"{code}@x.example", name="A", role="credit_officer", password_hash="x")
    db.add(user)
    db.flush()
    facility = Facility(borrower_id=b.id, code=f"{code}-VL", name="Venture Term Loan", facility_type="term_loan",
                        commitment=3_000_000)
    db.add(facility)
    db.flush()
    for number, (status, cov) in enumerate(versions, start=1):
        approved = status == "approved"
        db.add(TermsVersion(
            facility_id=facility.id, version=number, status=status, effective_from=date(2025, 1, 1),
            approved_by=user.id if approved else None, approved_at=datetime.now(UTC) if approved else None,
            terms={"definitions": {}, "covenants": [cov], "reporting_requirements": [], "borrowing_base": None}))
    db.flush()
    return b


def test_the_plan_is_read_from_the_approved_terms_as_decimals(db):
    b = setup(db, "PLAN1", [("approved", covenant({"2026-09-30": "800000", "2026-10-31": "850000"}))])
    plan = approved_plan(db, b, OCT)
    assert plan == {date(2026, 9, 30): 800000, date(2026, 10, 31): 850000}
    assert all(type(v).__name__ == "Decimal" for v in plan.values())


def test_a_proposed_version_never_supplies_a_plan(db):
    b = setup(db, "PLAN2", [("proposed", covenant({"2026-10-31": "850000"}))])
    assert approved_plan(db, b, OCT) is None


def test_an_arr_covenant_and_a_borrower_with_no_plan_give_no_revenue_plan(db):
    arr = setup(db, "PLAN3", [("approved", covenant({"2026-10-31": "9000000"}, metric="arr"))])
    assert approved_plan(db, arr, OCT) is None
    bare = Borrower(code="PLAN4", name="Ferrogate Cloud", template_id="vc-1")
    db.add(bare)
    db.flush()
    assert approved_plan(db, bare, OCT) is None
```

- [ ] **Step 2: Run to verify they fail**

Start Postgres first (`service postgresql start`), then run: `uv run pytest backend/tests/domain/test_document_types.py backend/tests/domain/test_approved_plan.py -v`
Expected: `test_the_monthly_types_are_document_types` fails (types missing), `test_a_monthly_document_can_be_filed_by_type` fails with `DocumentRefused: Unknown document type`, and `test_approved_plan.py` fails with `ImportError: cannot import name 'approved_plan'`.

- [ ] **Step 3: Implement**

In `backend/app/domain/documents.py`, replace

```python
DOCUMENT_TYPES = (
    "credit_agreement", "amendment", "waiver", "annual_statements", "interim_statements",
    "compliance_certificate", "borrowing_base_certificate", "receivables_aging", "tax_return", "other",
)
```

with

```python
DOCUMENT_TYPES = (
    "credit_agreement", "amendment", "waiver", "annual_statements", "interim_statements",
    "compliance_certificate", "borrowing_base_certificate", "receivables_aging", "tax_return",
    "monthly_financials", "mrr_report", "bank_statement", "term_sheet", "investor_update", "other",
)
```

In `backend/app/domain/signals_service.py` (re-read it first: it is being edited elsewhere), make three edits.

1. Replace `from app.domain.covenant_service import fact_provider` with:

```python
from app.domain.covenant_service import fact_provider, governing_terms
```

2. Insert this function immediately before `def _series(`:

```python
def approved_plan(db: Session, borrower: Borrower, period_end: date) -> dict[date, Decimal] | None:
    """The monthly revenue plan from the approved terms in force at `period_end` (design spec 5). Plan figures are
    terms data a person entered and a second person approved, never a budget column read from a borrower document. A
    proposed version never governs; a covenant on ARR is not a revenue plan. None when the terms hold no revenue plan."""
    plan: dict[date, Decimal] = {}
    for facility in db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars():
        row, version = governing_terms(db, facility, period_end)
        if row is None:
            continue
        for covenant in version.terms.covenants:
            if covenant.archetype == "revenue_vs_plan" and covenant.typed_params.metric == "revenue":
                plan.update({month.period_end: month.amount for month in covenant.typed_params.plan})
    return plan or None


```

3. In `_series`, replace

```python
    venture_inputs = sig.compute_signal_inputs(
        period_end, provider, fye_month=fye, template_id="vc-1", history_months=HISTORY_MONTHS - 1) if venture else None
```

with

```python
    plan = approved_plan(db, borrower, period_end) if venture else None
    venture_inputs = sig.compute_signal_inputs(
        period_end, provider, fye_month=fye, template_id="vc-1", history_months=HISTORY_MONTHS - 1,
        plan=plan) if venture else None
```

- [ ] **Step 4: Run tests and the neighbouring suites**

Run: `uv run pytest backend/tests/domain backend/tests/test_monthly_cycles.py backend/tests/test_funding.py -v && uv run ruff check .`
Expected: PASS (the monthly-cycle signal-history tests still pass: a borrower with no plan gets `plan=None`, as before).

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/documents.py backend/app/domain/signals_service.py backend/tests/domain/test_document_types.py backend/tests/domain/test_approved_plan.py
git commit -m "feat(p2): monthly document types; revenue plan for signals from approved terms"
```

---

### Task 8: Seed either book (innovation by default)

**Files:**
- Modify: `backend/app/seed_book.py`
- Create: `backend/tests/test_seed_innovation.py`

**Interfaces:**
- Consumes: the generated innovation book (Task 6); `FundingEvent`, `check_funding_events` (Phase 1); `approved_plan` wiring (Task 7); `Borrower.template_id` (Phase 1 — `seed_book.py` already reads `info.get("template_id", "ci-1")` in the working tree; confirm with `grep -n template_id backend/app/seed_book.py` and add it if a rebase dropped it).
- Produces: `seed_book.BOOKS` (`{"innovation": synthetic/books/innovation/out, "legacy": synthetic/out}`), `SYNTHETIC_ROOT` (= innovation), CLI `python -m app.seed_book [--book innovation|legacy] [--current seeded|live|none] [--only ...]`; `SeedReport.funding_events`, `.slipped_funding`, `.skipped_documents`; truth `funding_events` become `FundingEvent` rows with a `funding_event.recorded` ledger event each, evidence documents mapped to the seeded document ids; after all borrowers, `check_funding_events` runs at the latest `as_of` in the book (so Nimbusfield's passed date marks it `slipped` and raises one `funding_slipped` item); a truth document with `"held": true` is ingested unclassified in every mode; a non-PDF document is skipped and counted; stand-in items exist for `intake.unclassified` and `spread.value_unverified` (non-blocking, as v1's are for spreading problems).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_seed_innovation.py`

```python
"""The innovation book, seeded through the real services, against the generator's own expected values.

The generator computes those with separate arithmetic, so agreement here means two independent implementations reach
the same covenant tests, signals, exceptions and funding events. A disagreement is a finding to investigate, never a
value to patch. The legacy 21-borrower book keeps its own test (`test_seed_book.py`)."""
import json
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.core import ledger
from app.core.config import get_settings
from app.domain import hooks  # noqa: F401
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.funding import FundingEvent
from app.domain.monitoring import CovenantTest, Cycle, Signal, WorkItem
from app.domain.terms import TermsVersion
from app.seed_book import BOOKS, SYNTHETIC_ROOT, _day, halted, seed_book
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.slow
KEPT = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")
# raised by a reconciliation that the calculation layer does not do (Phase 3), so seeding cannot raise it
PENDING = {"cash.statement_mismatch"}


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("innovation") / "out"
    subprocess.run([sys.executable, "-m", "synthetic.books.innovation.generate", "--out", str(out), "--oracle",
                    str(out.parent / "oracle.csv")], cwd=REPO, check=True, capture_output=True)
    return out


@pytest.fixture(scope="module")
def seeded(engine, book, tmp_path_factory):
    import os

    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    report = seed_book(db, root=book, current="seeded")
    truths = {json.loads(p.read_text())["borrower"]["id"]: json.loads(p.read_text())
              for p in sorted((book / "truth").glob("*.json"))}
    yield db, truths, report
    db.close()
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


def borrower(db, code) -> Borrower:
    return db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()


def test_the_default_book_is_innovation_and_the_legacy_book_is_still_selectable():
    assert SYNTHETIC_ROOT == BOOKS["innovation"] and BOOKS["legacy"].name == "out"
    assert BOOKS["innovation"].parts[-3:] == ("books", "innovation", "out")


def test_twenty_borrowers_load_with_their_templates_and_clean_terms(seeded):
    db, truths, report = seeded
    assert report.borrowers == len(truths) == 20 and report.provenance_warnings == {}
    assert all(v.warnings == [] for v in db.execute(select(TermsVersion)).scalars())
    templates = {c: borrower(db, c).template_id for c in truths}
    assert sorted(set(templates.values())) == ["ci-1", "vc-1"]
    assert sorted(c for c, t in templates.items() if t == "ci-1") == sorted(KEPT)


def test_covenant_tests_match_the_generator_exactly(seeded):
    db, truths, _ = seeded
    problems, checked = [], 0
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        ours = {(t.period_end, t.covenant_id): t for t in db.execute(select(CovenantTest).where(
            CovenantTest.borrower_id == b.id, CovenantTest.superseded.is_(False))).scalars()}
        expected_keys = set()
        for e in truth["expected"]["covenant_tests"]:
            key = (_day(e["period_end"]), e["covenant_id"])
            if halted(truth) and key[0] == current:
                assert e["outcome"] == "cannot_test" and key not in ours  # the live cycle stops before testing
                continue
            expected_keys.add(key)
            checked += 1
            t = ours.get(key)
            if t is None:
                problems.append(f"missing {code} {key}")
                continue
            value = None if e.get("value") is None else D(e["value"])
            if (t.value, t.passed, t.outcome) != (value, e.get("pass"), e["outcome"]) or t.threshold != D(e["threshold"]):
                problems.append(f"{code} {key}: ours {t.value} {t.threshold} {t.passed} {t.outcome}; "
                                f"book {e.get('value')} {e['threshold']} {e.get('pass')} {e['outcome']}")
        problems.extend(f"unexpected {code} {k}" for k in sorted(set(ours) - expected_keys))
    assert problems == [] and checked > 720


def test_current_period_signals_match_the_generator(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        rows = list(db.execute(select(Signal).where(Signal.borrower_id == b.id, Signal.period_end == current)).scalars())
        ours = sorted((s.rule_id, s.severity, s.basis.get("covenant_id") or "") for s in rows)
        book_signals = sorted((s["rule"], s["severity"], (s.get("detail") or {}).get("covenant_id") or "")
                              for s in truth["expected"]["signals"] if _day(s["period_end"]) == current)
        if ours != book_signals:
            problems.append(f"{code}: ours {ours}; book {book_signals}")
    assert problems == []


def test_the_plan_for_revenue_below_plan_comes_from_the_approved_terms(seeded):
    db, _, _ = seeded
    corvane = borrower(db, "corvane-analytics")
    fired = db.execute(select(Signal).where(Signal.borrower_id == corvane.id, Signal.rule_id == "revenue_below_plan",
                                            Signal.period_end == _day("2026-10-31"))).scalars().all()
    assert len(fired) == 1 and fired[0].severity == "medium"
    clean = borrower(db, "mosswell-robotics")
    assert not db.execute(select(Signal).where(Signal.borrower_id == clean.id, Signal.rule_id == "revenue_below_plan",
                                               Signal.period_end == _day("2026-10-31"))).first()


def test_each_scenario_raises_exactly_its_exceptions_and_clean_clients_raise_none(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        ours = sorted({w.item_type for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == b.id)).scalars()})
        expected = sorted({x["type"] for x in truth["expected"]["exceptions"]} - PENDING)
        if ours != expected:
            problems.append(f"{code} ({truth['scenario']['code']}): ours {ours}; book {expected}")
    assert problems == []
    assert sorted(c for c, t in truths.items() if t["scenario"]["code"] == "clean") == [
        "harrowgate-precision", "mosswell-robotics", "orbitline-systems", "pellucid-sensors", "quillon-ai",
        "tessaract-labs", "veridia-payments"]  # harrowgate is the kept clean C&I borrower


def test_funding_events_are_seeded_and_only_nimbusfields_has_slipped(seeded):
    db, truths, report = seeded
    rows = {}
    for event in db.execute(select(FundingEvent)).scalars():
        rows.setdefault(db.get(Borrower, event.borrower_id).code, []).append(event)
    assert sorted(rows) == ["dataflake", "halcyon-grid", "kelvra-bio", "nimbusfield-security"] and report.funding_events == 4
    assert {c: [e.status for e in es] for c, es in rows.items()} == {
        "dataflake": ["signed"], "halcyon-grid": ["expected"], "kelvra-bio": ["expected"],
        "nimbusfield-security": ["slipped"]}
    assert rows["dataflake"][0].amount == D("8000000") and rows["dataflake"][0].expected_close == _day("2026-12-12")
    assert all(e.evidence_document_ids for es in rows.values() for e in es)
    nimbus = borrower(db, "nimbusfield-security")
    assert len(db.execute(select(WorkItem).where(WorkItem.borrower_id == nimbus.id,
                                                 WorkItem.item_type == "funding_slipped")).scalars().all()) == 1


def test_the_stray_mrr_export_is_held_unclassified_and_the_workbook_is_not_filed(seeded):
    db, _, report = seeded
    stripple = borrower(db, "stripple-tech")
    docs = list(db.execute(select(Document).where(Document.borrower_id == stripple.id)).scalars())
    held = [d for d in docs if d.meta.get("external_id") == "stripple-tech.mrr-export"]
    assert len(held) == 1 and held[0].doc_type is None and held[0].period_end is None
    assert not [d for d in docs if d.file_name.endswith(".xlsx")] and report.skipped_documents == 1


def test_venture_clients_run_monthly_cycles_and_the_kept_four_stay_quarterly(seeded):
    db, truths, _ = seeded
    for code in truths:
        types = {c.cycle_type for c in db.execute(select(Cycle).where(Cycle.borrower_id == borrower(db, code).id)).scalars()}
        assert types == ({"quarterly"} if code in KEPT else {"monthly"}), code
    dataflake = borrower(db, "dataflake")
    ends = sorted(c.period_end for c in db.execute(select(Cycle).where(Cycle.borrower_id == dataflake.id)).scalars())
    assert (ends[0], ends[-1], len(ends)) == (_day("2025-08-31"), _day("2026-10-31"), 15)


def test_the_ledger_chain_verifies_after_seeding_the_whole_book(seeded):
    db, _, _ = seeded
    ok, count, problem = ledger.verify_chain(db)
    assert ok and problem is None and count > 5000
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest backend/tests/test_seed_innovation.py -v`
Expected: `ImportError: cannot import name 'BOOKS' from 'app.seed_book'`.

- [ ] **Step 3: Implement**

Re-read `backend/app/seed_book.py`, then make these edits by exact text (the file is being edited elsewhere; if an anchor has moved, apply the same change by hand). Legacy callers pass `root=` explicitly, so `test_seed_book.py` is unaffected.

1. Imports — after `from app.domain.facts_service import add_fact` add:

```python
from app.domain.funding import FundingEvent, check_funding_events
```

2. Replace `SYNTHETIC_ROOT = Path(__file__).resolve().parents[2] / "synthetic" / "out"` with:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
# two books: v2's default is innovation banking; legacy is the frozen 21-borrower C&I book the engine tests run on
BOOKS = {"innovation": REPO_ROOT / "synthetic" / "books" / "innovation" / "out",
         "legacy": REPO_ROOT / "synthetic" / "out"}
SYNTHETIC_ROOT = BOOKS["innovation"]
```

3. In `SEEDED_ITEMS`, replace the last entry and the closing brace

```python
    "spread.restatement": ("The comparative column differs from what was confirmed last year. Has the borrower restated, and should the prior spread be updated?",
                           ["restated_update_prior", "keep_prior", "ask_borrower"], False),
}
```

with the same entry, the two stand-ins, the brace and the lookup that says where a stand-in sits:

```python
    "spread.restatement": ("The comparative column differs from what was confirmed last year. Has the borrower restated, and should the prior spread be updated?",
                           ["restated_update_prior", "keep_prior", "ask_borrower"], False),
    "intake.unclassified": ("Which client is this, and which month?",
                            ["classified_by_hand", "not_needed", "request_new_document"], False),
    "spread.value_unverified": ("The statements print a line, 'Contract liabilities', that is not in the template, and a "
                                "capitalised software figure that may be the balance rather than the month's spending. "
                                "Which template line does each belong to?",
                                ["values_confirmed", "values_corrected", "request_new_document"], False),
}
# where a stand-in item sits and who may decide it; anything not listed is a spreading item
SEEDED_WHERE = {"intake.unclassified": ("intake", "upload_document")}
```

4. In `SeedReport`, replace the line `    work_items: int = 0` with:

```python
    work_items: int = 0
    funding_events: int = 0
    slipped_funding: int = 0
    skipped_documents: int = 0
```

5. In the document loop, replace

```python
        path = docs_root / d["path"]
        if not path.exists():
            continue
        filed = not (is_current and current == "live")
```

with

```python
        path = docs_root / d["path"]
        if not path.exists():
            continue
        if path.suffix.lower() != ".pdf":  # the workbook beside a held export: intake takes PDFs only
            report.skipped_documents += 1
            continue
        held = bool(d.get("held"))  # a file that cannot be placed arrives unclassified, in every mode
        filed = not held and not (is_current and current == "live")
```

6. Immediately before the comment `# terms, exactly as the book states them`, add:

```python
    for e in truth.get("funding_events", []):
        event = FundingEvent(
            borrower_id=borrower.id, kind=e["kind"], amount=_d(e["amount"]), expected_close=_day(e["expected_close"]),
            status=e["status"],
            evidence_document_ids=[str(documents[i].id) for i in e.get("evidence_document_ids", []) if i in documents])
        db.add(event)
        db.flush()
        ledger.record(db, actor_type=SEED_ACTOR[0], actor_id=SEED_ACTOR[1], action="funding_event.recorded",
                      entity_type="funding_event", entity_id=event.id,
                      payload={"borrower_id": borrower.id, "kind": event.kind, "amount": event.amount,
                               "expected_close": event.expected_close, "seeded": True})
        report.funding_events += 1
```

7. In the stand-in loop, replace

```python
                    question, decisions, blocks = SEEDED_ITEMS[expected["type"]]
                    raise_item(
                        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="spreading",
                        item_type=expected["type"], severity="high" if blocks else "medium",
                        title=f"{borrower.name}: {expected['summary']}", question=question,
                        allowed_decisions=decisions, required_permission="confirm_spread", blocks_stage=blocks,
```

with

```python
                    question, decisions, blocks = SEEDED_ITEMS[expected["type"]]
                    stage, permission = SEEDED_WHERE.get(expected["type"], ("spreading", "confirm_spread"))
                    raise_item(
                        db, borrower_id=borrower.id, cycle_id=cycle.id, stage=stage,
                        item_type=expected["type"], severity="high" if blocks else "medium",
                        title=f"{borrower.name}: {expected['summary']}", question=question,
                        allowed_decisions=decisions, required_permission=permission, blocks_stage=blocks,
```

8. In `seed_book`, replace the `FileNotFoundError` message, the `as_of` handling and the clock lines:

```python
    if not files:
        raise FileNotFoundError(f"no truth files under {root}/truth; run: python -m synthetic.books.innovation.generate "
                                "(or python -m synthetic.generate for the legacy book)")
    as_ofs: list[date] = []
    for path in files:
        truth = json.loads(path.read_text())
        if only and truth["borrower"]["id"] not in only:
            continue
        if db.execute(select(Borrower.id).where(Borrower.code == truth["borrower"]["id"])).first():
            continue
        as_ofs.append(_day(truth["as_of"]))
        seed_borrower(db, truth, docs_root=root, current=current, password_hash=password_hash, report=report)
    if as_ofs:
        as_of = max(as_ofs)  # books can mix as-of dates: the kept C&I four are as of 17 November
        clock.set_today(db, as_of, actor=SEED_ACTOR)
        report.slipped_funding = len(check_funding_events(db, as_of))
    report.work_items = len(db.execute(select(WorkItem.id)).all())
    return report
```

9. In `main`, add the flag and use it:

```python
    parser.add_argument("--book", choices=tuple(BOOKS), default="innovation", help="which book to load")
```

and change `report = seed_book(db, current=args.current, only=args.only)` to `report = seed_book(db, root=BOOKS[args.book], current=args.current, only=args.only)`. Update the module docstring's Run line to `PYTHONPATH=backend python -m app.seed_book [--book innovation|legacy] [--current seeded|live|none]`.

- [ ] **Step 4: Run the seed tests, then the legacy seed test and lint**

Run: `uv run pytest backend/tests/test_seed_innovation.py backend/tests/test_seed_book.py -v && uv run ruff check .`
Expected: PASS for both (the legacy book still seeds 21 borrowers and 360 documents). Where `test_seed_innovation.py` disagrees with the generator on a covenant test, a signal or an exception, that is a finding: investigate which side is wrong; do not patch either to match, and report it to the owner.

- [ ] **Step 5: Commit**

```bash
git add backend/app/seed_book.py backend/tests/test_seed_innovation.py
git commit -m "feat(p2): seed either book; funding events, held files and stand-in items"
```

---

### Task 9: Cross-check both books against `app.calc`

**Files:**
- Create: `backend/tests/calc/test_synthetic_innovation_truth.py`

**Interfaces:**
- Consumes: the generated innovation truth files (JSON only); `app.calc` (`compute_statement`, `test_covenant`, `determine_outcome`, `compute_signal_inputs`, `evaluate_signals`, `provider_from_facts`, `TermsVersion`) with `template_id="vc-1"`.
- Produces: the independent-arithmetic check for the 16 innovation clients (statements, 720 covenant tests with outcomes, current-period signals) and the identity check for the kept four; `PENDING` pins the exceptions no calculation can raise.

The v1 book (including the kept four) keeps `backend/tests/calc/test_synthetic_truth.py`; together the two files run both books against the engine.

- [ ] **Step 1: Write the test**

`backend/tests/calc/test_synthetic_innovation_truth.py`

```python
"""Cross-check against the innovation book (design spec section 11).

The generator in `synthetic/books/innovation/` computes its `expected` block with its own arithmetic. This module
generates the book into a temporary directory, feeds every venture client's period values and terms through `app.calc`
(template `vc-1`), and requires exact agreement on the statements, every covenant test and its outcome, and the
current period's signals. It reads only the generator's JSON output, never its code. The four kept C&I borrowers
are the v1 book, cross-checked by `test_synthetic_truth.py`; here they are required to be byte-identical to v1.

A disagreement is a finding to investigate, never a number to patch.
"""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.calc import covenants as cov
from app.calc.periods import provider_from_facts
from app.calc.signals import PeriodMetrics, ReportingItem, compute_signal_inputs, evaluate_signals
from app.calc.template import compute_statement, template_lines
from app.calc.terms import TermsVersion

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    not (REPO / "synthetic" / "books" / "innovation" / "generate.py").exists(),
    reason="the innovation generator is not in this checkout")
KEPT = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")
# the engine's own tolerances (covenant_service.DEFAULT_TOLERANCE); a unit it does not list is exact
TOLERANCE = {"ratio": D("0.005"), "usd": D("1"), "pct": D("0.0005"), "days": D("0.5")}
# raised by an agent or a reconciliation, not by calculation: pinned so the suite fails when either side moves
PENDING = {"tidewell-medical": ["cash.statement_mismatch"],
           "stripple-tech": ["intake.unclassified", "spread.value_unverified"]}  # fmt: skip
VC_KEYS = {line.key for line in template_lines("vc-1")}


class Client:
    """One truth file, wired to the engine the way the services wire a borrower."""

    def __init__(self, path: Path) -> None:
        self.data = json.loads(path.read_text())
        self.id = self.data["borrower"]["id"]
        self.version = TermsVersion.model_validate(self.data["terms_versions"][0])
        self.terms = self.version.terms
        self.current = date.fromisoformat(self.data["current_period"])
        self.problems: list[str] = []
        facts = {}
        for period in self.data["periods"] + self.data["comparative_periods"]:
            end, months = date.fromisoformat(period["period_end"]), period["months"]
            stated = {k: D(str(v)) for k, v in period["values"].items()}
            if set(stated) != VC_KEYS:
                self.problems.append(f"{end}: keys differ from the template: {sorted(set(stated) ^ VC_KEYS)}")
            inputs = {k: v for k, v in stated.items() if not next(x for x in template_lines("vc-1") if x.key == k).computed}
            spread = compute_statement(inputs, template_id="vc-1")
            self.problems += [f"{end} {e.code} {e.key}" for e in spread.errors]
            self.problems += [f"{end} {k}: computed {v}, truth {stated.get(k)}" for k, v in spread.computed.items()
                              if stated.get(k) != v]
            for key, value in stated.items():
                facts[(key, end, months)] = value
        self.provider = provider_from_facts(facts)
        plan = next(c for c in self.terms.covenants if c.archetype == "revenue_vs_plan").typed_params.plan
        self.plan = {p.period_end: p.amount for p in plan}
        self.results = {}
        for row in self.data["expected"]["covenant_tests"]:
            end = date.fromisoformat(row["period_end"])
            covenant = self.terms.covenant(row["covenant_id"])
            self.results[(end, row["covenant_id"])] = cov.test_covenant(
                covenant, end, self.provider, self.terms.definitions, fye_month=12, template_id="vc-1")


def text(value) -> str | None:
    return None if value is None else str(value)


def covenant_problems(client: Client) -> list[str]:
    problems = []
    for row in client.data["expected"]["covenant_tests"]:
        end = date.fromisoformat(row["period_end"])
        result = client.results[(end, row["covenant_id"])]
        target = row.get("after_repair", row)
        reported = (row["reported_value"], row["reported_threshold"], row["reported_in_compliance"])
        entry = None
        if any(item is not None for item in reported):
            entry = cov.CertificateEntry(None if reported[0] is None else D(reported[0]),
                                         None if reported[1] is None else D(reported[1]), reported[2])
        outcome = cov.determine_outcome(result, entry, TOLERANCE.get(row["unit"], D("0")))
        mine = {"value": result.value, "pass": result.passed, "headroom": result.headroom_pct, "note": result.note,
                "threshold": result.threshold, "outcome": outcome.outcome}
        theirs = {"value": None if target["value"] is None else D(target["value"]), "pass": target["pass"],
                  "headroom": None if target["headroom"] is None else D(target["headroom"]),
                  "note": row.get("note"), "threshold": D(row["threshold"]), "outcome": target["outcome"]}
        for name in mine:
            if mine[name] != theirs[name]:
                problems.append(f"{client.id} {row['period_end']} {row['covenant_id']} {name}: "
                                f"app.calc {mine[name]!r}, truth {theirs[name]!r}")
    return problems


def signal_problems(client: Client) -> list[str]:
    """The current period's signals, with the engine's own covenant headroom and the approved plan from the terms."""
    if client.data["scenario"]["code"] == "late_package":
        return []  # the October spread is blocked, so financial signals are unmeasured (checked by the seed test)
    plan = {k: D(v) for k, v in client.plan.items()}
    inputs = compute_signal_inputs(client.current, client.provider, fye_month=12, template_id="vc-1",
                                   history_months=13, plan=plan)
    series = []
    for end in sorted({date.fromisoformat(r["period_end"]) for r in client.data["expected"]["covenant_tests"]})[-14:]:
        entry = inputs if end == client.current else inputs.history.get(end)
        headroom = {cid: res.headroom_pct for (e, cid), res in client.results.items()
                    if e == end and res.headroom_pct is not None}
        series.append(PeriodMetrics(end, end.month, dict(entry.values), headroom))
    items = [ReportingItem(i["requirement"], client.current, date.fromisoformat(i["due_date"]),
                           None if i["received_date"] is None else date.fromisoformat(i["received_date"]))
             for i in client.data["scenario"]["details"]["reporting"]]
    evaluation = evaluate_signals(client.current, series, reporting=items,
                                  as_of=date.fromisoformat(client.data["as_of"]), template_id="vc-1")
    mine = sorted((s.rule_id, s.severity, s.basis.get("covenant_id") or "") for s in evaluation.signals)
    theirs = sorted((s["rule"], s["severity"], (s.get("detail") or {}).get("covenant_id") or "")
                    for s in client.data["expected"]["signals"] if s["period_end"] == client.data["current_period"])
    return [] if mine == theirs else [f"{client.id}: app.calc {mine}; truth {theirs}"]


@pytest.fixture(scope="session")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("innovation-book")
    run = subprocess.run([sys.executable, "-m", "synthetic.books.innovation.generate", "--out", str(out / "out"),
                          "--oracle", str(out / "oracle.csv")], cwd=REPO, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, f"generate failed:\n{run.stdout}\n{run.stderr}"
    return out


@pytest.fixture(scope="session")
def clients(book) -> list[Client]:
    files = sorted(p for p in (book / "out" / "truth").glob("*.json") if p.stem not in KEPT)
    assert len(files) == 16
    return [Client(p) for p in files]


def test_statements_reproduce_every_subtotal(clients):
    assert [p for c in clients for p in c.problems] == []


def test_covenant_values_pass_flags_headroom_and_outcomes(clients):
    problems = [p for c in clients for p in covenant_problems(c)]
    assert sum(len(c.data["expected"]["covenant_tests"]) for c in clients) == 16 * 3 * 15
    assert problems == []


def test_current_period_signals_match(clients):
    assert [p for c in clients for p in signal_problems(c)] == []


def test_the_runway_of_a_cash_flow_positive_client_is_not_meaningful(clients):
    ferrogate = next(c for c in clients if c.id == "ferrogate-cloud")
    result = ferrogate.results[(ferrogate.current, "min_runway_months")]
    assert (result.value, result.passed, result.note) == (None, True, cov.NOT_MEANINGFUL_CASH_FLOW_POSITIVE)


def test_a_plan_that_stops_short_of_the_test_month_cannot_be_tested_and_names_the_month(clients):
    """The approved plan runs to October 2026. November cannot be tested against a partial plan."""
    client = clients[0]
    covenant = client.terms.covenant("revenue_vs_plan")
    result = cov.test_covenant(covenant, date(2026, 11, 30), client.provider, client.terms.definitions, fye_month=12,
                               template_id="vc-1")
    assert result.passed is None and result.value is None
    assert any("2026-11-30" in error.message for error in result.errors)


def test_only_agent_raised_exceptions_are_outside_the_calculation_checks(clients):
    pending = {c.id: sorted(x["type"] for x in c.data["expected"]["exceptions"] if x["type"] in
                            {t for kinds in PENDING.values() for t in kinds})
               for c in clients}
    assert {k: v for k, v in pending.items() if v} == PENDING


def test_kept_borrowers_are_the_v1_book_byte_for_byte(book, tmp_path):
    legacy_out = tmp_path / "legacy"
    run = subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(legacy_out), "--oracle",
                          str(tmp_path / "legacy-oracle.csv")], cwd=REPO, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    for borrower in KEPT:
        assert (book / "out" / "truth" / f"{borrower}.json").read_bytes() == \
            (legacy_out / "truth" / f"{borrower}.json").read_bytes(), borrower
    mine = {d["id"]: d["text_sha256"] for d in json.loads((book / "out" / "manifest.json").read_text())["documents"]
            if d["borrower_id"] in KEPT}
    theirs = {d["id"]: d["text_sha256"] for d in json.loads((legacy_out / "manifest.json").read_text())["documents"]
              if d["borrower_id"] in KEPT}
    assert mine == theirs and len(mine) == 73


def test_oracle_keeps_the_kept_rows_signed_and_leaves_the_new_rows_for_the_owner(book):
    import csv

    rows = list(csv.DictReader((book / "oracle.csv").open(newline="")))
    kept = [r for r in rows if r["borrower_id"] in KEPT]
    new = [r for r in rows if r["borrower_id"] not in KEPT]
    assert kept and all(r["owner_signed_off"] == "yes" for r in kept)
    assert new and all(r["owner_signed_off"] == "no" for r in new)
```

- [ ] **Step 2: Run it**

Run: `uv run pytest backend/tests/calc/test_synthetic_innovation_truth.py backend/tests/calc/test_synthetic_truth.py -v`
Expected: PASS (8 new tests and the v1 cross-check). This task has no implementation step: the test is the deliverable, and the generator was built against these same engine calls. A disagreement is a finding: investigate (is the generator's arithmetic wrong, or the engine's?), record it for the owner, never patch one side to match.

- [ ] **Step 3: Lint**

Run: `uv run ruff check backend/tests`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/calc/test_synthetic_innovation_truth.py
git commit -m "test(p2): cross-check the innovation book against app.calc"
```

---

### Task 10: Owner questions, documentation, and the whole-suite check

**Files:**
- Modify: `docs/owner-questions.md`, `CLAUDE.md`, `docker-compose.yml`, `docs/HANDOFF.md`

- [ ] **Step 1: List every invented name for the owner (no web search)**

Run: `uv run python -m synthetic.books.innovation.names`
Expected: a markdown table of 16 company names and 16 officer names, with the six flagged for a first look (Stripple Tech, Tessaract Labs, Dataflake Inc, Veridia Payments, Halcyon Grid, Quillon AI). Nothing is searched here; the table says what to check, not what was found.

- [ ] **Step 2: Record the questions and the decisions taken in `docs/owner-questions.md`**

Append after item 7 in the "Added while you were away" section (numbers continue; paste the name table from Step 1 under item 8):

```markdown
8. **Check the invented names against real companies before anything is shown outside the team.** The innovation book adds 16 company names and 16 officer names (table below; the six marked are the ones most likely to collide). No search was done. *Taken: names stay as the spec lists them.* **Owner: to check.**
9. **DSCR in the innovation book.** None of the 16 has a DSCR covenant: a trailing-twelve-months test needs twelve published months, so the first possible test is May 2026 and an earlier test would leave "cannot test" rows through the history. Ferrogate (the only client with positive EBITDA) is the one place it makes sense. *Taken (controller, following the owner's earlier "have DSCR as well"): Ferrogate gets DSCR ≥ 1.25x on a trailing-twelve-months basis from May 2026 via a second terms version.*
10. **MRR export for Stripple.** The file is delivered as the real `mrr_export.xlsx` and as a PDF print of the same sheet, because intake accepts PDFs only. *Taken: both exist; the print is the file that is held.* Should intake accept spreadsheets?
11. **Due dates for the monthly package.** Financials and certificate 30 days (spec 3); MRR report 15; bank statements 7. The 7 and 15 are mine: "Lumora October reporting 12 days late" at an as-of of 19 November needs an item due on 7 November. *Taken: as stated.*
12. **Tidewell's cash mismatch.** The calculation records a passing variance on the ledger only, so no item is raised today. The answer key expects an exception `cash.statement_mismatch` (statements to certificate), which needs a reconciliation step built in Phase 3. *Taken: the key expects it; the tests pin it as pending.*
13. **Corvane's plan miss is a breach.** Revenue is under 80 percent of the approved plan in September and October; the certificate says so honestly, so the exception is `covenant.breach`. *Taken: as described.*
14. **Figures the spec left open for the four extra clients** (cash, burn, runway at 31 October 2026): Corvane $8.4M / $0.60M / 14.0; Nimbusfield $3.3M / $0.40M / 8.3; Tidewell $4.3M after the newly restricted account / $0.35M / 12.3; Ferrogate $16.0M / net burn −$0.25M / not meaningful. *Taken: as stated.*
15. **Sign the new answer key.** `synthetic/books/innovation/oracle.csv` has 63 unsigned rows (62 plus Ferrogate's DSCR test) for the 16 innovation clients (covenant tests, funding events and expected exceptions); the 16 rows for the four kept borrowers are the v1 rows and stay signed. It will arrive as one short table (standing approval 3).
```

- [ ] **Step 3: Update `CLAUDE.md` Commands**

After the line `uv run python -m synthetic.generate             # build the synthetic book into synthetic/out/` add:

```
uv run python -m synthetic.books.innovation.generate  # build the innovation book into synthetic/books/innovation/out/ (v2 default)
PYTHONPATH=backend uv run python -m app.seed_book     # seed the innovation book; add --book legacy for the v1 book
```

and change the comment on the first line to `# legacy C&I book into synthetic/out/ (frozen; engine tests run on it)`.

- [ ] **Step 4: Update `docker-compose.yml`**

In the comment on line 4 replace `python -m synthetic.generate && python -m app.seed_book` with `python -m synthetic.books.innovation.generate && python -m app.seed_book`.

- [ ] **Step 5: Add a short entry to `docs/HANDOFF.md`**

Directly under the "Where things stand" heading add:

```markdown
**Phase 2 (v2 innovation book, 20 November 2026):** `synthetic/books/innovation/` holds the 20-borrower book (16 venture-backed clients on a monthly cadence plus the four kept C&I borrowers, byte-identical to v1). The v1 generator and `synthetic/out/` are frozen and pinned by digest. The answer key `synthetic/books/innovation/oracle.csv` has 62 rows waiting for the owner's signature. `python -m app.seed_book` now loads the innovation book by default (`--book legacy` for v1). Expected values are computed independently of `app/calc`; `backend/tests/calc/test_synthetic_innovation_truth.py` runs the book through the engine. The stand-in reader for the new document types, recordings and the live run are Phase 3; the Tidewell reconciliation exception is pending until then.
```

- [ ] **Step 6: Whole-suite check**

Run:

```bash
service postgresql start
uv run ruff check .
uv run pytest
```

Expected: all green, including the legacy suites (`synthetic/tests`, `backend/tests/test_seed_book.py`, `backend/tests/calc/test_synthetic_truth.py`, `evals/tests`). If an evals test reads `synthetic/out` it is unaffected (v1 untouched); if one fails, it is a finding to report, not to patch.

- [ ] **Step 7: Commit**

```bash
git add docs/owner-questions.md CLAUDE.md docker-compose.yml docs/HANDOFF.md
git commit -m "docs(p2): owner questions, commands and handoff for the innovation book"
```

---

## Self-review (against the spec)

| Spec | Where |
|---|---|
| 2.1 twelve demo clients with exact October cash, burn, RML; four more with their situations | Tasks 1 (roster, owner table), 2 (exact figures, tested), 5 (`verify`) |
| 2.2 kept four unchanged: same truth, terms, documents, signed rows | Tasks 1 (pins), 6 (byte-identical, `_keep_sign_off`), 9 (identity), 8 (quarterly, `ci-1`) |
| 2.3 v1 stays a fixture; new book beside it | Tasks 1, 6 (README, `.gitignore`), 8 (`--book`) |
| 3 cadence, as-of, 18 months, requirements, cycles per frequency | Tasks 2 (18 months), 3 (requirements), 5 (documents), 8 (monthly cycles) |
| 10 every scenario self-verifying | Task 5 (`verify` and `test_scenarios.py`), Task 6 (pages), Task 8 (seeded exceptions), Task 9 (engine) |
| 11 independent expected values; cross-check both books; unsigned key; kept rows signed | Tasks 2, 9, 6 |
| 11 stand-in reader, recordings, live run | Not this phase (Phase 3); the truth carries `figures` and `page_map` for the stand-in |
| Funding events seeded (Dataflake, Halcyon, Kelvra, Nimbusfield slipped) | Tasks 5, 6, 8 |
| `revenue_below_plan` plan from approved terms | Task 7 (wiring), Task 8 (seeded signal), Task 9 (engine) |
| Seed either book; innovation default | Task 8 |
| Name check as an owner question, no web search | Tasks 1 (list), 10 (question 8) |
| Bank of Stoic, no real bank names | Task 6 (page scan) |

Placeholder scan: no TBD/TODO; every code step is a complete file or an exact old/new edit. Type consistency: `ClientSpec` fields, `Series` methods, `ClientBook` fields, `DocPlan` positional order (`id, slug, type, title, period_end, document_date, received_date, payload`) and the `generate` helper names are the ones the staged, passing code uses.

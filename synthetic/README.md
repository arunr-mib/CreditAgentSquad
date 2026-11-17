# Synthetic bank

A deterministic generator for the fictional commercial loan book of **Bank of Stoic**, built for
Credit Agent Squad. It produces a ground-truth financial model, the PDF documents a lender would
receive, and the exact results the product should reach from them. Because the truth is known
exactly, extraction, covenant tests and exceptions can be graded exactly.

Every document carries `SYNTHETIC - FOR DEMONSTRATION` in the footer of every page. All borrower,
customer, officer and audit-firm names are invented.

## Regenerate

```bash
uv run python -m synthetic.generate            # writes synthetic/out/ and synthetic/oracle.csv
uv run python -m synthetic.generate --out /tmp/book --seed 20261117
uv run pytest synthetic/tests -q
uv run ruff check synthetic
```

The same seed gives byte-identical truth files and identical PDF text (about 5 seconds for 21
borrowers, 360 documents, 1,570 pages). Generation fails loudly if any borrower's results are not
what its scenario is designed to produce, so a new seed either reproduces every scenario or stops.

| Output | Contents |
|---|---|
| `synthetic/out/truth/<borrower_id>.json` | ground truth and expected results (decimals as strings, ISO dates) |
| `synthetic/out/documents/<borrower_id>/*.pdf` | rendered documents (git-ignored) |
| `synthetic/out/manifest.json` | every document with the sha256 of its extracted text |
| `synthetic/oracle.csv` | one row per expected covenant test, borrowing base result and exception for the current period; `owner_signed_off` is `no` until the owner signs |

## The book

Today is 2026-11-17. The current period is the quarter ended 2026-09-30. All fiscal years end in
December. Truth periods are fiscal-year-to-date at Q1 2024 through Q3 2026 (11 periods);
fiscal 2023 is kept as `comparative_periods` because the FY2024 statements print it.

| Borrower id | Name | Industry | FY2025 revenue ($M) | Statements in | Facilities | Rating | Covenants | Scenario |
|---|---|---|---|---|---|---|---|---|
| `harrowgate-precision` | Harrowgate Precision Components, Inc. | manufacturing | 94 | thousands | BB line + term | 4 | fccr, total_leverage, min_tnw | clean |
| `tallwater-foodservice` | Tallwater Foodservice Supply, LLC | distribution | 232 | thousands | BB line + term | 5 | fccr, senior_leverage | clean (one customer over the concentration limit, correctly reported) |
| `brindlewood-home-health` | Brindlewood Home Health Partners, LLC | healthcare services | 45 | thousands | line + term | 4 | dscr, total_leverage, min_liquidity | clean |
| `marlowe-ridge-logistics` | Marlowe Ridge Cold Storage & Logistics, Inc. | logistics | 140 | thousands | line + term | 5 | fccr, total_leverage, max_capex | clean (an approved amendment creates terms version 2 from 2025-07-01) |
| `ostrander-valley-foods` | Ostrander Valley Foods, Inc. | food processing | 173 | thousands | BB line + term | 4 | fccr, total_leverage, min_tnw | clean (uncapped add-back) |
| `dunmore-industrial-supply` | Dunmore Industrial Supply Co. | distribution | 71 | dollars | BB line | 3 | interest_coverage, current_ratio, debt_to_tnw | clean |
| `sablewood-dental` | Sablewood Dental Management, LLC | healthcare services | 31 | dollars | term | 4 | dscr, total_leverage | clean |
| `larkspur-environmental` | Larkspur Environmental Services, Inc. | services | 57 | thousands | line + term | 3 | fccr, total_leverage, max_capex | clean (add-back capped at 10% of EBITDA, within the cap) |
| `kestrel-bay-packaging` | Kestrel Bay Packaging Corp. | manufacturing | 128 | thousands | line + term | 6 | total_leverage, current_ratio | `hidden_breach` |
| `vantry-freight` | Vantry Freight Systems, LLC | logistics | 103 | thousands | line + term | 6 | total_leverage, interest_coverage | `unapproved_amendment` |
| `quillfeather-bakery` | Quillfeather Bakery Brands, Inc. | food processing | 78 | thousands | line + term | 5 | total_leverage, fccr | `addback_over_cap` |
| `thornbury-metal` | Thornbury Metal Fabricators, Inc. | manufacturing | 49 | thousands | line + term | 7 | total_leverage, interest_coverage, current_ratio | `deteriorating_trend` |
| `eastmere-building` | Eastmere Building Products, LLC | distribution | 148 | thousands | line + term | 5 | fccr, total_leverage | `late_reporting` |
| `northgale-electrical` | Northgale Electrical Wholesale, Inc. | distribution | 96 | thousands | BB line | 5 | interest_coverage, debt_to_tnw | `miscounted_ineligible` |
| `briarstone-beverage` | Briarstone Beverage Company | food processing | 43 | dollars | BB line + term | 6 | fccr, total_leverage | `over_advance` |
| `wrenfield-diagnostics` | Wrenfield Diagnostic Laboratories, Inc. | healthcare services | 66 | thousands | line + term | 4 | total_leverage, min_tnw, max_capex, min_liquidity | `scale_trap` |
| `halvorsen-plastics` | Halvorsen Plastics & Molding, Inc. | manufacturing | 83 | thousands | BB line + term | 5 | fccr, total_leverage | `restated_comparative` |
| `ashgrove-fleet` | Ashgrove Fleet Maintenance, LLC | services | 24 | dollars | line + term | 5 | fccr, total_leverage, current_ratio | `missing_page` |
| `stanmoor-mechanical` | Stanmoor Mechanical Contractors, Inc. | services | 36 | dollars | line + term | 5 | dscr, current_ratio, min_tnw | `image_only` |
| `calder-finch-staffing` | Calder & Finch Staffing Group, LLC | services | 18 | dollars | line + term | 6 | total_leverage, fccr | `step_up` |
| `pellham-grain` | Pellham Grain & Milling Co. | food processing | 235 | thousands | BB line + term | 7 | fccr, total_leverage, min_tnw | `reported_breach` |

### Scenarios and what the product should raise for the current period

| Scenario | What happens | Expected exceptions |
|---|---|---|
| `clean` (8 borrowers) | everything passes with room, complete and on time | none |
| `hidden_breach` | leverage fails; the certificate adds unpermitted "pro forma cost savings" and claims compliance | `covenant.reported_mismatch` |
| `unapproved_amendment` | a signed amendment raising the add-back cap from $500,000 to $3,500,000 is on file but in no terms version; leverage fails under approved terms and passes under the amendment, which the certificate uses | `covenant.reported_mismatch`, `terms.unapproved_amendment` |
| `addback_over_cap` | the certificate adds back all restructuring charges, above the $500,000 cap; both calculations pass | none (both tests are `compliant_variance`, a logged variance) |
| `deteriorating_trend` | revenue, margin, DSO, DPO and leverage worsen over five quarters; covenants still pass with thin, falling headroom; line over 90% used; payment 12 days past due | `signal.high` (payment past due) |
| `late_reporting` | no Q3 2026 statements or certificate; due after 30 days, now 18 days late | `intake.missing_document` x2, `signal.high` (reporting late) |
| `miscounted_ineligible` | the borrowing base certificate counts one customer's over-90-day invoices as eligible | `bb.certificate_mismatch` |
| `over_advance` | a large customer cross-ages out; outstanding exceeds the borrowing base; the certificate is honest | `bb.over_advance` |
| `scale_trap` | statements in thousands, certificate in whole dollars; figures agree | none (all `compliant`) |
| `restated_comparative` | the Q3 2026 comparative column restates Q3 2025 revenue and cost of goods sold | `spread.restatement` |
| `missing_page` | the liabilities and equity page of the Q3 2026 balance sheet is omitted | `spread.does_not_foot` |
| `image_only` | the Q3 2026 income statement page is an image with no text layer | `spread.image_only` |
| `step_up` | maximum leverage steps down on 2026-01-01; Q3 2026 sits between the old and new levels; the certificate tests against the old level | `covenant.reported_mismatch` |
| `reported_breach` | fixed charge coverage fails and the certificate says so | `covenant.breach` |

Every covenant test before the current period is `compliant` for every borrower.

## Code

| File | Role |
|---|---|
| `model.py` | template `ci-1` lines, the quarterly simulation, year-to-date accumulation, consistency checks |
| `scenarios.py` | the roster, each borrower's scenario and drivers |
| `terms.py` | threshold selection, credit agreement and amendment text, terms versions with citations |
| `certificates.py` | what each borrower reported (correct or distorted per scenario) |
| `collateral.py` | receivables aging, inventory and borrowing base certificates |
| `expected.py` | expected covenant tests, borrowing base results and signals, in plain arithmetic |
| `book.py` | assembles one borrower and verifies its scenario came out as designed |
| `render/` | reportlab renderers: statements, legal documents, certificates |
| `generate.py` | CLI: renders, writes truth, manifest and oracle |

`expected.py` never imports from `backend/app`. If the calculation engine disagrees with it,
investigate; do not patch either side to match.

## Conventions the spec left open

These are the generator's decisions. The engine has to make the same ones, so they are listed here.

- **Truth file extras.** Beside the spec's keys: `comparative_periods` (fiscal 2023), `memo` per
  period (equity components, beginning cash; not template lines), `clause_index` per terms version
  (citations for facility amounts and borrowing base eligibility), and per document `scale`,
  `page_map`, `figures` (template key to page, printed label and printed text), `absent_keys`,
  `unreadable_keys`, `defects`. `scenario.details` holds the facts a grader needs.
- **Terms versions** hang off the borrower's primary facility (the line of credit, or the term loan
  when there is no line). A dated threshold change inside one agreement is a `steps` entry.
- **Rounding.** Ratios round to 2 decimals half-up, dollars to 0; the rounded value is compared with
  the threshold. No ratio test in the book sits within 0.03 of its threshold.
- **Certificate tolerance.** 0.01 for ratios, 1,000 dollars for amounts. Clean certificates agree
  exactly and variances are large, so the choice does not change any outcome.
- **Outcome to exception.** `breach` raises `covenant.breach`; `breach_reported_compliant` raises
  `covenant.reported_mismatch` only; `compliant_variance` raises nothing.
- **Blocked spreads.** For `late_reporting`, `missing_page` and `image_only` the current-period
  covenant tests are `cannot_test` (with `after_repair` holding what the test gives once the gap is
  fixed) and financial signals are unmeasured. The exception list holds the root cause only, not a
  `covenant.cannot_test` per covenant, on the reading that the cycle stops at intake or spreading.
- **Availability** in `min_liquidity` with `include_availability` is commitment less line
  outstanding (used only by a borrower without a borrowing base).
- **Borrowing base order.** Per customer: excluded categories (whole balance); over 90 days from
  invoice; cross-aging (if over-90 exceeds 50% of the customer's balance, the rest); contra (limited
  to what is left); concentration (the excess over 25% of the total left across customers, computed
  once). All eligible balances are multiples of 400 dollars, so every line is a whole number.
- **Signals (`signals-1`).** Changes are measured against the same period a year earlier, using only
  the 11 published periods; a rule whose inputs are not all available is unmeasured and gives no
  signal. Headroom is distance from the threshold divided by the threshold. "Falling two periods
  running" needs three consecutive tested quarters. Availability below 10% applies to borrowing base
  lines at a certificate date. Reporting lateness is the worst of the statements and certificate
  for the quarter, measured to the received date or to today. The auditor-opinion signal is not
  generated (every opinion here is unqualified). Severity: high for net loss, reporting late and
  payment past due; low for headroom falling; medium for the rest. A clean borrower may carry a
  low-severity "headroom falling" signal.
- **Absent lines.** A template input that is zero in both columns is left off the statement and
  listed in `absent_keys`. The four supplemental lines are always printed. Zero prints as `-`.
- **Comparative columns** are the same period one year earlier, for all three statements.

# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T07:58:41+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 4 borrower(s) (['pellham-grain', 'pellucid-sensors', 'quillon-ai', 'tessaract-labs']); 1 pass(es); run time 169.7 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- pass 1: 3 invented-number

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (385 of 385) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 75.0% (the book expects 75.0%) |
| Cycles reaching the signals stage or beyond | 4 of 4 |
| Cycles closed | 4 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 178,765 / 45,695 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 3 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 0 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `quillon-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `tessaract-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `pellucid-sensors` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a month-only rollforward of capitalised software; it was not spread as it has no template lines beyond the balance already reported from the balance sheet.' |  |
| `quillon-ai` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a month-only capitalised software rollforward (start balance, additions, amortisation, end balance); it has no template line and was not spread.' |  |
| `tessaract-labs` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page five is a single-month rollforward of capitalised software (opening balance, additions, amortisation, closing balance); its amortisation row has no template line and was not spread.' |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillon-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tessaract-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:3e25c14d-37d3-40d2-b995-7f155db348fd}}. Section 6.1 requires at least {{fact:96526fb0-3f31-4d0a-a1ea-1eed755f60f1}}, so the ratio falls short by {{fact:47368e5d-9530-498c-bb3f-6ccd8b1b8bf5}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:70093d31-8e18- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:3e25c14d-37d3-40d2-b995-7f155db348fd}}. Section 6.1 requires at least {{fact:96526fb0-3f31-4d0a-a1ea-1eed755f60f1}}, so the ratio falls short by {{fact:47368e5d-9530-498c-bb3f-6ccd8b1b8bf5}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:70093d31-8e18- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:3e25c14d-37d3-40d2-b995-7f155db348fd}} against a covenant minimum of {{fact:96526fb0-3f31-4d0a-a1ea-1eed755f60f1}}, leaving headroom of {{fact:47368e5d-9530-498c-bb3f-6ccd8b1b8bf5}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:aaf5ce44-5ac7-40da-ac53-5e1a0a2a5092}} in August to {{fact:a8d34e6d-7944-42a3-a427-b5ba27eedff6}} in October, pointing to ongoing cash burn. Cash of {{fact:9eded154-4a97-4052-9152-04adb81692ad}} still sits well above the {{fact:42ababe7-9a58-48b0-a9ae-6b34d1c02184}} minimum, so the concern is the trend rather than an imminent breach. No |
| `quillon-ai` | certificate | none | All three covenants are reported in the summary table on page one and agree with the calculation schedule on page two. |
| `quillon-ai` | certificate | none | In the summary table the Revenue to Plan requirement wraps across two lines; it is reported here as one phrase. |
| `quillon-ai` | certificate | none | The summary table header shows the Actual and In compliance column headings overlapping in the rendered page. |
| `quillon-ai` | early_warning | none | Headroom over the minimum cash covenant has narrowed steadily, from {{fact:02047848-6454-4372-858e-53aa62d1cb3c}} in August to {{fact:9798bca3-514e-463c-9ab6-3144de1159bb}} in September and {{fact:77a74bfd-623b-4e7e-b893-f03c58af6e7c}} in October. Cash of {{fact:a5e2880c-3816-4814-b67a-d7a7ead1b1a7}} remains well above the {{fact:6c53ba62-0a59-4725-943e-393ce7da89e1}} floor, but the steady decline |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:d18e3807-8d81-410f-96b6-fbf4f9f886c6}} in August to {{fact:c8a4cbcc-1999-4860-9fc1-731917123e18}} in October. Cash of {{fact:7c38f8d5-ee18-46a8-9447-10bf0282742d}} is still well above the {{fact:728cff81-c4d3-4982-9d7c-05e684a3259f}} minimum, so there is no near-term breach. The steady decline points to ongoing cash burn, and no other |


# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T03:11:37+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 4 borrower(s) (['stripple-tech', 'tessaract-labs', 'tidewell-medical', 'veridia-payments']); 1 pass(es); run time 403.6 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (236 of 236) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 75.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 50.0% (the book expects 50.0%) |
| Cycles reaching the signals stage or beyond | 3 of 4 |
| Cycles closed | 3 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 145,323 / 41,356 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
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
| `stripple-tech` | stripple_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `tessaract-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tidewell-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | none |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `stripple-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `stripple-tech` | intake | intake.unclassified | intake.unclassified: not_needed by analyst |
| `stripple-tech` | spreading | spread.value_unverified | none (left open) |
| `tessaract-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tidewell-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Figures held for a person

| Borrower | Item | Filed under | Label the reader gave | Label on the page | Reason |
|---|---|---|---|---|---|
| `stripple-tech` | spread.value_unverified | `bs.capitalised_software` | Capitalised software development costs | Capitalised software development costs | mapping_doubt |
| `stripple-tech` | spread.value_unverified | `bs.deferred_revenue_current` | Contract liabilities | Contract liabilities | mapping_doubt |
| `stripple-tech` | spread.value_unverified | `cf.capitalised_software_spend` | Software development costs | Software development costs | mapping_doubt |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `stripple-tech` | intake | none | Raw spreadsheet export of monthly recurring revenue and customer counts with no title, no borrower name and no stated report date; the borrower and period cannot be confirmed from the document itself, and the data shown ends in an earlier year than the other documents in this delivery. |
| `stripple-tech` | spreading | 1 | Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread. |
| `stripple-tech` | spreading | none | The document is a bank statement for the month of October 2026 rather than a set of financial statements, so only the two bank account total lines were spread. |
| `tessaract-labs` | spreading | 1 | Note 1 on page five is a single-month rollforward of capitalised software (opening balance, additions, amortisation, closing balance); its amortisation row has no template line and was not spread. |
| `tessaract-labs` | spreading | none | The document is a single-page bank statement from Bank of Stoic for the month of October 2026, not a set of financial statements. Only the two bank account totals are reported. |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Cash headroom has narrowed each month, from {{fact:4b37739c-9999-41ff-8506-13e0d10641e6}} in August to {{fact:b0944c84-9b0b-4812-882a-c9779a0e5366}} in September and {{fact:8c67eca2-8228-47eb-9b00-870ececfe2fc}} in October. Cash of {{fact:a4b95ad7-3fec-4d34-b09d-c4fa85296d11}} remains well above the {{fact:596fc38d-d1fc-426c-bfc8-5cd5ca81a2b7}} minimum, but the steady decline suggests ongoing cash |
| `tidewell-medical` | spreading | 1 | Note 1 (page 5) presents a one-month capitalised software roll-forward only; it was not spread, and its closing balance agrees in label to the balance sheet line already reported. |
| `tidewell-medical` | spreading | none | This document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines are reported. The balances are as at October 31, 2026, the requested period end. |
| `tidewell-medical` | spreading | 9002) | A new restricted escrow collateral account (ending 9002) was opened on October 14, 2026 under an escrow arrangement. It is included in the printed total of pledged and restricted accounts, and the reviewer may wish to confirm the related arrangement. |
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom fell from {{fact:c2914146-cfeb-479b-b943-e568509223c3}} to {{fact:05e182ac-c859-46a7-866c-57a6a1be9e48}}, most of it in October, leaving cash of {{fact:96b12a12-368d-4129-9236-712e7e3156e6}} against a floor of {{fact:761c7dcc-be1e-42c5-9a5e-26a784793936}}. This is the thinnest cushion of the three and moves with the shrinking runway. |
| `tidewell-medical` | early_warning | none | Runway headroom dropped from {{fact:ddf1fde1-cd39-4e90-b857-4ea3c52e0f87}} to {{fact:d9e898ae-2b1f-42ba-8999-f930ad36c25c}}, with the sharpest fall in October. Runway of {{fact:7c8c3773-efde-4e13-92a5-b513fb7c1581}} months is still well above the {{fact:1253ff82-d663-4110-9480-898c859a1ca6}}-month minimum. The October drop coincides with the cash decline, which points to faster burn. |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only from {{fact:39437d3e-cb04-4838-bbfe-ef4925e09d42}} to {{fact:61d46daf-6cf4-44b4-a43c-412e83f0fa84}}. Revenue is running at {{fact:470a6db8-749e-4b27-81a2-e1f4f213f28c}} of plan. That suggests the cash and runway pressure comes from spending or working capital rather than a sales shortfall. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom fell from {{fact:c2914146-cfeb-479b-b943-e568509223c3}} to {{fact:05e182ac-c859-46a7-866c-57a6a1be9e48}}, most of it in October, leaving cash of {{fact:96b12a12-368d-4129-9236-712e7e3156e6}} against a floor of {{fact:761c7dcc-be1e-42c5-9a5e-26a784793936}}. This is the thinnest cushion among these signals and moves with the shrinking runway. |
| `tidewell-medical` | early_warning | none | Runway headroom dropped from {{fact:ddf1fde1-cd39-4e90-b857-4ea3c52e0f87}} to {{fact:d9e898ae-2b1f-42ba-8999-f930ad36c25c}}, with the sharpest fall in October. Runway of {{fact:7c8c3773-efde-4e13-92a5-b513fb7c1581}} months is still well above the minimum of {{fact:1253ff82-d663-4110-9480-898c859a1ca6}} months. The October drop coincides with the cash decline, which points to faster burn. |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only from {{fact:39437d3e-cb04-4838-bbfe-ef4925e09d42}} to {{fact:61d46daf-6cf4-44b4-a43c-412e83f0fa84}}. Revenue is running at {{fact:470a6db8-749e-4b27-81a2-e1f4f213f28c}} of plan. That suggests the cash and runway pressure comes from spending or working capital rather than a sales shortfall. |
| `veridia-payments` | spreading | 1, | Page 5 (Note 1, capitalised software roll-forward) presents the month only and has no matching template lines; it was not spread. |
| `veridia-payments` | spreading | none | This document is a one-page bank statement (Bank of Stoic, statement period October 1, 2026 to October 31, 2026), not a set of financial statements, so only the two bank summary lines are reported. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Headroom on the minimum cash covenant narrowed each month, from {{fact:a56d6e09-60f7-42f2-8996-014564dc68aa}} at August 31 to {{fact:f5c4e11d-f469-43d3-b4be-4cf3278a59a6}} and then {{fact:8e3cc6ee-3f32-4372-8ffa-b56474e37f7b}} at October 31. Unrestricted cash of {{fact:6e1f9945-aca3-4aff-92b9-e5fc64446651}} remains well above the {{fact:a7dc4d4b-e463-4f7e-b37b-0776585b1b49}} floor, but the steady  |
| `veridia-payments` | early_warning | none | Headroom on the minimum cash covenant narrowed each month, from {{fact:a56d6e09-60f7-42f2-8996-014564dc68aa}} at end of August to {{fact:f5c4e11d-f469-43d3-b4be-4cf3278a59a6}} and then {{fact:8e3cc6ee-3f32-4372-8ffa-b56474e37f7b}} at end of October. Unrestricted cash of {{fact:6e1f9945-aca3-4aff-92b9-e5fc64446651}} remains well above the {{fact:a7dc4d4b-e463-4f7e-b37b-0776585b1b49}} floor, but the |

## Observations

- `stripple-tech`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `stripple-tech`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tessaract-labs`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tessaract-labs`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `veridia-payments`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `veridia-payments`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed


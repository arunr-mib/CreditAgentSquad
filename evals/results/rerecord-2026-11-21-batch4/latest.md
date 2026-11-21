# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T08:00:18+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 2 borrower(s) (['tidewell-medical', 'veridia-payments']); 1 pass(es); run time 96.2 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- pass 1: 3 invented-number

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (124 of 124) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 50.0% (the book expects 50.0%) |
| Cycles reaching the signals stage or beyond | 2 of 2 |
| Cycles closed | 2 of 2 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 78,975 / 22,665 |

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
| `tidewell-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | 2 |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `tidewell-medical` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 (page 5) presents a one-month capitalised software roll-forward only; it was not spread, and its closing balance agrees in label to the balance sheet line already reported.' |  |
| `tidewell-medical` | invented-number | spreading note | a note shown to a person types a figure: 'A new restricted escrow collateral account (ending 9002) was opened on October 14, 2026 under an escrow arrangement. It is included in the printed total of pledged and restricted accounts, and the reviewer may wish to  |  |
| `veridia-payments` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1, capitalised software roll-forward) presents the month only and has no matching template lines; it was not spread.' |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `tidewell-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:735d4528-2bc3-4245-ae80-f5fe5ee72941}} to {{fact:47642701-27fe-490a-928f-b33adde90f1c}} and then sharply to {{fact:370f7427-3266-4da7-b8ed-3e2ef5795114}}. Cash of {{fact:c71186d0-4532-4650-b75d-ba279b3f1fd5}} against a {{fact:587ac04d-68ab-41c8-acab-61e61e84577d}} floor is the tightest cushion of the three. The same cash decline is li |
| `tidewell-medical` | early_warning | none | Runway headroom fell from {{fact:5923156d-5b17-4795-b08d-aaba65784c4f}} to {{fact:2be480c2-276a-4efa-87fa-e64211c8e831}}, with the steepest drop in October. Runway of {{fact:5c962657-cdc9-4c76-86e7-d5549a472a92}} months is still well above the {{fact:5924794a-483f-4ff7-a304-12c5266711bc}}-month minimum. The decline mirrors the shrinking cash cushion and points to faster burn rather than a separate |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only marginally to {{fact:9a38fdcd-b162-4b44-b97a-35e865451eb5}}. Revenue of {{fact:c277bd3c-74ac-4e79-b397-8c5931c3ba02}} of plan is comfortably above the {{fact:aa19c384-9083-4796-ab5b-79411e86381e}} threshold. Because sales are on track, the falling cash and runway look driven by spending or working capital rather than weaker revenue. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:735d4528-2bc3-4245-ae80-f5fe5ee72941}} to {{fact:47642701-27fe-490a-928f-b33adde90f1c}} and then sharply to {{fact:370f7427-3266-4da7-b8ed-3e2ef5795114}}. Cash of {{fact:c71186d0-4532-4650-b75d-ba279b3f1fd5}} against a {{fact:587ac04d-68ab-41c8-acab-61e61e84577d}} floor is the tightest cushion among these signals. The same cash declin |
| `tidewell-medical` | early_warning | none | Runway headroom fell from {{fact:5923156d-5b17-4795-b08d-aaba65784c4f}} to {{fact:2be480c2-276a-4efa-87fa-e64211c8e831}}, with the steepest drop in October. Runway of {{fact:5c962657-cdc9-4c76-86e7-d5549a472a92}} months is still well above the minimum of {{fact:5924794a-483f-4ff7-a304-12c5266711bc}} months. The decline mirrors the shrinking cash cushion and points to faster burn rather than a sepa |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only marginally to {{fact:9a38fdcd-b162-4b44-b97a-35e865451eb5}}. Revenue of {{fact:c277bd3c-74ac-4e79-b397-8c5931c3ba02}} of plan is comfortably above the {{fact:aa19c384-9083-4796-ab5b-79411e86381e}} threshold. Because sales are on track, the falling cash and runway look driven by spending or working capital rather than weaker revenue. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:93a7f83d-996b-4908-861d-723a8d16193f}} in August to {{fact:5927a04e-a91f-4c77-83e6-6daaa17ae2f9}} in September and {{fact:325e2386-52d1-44bd-a92a-b5fd4954210e}} at October 31. Cash of {{fact:28ab73da-d0c2-4579-a5ff-f07545fb48f7}} remains comfortably above the {{fact:0aaf58ab-8c61-4ac7-817d-7030666e6bb9}} minimum, but the consistent drain ma |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:93a7f83d-996b-4908-861d-723a8d16193f}} in August to {{fact:5927a04e-a91f-4c77-83e6-6daaa17ae2f9}} in September and {{fact:325e2386-52d1-44bd-a92a-b5fd4954210e}} at October month-end. Cash of {{fact:28ab73da-d0c2-4579-a5ff-f07545fb48f7}} remains comfortably above the {{fact:0aaf58ab-8c61-4ac7-817d-7030666e6bb9}} minimum, but the consistent d |


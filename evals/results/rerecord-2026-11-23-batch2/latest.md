# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-23T23:58:22+00:00; commit `9f0b401a44be878cf0089a52c9c473b8c740102a`; 3 borrower(s) (['brackmere-medical', 'cindrel-tech', 'calvere-health']); 1 pass(es); run time 199.9 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (112 of 112) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 66.7% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 0.0%) |
| Cycles reaching the signals stage or beyond | 1 of 3 |
| Cycles closed | 1 of 3 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 69,340 / 20,627 |

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
| `brackmere-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | none |
| `calvere-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `cindrel-tech` | cindrel_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `cindrel-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `brackmere-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager |
| `calvere-health` | awaiting_package | intake.missing_document | none (left open) |
| `cindrel-tech` | intake | intake.unclassified | intake.unclassified: not_needed by analyst |
| `cindrel-tech` | spreading | spread.value_unverified | none (left open) |

## Figures held for a person

| Borrower | Item | Filed under | Label the reader gave | Label on the page | Reason |
|---|---|---|---|---|---|
| `cindrel-tech` | spread.value_unverified | `bs.capitalised_software` | Capitalised software development costs | Capitalised software development costs | mapping_doubt |
| `cindrel-tech` | spread.value_unverified | `bs.deferred_revenue_current` | Contract liabilities | Contract liabilities | mapping_doubt |
| `cindrel-tech` | spread.value_unverified | `cf.capitalised_software_spend` | Software development costs | Software development costs | mapping_doubt |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `brackmere-medical` | certificate | none | The Schedule 1 calculation of Unrestricted Cash on page two includes cash held in an escrow collateral account opened during the month; escrow collateral cash may not qualify as unrestricted, so the reported cash and runway figures may warrant review. |
| `brackmere-medical` | certificate | none | The requirement for Revenue to Plan on page one wraps across two lines in the summary table. |
| `brackmere-medical` | early_warning | none | Unrestricted cash headroom slipped from {{fact:3ce160dd-3a08-48c9-bb27-ba864fb42ea9}} to {{fact:9c317a78-fb2b-4ef1-8d0b-99c44a0f3974}}, then fell sharply to {{fact:2906f61f-4b39-46a4-964a-c9a108fc19cf}} in October. Cash of {{fact:a280aeb3-37d8-4e61-b9b6-7bd220b149f0}} still clears the {{fact:2e0970d5-4f5d-4491-bf43-4b2ff6fc2d2e}} floor. The runway decline points the same way, suggesting cash burn  |
| `brackmere-medical` | early_warning | none | Runway headroom fell from {{fact:bc6196a2-5e4a-405b-a31a-3507c574581f}} to {{fact:ab609b05-cc7f-49e3-885d-d5d2cabfd20f}} and then to {{fact:c088cb13-c166-4468-ba16-365e40e93a7c}}, with the steepest drop in October. Runway of {{fact:ccb823a4-d9d6-4a9a-ad4e-4b352a725383}} months is still well above the {{fact:b922f3af-45bc-42e7-abf0-39ee86c2a5e1}}-month minimum. The October drop mirrors the falling  |
| `brackmere-medical` | early_warning | none | Revenue headroom has been essentially flat, at {{fact:018378f7-0ac5-4927-a5d6-7fed9f650a7f}}, {{fact:8ecd74bb-c12a-4cbe-b597-e72a4aa38448}} and {{fact:6bee3bb8-0aa3-4731-a413-f092a6711030}}. Revenue is running at {{fact:7afe03cb-986c-438b-a580-887f6533735b}} of plan against an {{fact:5801d833-6a61-43d7-a541-8526ce1751ac}} floor. This suggests the cash and runway declines stem from spending or work |
| `brackmere-medical` | early_warning | none | Unrestricted cash headroom slipped from {{fact:3ce160dd-3a08-48c9-bb27-ba864fb42ea9}} to {{fact:9c317a78-fb2b-4ef1-8d0b-99c44a0f3974}}, then fell sharply to {{fact:2906f61f-4b39-46a4-964a-c9a108fc19cf}} in October. Cash of {{fact:a280aeb3-37d8-4e61-b9b6-7bd220b149f0}} still clears the {{fact:2e0970d5-4f5d-4491-bf43-4b2ff6fc2d2e}} floor. The runway decline points the same way, suggesting cash burn  |
| `brackmere-medical` | early_warning | none | Runway headroom fell from {{fact:bc6196a2-5e4a-405b-a31a-3507c574581f}} to {{fact:ab609b05-cc7f-49e3-885d-d5d2cabfd20f}} and then to {{fact:c088cb13-c166-4468-ba16-365e40e93a7c}}, with the steepest drop in October. Runway of {{fact:ccb823a4-d9d6-4a9a-ad4e-4b352a725383}} months is still well above the minimum of {{fact:b922f3af-45bc-42e7-abf0-39ee86c2a5e1}} months. The October drop mirrors the fall |
| `brackmere-medical` | early_warning | none | Revenue headroom has been essentially flat, at {{fact:018378f7-0ac5-4927-a5d6-7fed9f650a7f}}, {{fact:8ecd74bb-c12a-4cbe-b597-e72a4aa38448}} and {{fact:6bee3bb8-0aa3-4731-a413-f092a6711030}}. Revenue is running at {{fact:7afe03cb-986c-438b-a580-887f6533735b}} of plan against an {{fact:5801d833-6a61-43d7-a541-8526ce1751ac}} floor. This suggests the cash and runway declines stem from spending or work |
| `cindrel-tech` | intake | none | Untitled spreadsheet export of monthly recurring revenue and customer counts with no borrower name, no title and no report date; it covers months in the prior year rather than the current period, so it cannot be confirmed as a borrower MRR report and needs a person to review. |


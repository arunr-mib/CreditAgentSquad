# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T07:49:33+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 1 borrower(s) (['dataflake']); 1 pass(es); run time 106.0 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- pass 1: 1 invented-number

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (62 of 62) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 0.0%) |
| Cycles reaching the signals stage or beyond | 1 of 1 |
| Cycles closed | 1 of 1 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 65,918 / 16,213 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 1 |
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
| `dataflake` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `dataflake` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a one-month capitalised software rollforward; it was not spread as it covers the month only and has no template line beyond the balance sheet figure.' |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `dataflake` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `dataflake` | signals | signal.high | signal.high: acknowledged by analyst |
| `dataflake` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | covenant | 1 | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:72314421-976e-4db8-8c1a-54edfb96cefd}} against a minimum of {{fact:90263cfa-801d-4997-8049-daccf4de5980}} ({{fact:420db624-0e32-49de-bd64-e9d3d4a80144}} headroom). The certificate reports {{fact:20e82f95-f192-4d3b-ad4b-4c408e3fa3fc}} and claims compliance. Its Schedule 1 reaches that figure by adding the pledged collat |
| `dataflake` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:72314421-976e-4db8-8c1a-54edfb96cefd}} against a minimum of {{fact:90263cfa-801d-4997-8049-daccf4de5980}} ({{fact:420db624-0e32-49de-bd64-e9d3d4a80144}} headroom). The certificate reports {{fact:20e82f95-f192-4d3b-ad4b-4c408e3fa3fc}} and claims compliance. Its covenant schedule reaches that figure by adding the pledged |
| `dataflake` | early_warning | none | Runway stands at {{fact:07b61f82-22e1-414c-b86a-41bc7d9627c7}} months at October 31, so at the current burn the cash on hand would be exhausted in well under a year. This is the core repayment concern, and the cash covenant shortfall and the shrinking runway covenant cushion both point the same way. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:72314421-976e-4db8-8c1a-54edfb96cefd}} is below the covenant minimum of {{fact:90263cfa-801d-4997-8049-daccf4de5980}}, leaving headroom of {{fact:420db624-0e32-49de-bd64-e9d3d4a80144}}. The cushion is not just thin but negative, which reads as the covenant level being crossed. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Cash covenant headroom has fallen steadily, from {{fact:741f3e4a-e75a-45fa-a96d-a724bb5bbbdd}} in August to {{fact:27f2a252-f5c7-43cc-b69c-5b44d45a368b}} in September and {{fact:420db624-0e32-49de-bd64-e9d3d4a80144}} in October. The trend shows the shortfall is a sustained cash drain rather than a one-month dip, which reinforces the runway concern. |
| `dataflake` | early_warning | none | Runway covenant headroom has narrowed from {{fact:d69d82c4-2686-4c71-a085-bde0ef4a0246}} in August to {{fact:0f4a516c-80bb-4a2d-90d8-840c4dc82c95}} in September and {{fact:fd556cd6-994a-4d89-9e88-46a9b164bf2d}} in October. Runway of {{fact:487a261a-74e2-4da2-b28a-9a21c7314a68}} months is still above the minimum of {{fact:4ade100d-b734-4ee7-b218-8cfac3d30ff0}}, but at this pace the cushion could di |
| `dataflake` | early_warning | none | Runway stands at {{fact:07b61f82-22e1-414c-b86a-41bc7d9627c7}} months at October 31, so at the current burn cash on hand would run out within a short horizon. This is the core repayment concern, and the cash covenant shortfall and the shrinking runway covenant cushion both point the same way. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:72314421-976e-4db8-8c1a-54edfb96cefd}} is below the covenant minimum of {{fact:90263cfa-801d-4997-8049-daccf4de5980}}, leaving headroom of {{fact:420db624-0e32-49de-bd64-e9d3d4a80144}}. The cushion is not just thin but negative, which reads as the covenant level being crossed. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Cash covenant headroom has fallen steadily, from {{fact:741f3e4a-e75a-45fa-a96d-a724bb5bbbdd}} in August to {{fact:27f2a252-f5c7-43cc-b69c-5b44d45a368b}} in September and {{fact:420db624-0e32-49de-bd64-e9d3d4a80144}} in October. The trend shows the shortfall is a sustained cash drain rather than a one-month dip, which reinforces the runway concern. |
| `dataflake` | early_warning | none | Runway covenant headroom has narrowed from {{fact:d69d82c4-2686-4c71-a085-bde0ef4a0246}} in August to {{fact:0f4a516c-80bb-4a2d-90d8-840c4dc82c95}} in September and {{fact:fd556cd6-994a-4d89-9e88-46a9b164bf2d}} in October. Runway of {{fact:487a261a-74e2-4da2-b28a-9a21c7314a68}} months is still above the minimum of {{fact:4ade100d-b734-4ee7-b218-8cfac3d30ff0}}, but at this pace the cushion could di |

## Observations

- `dataflake`: guardrail note on early_warning: figure_untraceable -> explanation_dropped: runway_below_watch: a figure was typed, not referenced, and matches no fact or cited quote


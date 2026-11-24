# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-23T23:47:29+00:00; commit `9f0b401a44be878cf0089a52c9c473b8c740102a`; 1 borrower(s) (['datamarrow']); 1 pass(es); run time 171.1 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

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
| Model tokens in / out | 62,725 / 15,415 |

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
| `datamarrow` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `datamarrow` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `datamarrow` | signals | signal.high | signal.high: acknowledged by analyst |
| `datamarrow` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `datamarrow` | certificate | none | On page one the Revenue to Plan requirement text wraps across two lines in the summary table. |
| `datamarrow` | certificate | none | Schedule 1 shows Unrestricted Cash built up by including cash held in the pledged collateral account; the credit team may wish to review whether pledged cash qualifies as unrestricted. |
| `datamarrow` | certificate | none | No instructions addressed to the reader were found in the document. |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:53d25263-b311-4585-b901-bb5e0d9e2417}} against a minimum of {{fact:9d83270b-8f7c-4f19-9827-52b53df285ea}}, a headroom of {{fact:d1fba6d5-34ab-40e5-a99d-0ddedf31157f}}. The borrower certified {{fact:3ebf12fc-c267-4cdd-979c-69dba2eae6b6}} and reported compliance. The certificate's schedule reaches that figure by adding t |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:53d25263-b311-4585-b901-bb5e0d9e2417}} against a minimum of {{fact:9d83270b-8f7c-4f19-9827-52b53df285ea}} (headroom {{fact:d1fba6d5-34ab-40e5-a99d-0ddedf31157f}}). The borrower certified {{fact:3ebf12fc-c267-4cdd-979c-69dba2eae6b6}} and compliance. Its schedule adds the pledged collateral account to operating-account c |
| `datamarrow` | early_warning | none | At current burn, Datamarrow's cash covers about {{fact:3d20f048-c166-46e0-8861-1d90c619ef38}} months of operations, short enough that its ability to keep paying depends on new funding or cost cuts arriving soon. The falling runway covenant headroom and the cash covenant now below its minimum point the same way. |
| `datamarrow` | early_warning | none | Negative headroom means unrestricted cash of {{fact:dd933902-67d2-4a16-b45e-74e0de748a96}} is below the covenant minimum of {{fact:f333b89d-4d27-489d-9610-89b687ea4fc0}}, so on these figures the covenant appears breached at October 31, not merely tight. Together with the short runway, this shows the cash cushion has run out ahead of the borrower's funding needs. |
| `datamarrow` | early_warning | none | Cash covenant headroom slid from {{fact:197c121f-7e91-4273-8a36-453a5d8d1ab1}} in August to {{fact:59d498c9-d219-4568-8398-293abf56dfef}} in September and {{fact:9776bf85-4868-48f0-b981-81214cd2b2f1}} in October. The steady decline shows the breach is the result of continued burn rather than a one-off dip, which makes a quick recovery less likely without new cash. |
| `datamarrow` | early_warning | none | Runway covenant headroom fell from {{fact:4d5024dc-4ffa-4e10-bdfd-749c69fab4ae}} in August to {{fact:6874f8b3-ca06-4b29-a80f-4e460ca0fe3f}} in September and {{fact:43d454bb-6fa1-4042-b1a2-57b541bb9a7e}} in October, with runway of {{fact:f3ab609d-f31c-4a88-997b-8c1d36d40060}} months against a minimum of {{fact:4a0dd73f-970c-49a0-a66a-b603ca978dee}}. The covenant still passes, but if the pace contin |
| `datamarrow` | early_warning | none | At current burn, Datamarrow's cash covers about {{fact:3d20f048-c166-46e0-8861-1d90c619ef38}} months of operations, short enough that its ability to keep paying depends on new funding or cost cuts arriving soon. The falling runway covenant headroom and the cash covenant now below its minimum point the same way. |
| `datamarrow` | early_warning | none | Headroom of {{fact:9776bf85-4868-48f0-b981-81214cd2b2f1}} means unrestricted cash of {{fact:dd933902-67d2-4a16-b45e-74e0de748a96}} is below the covenant minimum of {{fact:f333b89d-4d27-489d-9610-89b687ea4fc0}}, so on these figures the covenant appears breached at period end, not merely tight. Together with the short runway, this shows the cash cushion has run out ahead of the borrower's funding ne |
| `datamarrow` | early_warning | none | Cash covenant headroom slid from {{fact:197c121f-7e91-4273-8a36-453a5d8d1ab1}} in August to {{fact:59d498c9-d219-4568-8398-293abf56dfef}} in September and {{fact:9776bf85-4868-48f0-b981-81214cd2b2f1}} in October. The steady decline shows the breach is the result of continued burn rather than a one-off dip, which makes a quick recovery less likely without new cash. |
| `datamarrow` | early_warning | none | Runway covenant headroom fell from {{fact:4d5024dc-4ffa-4e10-bdfd-749c69fab4ae}} in August to {{fact:6874f8b3-ca06-4b29-a80f-4e460ca0fe3f}} in September and {{fact:43d454bb-6fa1-4042-b1a2-57b541bb9a7e}} in October, with runway of {{fact:f3ab609d-f31c-4a88-997b-8c1d36d40060}} months against a minimum of {{fact:4a0dd73f-970c-49a0-a66a-b603ca978dee}}. The covenant still passes, but if the pace contin |


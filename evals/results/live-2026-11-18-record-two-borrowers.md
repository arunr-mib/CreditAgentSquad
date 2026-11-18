# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-18T23:14:27+00:00; commit `f81e6a9c55adbac0e30ec5a3006ff0bd92261c5e`; 2 borrower(s) (['harrowgate-precision', 'briarstone-beverage']); 1 pass(es); run time 235.8 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (400 of 400) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 33.3% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 50.0%) |
| Cycles reaching the signals stage or beyond | 2 of 2 |
| Cycles closed | 2 of 2 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 79,567 / 28,679 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 2 |
| wrong-citation | 0 |
| wrong-abstain | 0 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance, intake.unclassified | 100.0% (201/201) | 2/2 | 1 |
| `harrowgate-precision` | clean | closed (closed) | none | intake.unclassified | 100.0% (199/199) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `briarstone-beverage` | false-exception | intake.unclassified | not expected for scenario over_advance: bbc-2026-09-30.pdf: the Intake Agent raised a concern |  |
| `harrowgate-precision` | false-exception | intake.unclassified | not expected for scenario clean: bbc-2026-09-30.pdf: the Intake Agent raised a concern |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance, intake.unclassified | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | intake.unclassified, review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | intake.unclassified, review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page; the calculation schedule on the second page shows matching values. |
| `briarstone-beverage` | certificate | none | No instructions were found in the document text. |
| `briarstone-beverage` | collateral | 0, 30 | 0-30 days |
| `briarstone-beverage` | collateral | 31, 60 | 31-60 days |
| `briarstone-beverage` | collateral | 61, 90 | 61-90 days |
| `briarstone-beverage` | collateral | 90 | Over 90 days |
| `briarstone-beverage` | collateral | none | The certificate prints a single combined line labelled availability with over-advance in brackets; it is reported under availability only, and no separate over-advance line is printed, so over_advance is omitted. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate rows were skipped as percentage rows. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base as of the date shown. |
| `briarstone-beverage` | collateral | none | The inventory report states that work in process and consignment inventory are not eligible, and that inventory was last physically counted at the most recent fiscal year end, with current quantities taken from perpetual records. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; values were taken from that table rather than the Schedule 1 calculations. |
| `harrowgate-precision` | certificate | none | No embedded instructions were found in the document. |
| `harrowgate-precision` | collateral | 0, 30 | 0-30 days |
| `harrowgate-precision` | collateral | 31, 60 | 31-60 days |
| `harrowgate-precision` | collateral | 61, 90 | 61-90 days |
| `harrowgate-precision` | collateral | 90 | Over 90 days |
| `harrowgate-precision` | collateral | none | The certificate prints an inventory sublimit line that matches no requested line name, so it was not reported. |
| `harrowgate-precision` | collateral | none | No separate over-advance line is printed; the availability line is labelled availability with over-advance in brackets and was reported as availability only. |
| `harrowgate-precision` | collateral | none | Percentage advance rate rows were skipped as instructed. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory report states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end, not at the certificate date. |
| `harrowgate-precision` | collateral | none | No instructions addressed to the reader were found in the document. |

## Observations

- `harrowgate-precision`: guardrail note on intake: figure_untraceable -> dropped: a concern from the agent contained a typed figure and was removed
- `harrowgate-precision`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact


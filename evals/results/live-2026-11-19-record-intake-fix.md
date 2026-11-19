# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-19T07:03:34+00:00; commit `0c77f8c1208dc649943e43e5561010b4562e9641`; 2 borrower(s) (['harrowgate-precision', 'briarstone-beverage']); 1 pass(es); run time 217.0 seconds.
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
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 50.0% (the book expects 50.0%) |
| Cycles reaching the signals stage or beyond | 2 of 2 |
| Cycles closed | 2 of 2 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 76,703 / 25,746 |

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
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page; the calculation schedule on the second page shows matching values. |
| `briarstone-beverage` | collateral | none | No separate over-advance line is printed; the single line labelled Availability (over-advance) is reported under availability and shows a bracketed (negative) figure. |
| `briarstone-beverage` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states the borrower acknowledges revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory report states work in process and consigned inventory are not eligible, but no consignment category is listed; it also states quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | The aging is aged from invoice date; inventory is stated at lower of cost and market. |
| `briarstone-beverage` | collateral | none | No instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:47c5f695-e47b-4894-ac60-e0a1ba696867}}, or {{fact:6ee5f9bc-2aba-4ced-9af1-0027a8bc22f1}} of the {{fact:d77ca677-c565-4134-aa02-00a92e729f6a}} commitment. Outstandings exceed eligible collateral, leaving no liquidity cushion on the line. No other signal fired to show whether this comes from heavier borrowing or shrinking receivables and inventory. |
| `harrowgate-precision` | spreading | none | The debt schedule on page 5 (revolving line of credit, term notes payable, total debt outstanding) was not mapped as the template has no separate lines for it. |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; values were taken from that table rather than the Schedule 1 calculations. |
| `harrowgate-precision` | certificate | none | No instructions were found embedded in the document. |
| `harrowgate-precision` | collateral | none | The certificate prints availability and over-advance on a single combined line labelled 'Availability (over-advance)'; it is reported as availability, and no separate over-advance line is printed, so over_advance is omitted. |
| `harrowgate-precision` | collateral | none | The certificate's 'Inventory sublimit' line does not match any requested line name and was not reported. |
| `harrowgate-precision` | collateral | none | Advance rate rows are percentages and were skipped. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the aging and inventory pages also state amounts in U.S. dollars, the inventory being at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `harrowgate-precision` | collateral | none | No instructions addressed to the reader were found in the document. |

## Observations

- `harrowgate-precision`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed


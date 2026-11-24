# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T08:03:10+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 3 borrower(s) (['briarstone-beverage', 'harrowgate-precision', 'kestrel-bay-packaging']); 1 pass(es); run time 165.9 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (502 of 502) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 33.3% (the book expects 33.3%) |
| Cycles reaching the signals stage or beyond | 3 of 3 |
| Cycles closed | 3 of 3 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 143,858 / 41,785 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 1 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:cd93dc75-5983-49a9-8374-b50c46e4f979}}, or {{fact:b9ff8a3a-cceb-4626-b051-5ca7934ab285}} of the {{fact:5265b84a-c875-41af-9b8a-72904945e1b3}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:71f1f463-4257-42f8-a87e-3caed6a4e61c}} against a maximum of {{fact:46ed2531-fbc9-49f8-bd24-8efba7c42b63}}, while the certificate reports {{fact:ec15fc1e-2bdd-4b2e-9347-dfc5042bdd4d}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:71f1f463-4257-42f8-a87e-3caed6a4e61c}} against a maximum of {{fact:46ed2531-fbc9-49f8-bd24-8efba7c42b63}}, while the certificate reports {{fact:ec15fc1e-2bdd-4b2e-9347-dfc5042bdd4d}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:73a0f1be-e6b3-41c8-88ab-5cec81ce5057}}): total leverage of {{fact:e7c6b39a-e868-4737-a6fc-76c468a363cf}} sits above the {{fact:1ee786fb-b461-4549-a2b7-db006389a4f4}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:3813a38c-187f-4e5b-848c-4b792f920a25}} is only slightly above the {{fact:ee9bd154-3746-46f2-9608-e3f2701d47fa}} minimum, leaving headroom of {{fact:a80ae34a-8f2a-4db5-87da-8b731aa1b389}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:12fa2d39-ae86-4c28-adc1-2c7240aada9f}} in March to {{fact:bfecb3a5-0ab0-4ed0-b133-7aea2c2c9e41}} in June, then dropped sharply to {{fact:a80ae34a-8f2a-4db5-87da-8b731aa1b389}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |

## Observations

- `kestrel-bay-packaging`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote


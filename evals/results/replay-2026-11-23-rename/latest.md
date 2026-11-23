# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-23T08:30:18+00:00; commit `f254a77f80765d6c6100a7571de7c28e2ed399f1`; 12 borrower(s) (whole book except 8 not replayed); 1 pass(es); run time 77.6 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- **NOT REPLAYED (8; the gate covers only the 12 that ran): brackmere-medical, calvere-health, cindrel-tech, datamarrow, meridew-analytics, tarnavi-ai, tavernel-grid, vantrell-labs - no recording: renamed 22 Nov, re-record needs owner go-ahead.**
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (1199 of 1199) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 66.7% (the book expects 66.7%) |
| Cycles reaching the signals stage or beyond | 12 of 12 |
| Cycles closed | 12 of 12 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 513,265 / 137,921 |

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
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

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
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:062f8136-d395-48cb-9202-03152adf0e9e}}, or {{fact:3edd0c9b-7784-4f3c-80a9-39aaf4f6ff6a}} of the {{fact:128249b3-69c1-4e80-9c54-410c71f50ade}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:0be5f542-1af4-41e2-a3b1-da4050b51168}} months at July 31 to {{fact:f0965a60-c6ce-4bc9-b2d8-8a26a8a81349}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:443c5fd6-9e3c-4ead-80a0-670d0ddd89e3}} in August to {{fact:6535f088-1fd3-488a-91ad-a1894a332a8c}} in October, with runway at {{fact:8fd4281a-b505-4f58-ba2d-48300682eede}} months against a floor of {{fact:767c1139-dcd0-4d17-936c-0b8be3796f81}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:ec074b7e-1792-4d78-9dc5-339ebdd9accc}} still clears the {{fact:f82be780-c9da-4e55-aeb8-7faa4ea208d4}} minimum. However, headroom fell from {{fact:4c1422a5-3a96-4fc6-b8fc-cf5a312a3bbf}} to {{fact:6df0ca66-c839-4252-8354-3a6c0650bb9b}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kelvra-bio` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `kelvra-bio` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `kelvra-bio` | certificate | none | No embedded instructions were found in the document. |
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:51128769-1b84-48da-af9f-4639a87613bd}} in August to {{fact:527c90a1-d20c-48ce-a245-1dce8505f036}} in October, suggesting steady cash burn. Cash of {{fact:d8c02106-9506-42c1-ae58-088d5e2116f2}} still sits well above the {{fact:1f5e826e-8bf5-4775-8457-cbd5a0aee88b}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:eed352b3-086c-45cb-90e4-a3e6ea65682e}} against a maximum of {{fact:0d39c49d-8299-4021-bf69-806333b5158c}}, while the certificate reports {{fact:abdaceb3-0799-4c58-b566-a8c3a31173d4}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:eed352b3-086c-45cb-90e4-a3e6ea65682e}} against a maximum of {{fact:0d39c49d-8299-4021-bf69-806333b5158c}}, while the certificate reports {{fact:abdaceb3-0799-4c58-b566-a8c3a31173d4}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:420fa0e9-717c-4968-b54c-999159eca728}}): total leverage of {{fact:fc067eec-e4d4-4d76-bda5-000d2c9c55bd}} sits above the {{fact:1aca5cb9-b32c-4eb5-bdc8-d0bdb1064193}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:30f23225-b83f-4505-b887-1b00837a0e01}} is only slightly above the {{fact:69f09fad-98e5-425e-87f6-3c5980ffc3c5}} minimum, leaving headroom of {{fact:b0cc2e7c-a9c3-49b1-b5c9-d27a94169b90}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:8f69c8b3-3d63-440c-85e0-1f804b025919}} in March to {{fact:9f776c54-286e-41b4-9b94-e5502691e993}} in June, then dropped sharply to {{fact:b0cc2e7c-a9c3-49b1-b5c9-d27a94169b90}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:ca31d0b3-088c-4969-be57-ad6921bcdb6b}} in August to {{fact:abeb0906-68b3-4c4f-b984-9f3343ed35e3}} in October, suggesting ongoing cash burn. Cash of {{fact:03beffde-fd63-4492-b47e-cca82993500b}} still sits well above the {{fact:f2428560-abf8-4915-b5b7-9c072f4e23c7}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:e43f54b1-56e0-4e01-94c9-4030d978c6c6}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:1ce5ecb2-a48a-4039-8fcf-988df9a5ae13}} in August to {{fact:70915b6a-f335-4f3d-b21e-6a8a7da9fc39}} in October, with runway at {{fact:66ae6e64-a245-4897-8f8e-1fe7d6453c5a}} months against a floor of {{fact:63c19cf2-5c1f-47dd-96f7-213e4bce0013}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:982a9353-830b-4009-948e-eccbfb11feae}} remains above the {{fact:8d6b77d9-cb75-48e0-bc42-1e99c9a76dd1}} minimum, but headroom dropped from {{fact:61a17186-de6c-437e-961d-988ee31d7098}} in August to {{fact:209047f2-061e-454c-9364-b6b1374ecb19}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:67bf5f78-6584-49e4-835a-de949f2f2f43}} of plan against an {{fact:66ec46c6-4616-46bf-a9cd-fb1cd4b5315f}} floor, and headroom has been essentially flat, moving only from {{fact:2bf7753c-daeb-4426-a25e-dcba6dc1da76}} to {{fact:d7d29833-2444-4c1e-96d3-84aaa8d8735e}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:bc4e62d8-b357-4703-a77a-be587d600662}} against {{fact:49e4d111-a9d2-4b41-aaf3-4b4b7cd67c61}}), but headroom has fallen steadily from {{fact:f6cde8ef-9210-4fb2-8984-a67972681345}} to {{fact:723d16ad-d178-48ea-8404-c0af85719715}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:261376aa-1545-4a8c-a3f8-9b91bb01a521}}. Section 6.1 requires at least {{fact:b2f638c0-94c4-4268-b880-0f0cfd8043f7}}, so the ratio falls short by {{fact:bd3f9a93-0b4e-4296-86a6-8f029e5d2f95}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:8fa5da6c-6831- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:261376aa-1545-4a8c-a3f8-9b91bb01a521}}. Section 6.1 requires at least {{fact:b2f638c0-94c4-4268-b880-0f0cfd8043f7}}, so the ratio falls short by {{fact:bd3f9a93-0b4e-4296-86a6-8f029e5d2f95}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:8fa5da6c-6831- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:261376aa-1545-4a8c-a3f8-9b91bb01a521}} against a covenant minimum of {{fact:b2f638c0-94c4-4268-b880-0f0cfd8043f7}}, leaving headroom of {{fact:bd3f9a93-0b4e-4296-86a6-8f029e5d2f95}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:0dd86cee-3b0e-4f87-8019-371e479f041d}} in August to {{fact:3f406d44-9cdd-45e3-847f-bbd49aec4a4f}} in October, pointing to ongoing cash burn. Cash of {{fact:95782ad0-10ee-414b-99a0-867355226bd3}} still sits well above the {{fact:f85d045d-a266-4406-91c2-086480ddf27b}} minimum, so the concern is the trend rather than an imminent breach. No |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:541431a0-0f45-4199-84be-c67157d83f65}} in August to {{fact:7df0c9e6-0b11-4d5c-99d8-d809eae41c77}} in September and {{fact:277e0092-0aab-4bc5-9b1a-fdcc998d6449}} at October 31. Cash of {{fact:5ea8cc8b-9481-4d4c-9366-1be586f57e9f}} remains comfortably above the {{fact:5b36373d-883e-412a-bbc6-2cea03c24ee1}} minimum, but the consistent drain ma |

## Observations

- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `briarstone-beverage`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kelvra-bio`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `kestrel-bay-packaging`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `mosswell-robotics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `orbitline-systems`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellham-grain`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellucid-sensors`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `veridia-payments`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity


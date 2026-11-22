# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-22T04:50:28+00:00; commit `00caf6334eaf9a3e82068d9dcf2311810f53c2c4`; 20 borrower(s) (whole book); 1 pass(es); run time 171.8 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (1621 of 1621) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 94.9% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 55.0% (the book expects 55.0%) |
| Cycles reaching the signals stage or beyond | 18 of 20 |
| Cycles closed | 18 of 20 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 809,450 / 216,814 |

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
| `corvane-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `dataflake` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `halcyon-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |
| `lumora-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `quillon-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `stripple-tech` | stripple_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `tessaract-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tidewell-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | none |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `stripple-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `corvane-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `corvane-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `dataflake` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `dataflake` | signals | signal.high | signal.high: acknowledged by analyst |
| `dataflake` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `halcyon-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `lumora-health` | awaiting_package | intake.missing_document | none (left open) |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillon-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
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
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:4cba36a7-df78-405f-ac82-38a03f7db0f6}}, or {{fact:77c01e1f-9c5d-42cc-855d-f912b411a230}} of the {{fact:32bcc249-6068-4649-bcf9-dc4f984f61e0}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:4c5b1f97-a0a6-4a3c-80ce-0dbab7b1d207}} months at July 31 to {{fact:84b056ed-2f5a-4765-b17f-85554e606014}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:b47be179-c693-4df8-9253-7bd67ab3ed10}} in August to {{fact:22ead80d-f525-4932-a728-a603a297bee7}} in October, with runway at {{fact:79e5f0fa-d5fd-4c86-a249-9c17bd946644}} months against a floor of {{fact:5439c819-c426-4c38-b3f6-5cfd167c52cb}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:f34e7996-acd0-4731-9586-506b96112f4d}} still clears the {{fact:40d6a6e7-50c4-403a-9708-b5ce6c0e3be2}} minimum. However, headroom fell from {{fact:5e2a1b88-194b-4b9e-9d48-450fc199ba85}} to {{fact:896babc2-e31a-444c-850a-6abc9a50ba28}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `corvane-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `corvane-analytics` | certificate | none | The borrower reports non-compliance with the Revenue to Plan covenant. |
| `corvane-analytics` | certificate | none | On page one the Revenue to Plan requirement wraps across two lines in the table. |
| `corvane-analytics` | certificate | none | No instructions were found in the document text. |
| `corvane-analytics` | covenant | 1, | The Revenue to Plan test fails for the three months ended October 31, 2026. Revenue was {{fact:28b7ec4e-ed27-4020-bbec-2c3cdd7cf93b}} of the Approved Plan. Section 6.3 requires at least {{fact:3b21a8b8-12d2-4ff9-b278-f45702b721c5}}. I reran the test under terms version 1, the only version on file, and it still fails, with headroom of {{fact:874e1bfb-c4ab-444a-8a28-abb8a444aaf0}}. The borrower's Oc |
| `corvane-analytics` | early_warning | none | Revenue reached {{fact:13a92a60-abbf-4020-b5ee-5a12113c079b}} of plan against a covenant floor of {{fact:ff7b9522-3630-418a-8d6d-17c51ba8a09f}}, so headroom is negative at {{fact:dee4f213-22c2-417b-811c-3100ad7e9dea}}. The covenant measure therefore sits below its threshold, not merely close to it. This is the covenant view of the same shortfall flagged by the revenue-below-plan signal. |
| `corvane-analytics` | early_warning | none | Revenue came in at {{fact:79babefd-966f-4141-b170-fd209fe729f8}} of plan, a material miss for a subscription business whose plan underpins its cash runway. It is the operating cause behind the revenue covenant falling below its floor. If the miss persists, it may also explain the steady erosion in cash headroom. |
| `corvane-analytics` | early_warning | none | Unrestricted cash of {{fact:73205f43-2f28-4b0c-ad44-937cd43c4512}} remains well above the {{fact:834d4222-8616-4224-86f4-88d5ed5c35c8}} minimum, but headroom has declined each month, from {{fact:519c120d-0d42-4647-9b25-04afb4695901}} in August to {{fact:635956fe-4385-481c-9f7f-d66d475ca683}} in September and {{fact:65b8e746-23c5-4045-9bff-e9a893257fe2}} in October. Ongoing burn alongside the reven |
| `corvane-analytics` | early_warning | none | Revenue covenant headroom has deteriorated each month, from {{fact:02a9d8a2-19b4-4939-9057-df7e56b300b2}} in August to {{fact:a12ef935-594c-4901-adb7-95b6b89734c1}} in September and {{fact:dee4f213-22c2-417b-811c-3100ad7e9dea}} in October. It turned negative in September and the gap widened in October, showing the shortfall is worsening rather than a one-month miss. |
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | covenant | 1 | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:fd2843ab-a412-4b7c-956d-deace882f1c4}} against a minimum of {{fact:4e010533-f307-41c7-94ca-101bb91ab4c6}} ({{fact:26a7288c-c90a-4801-8e87-3a224e8cecd6}} headroom). The certificate reports {{fact:ea89345c-f889-4c0d-bc9d-5c81eef876fb}} and claims compliance. Its Schedule 1 reaches that figure by adding the pledged collat |
| `dataflake` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:fd2843ab-a412-4b7c-956d-deace882f1c4}} against a minimum of {{fact:4e010533-f307-41c7-94ca-101bb91ab4c6}} ({{fact:26a7288c-c90a-4801-8e87-3a224e8cecd6}} headroom). The certificate reports {{fact:ea89345c-f889-4c0d-bc9d-5c81eef876fb}} and claims compliance. Its covenant schedule reaches that figure by adding the pledged |
| `dataflake` | early_warning | none | Runway stands at {{fact:263adbb7-a868-4625-9247-65b36d7f20b1}} months at October 31, so at the current burn the cash on hand would be exhausted in well under a year. This is the core repayment concern, and the cash covenant shortfall and the shrinking runway covenant cushion both point the same way. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:fd2843ab-a412-4b7c-956d-deace882f1c4}} is below the covenant minimum of {{fact:4e010533-f307-41c7-94ca-101bb91ab4c6}}, leaving headroom of {{fact:26a7288c-c90a-4801-8e87-3a224e8cecd6}}. The cushion is not just thin but negative, which reads as the covenant level being crossed. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Cash covenant headroom has fallen steadily, from {{fact:ffdd5fe6-7930-4a1c-aad7-684b9dd3f3a5}} in August to {{fact:fbb96529-360d-4e7e-b312-bcb09ecd59f1}} in September and {{fact:26a7288c-c90a-4801-8e87-3a224e8cecd6}} in October. The trend shows the shortfall is a sustained cash drain rather than a one-month dip, which reinforces the runway concern. |
| `dataflake` | early_warning | none | Runway covenant headroom has narrowed from {{fact:511afeb0-7f71-4a4d-b719-dcc29a9e225b}} in August to {{fact:fffb7f39-2dd1-4aff-8f21-dde7db123676}} in September and {{fact:b05ce7e3-a867-4f4e-b7e1-29a9bf52938e}} in October. Runway of {{fact:1e31f2c1-806d-46e9-81f8-f91e2ee934f3}} months is still above the minimum of {{fact:53d60202-9ba0-4848-aa37-046a2abc7b95}}, but at this pace the cushion could di |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `halcyon-grid` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the Revenue to Plan requirement wraps across two lines in the table. |
| `halcyon-grid` | certificate | none | The summary table header for the actual and compliance columns appears overlapped in the rendering, but row values are legible. |
| `halcyon-grid` | certificate | none | No embedded instructions were found in the document. |
| `halcyon-grid` | early_warning | none | Cash headroom has fallen steadily, from {{fact:0c4bd120-7cda-4d10-971c-4a430230c5b4}} in August to {{fact:a65c790d-47bd-498d-85f4-2ea26c78a60e}} in October, with unrestricted cash of {{fact:f63d3a9b-0e01-4256-ab57-7fafffee8961}} against a {{fact:82086fe9-343d-4185-a68c-8f5401693398}} floor. Revenue is running ahead of plan, so the burn seems to come from spending rather than a sales shortfall. If  |
| `halcyon-grid` | early_warning | none | Revenue is at {{fact:e5490943-daef-4818-91f2-4bb6365623ed}} of plan against an {{fact:378eb234-26ff-4873-bbad-7bfce37b2d8c}} minimum. Headroom has only edged down, from {{fact:78a9a009-b29a-4a8a-a0f7-56b286554032}} to {{fact:ffc139b5-c3d4-496a-8c11-7d96a8b27e4d}}, which is a minor change. This signal mainly shows that the falling cash position is not explained by weak sales. |
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
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:d5622c48-d49a-497a-bc20-6befdcaf3ad7}} in August to {{fact:1a5a0632-0863-463f-af09-0e5e1de157c3}} in October, suggesting steady cash burn. Cash of {{fact:5946e000-9ce3-4291-a035-c0172290b946}} still sits well above the {{fact:2db10985-bd90-4ba7-8a2d-bf2bdccaa723}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:80c8c8ff-05d4-4f07-9de7-55d1e4b79568}} against a maximum of {{fact:8b503cd7-fc9e-4405-a03a-24090ef189db}}, while the certificate reports {{fact:74cbf598-ec16-437f-ba24-c12ff9ed9dc9}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:80c8c8ff-05d4-4f07-9de7-55d1e4b79568}} against a maximum of {{fact:8b503cd7-fc9e-4405-a03a-24090ef189db}}, while the certificate reports {{fact:74cbf598-ec16-437f-ba24-c12ff9ed9dc9}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:0f1e21ed-9ed3-41dc-adee-0ae1464676db}}): total leverage of {{fact:5c0a63ea-02b8-4bfa-821b-d41a1104cce5}} sits above the {{fact:a08174e7-c68d-40f8-8b6d-3cf6236c9f9f}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:125f2228-6362-40c9-868c-928e6472485e}} is only slightly above the {{fact:e9c9cc0a-0de0-4a33-b409-99a5a6ef5ac6}} minimum, leaving headroom of {{fact:724eb32c-429c-431c-b7e6-601e198066f4}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:8f31b81f-8351-48d2-ac4e-a763e6693dd9}} in March to {{fact:634135fd-2d7e-466a-bd56-ef0927c3812e}} in June, then dropped sharply to {{fact:724eb32c-429c-431c-b7e6-601e198066f4}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:ef2bb4f9-2b6b-41b8-93a9-ed77c0a02e0c}} in August to {{fact:90f596d5-4d13-4ab5-ba60-684a20b83a35}} in October, suggesting ongoing cash burn. Cash of {{fact:ad122da7-e15e-45b4-a479-23be42ef451a}} still sits well above the {{fact:8aee3ac8-3575-46c0-a311-12ac29de15e4}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:8400c520-2b1f-4e34-a85b-f624e96d467b}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:7fc96e7e-8773-4228-8609-3ba3952e2bbe}} in August to {{fact:74dc7d3b-708f-4131-bf56-d56cdbdb156b}} in October, with runway at {{fact:6b788c68-97e7-4e7b-8cfb-8f80e04b3e36}} months against a floor of {{fact:7e53160d-2803-4849-a6a5-65df7b40c638}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:f7f78cf3-be69-4fba-9c28-0d1866644222}} remains above the {{fact:51e40d6b-3f77-4952-937b-9148c3a4ec59}} minimum, but headroom dropped from {{fact:9f73ae1c-faea-4b7c-9ee4-e0f8100c2790}} in August to {{fact:8f73f491-790b-42f3-b70a-20b6c3ba08da}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:f00556e1-c98c-404c-ae77-dfb123fbf041}} of plan against an {{fact:dba395cd-3c01-4edd-859b-508d5bd30f87}} floor, and headroom has been essentially flat, moving only from {{fact:3e98c2aa-8633-49d2-aabd-d0dbc15fe9a9}} to {{fact:fa2361a3-5325-4b16-8e0d-6b195d6db7c5}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:010427fa-b235-42ab-80e1-a683c95ad969}} against {{fact:521bc423-07d8-4a3c-84cd-f32732f172c2}}), but headroom has fallen steadily from {{fact:ad2be4f3-619a-44ce-bf93-201bda1a8cc7}} to {{fact:45225e4b-83ef-43ad-b713-697e498c2047}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:afad13ea-6042-4219-b584-0f0ad354a4e4}}. Section 6.1 requires at least {{fact:74c98c0f-c0d1-469b-8eb1-2c552035f4e7}}, so the ratio falls short by {{fact:446eaad6-ab95-42f7-a88f-4c02764fb022}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:41f4145e-8687- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:afad13ea-6042-4219-b584-0f0ad354a4e4}}. Section 6.1 requires at least {{fact:74c98c0f-c0d1-469b-8eb1-2c552035f4e7}}, so the ratio falls short by {{fact:446eaad6-ab95-42f7-a88f-4c02764fb022}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:41f4145e-8687- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:afad13ea-6042-4219-b584-0f0ad354a4e4}} against a covenant minimum of {{fact:74c98c0f-c0d1-469b-8eb1-2c552035f4e7}}, leaving headroom of {{fact:446eaad6-ab95-42f7-a88f-4c02764fb022}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:4d3ee8a4-53b7-4a94-9fba-491645a8ca32}} in August to {{fact:b453502b-12f9-4663-9608-df1fcae962a0}} in October, pointing to ongoing cash burn. Cash of {{fact:851bdf19-a325-42cd-a928-232cf91cee0b}} still sits well above the {{fact:98e91c52-4a4d-4b56-9394-06e02262c512}} minimum, so the concern is the trend rather than an imminent breach. No |
| `quillon-ai` | certificate | none | All three covenants are reported in the summary table on page one and agree with the calculation schedule on page two. |
| `quillon-ai` | certificate | none | In the summary table the Revenue to Plan requirement wraps across two lines; it is reported here as one phrase. |
| `quillon-ai` | certificate | none | The summary table header shows the Actual and In compliance column headings overlapping in the rendered page. |
| `quillon-ai` | early_warning | none | Headroom over the minimum cash covenant has narrowed steadily, from {{fact:f0de423b-4d6b-4d14-ae21-dbf6fcb2457a}} in August to {{fact:6a2efed9-5794-48f5-a0d0-463832b5324c}} in September and {{fact:44123986-1098-4723-8d8e-363836666599}} in October. Cash of {{fact:3a5c3c1d-b102-4bea-951a-63cb092e715b}} remains well above the {{fact:643a0dc8-d16f-4f22-8c83-96890930e33a}} floor, but the steady decline |
| `stripple-tech` | intake | none | Raw spreadsheet export of monthly recurring revenue and customer counts with no title, no borrower name and no stated report date; the borrower and period cannot be confirmed from the document itself, and the data shown ends in an earlier year than the other documents in this delivery. |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:c6a1f1dd-865a-4775-bae4-d22cdd42b1cf}} in August to {{fact:55733d8e-e467-4102-8feb-6db4d6b45987}} in October. Cash of {{fact:73530687-3b97-4b98-8a5a-06120eb2c798}} is still well above the {{fact:e1b93aff-ff98-4bd1-997e-df8174ed3186}} minimum, so there is no near-term breach. The steady decline points to ongoing cash burn, and no other |
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:fe94c836-3c70-4246-aada-3ce70c9947dd}} to {{fact:569ade9b-fd66-4940-89c5-406060ffe8d0}} and then sharply to {{fact:4518e17e-7972-4614-abd1-b49c0094b3ea}}. Cash of {{fact:cc387884-302b-4068-b975-12ffb8c19f1f}} against a {{fact:8b6a0df5-b655-4a2f-af1e-267392b35506}} floor is the tightest cushion of the three. The same cash decline is li |
| `tidewell-medical` | early_warning | none | Runway headroom fell from {{fact:96d8597f-c7d2-4b95-9739-32bb0fe2c8fa}} to {{fact:b6ee5fd3-73f7-48c2-bc7b-c22e8d947be1}}, with the steepest drop in October. Runway of {{fact:206f2e5a-a53a-4729-8091-b1cafbf93c03}} months is still well above the {{fact:b20f44b7-e93f-4125-acb0-dadfa732980e}}-month minimum. The decline mirrors the shrinking cash cushion and points to faster burn rather than a separate |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only marginally to {{fact:9c01a2bd-630d-4cc7-b3eb-37efa4aff680}}. Revenue of {{fact:9061f7ea-15be-43b0-861b-1c851c3d9705}} of plan is comfortably above the {{fact:7ce3019b-2290-4ac9-8a07-28d3c29b53c1}} threshold. Because sales are on track, the falling cash and runway look driven by spending or working capital rather than weaker revenue. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:ebacfa1c-c55d-4ad6-a392-3f27335c69d1}} in August to {{fact:13898de4-86f6-4e39-b827-af789481d638}} in September and {{fact:08160a6c-4a63-484e-b3c7-c4f1c8c7fdb7}} at October 31. Cash of {{fact:44d9cf5f-f590-4944-9009-2f88e6ccb633}} remains comfortably above the {{fact:c6450e12-c35e-40d1-907d-f559a2d0471d}} minimum, but the consistent drain ma |

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
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 2 signal(s) were left out of the ranking and were placed after the rest by severity
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
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `quillon-ai`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tessaract-labs`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `veridia-payments`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity


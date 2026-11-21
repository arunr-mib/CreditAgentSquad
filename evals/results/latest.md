# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T08:20:22+00:00; commit `c94f23b65ca5c24a8fb3ac08d15215dbf01eadec`; 20 borrower(s) (whole book); 1 pass(es); run time 213.0 seconds.
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
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:35137185-7ce8-415d-91e2-17d9ec2c48c9}}, or {{fact:7f849ef8-c6ca-4ea8-99e6-ac2df1b9f66a}} of the {{fact:5da0ddc9-8c08-4431-967f-6ae096855397}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:a5bb38f6-ffd8-4c02-afe9-f82d464f4341}} months at July 31 to {{fact:0322424c-bf6b-4303-8812-5939e094af4c}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:b79cf9cf-9b99-49f6-9454-3fddfcbd818b}} in August to {{fact:05818cf0-d361-4011-aeb4-5f858bcc7e8d}} in October, with runway at {{fact:eb77cb11-48c8-4c9a-80a5-e2c8b0a4b283}} months against a floor of {{fact:211db17a-257a-4c4d-ae58-99eefbc73fb9}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:6cd478ae-511b-4767-97e4-83600e7e34b5}} still clears the {{fact:293f580e-2b99-4e00-840d-7e5ed64d4604}} minimum. However, headroom fell from {{fact:dbbfb928-391d-49f4-86b2-45e132931fe2}} to {{fact:9b294630-204d-4d13-9666-350c3e44f414}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `corvane-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `corvane-analytics` | certificate | none | The borrower reports non-compliance with the Revenue to Plan covenant. |
| `corvane-analytics` | certificate | none | On page one the Revenue to Plan requirement wraps across two lines in the table. |
| `corvane-analytics` | certificate | none | No instructions were found in the document text. |
| `corvane-analytics` | covenant | 1, | The Revenue to Plan test fails for the three months ended October 31, 2026. Revenue was {{fact:d3b63286-6a89-4cbc-915b-1b7fb12cfffd}} of the Approved Plan. Section 6.3 requires at least {{fact:93a73ff1-deb8-43a6-8de3-8172e52a4587}}. I reran the test under terms version 1, the only version on file, and it still fails, with headroom of {{fact:2e69c1b1-06f7-48cf-89ac-89e01cc49405}}. The borrower's Oc |
| `corvane-analytics` | early_warning | none | Revenue reached {{fact:98062c80-2b0c-4c86-88a5-00a384279b1e}} of plan against a covenant floor of {{fact:93b640a7-0a41-4339-a67a-7e969fcba7a3}}, so headroom is negative at {{fact:775db410-c6cb-4de3-9181-c097c5050561}}. The covenant measure therefore sits below its threshold, not merely close to it. This is the covenant view of the same shortfall flagged by the revenue-below-plan signal. |
| `corvane-analytics` | early_warning | none | Revenue came in at {{fact:b9a463b1-6114-4fc6-aad3-14cf97c9546d}} of plan, a material miss for a subscription business whose plan underpins its cash runway. It is the operating cause behind the revenue covenant falling below its floor. If the miss persists, it may also explain the steady erosion in cash headroom. |
| `corvane-analytics` | early_warning | none | Unrestricted cash of {{fact:8a8c1d7f-0da1-4401-a445-af1e42630da7}} remains well above the {{fact:55f4a914-74e7-4283-8cf3-970c11f98448}} minimum, but headroom has declined each month, from {{fact:95e707c7-4d6e-40ec-8097-778ef311dec9}} in August to {{fact:d9e92bed-ea1c-48a6-a545-8d9cf2dc40e9}} in September and {{fact:165a42b9-587d-433c-89bc-2a17acb020fb}} in October. Ongoing burn alongside the reven |
| `corvane-analytics` | early_warning | none | Revenue covenant headroom has deteriorated each month, from {{fact:a5257919-0d54-46bb-bef8-a6a8dbff38ec}} in August to {{fact:226a2387-4f51-444c-a3cd-eed278c68c1d}} in September and {{fact:775db410-c6cb-4de3-9181-c097c5050561}} in October. It turned negative in September and the gap widened in October, showing the shortfall is worsening rather than a one-month miss. |
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | covenant | 1 | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:c4b32fc7-0c19-43b1-8663-becf1e74695b}} against a minimum of {{fact:059b2b50-c1ca-4961-97f7-cdcdc04e2229}} ({{fact:e33a7c82-20c4-47d5-8bcd-d401167945b8}} headroom). The certificate reports {{fact:f071f07b-5664-4408-af8f-cfa68eaeceb1}} and claims compliance. Its Schedule 1 reaches that figure by adding the pledged collat |
| `dataflake` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:c4b32fc7-0c19-43b1-8663-becf1e74695b}} against a minimum of {{fact:059b2b50-c1ca-4961-97f7-cdcdc04e2229}} ({{fact:e33a7c82-20c4-47d5-8bcd-d401167945b8}} headroom). The certificate reports {{fact:f071f07b-5664-4408-af8f-cfa68eaeceb1}} and claims compliance. Its covenant schedule reaches that figure by adding the pledged |
| `dataflake` | early_warning | none | Runway stands at {{fact:745083a7-5662-4eb3-ad5e-9bfda58a7856}} months at October 31, so at the current burn the cash on hand would be exhausted in well under a year. This is the core repayment concern, and the cash covenant shortfall and the shrinking runway covenant cushion both point the same way. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:c4b32fc7-0c19-43b1-8663-becf1e74695b}} is below the covenant minimum of {{fact:059b2b50-c1ca-4961-97f7-cdcdc04e2229}}, leaving headroom of {{fact:e33a7c82-20c4-47d5-8bcd-d401167945b8}}. The cushion is not just thin but negative, which reads as the covenant level being crossed. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Cash covenant headroom has fallen steadily, from {{fact:01615826-23b4-46a7-a2f4-096529055e1f}} in August to {{fact:e82a33dd-cba9-4b11-b525-a7b1ec8c669b}} in September and {{fact:e33a7c82-20c4-47d5-8bcd-d401167945b8}} in October. The trend shows the shortfall is a sustained cash drain rather than a one-month dip, which reinforces the runway concern. |
| `dataflake` | early_warning | none | Runway covenant headroom has narrowed from {{fact:7d8a5812-b003-4fa5-b47e-b483f195385b}} in August to {{fact:ceabc4ce-66ef-4099-8a6d-59438e1e5d14}} in September and {{fact:4e772aab-3870-47b8-af01-4e05a62e9cc6}} in October. Runway of {{fact:cbed3551-1e13-4a66-a0b1-4bcdf592ed7f}} months is still above the minimum of {{fact:10fb341a-0da7-4945-9895-7e0af6393ccc}}, but at this pace the cushion could di |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `halcyon-grid` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the Revenue to Plan requirement wraps across two lines in the table. |
| `halcyon-grid` | certificate | none | The summary table header for the actual and compliance columns appears overlapped in the rendering, but row values are legible. |
| `halcyon-grid` | certificate | none | No embedded instructions were found in the document. |
| `halcyon-grid` | early_warning | none | Cash headroom has fallen steadily, from {{fact:af782f9e-c66a-4911-869e-648902541a10}} in August to {{fact:a24e5a9a-a431-428a-a9bb-18fba7e41f5b}} in October, with unrestricted cash of {{fact:92252626-8e4a-488e-9e55-26b7535f1edd}} against a {{fact:631670dc-5694-4985-bdf4-a729caf4c710}} floor. Revenue is running ahead of plan, so the burn seems to come from spending rather than a sales shortfall. If  |
| `halcyon-grid` | early_warning | none | Revenue is at {{fact:35f38096-bd96-47d0-b7f0-b5fc5c385cb2}} of plan against an {{fact:a27235eb-c24f-4ffc-b2dc-1f69bacf2722}} minimum. Headroom has only edged down, from {{fact:a8cf5279-14ac-4e8f-bda0-ae205014dbd3}} to {{fact:577ab7e9-08f9-4863-9d8b-f0bc37f47261}}, which is a minor change. This signal mainly shows that the falling cash position is not explained by weak sales. |
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
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:489eaf6c-1a39-4a9d-aca7-bd197e8283c7}} in August to {{fact:a3176b14-102b-4a6e-824a-b8ff29b2b339}} in October, suggesting steady cash burn. Cash of {{fact:4656e342-82a9-4667-bd8c-e4c4296dfba9}} still sits well above the {{fact:8a291bf2-c97e-4f1e-bfd0-e11052e988f6}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:afc4865f-2a98-4abf-83cd-9c18769f8ba0}} against a maximum of {{fact:73908d0b-e416-4390-8e7a-404aa643d4a6}}, while the certificate reports {{fact:b97284d0-91ad-443e-a7d9-ff929d6d24d8}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:afc4865f-2a98-4abf-83cd-9c18769f8ba0}} against a maximum of {{fact:73908d0b-e416-4390-8e7a-404aa643d4a6}}, while the certificate reports {{fact:b97284d0-91ad-443e-a7d9-ff929d6d24d8}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:9cb22ace-8135-4135-a29e-e9560a210c32}}): total leverage of {{fact:3115e91a-b1c1-48e2-94e4-3a0427117558}} sits above the {{fact:90f89cb0-530b-4868-ba25-cdb2e015eaab}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:1988d592-7225-423a-b692-d6621633ff8f}} is only slightly above the {{fact:84221cfd-6b56-4c1a-88b3-9c3b5f31d88a}} minimum, leaving headroom of {{fact:2572eac5-14b9-4885-b56b-5134010a9959}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:15f45500-e1ea-4011-812b-2f56c2a349d2}} in March to {{fact:205e0f79-bae0-405e-9211-1cc41e03ce72}} in June, then dropped sharply to {{fact:2572eac5-14b9-4885-b56b-5134010a9959}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:eaa400da-c7cb-43c6-9ab9-aeb7c1ba2f57}} in August to {{fact:b8802769-be40-4eb6-b44e-076e327ad557}} in October, suggesting ongoing cash burn. Cash of {{fact:8c22f6a4-cc43-42f5-957d-e53d0e244235}} still sits well above the {{fact:344117f9-66d7-49ee-b609-719c22b9714d}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:98b6ef6d-b5ad-4fc1-8f3e-1b7c0b9cb3ef}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:f346a5be-c68f-446e-bfb8-c441c4178264}} in August to {{fact:a0543faa-a2eb-4ca4-b459-8c9b2b07d8d2}} in October, with runway at {{fact:a2d665b8-e777-4e64-a747-1514b99cdd18}} months against a floor of {{fact:b6a80f6e-d52e-4ba4-9c50-8e40b0787aa2}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:ee2bad2c-a54d-4ff0-a87e-63d3c2482e6f}} remains above the {{fact:12601756-43fc-48bc-9d66-0572ce60a92d}} minimum, but headroom dropped from {{fact:f1f5272e-161f-4e1e-b1fe-3f31549e6ac3}} in August to {{fact:c5923c39-ccff-4aed-850a-8ec42cb88303}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:ec43ff3f-d199-4dab-8cd7-30de04945194}} of plan against an {{fact:d812f97f-2e16-426b-9be8-9c71fec22e49}} floor, and headroom has been essentially flat, moving only from {{fact:5d6afd99-f02a-4aa9-9aca-d683254eee03}} to {{fact:c575ab0b-f94e-4d37-a948-2ccfeb22c362}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:1b18cc45-732f-4cdb-91ed-fe8b0888b512}} against {{fact:f84216a3-6dc6-4f42-b916-c14939b6ff8b}}), but headroom has fallen steadily from {{fact:cdc9ef9d-3b17-4db5-9c9c-b29a7f61e542}} to {{fact:dc91b56f-8344-48f4-8e74-00ca33b8cd9e}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:ffd5e349-6be2-476e-b49f-9a6628a050b9}}. Section 6.1 requires at least {{fact:a62f37f3-c480-4682-bb1d-d111105132c8}}, so the ratio falls short by {{fact:644e74bf-3530-4ed5-bfca-ca70ef93d245}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:f30e35f2-558b- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:ffd5e349-6be2-476e-b49f-9a6628a050b9}}. Section 6.1 requires at least {{fact:a62f37f3-c480-4682-bb1d-d111105132c8}}, so the ratio falls short by {{fact:644e74bf-3530-4ed5-bfca-ca70ef93d245}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:f30e35f2-558b- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:ffd5e349-6be2-476e-b49f-9a6628a050b9}} against a covenant minimum of {{fact:a62f37f3-c480-4682-bb1d-d111105132c8}}, leaving headroom of {{fact:644e74bf-3530-4ed5-bfca-ca70ef93d245}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:e3632feb-cb54-451b-9bdb-78a2f16bc082}} in August to {{fact:142b2b2d-035b-4cc3-aa6b-140a5aa101bc}} in October, pointing to ongoing cash burn. Cash of {{fact:6b2eeb68-c409-47e6-8eb5-246e37b3d632}} still sits well above the {{fact:ce35aec7-cdc3-46b6-8cdd-038f371c6443}} minimum, so the concern is the trend rather than an imminent breach. No |
| `quillon-ai` | certificate | none | All three covenants are reported in the summary table on page one and agree with the calculation schedule on page two. |
| `quillon-ai` | certificate | none | In the summary table the Revenue to Plan requirement wraps across two lines; it is reported here as one phrase. |
| `quillon-ai` | certificate | none | The summary table header shows the Actual and In compliance column headings overlapping in the rendered page. |
| `quillon-ai` | early_warning | none | Headroom over the minimum cash covenant has narrowed steadily, from {{fact:e771b061-767b-4c4d-a088-2f9d409c70b6}} in August to {{fact:c4f7d9e4-8944-4858-b030-a411c1f7b552}} in September and {{fact:ea043f55-d22e-4939-81e9-95ee84e65778}} in October. Cash of {{fact:e40c55b6-82af-4852-b20e-bbeb6a2fcb20}} remains well above the {{fact:cad66783-7aa6-49bb-80b9-08521a8d2a0c}} floor, but the steady decline |
| `stripple-tech` | intake | none | Raw spreadsheet export of monthly recurring revenue and customer counts with no title, no borrower name and no stated report date; the borrower and period cannot be confirmed from the document itself, and the data shown ends in an earlier year than the other documents in this delivery. |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:dc77bd2b-23be-4773-b72f-45578f5d3f6b}} in August to {{fact:58bb6deb-f4ab-45ad-a1a2-b70c04b9e394}} in October. Cash of {{fact:2409d294-b1b6-4ea2-8ba5-79ee164c35f5}} is still well above the {{fact:0feb8bac-9955-4d02-a9aa-872a3963bded}} minimum, so there is no near-term breach. The steady decline points to ongoing cash burn, and no other |
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:db43268c-e430-47ac-8daa-46cb9b99d2d7}} to {{fact:b219d489-7fca-458a-b935-5748d6d37364}} and then sharply to {{fact:d4927939-39e2-47c2-b515-613eb65e99af}}. Cash of {{fact:00b543fe-a4f3-4349-8181-0ccedf75c504}} against a {{fact:cccf7dac-b9f2-48e7-be2c-2357f9619ac5}} floor is the tightest cushion of the three. The same cash decline is li |
| `tidewell-medical` | early_warning | none | Runway headroom fell from {{fact:62eaff34-961b-4a61-a208-4b54109b4f58}} to {{fact:65901f6a-f928-4d24-b759-f1a1c5b519b5}}, with the steepest drop in October. Runway of {{fact:e51748ff-eb47-4667-b2e2-2d271fcaba3c}} months is still well above the {{fact:d4f2130d-353c-4735-b30c-6f7257999072}}-month minimum. The decline mirrors the shrinking cash cushion and points to faster burn rather than a separate |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only marginally to {{fact:e05442a5-98a5-4e2b-be4a-c73d6b580650}}. Revenue of {{fact:c1e7f767-bc23-4349-b7d8-87149471d9fb}} of plan is comfortably above the {{fact:7fbc6908-d30a-455c-bd6e-115a1e39c0e4}} threshold. Because sales are on track, the falling cash and runway look driven by spending or working capital rather than weaker revenue. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:1cb10dc3-2cb2-4944-9d64-45f59a3282a2}} in August to {{fact:1e020789-ce20-4f0b-9c83-92dda9d9d825}} in September and {{fact:70381ede-77fa-4333-8a3e-6b5f54cdf43e}} at October 31. Cash of {{fact:434be0cd-5abc-489f-9844-3b2a8a55b2d5}} remains comfortably above the {{fact:166460e2-f635-4b42-85fb-72b53dfb9730}} minimum, but the consistent drain ma |

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


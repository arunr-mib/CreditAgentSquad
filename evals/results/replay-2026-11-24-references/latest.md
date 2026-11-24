# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-24T07:02:59+00:00; commit `4fcb4e17b17d90343d39b90afde6e82abe063317`; 20 borrower(s) (whole book); 1 pass(es); run time 185.9 seconds.
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
| Model tokens in / out | 818,381 / 217,135 |

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
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `calvere-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `cindrel-tech` | cindrel_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `datamarrow` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | none |
| `meridew-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tarnavi-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tavernel-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `vantrell-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `cindrel-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `brackmere-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager |
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `calvere-health` | awaiting_package | intake.missing_document | none (left open) |
| `cindrel-tech` | intake | intake.unclassified | intake.unclassified: not_needed by analyst |
| `cindrel-tech` | spreading | spread.value_unverified | none (left open) |
| `datamarrow` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `datamarrow` | signals | signal.high | signal.high: acknowledged by analyst |
| `datamarrow` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `meridew-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `meridew-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tarnavi-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tavernel-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `vantrell-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

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
| `brackmere-medical` | early_warning | none | Unrestricted cash headroom slipped from {{fact:a3d0e194-a526-423b-91f0-d55a79a82027}} to {{fact:3447f356-d592-4d39-9f91-2b466195303e}}, then fell sharply to {{fact:666f2988-4ebf-409b-97d2-ac3a7bc6d52a}} in October. Cash of {{fact:09948538-db08-4960-837f-59532f5f057d}} still clears the {{fact:66e1ee75-fb3f-4851-98de-2147f35798b7}} floor. The runway decline points the same way, suggesting cash burn  |
| `brackmere-medical` | early_warning | none | Runway headroom fell from {{fact:9f46aff8-8968-46b1-80f6-bdebc7c2cd8b}} to {{fact:e5f62384-bf10-4a18-893d-aa5a7749d928}} and then to {{fact:5860a7af-d79c-4574-a429-23f10fea9e28}}, with the steepest drop in October. Runway of {{fact:ea8699fd-880f-4177-ab6d-22c362f9d013}} months is still well above the {{fact:abcf8b09-54ce-4f5f-9734-1f5978e61a82}}-month minimum. The October drop mirrors the falling  |
| `brackmere-medical` | early_warning | none | Revenue headroom has been essentially flat, at {{fact:925d5f13-2073-4bbd-b01b-3123404c3316}}, {{fact:78ea640f-e57d-4d5b-97fa-ea552e0608d3}} and {{fact:aa2b52be-89f0-4729-8612-bc6385be27f0}}. Revenue is running at {{fact:3c051479-e52f-4317-a194-8aab701e2307}} of plan against an {{fact:429cd941-f106-4fca-a68c-753407e52829}} floor. This suggests the cash and runway declines stem from spending or work |
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:c244df5e-5b58-4656-a12b-69fa0bf37457}}, or {{fact:00873a24-5d08-487e-91e5-16fc4901c228}} of the {{fact:c79bf085-1c70-4ac9-adb8-ba80edaec75e}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:942cb838-3351-41e6-8fc9-38ad5541f913}} months at July 31 to {{fact:34b89224-9e26-47de-8915-ec2c30fabe3a}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:79095fac-104d-4aaf-a2f6-a7da7ab50da5}} in August to {{fact:f8166472-27e5-4795-b344-221d6696da55}} in October, with runway at {{fact:9c71f222-e969-4e46-a3d8-578f4947a34d}} months against a floor of {{fact:2b972b26-bb8e-43cc-af69-10b6f90cc030}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:93618f13-a859-4c2d-b818-0c761e2743dc}} still clears the {{fact:c9a62e0f-5c8b-4802-89a6-4d59956198d2}} minimum. However, headroom fell from {{fact:c914fb9a-09ca-4d4f-ad89-518cc5b15e65}} to {{fact:3ef795e6-2798-4464-a59d-5f6e15c04324}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `cindrel-tech` | intake | none | Untitled spreadsheet export of monthly recurring revenue and customer counts with no borrower name, no title and no report date; it covers months in the prior year rather than the current period, so it cannot be confirmed as a borrower MRR report and needs a person to review. |
| `datamarrow` | certificate | none | On page one the Revenue to Plan requirement text wraps across two lines in the summary table. |
| `datamarrow` | certificate | none | Schedule 1 shows Unrestricted Cash built up by including cash held in the pledged collateral account; the credit team may wish to review whether pledged cash qualifies as unrestricted. |
| `datamarrow` | certificate | none | No instructions addressed to the reader were found in the document. |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:6146fce8-6828-45e8-8d09-520a933d9a5f}} against a minimum of {{fact:f6d827f0-e9d2-44ca-bb69-b9e1138d06ca}}, a headroom of {{fact:c805c23f-be8c-4aa8-88e2-6cd4a3745a93}}. The borrower certified {{fact:2917bbbd-a5ea-4095-8725-da43f739f2ea}} and reported compliance. The certificate's schedule reaches that figure by adding t |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:6146fce8-6828-45e8-8d09-520a933d9a5f}} against a minimum of {{fact:f6d827f0-e9d2-44ca-bb69-b9e1138d06ca}} (headroom {{fact:c805c23f-be8c-4aa8-88e2-6cd4a3745a93}}). The borrower certified {{fact:2917bbbd-a5ea-4095-8725-da43f739f2ea}} and compliance. Its schedule adds the pledged collateral account to operating-account c |
| `datamarrow` | early_warning | none | At current burn, Datamarrow's cash covers about {{fact:8f300210-8c4b-43bf-9cc0-804bcd2748fa}} months of operations, short enough that its ability to keep paying depends on new funding or cost cuts arriving soon. The falling runway covenant headroom and the cash covenant now below its minimum point the same way. |
| `datamarrow` | early_warning | none | Negative headroom means unrestricted cash of {{fact:8a2dd349-b6e5-41ab-b6be-05954633108a}} is below the covenant minimum of {{fact:f02ef0d7-f49b-4879-8c50-3da80f1f8d73}}, so on these figures the covenant appears breached at October 31, not merely tight. Together with the short runway, this shows the cash cushion has run out ahead of the borrower's funding needs. |
| `datamarrow` | early_warning | none | Cash covenant headroom slid from {{fact:58788de3-1f23-4c5a-b9b3-f70319889371}} in August to {{fact:f7b3092c-8a02-4a1e-8166-76961836cda5}} in September and {{fact:3715b198-c83d-4976-a358-475f45a8c0f3}} in October. The steady decline shows the breach is the result of continued burn rather than a one-off dip, which makes a quick recovery less likely without new cash. |
| `datamarrow` | early_warning | none | Runway covenant headroom fell from {{fact:9119883a-3477-4266-90d4-501683a7d484}} in August to {{fact:59550f11-9b7d-499d-96dd-e704fa1f8ab2}} in September and {{fact:29b15a39-9b32-4a02-addb-4aa9e5516240}} in October, with runway of {{fact:0b76f42f-c135-46ee-833e-5b635a156b4d}} months against a minimum of {{fact:4f5a1d78-edc8-4b67-8e12-c2cea7c2e95a}}. The covenant still passes, but if the pace contin |
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
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:62a692b2-4feb-4883-8cf9-a0f74bb69606}} in August to {{fact:26b86bef-1c9a-41f4-bf49-1bd2a56db0c1}} in October, suggesting steady cash burn. Cash of {{fact:782079ca-a1fc-4a58-87cd-6e961961ee95}} still sits well above the {{fact:1941374e-e785-4ccc-a172-c9181aac3678}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:6c64c6af-9d31-495c-834b-a3e4598b8214}} against a maximum of {{fact:3489f876-708a-41af-8dd3-d7e2bba7a6cf}}, while the certificate reports {{fact:c024d5d7-8ac5-488d-a112-ad6dd7239fc0}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:6c64c6af-9d31-495c-834b-a3e4598b8214}} against a maximum of {{fact:3489f876-708a-41af-8dd3-d7e2bba7a6cf}}, while the certificate reports {{fact:c024d5d7-8ac5-488d-a112-ad6dd7239fc0}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:8ebd8a79-e94a-48be-ba62-7c22210c368e}}): total leverage of {{fact:bff7a429-42e0-4ec3-b6d8-bf4d5ed7908a}} sits above the {{fact:bc5ed241-5955-4b57-828a-9e55367bbb3c}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:5827c54c-d223-4433-9da6-f42e19574a9b}} is only slightly above the {{fact:0ff32e60-18ef-4f79-b8d1-6cce73cb9aef}} minimum, leaving headroom of {{fact:f46dc689-fdec-4d08-9134-e8c793275314}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:147ad3d0-bd4b-4f1f-ac66-22922756c6d9}} in March to {{fact:7f7c43b8-80aa-453c-9c59-42d0426ab884}} in June, then dropped sharply to {{fact:f46dc689-fdec-4d08-9134-e8c793275314}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `meridew-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `meridew-analytics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `meridew-analytics` | certificate | none | The borrower reports non-compliance with Revenue to Plan. |
| `meridew-analytics` | covenant | 1, 1 | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:5cedbc4e-c921-4d52-9089-0b6173a9d3b7}} of the Approved Plan, below the required minimum of {{fact:fab6c434-829a-414b-9b21-82efccc7f846}}. The borrower's October certificate reports the same figure, {{fact:7043f3c1-fb85-4781-a705-abe866afa2d8}}, and states it was not in compliance. Approved terms ver |
| `meridew-analytics` | covenant | none | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:5cedbc4e-c921-4d52-9089-0b6173a9d3b7}} of the Approved Plan, below the required minimum of {{fact:fab6c434-829a-414b-9b21-82efccc7f846}}. The borrower's October certificate reports the same figure, {{fact:7043f3c1-fb85-4781-a705-abe866afa2d8}}, and states it was not in compliance. The approved terms |
| `meridew-analytics` | early_warning | none | Revenue reached {{fact:5cedbc4e-c921-4d52-9089-0b6173a9d3b7}} of plan against a covenant floor of {{fact:fab6c434-829a-414b-9b21-82efccc7f846}}. That leaves headroom of {{fact:c6096120-13ce-475a-9a3c-4e094325bc77}}, so the covenant level is not being met rather than merely close. The revenue-below-plan and falling-headroom signals describe the same shortfall. |
| `meridew-analytics` | early_warning | none | Revenue came in at {{fact:4a4f0bb9-3a15-4347-8b3a-418c7d837422}} of plan. For a SaaS borrower, that points to weaker bookings, churn or delayed renewals. This is the operating cause behind the revenue covenant shortfall, and it may also explain the steady erosion in cash headroom. |
| `meridew-analytics` | early_warning | none | Revenue covenant headroom has slid each month: from {{fact:a3d32892-415e-4ce2-a815-1e48301ef46b}} in August, to {{fact:9d7c8bcf-02d3-4c27-be80-968f759493fb}} in September, to {{fact:c6096120-13ce-475a-9a3c-4e094325bc77}} in October. The shortfall began in September and deepened in October, so it is a worsening trend rather than a one-month miss. |
| `meridew-analytics` | early_warning | none | Unrestricted cash of {{fact:05898ae8-c3b4-4ddc-8d29-7e1f05777a3a}} remains comfortably above the {{fact:c2862161-e6bf-4c1d-8148-0fd47e025235}} minimum. However, headroom has declined steadily, from {{fact:00990abf-473d-4ab5-b4ca-1208c0ed0a27}} to {{fact:3d5c18ef-2671-4f3b-beab-7a8b3d8f5831}} to {{fact:58b78aa2-6632-4582-a3c7-c4fe8e4f7576}}. Taken together with the revenue shortfall, this suggests  |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:9c6c0589-99a4-45dd-a2ed-14bd8238ae7e}} in August to {{fact:4999f1b2-5c4c-4487-9f8a-1384026257dc}} in October, suggesting ongoing cash burn. Cash of {{fact:b19b94e8-8bb7-49f7-84b1-4fc86823840f}} still sits well above the {{fact:ee38ae96-29f0-4f9f-8765-15b2194459aa}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:c0c49073-3b83-4e35-a75b-56e02a934cc8}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:19776cbb-f0a8-42b7-92f7-a93431c9ed61}} in August to {{fact:1e34a1f1-447b-40d2-b415-0c80392ffae7}} in October, with runway at {{fact:ce81bb98-2209-4c61-b049-26186a7ad6a4}} months against a floor of {{fact:616cde65-ef57-4485-bfea-199f24a92914}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:bb2a117e-ce1a-4107-9b98-213f80afb8c8}} remains above the {{fact:734c3e5f-7179-4502-873d-5a8f98141e04}} minimum, but headroom dropped from {{fact:d3c3a18f-e9bd-49b9-bf52-1b3585a53b58}} in August to {{fact:7cfa612e-93f0-4dfb-9b32-c7576e4086b9}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:fef4de87-cbed-4a3b-8539-1e0963b00572}} of plan against an {{fact:f232ef94-9df6-411d-89af-6cd2e20f6e06}} floor, and headroom has been essentially flat, moving only from {{fact:f4a86baf-b6bb-445d-b490-6ad51a1d20ed}} to {{fact:183ddf63-85f1-4655-a792-5ad3c4ccf4b0}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:ab20eb23-4abb-4d3c-9a8e-cc6fcaf06e8b}} against {{fact:32869481-8084-4053-961d-cbf744d68f15}}), but headroom has fallen steadily from {{fact:9c0425cc-78e4-4445-a732-283f881f960c}} to {{fact:cb3bf224-b65b-4dbe-bf91-ae32919477bd}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:b065cbd9-62a7-48e7-b799-668890c976fd}}. Section 6.1 requires at least {{fact:4b3ef350-fa0f-47f9-a98c-7ff05464817a}}, so the ratio falls short by {{fact:3477d52c-85fb-4c77-9943-4f7b497f2e4b}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:d9ff0062-5ff3- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:b065cbd9-62a7-48e7-b799-668890c976fd}}. Section 6.1 requires at least {{fact:4b3ef350-fa0f-47f9-a98c-7ff05464817a}}, so the ratio falls short by {{fact:3477d52c-85fb-4c77-9943-4f7b497f2e4b}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:d9ff0062-5ff3- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:b065cbd9-62a7-48e7-b799-668890c976fd}} against a covenant minimum of {{fact:4b3ef350-fa0f-47f9-a98c-7ff05464817a}}, leaving headroom of {{fact:3477d52c-85fb-4c77-9943-4f7b497f2e4b}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:288b4d3d-a9b4-4d95-929f-78712aca7e6c}} in August to {{fact:4e6a6fb7-f3b1-4439-bc62-520d58c24302}} in October, pointing to ongoing cash burn. Cash of {{fact:95fd8827-2a62-4bfe-b0cd-b735437bddf4}} still sits well above the {{fact:994a6e5a-6c5d-4ea1-95f9-affc2d39fdba}} minimum, so the concern is the trend rather than an imminent breach. No |
| `tarnavi-ai` | certificate | none | All three covenants are reported in the page one summary table and match the calculation schedule on page two. |
| `tarnavi-ai` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tarnavi-ai` | early_warning | none | Unrestricted cash still sits well above the covenant minimum ({{fact:6ddd7fb6-ec9a-45f8-991f-1d7782d2b102}} against {{fact:8874b80b-10d7-46e2-ad9f-ecfa6714323c}}). However, headroom has shrunk steadily, from {{fact:b3a3ffa9-84f8-44e2-a325-e9fdb9fe8191}} in August to {{fact:4bf73f26-9a32-4387-ac95-68be10d51716}} in October, which suggests ongoing cash burn. No other signal fired, so this trend stan |
| `tavernel-grid` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `tavernel-grid` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tavernel-grid` | early_warning | none | Cash headroom has shrunk steadily, from {{fact:714363a5-9135-4118-9750-4cec753c6020}} in August to {{fact:60fa7f0a-69db-4ca6-95dd-f3e1ce4d8f59}} in October, with cash at {{fact:d941b826-4a9d-4222-82f4-e9de82a963ad}} against a {{fact:fcf3ad38-1788-4908-a7a3-c86fa15d5772}} floor. The cushion is still comfortable, but the pace of decline matters. Revenue is running ahead of plan, so the cash drain li |
| `tavernel-grid` | early_warning | none | Headroom slipped only marginally, from {{fact:2b6d280e-e3ec-4ae9-b91d-df299de78cdc}} to {{fact:8f371b33-14f7-472a-8a00-751d751fca5f}}, and revenue sits at {{fact:2bfae7a8-5a7f-495e-93da-93a2b8ba94b9}} of plan versus a {{fact:a5f03694-364a-409f-9f1b-ece4d0fa0097}} minimum. This is close to flat and does not explain the falling cash balance. |
| `vantrell-labs` | certificate | none | All three covenants are reported in the summary table on page one and in Schedule 1 on page two. |
| `vantrell-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `vantrell-labs` | certificate | none | No embedded instructions were found in the document. |
| `vantrell-labs` | early_warning | none | Cushion over the minimum cash covenant has narrowed steadily, from {{fact:21ad5c66-e375-4ff5-b7c9-6dc3280d02f5}} in August to {{fact:b8564934-4642-4474-ad7a-dab30b718ba7}} in September and {{fact:c74ad4e9-095d-419f-aca8-93ac016841af}} in October. Cash of {{fact:4c43eddb-3802-47de-be23-b63003983df3}} still sits well above the {{fact:880c8e5c-09e5-4b11-9af2-fb6515e2a280}} floor, so the concern is th |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:d2deb766-423f-42b5-ad19-7e3462debb80}} in August to {{fact:7cbeca9b-51c4-4919-a096-d1cf9a208b46}} in September and {{fact:cd39caa7-b036-4452-ae48-c7481110cdc5}} at October 31. Cash of {{fact:869d99e6-92fe-4157-be80-91356bc7cc39}} remains comfortably above the {{fact:c23a227a-0df5-4950-896d-518d4a41a6fe}} minimum, but the consistent drain ma |

## Observations

- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brackmere-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brackmere-medical`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
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
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `datamarrow`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `datamarrow`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kelvra-bio`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `meridew-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `meridew-analytics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `meridew-analytics`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact
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
- `tarnavi-ai`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tarnavi-ai`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tarnavi-ai`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tavernel-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tavernel-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tavernel-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tavernel-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tavernel-grid`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 2 signal(s) were left out of the ranking and were placed after the rest by severity
- `vantrell-labs`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `vantrell-labs`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `vantrell-labs`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `veridia-payments`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity


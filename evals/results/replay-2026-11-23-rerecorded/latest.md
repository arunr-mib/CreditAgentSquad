# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-24T00:02:55+00:00; commit `9f0b401a44be878cf0089a52c9c473b8c740102a`; 20 borrower(s) (whole book); 1 pass(es); run time 200.7 seconds.
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
| wrong-abstain | 1 |
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
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |
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

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |

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
| `brackmere-medical` | early_warning | none | Unrestricted cash headroom slipped from {{fact:4bb1b345-41a8-4409-bc2b-bb50f783826e}} to {{fact:993d7db7-40ce-45f2-94b2-044e09bea366}}, then fell sharply to {{fact:d1ef9393-9302-40bd-b7f7-b22cb9eb2124}} in October. Cash of {{fact:0eadb2c5-0f00-4d79-87d0-425a25988073}} still clears the {{fact:e38f48f2-5cb6-4b7a-822d-3c80bff25cff}} floor. The runway decline points the same way, suggesting cash burn  |
| `brackmere-medical` | early_warning | none | Runway headroom fell from {{fact:f9c799e0-4a85-43ce-bce8-fee23168602d}} to {{fact:3d924bd1-fd16-4532-bebe-0ecf30659012}} and then to {{fact:ac91ee50-2ac7-484a-8dc5-7611a96eb5e9}}, with the steepest drop in October. Runway of {{fact:7dbbb81f-8207-4aa9-9ae8-afb259d249dd}} months is still well above the {{fact:c17f3f4e-210b-44b7-a66c-e811083fedee}}-month minimum. The October drop mirrors the falling  |
| `brackmere-medical` | early_warning | none | Revenue headroom has been essentially flat, at {{fact:007d99a4-e41c-49a3-bed1-1381f5290125}}, {{fact:36de1655-c798-424a-90a6-ee5c356fa1b0}} and {{fact:d9e70069-35b2-4c21-a5c5-64b0d4f01d32}}. Revenue is running at {{fact:d9c3b554-45db-4147-a957-92f7577bd015}} of plan against an {{fact:82dd0d63-b3fe-455c-be96-6900f006fd51}} floor. This suggests the cash and runway declines stem from spending or work |
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:5c80fdd2-c8e1-499d-b0aa-ca3cbebeee6e}}, or {{fact:6df56d75-f021-4e84-805d-5d89d35c167a}} of the {{fact:5fcd2302-01e2-43cb-87d5-4ce3a554183c}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:4220af42-6094-41ef-b8f3-c9208bcebc9c}} months at July 31 to {{fact:942f4ce0-c9c2-4302-a74a-41608d76bad1}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:6e8347e7-28a7-401e-8e4b-1e803fa0c4f3}} in August to {{fact:77bfc437-ca90-43a0-938e-9e86a8101eab}} in October, with runway at {{fact:b8ae9c78-6ee1-41aa-963e-714d7ad062d6}} months against a floor of {{fact:536c1240-6656-49b4-96a9-44c1780fe136}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:b45935e7-d1f8-41f6-9ca9-531487a16bcc}} still clears the {{fact:0b059a7e-05d9-44ff-907e-8f47104de06f}} minimum. However, headroom fell from {{fact:15c8e486-36e7-40cf-9b96-7f5107f20206}} to {{fact:c35dbf2b-70d3-49a6-876b-7b2013402f76}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `cindrel-tech` | intake | none | Untitled spreadsheet export of monthly recurring revenue and customer counts with no borrower name, no title and no report date; it covers months in the prior year rather than the current period, so it cannot be confirmed as a borrower MRR report and needs a person to review. |
| `datamarrow` | certificate | none | On page one the Revenue to Plan requirement text wraps across two lines in the summary table. |
| `datamarrow` | certificate | none | Schedule 1 shows Unrestricted Cash built up by including cash held in the pledged collateral account; the credit team may wish to review whether pledged cash qualifies as unrestricted. |
| `datamarrow` | certificate | none | No instructions addressed to the reader were found in the document. |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:d8eed07a-fe09-4c90-b1dd-219e3e4abfe7}} against a minimum of {{fact:b942e837-bf21-4a8e-8028-565c1775690f}}, a headroom of {{fact:993d32b1-5c17-4913-9149-c72db8310315}}. The borrower certified {{fact:59eeafb6-086c-427d-a646-f17f7b766bcf}} and reported compliance. The certificate's schedule reaches that figure by adding t |
| `datamarrow` | covenant | none | Minimum Unrestricted Cash at October 31, 2026 fails. The bank calculated {{fact:d8eed07a-fe09-4c90-b1dd-219e3e4abfe7}} against a minimum of {{fact:b942e837-bf21-4a8e-8028-565c1775690f}} (headroom {{fact:993d32b1-5c17-4913-9149-c72db8310315}}). The borrower certified {{fact:59eeafb6-086c-427d-a646-f17f7b766bcf}} and compliance. Its schedule adds the pledged collateral account to operating-account c |
| `datamarrow` | early_warning | none | At current burn, Datamarrow's cash covers about {{fact:39cd960d-1e4d-4b49-8a37-6fe8b428b804}} months of operations, short enough that its ability to keep paying depends on new funding or cost cuts arriving soon. The falling runway covenant headroom and the cash covenant now below its minimum point the same way. |
| `datamarrow` | early_warning | none | Negative headroom means unrestricted cash of {{fact:1ca25872-b68b-4615-8cad-a6ff9b27007a}} is below the covenant minimum of {{fact:2d6abd8b-19e1-43ca-b93c-1ce59b8a4d23}}, so on these figures the covenant appears breached at October 31, not merely tight. Together with the short runway, this shows the cash cushion has run out ahead of the borrower's funding needs. |
| `datamarrow` | early_warning | none | Cash covenant headroom slid from {{fact:68c7573b-94b4-4368-b045-3672a805bb0e}} in August to {{fact:fc8b4555-669d-4d39-b047-81dedb4158b5}} in September and {{fact:718155d4-0033-4220-adda-f80f4402b7bd}} in October. The steady decline shows the breach is the result of continued burn rather than a one-off dip, which makes a quick recovery less likely without new cash. |
| `datamarrow` | early_warning | none | Runway covenant headroom fell from {{fact:5ff6f104-4911-49ce-af4f-f5199d4555eb}} in August to {{fact:976f6239-fa0e-43b6-ac31-63ea2c4a0b6b}} in September and {{fact:1c193dab-9bb0-42ac-8c21-e919dca205b6}} in October, with runway of {{fact:bfbb7274-6b98-4fb6-9a28-1ce0b5d65c89}} months against a minimum of {{fact:f9fef95c-0f1c-4181-ac5c-18602b304a69}}. The covenant still passes, but if the pace contin |
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
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:e622f9e0-d7c3-478b-823c-819a307f0750}} in August to {{fact:e194bda1-bfc8-409b-9f7d-f165638e39bc}} in October, suggesting steady cash burn. Cash of {{fact:d0e2b579-8221-48ee-830e-5c80f53e7540}} still sits well above the {{fact:5cae4283-be36-4789-9fc8-8f864376a2b6}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | covenant | 1) | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:dcf322c6-64df-44da-a5fc-1ba194d0737b}} against a maximum of {{fact:bc623526-af94-4eaf-911b-ee4393569582}}, while the certificate reports {{fact:6cd045ab-1df4-412f-a57d-f2dc2373399a}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | covenant | none | The Total Leverage Ratio for the period ended September 30, 2026 tests at {{fact:dcf322c6-64df-44da-a5fc-1ba194d0737b}} against a maximum of {{fact:bc623526-af94-4eaf-911b-ee4393569582}}, while the certificate reports {{fact:6cd045ab-1df4-412f-a57d-f2dc2373399a}} and compliance. In Schedule 1 of the certificate, the borrower's Total Debt and EBITDA components match the bank's inputs. The gap comes |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:764a92cf-9626-43b5-b366-c41653c1f31a}}): total leverage of {{fact:d4cfc63b-d45e-4f84-9161-ce6b495d8ecc}} sits above the {{fact:253f8e31-2bdd-4820-9f85-b931788368e6}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:201dae6f-538d-45a0-99de-94f3e5ad8bd1}} is only slightly above the {{fact:47b5f29a-0be2-4869-9248-f2a1003d14b6}} minimum, leaving headroom of {{fact:81fb0c74-0edc-4df7-9291-9d573d49fcf7}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:2e60f524-88ab-4428-b7d0-db6ad05056ff}} in March to {{fact:9deedd19-1f7c-4974-8a54-5eed1d691efa}} in June, then dropped sharply to {{fact:81fb0c74-0edc-4df7-9291-9d573d49fcf7}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `meridew-analytics` | spreading | 2, 4 | The one-month columns on pages 2 to 4 were not spread. |
| `meridew-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `meridew-analytics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `meridew-analytics` | certificate | none | The borrower reports non-compliance with Revenue to Plan. |
| `meridew-analytics` | covenant | 1, 1 | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:1ae51c05-838d-47e5-925d-9289f773a3dc}} of the Approved Plan, below the required minimum of {{fact:919f6135-7d12-4a0c-bbc5-7c11cd97d76b}}. The borrower's October certificate reports the same figure, {{fact:9a3b79be-12d8-4229-a1ea-e0ac067ffba4}}, and states it was not in compliance. Approved terms ver |
| `meridew-analytics` | covenant | none | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:1ae51c05-838d-47e5-925d-9289f773a3dc}} of the Approved Plan, below the required minimum of {{fact:919f6135-7d12-4a0c-bbc5-7c11cd97d76b}}. The borrower's October certificate reports the same figure, {{fact:9a3b79be-12d8-4229-a1ea-e0ac067ffba4}}, and states it was not in compliance. The approved terms |
| `meridew-analytics` | early_warning | none | Revenue reached {{fact:1ae51c05-838d-47e5-925d-9289f773a3dc}} of plan against a covenant floor of {{fact:919f6135-7d12-4a0c-bbc5-7c11cd97d76b}}. That leaves headroom of {{fact:d50a7c5f-1e10-4846-be85-3ac7a5a6d597}}, so the covenant level is not being met rather than merely close. The revenue-below-plan and falling-headroom signals describe the same shortfall. |
| `meridew-analytics` | early_warning | none | Revenue came in at {{fact:a286b401-024e-4cc2-8f5d-662798b9f663}} of plan. For a SaaS borrower, that points to weaker bookings, churn or delayed renewals. This is the operating cause behind the revenue covenant shortfall, and it may also explain the steady erosion in cash headroom. |
| `meridew-analytics` | early_warning | none | Revenue covenant headroom has slid each month: from {{fact:e63b6553-cfd0-45ee-b2a0-759a658188bd}} in August, to {{fact:8331a11d-1df5-4864-8eb8-d7fe462758a9}} in September, to {{fact:d50a7c5f-1e10-4846-be85-3ac7a5a6d597}} in October. The shortfall began in September and deepened in October, so it is a worsening trend rather than a one-month miss. |
| `meridew-analytics` | early_warning | none | Unrestricted cash of {{fact:e57996c6-39ee-4997-b87e-3f632120656b}} remains comfortably above the {{fact:9a7ad1f6-5139-4cec-8960-84b27e6acc3c}} minimum. However, headroom has declined steadily, from {{fact:7e72be46-25b7-497d-8f12-302c09a00e97}} to {{fact:bfc0e8c6-ff31-4c80-bfcf-c28825523d2d}} to {{fact:872690e9-3d86-407e-8992-6d748f75d8a3}}. Taken together with the revenue shortfall, this suggests  |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:06b06d8a-b5d1-42ec-b12e-3f7990b52de0}} in August to {{fact:24ccf217-08f2-4b85-95e4-c0a91d6883d3}} in October, suggesting ongoing cash burn. Cash of {{fact:83c9cb7f-8ca3-4082-ae50-a0114abc16a1}} still sits well above the {{fact:e5358a85-331d-4a37-a2ae-513474f823d0}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:8d01a2ad-76c5-4f49-8fa0-a732068d94df}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:aeaf7b4e-5abe-418d-affd-6908efaa8a75}} in August to {{fact:33b30385-3fce-4f7a-bf9e-229444d468fe}} in October, with runway at {{fact:b9ab274e-40f8-43c2-b19b-00d58fc8cefd}} months against a floor of {{fact:f9171996-e730-4413-962d-602defd3308d}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:f688237e-da7d-4c4a-be30-7741ae4cefcd}} remains above the {{fact:acf1ffda-3115-42be-9ef6-2c6a57e91285}} minimum, but headroom dropped from {{fact:6be68939-9099-4c46-bd15-d6896dfb9a4e}} in August to {{fact:6f637811-bf0d-4383-9371-8feb3ecff99e}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:939eb481-1004-491a-a1a3-23a3a739a866}} of plan against an {{fact:44ea7a73-9d6a-468c-9a33-de88481bdc6d}} floor, and headroom has been essentially flat, moving only from {{fact:a57876ea-5782-476b-9c55-eab9f7283817}} to {{fact:5d27a239-fcdb-4fe5-bf59-f5e5ba3ca0b2}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:8ef4ea09-c44b-4ace-85c1-12291272ec10}} against {{fact:a15d53c2-809b-4f84-b3cc-7dc9af0ff186}}), but headroom has fallen steadily from {{fact:fcdf713b-592e-4c36-b6ea-ac78ae4f4a66}} to {{fact:3fea1c04-455e-435d-a7a1-89dca57a5e14}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:01a0ec28-6ed9-4a35-a2f2-4a1a1b4f42bb}}. Section 6.1 requires at least {{fact:317dd083-d06b-429a-92c0-bdda986c1b3a}}, so the ratio falls short by {{fact:9a7b287d-abc5-4010-ba6d-e77d2988c3e7}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:c6b46c35-1e0d- |
| `pellham-grain` | covenant | none | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 came out at {{fact:01a0ec28-6ed9-4a35-a2f2-4a1a1b4f42bb}}. Section 6.1 requires at least {{fact:317dd083-d06b-429a-92c0-bdda986c1b3a}}, so the ratio falls short by {{fact:9a7b287d-abc5-4010-ba6d-e77d2988c3e7}} of the requirement. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:c6b46c35-1e0d- |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:01a0ec28-6ed9-4a35-a2f2-4a1a1b4f42bb}} against a covenant minimum of {{fact:317dd083-d06b-429a-92c0-bdda986c1b3a}}, leaving headroom of {{fact:9a7b287d-abc5-4010-ba6d-e77d2988c3e7}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:4677162e-b003-4902-a011-17588a4ae71a}} in August to {{fact:8cd000c0-dd4e-4c09-bb6f-45ca0f00d913}} in October, pointing to ongoing cash burn. Cash of {{fact:e84da45e-1595-4df1-9678-bfdc21a5fe2c}} still sits well above the {{fact:0608c46b-0ed2-4d23-a42c-5a030f04df2e}} minimum, so the concern is the trend rather than an imminent breach. No |
| `tarnavi-ai` | certificate | none | All three covenants are reported in the page one summary table and match the calculation schedule on page two. |
| `tarnavi-ai` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tarnavi-ai` | early_warning | none | Unrestricted cash still sits well above the covenant minimum ({{fact:af7273b3-d06b-4d10-af90-c9fc6a475db6}} against {{fact:67ac5a89-f0dd-451e-b2cb-e498d8fc8b9c}}). However, headroom has shrunk steadily, from {{fact:0bf82381-a3c2-4624-8e0e-1d9d768cf561}} in August to {{fact:05f17f11-bf6d-4c31-a1e6-ee1a1ea1be67}} in October, which suggests ongoing cash burn. No other signal fired, so this trend stan |
| `tavernel-grid` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `tavernel-grid` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tavernel-grid` | early_warning | none | Cash headroom has shrunk steadily, from {{fact:b56b2b87-6a4b-4e6c-8f31-40ba64cf1a5f}} in August to {{fact:d1d2ef72-a715-49a5-a895-ace11523668c}} in October, with cash at {{fact:215fdcd3-9e7d-458e-bd4e-feaae30b9a66}} against a {{fact:5c8969f1-faff-44ab-94a0-cdd6fbfc2acb}} floor. The cushion is still comfortable, but the pace of decline matters. Revenue is running ahead of plan, so the cash drain li |
| `tavernel-grid` | early_warning | none | Headroom slipped only marginally, from {{fact:6fc86a11-bf4d-4f48-83f6-f29cdf023b8b}} to {{fact:2d188797-ee07-4042-aa72-3d177ad4b31f}}, and revenue sits at {{fact:fc4c4aae-f12e-4b6c-8365-5aa3ed019d9e}} of plan versus a {{fact:a8c86164-6bd9-4822-8a95-d709a1c067a2}} minimum. This is close to flat and does not explain the falling cash balance. |
| `vantrell-labs` | certificate | none | All three covenants are reported in the summary table on page one and in Schedule 1 on page two. |
| `vantrell-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `vantrell-labs` | certificate | none | No embedded instructions were found in the document. |
| `vantrell-labs` | early_warning | none | Cushion over the minimum cash covenant has narrowed steadily, from {{fact:a6c907d0-14ef-49a1-9da3-8690afe347b9}} in August to {{fact:dd9808fd-5e8c-46ed-8a18-381be26b85d6}} in September and {{fact:208eb5c8-c585-4661-8658-b912dff3c282}} in October. Cash of {{fact:481ae806-ca22-4649-ace9-fcb7ade126ea}} still sits well above the {{fact:93bc8ada-ddb8-45d5-b86f-f0af4ed0d331}} floor, so the concern is th |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:106ccf73-47e7-448b-a9c0-9dc3b604fc28}} in August to {{fact:01a55eee-e0e6-40ac-91a5-15d5fcd6ee2f}} in September and {{fact:c156d5a7-ab44-4623-aa37-1ffcdde7100f}} at October 31. Cash of {{fact:6305efd2-00c2-412d-99df-08c6a1fa5406}} remains comfortably above the {{fact:eb8c7276-949f-40f7-93a3-b8116be9621e}} minimum, but the consistent drain ma |

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
- `kestrel-bay-packaging`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `meridew-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
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


# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T03:23:22+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 20 borrower(s) (whole book); 1 pass(es); run time 173.6 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- run-error: 6 cycle(s) failed on an error, so nothing was measured. First: briarstone-beverage (review run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json; dataflake (review run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/dataflake/2026-10-31/02.json; mosswell-robotics (review run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/mosswell-robotics/2026-10-31/02.json

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
| Cycles closed | 1 of 20 |
| Other disagreements with the truth | 6 |
| Model tokens in / out | 765,566 / 215,654 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 8 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | review_prep (needs_person) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | 2 |
| `brightvane-energy` | runway_falling | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `corvane-analytics` | plan_miss | review_prep (needs_person) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `dataflake` | pledged_cash | review_prep (needs_person) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | 3 |
| `ferrogate-cloud` | cash_flow_positive | review_prep (needs_person) | none | none | 100.0% (64/64) | 4/4 | none |
| `halcyon-grid` | funding_expected | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `harrowgate-precision` | clean | review_prep (needs_person) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | review_prep (needs_person) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |
| `lumora-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `mosswell-robotics` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | 2 |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |
| `orbitline-systems` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | review_prep (needs_person) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | 2 |
| `pellucid-sensors` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `quillon-ai` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | 2 |
| `stripple-tech` | stripple_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `tessaract-labs` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |
| `tidewell-medical` | restricted_account | review_prep (needs_person) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | 2 |
| `veridia-payments` | clean | review_prep (needs_person) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `briarstone-beverage` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json |  |
| `dataflake` | wrong-abstain | covenant run | the run abstained: no answer |  |
| `dataflake` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/dataflake/2026-10-31/02.json |  |
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run abstained: no answer |  |
| `mosswell-robotics` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/mosswell-robotics/2026-10-31/02.json |  |
| `pellham-grain` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/pellham-grain/2026-09-30/02.json |  |
| `quillon-ai` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/quillon-ai/2026-10-31/02.json |  |
| `tidewell-medical` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/tidewell-medical/2026-10-31/02.json |  |
| `briarstone-beverage` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json |  |
| `dataflake` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/dataflake/2026-10-31/02.json |  |
| `mosswell-robotics` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/mosswell-robotics/2026-10-31/02.json |  |
| `pellham-grain` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/pellham-grain/2026-09-30/02.json |  |
| `quillon-ai` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/quillon-ai/2026-10-31/02.json |  |
| `tidewell-medical` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/tidewell-medical/2026-10-31/02.json |  |

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `stripple-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `corvane-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `corvane-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `dataflake` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `dataflake` | signals | signal.high | signal.high: acknowledged by analyst |
| `dataflake` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `halcyon-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `lumora-health` | awaiting_package | intake.missing_document | none (left open) |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `quillon-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `stripple-tech` | intake | intake.unclassified | intake.unclassified: not_needed by analyst |
| `stripple-tech` | spreading | spread.value_unverified | none (left open) |
| `tessaract-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `tidewell-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `tidewell-medical` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |

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
| `briarstone-beverage` | spreading | none | Statements are unaudited, prepared by management, and cover the nine months ended September 30, 2026 with a nine-month 2025 comparative. |
| `briarstone-beverage` | spreading | none | Equity components (Common stock and additional paid-in capital; Retained earnings) on page 2 are not reported separately; the printed Total stockholders' equity row is reported under bs.total_equity. |
| `briarstone-beverage` | spreading | none | Dividends paid on page 4 is mapped to cf.distributions. |
| `briarstone-beverage` | spreading | none | Cash flow rows 'Cash and equivalents, beginning of period' and 'Cash and equivalents, end of period' on page 4 have no template line and are not reported. |
| `briarstone-beverage` | spreading | none | Debt schedule rows on page 5 (Revolving line of credit - Bank of Stoic, Term notes payable - Bank of Stoic, Total debt outstanding, Term debt principal due within twelve months) have no separate template line and are not reported; they correspond to balance sheet debt lines already spread. |
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability was {{fact:eccefdef-af40-4438-9a60-4bd6a41d5296}} against a {{fact:8420f7b3-112e-483b-9917-0cfe30253b1c}} commitment, or {{fact:afda2f63-269b-40dc-9165-b1ed2a2729c3}} of the line. Below zero means borrowings exceed what the collateral supports, so the borrower is over-advanced and has no revolver cushion for liquidity. No other signal fired, so the facts do not show whether weaker col |
| `brightvane-energy` | spreading | 1 | Page 5 (Note 1 - Capitalised software) is a month-only rollforward of capitalised software; it was not spread because it is not a ten-month figure and the template has no lines for it. |
| `brightvane-energy` | spreading | none | The document is a bank account statement for the month of October 2026, not a set of financial statements. Only the two bank lines are reported, taken from closing balances at October 31, 2026. |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:e808f329-9ed2-4660-864e-85468337786f}} months at July end through {{fact:7c471ca8-9a09-435d-b265-5ad25f42b31b}} and {{fact:4e9ad01a-26dd-47bf-af8b-010049b697d1}} to {{fact:91ab4d4e-02f6-4093-9c9b-6fdd09d6ab06}} at October end. The steady decline means cash is being used faster than it is replenished. This underlying trend drives both covenant headroom  |
| `brightvane-energy` | early_warning | none | Headroom on the minimum cash covenant fell from {{fact:f4a47252-f39e-4885-b92c-2417cd690951}} to {{fact:2e29a2c8-d621-4b31-a025-495dc0a2fcb6}} to {{fact:70437476-3cba-47c4-968d-bf53abaeaf98}}, with unrestricted cash at {{fact:7146bbbd-8978-474c-9d9f-b125f7f7a94d}} against a floor of {{fact:9d60030b-f402-47e5-9c64-00df9f1582df}}. This is the thinner of the two covenant cushions. The cash burn behin |
| `brightvane-energy` | early_warning | none | Headroom on the minimum runway covenant narrowed from {{fact:406c40a8-c588-4040-af98-afe0429ccf53}} to {{fact:05172343-e33a-447f-929b-b97a25beb1f4}} to {{fact:d17b43e9-1b63-4865-9051-65f587a66bce}}. Runway of {{fact:d3a61e1f-0098-40b9-86a5-b0e1e3f5df58}} months still clears the {{fact:1ffb0178-4f03-45c9-945c-4f203f5e6270}}-month minimum comfortably. The signal mirrors the falling runway rather tha |
| `corvane-analytics` | spreading | 1 | Note 1 on page 5 (capitalised software roll-forward) covers only the single month and has no template lines; it was not spread. |
| `corvane-analytics` | spreading | none | The document is a bank account statement for October 1, 2026 to October 31, 2026, not a set of financial statements, so only the two bank template lines are reported. |
| `corvane-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `corvane-analytics` | certificate | none | The borrower reports non-compliance with the Revenue to Plan covenant. |
| `corvane-analytics` | certificate | none | On page one the Revenue to Plan requirement wraps across two lines in the table. |
| `corvane-analytics` | certificate | none | No instructions were found in the document text. |
| `corvane-analytics` | covenant | 1,, 1 | The breach looks real. Revenue to Plan (Section 6.3) for the three months ended October 31, 2026 came to {{fact:2aa946f7-88cb-43f5-9d81-36858ba826b6}}. The minimum is {{fact:86b794ce-e84e-4abc-994a-281808cbcc21}}, so the shortfall is {{fact:6571fa4a-90b8-4cb3-b718-3e9e95db9631}}. The borrower's own October certificate agrees: it reports {{fact:194229d5-2cee-41c8-a7b3-fc68f0dd8337}} and says the bo |
| `corvane-analytics` | early_warning | none | Revenue against plan stands at {{fact:d3c0308e-5362-4a2d-add5-7f48ba7438ce}}, below the covenant level of {{fact:2b1e9f12-88af-480c-8839-8321fdd53587}}, so headroom is negative at {{fact:143008c9-152b-4303-8b94-f0ec44e56200}}. The test is not merely tight but already on the wrong side of the threshold. The revenue shortfall and trend signals describe the same problem. |
| `corvane-analytics` | early_warning | none | Revenue came in at only {{fact:7c03c73e-aea4-4930-a6c3-32d6151c4c01}} of plan, a substantial miss for a subscription business that usually plans revenue with some visibility. This shortfall is what drives the failed revenue covenant and may also explain the steady erosion in cash headroom. |
| `corvane-analytics` | early_warning | none | Headroom on the revenue covenant has worsened each month, from {{fact:bd640ec7-ecf0-43d3-a63d-9192b211663f}} in August to {{fact:a542ff08-ffd1-4346-a466-7861b003c49b}} in September and {{fact:143008c9-152b-4303-8b94-f0ec44e56200}} in October. The miss is deepening rather than a one-off, which makes the current shortfall harder to dismiss as timing. |
| `corvane-analytics` | early_warning | none | Unrestricted cash of {{fact:dbd79489-2b03-4727-a834-ad64cbe6d2f4}} is still well above the {{fact:470a0286-54f6-4cc7-9317-4263d93d03ed}} minimum, but headroom has slid from {{fact:fdb0de1b-4a3b-4926-a56f-074e66e78c2b}} in August to {{fact:646000c5-6cea-46af-87a0-9d19e4f548b5}} in October. Falling cash alongside a widening revenue miss may point to burn that the business is not covering with sales. |
| `dataflake` | spreading | 1 | Note 1 on page 5 is a one-month capitalised software rollforward; it was not spread as it covers the month only and has no template line beyond the balance sheet figure. |
| `dataflake` | spreading | none | The document is a bank statement for October 2026, not a set of financial statements, so only the two bank account total lines were reported. |
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | early_warning | none | Dataflake has about {{fact:78f6ae81-0bfe-4964-bff9-c570772de4ee}} months of cash at current burn, which limits its ability to absorb setbacks before it needs new funding. The low-severity runway covenant signal shows this has been shrinking quickly. The cash covenant signals show the same pressure on its balance sheet. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:c6b23fca-d829-47de-afb9-2c23d0a23106}} is below the {{fact:dfe07fca-0fbc-40ee-b40b-3a228a34e2f2}} minimum, giving headroom of {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}}. That means the level is past the threshold, not merely close to it, though the signal is rated medium. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Runway covenant headroom fell from {{fact:0ac55194-1dd2-43ef-8b72-a1df0510d927}} in August to {{fact:3caa60a2-0f31-4409-a26f-9fb416c6117f}} in September and {{fact:09bff13b-0bba-432a-8f89-e9c4a43c04b8}} in October. Runway of {{fact:88465eb6-1917-4cd2-b16b-08d16b705fd9}} months remains above the {{fact:629bd59a-680f-43d2-9cd0-1e4063fb047e}}-month floor, but at this pace the cushion is thin. This is |
| `dataflake` | early_warning | none | Cash covenant headroom moved from {{fact:c62ed519-9cd5-4290-86ff-3a880e7c459e}} in August to {{fact:34304bd5-0c7c-4ff3-a214-d8e31aa6b48b}} in September, then to {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}} in October. The steady decline crossed below the minimum. This shows the medium-severity cash signal reflects ongoing burn, not a one-month dip. |
| `ferrogate-cloud` | spreading | 1 | Note 1 on page 5 is a single-month capitalised software rollforward (start balance, additions, amortisation, end balance); none of its rows were spread as they fit no template line for the ten-month period. |
| `ferrogate-cloud` | spreading | none | The document is a single-page bank statement for the period October 1, 2026 to October 31, 2026, not a set of financial statements, so only the two bank account total lines are reported. |
| `ferrogate-cloud` | spreading | 9001) | The collateral account (ending 9001) is pledged under the venture loan agreement and is not available for withdrawal. |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `halcyon-grid` | spreading | 1 | Page 5 (Note 1 - Capitalised software) is a one-month rollforward of capitalised software and was not spread; its closing balance agrees in wording to the balance sheet line. |
| `halcyon-grid` | spreading | none | This document is a bank statement for the period October 1, 2026 to October 31, 2026, not a set of financial statements. Only the two bank template lines are reported. |
| `halcyon-grid` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the Revenue to Plan requirement wraps across two lines in the table. |
| `halcyon-grid` | certificate | none | The summary table header for the actual and compliance columns appears overlapped in the rendering, but row values are legible. |
| `halcyon-grid` | certificate | none | No embedded instructions were found in the document. |
| `halcyon-grid` | early_warning | none | Cash headroom has dropped steadily, from {{fact:215d7fe7-96e0-4ef0-a08e-22a42452f925}} in August to {{fact:77ec4e2c-7742-43d8-8e63-8fbaa4771311}} in October. Unrestricted cash of {{fact:b9098cac-dcd5-4879-9df4-cb17ce63100f}} remains above the {{fact:a51b3150-6a6d-419b-a4d7-63750a532c0d}} floor, but the pace of decline points to ongoing cash burn. With revenue ahead of plan, the burn appears driven |
| `halcyon-grid` | early_warning | none | Revenue is running at {{fact:8ea400e0-d968-48ae-b48a-e822bb1a76db}} of plan against a {{fact:7ce5a9d8-2685-45c5-b272-ba54dfb40d46}} minimum. Headroom has slipped only marginally, from {{fact:db12b9ee-916b-400d-bf72-536f72a54349}} to {{fact:901a8aea-6453-43fe-a3f4-eeb84f9282ab}}, which is essentially flat. This signal is reassuring rather than concerning, and it suggests the falling cash balance is |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kelvra-bio` | spreading | 1 | Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread. |
| `kelvra-bio` | spreading | none | This document is a bank account statement for October 2026, not a set of financial statements, so only the two bank account total lines were reported. |
| `kelvra-bio` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `kelvra-bio` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `kelvra-bio` | certificate | none | No embedded instructions were found in the document. |
| `kelvra-bio` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:a5cc90e5-6284-4ae0-959c-8aac343b2d28}} to {{fact:e849c4f5-c89e-46a2-a99e-69d7c5ef0e11}} to {{fact:0e40c1c4-1993-4343-bc36-6f621f1475db}}, consistent with steady cash burn. Cash of {{fact:e135f087-ef39-441e-a2d9-90b2e31308ea}} still sits well above the {{fact:5d992da1-7eea-48af-952f-cdbe15207cd7}} floor. No other signal fired, so this  |
| `kestrel-bay-packaging` | spreading | none | The cover page states units as 'In thousands of u.s. dollars'; the statement pages use the phrase reported as the scale statement. |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | early_warning | none | Total leverage of {{fact:cf09aa30-14d6-4214-b8dc-b7369f0a5824}} is above the {{fact:cf5ce94d-59c2-485d-ac3c-f864cf033957}} maximum, so headroom is negative at {{fact:b1a2482c-4174-437b-956c-da582a08fa26}}. On these figures the covenant appears already breached, not merely tight. Debt is high relative to earnings while the liquidity cushion is also shrinking. |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:0f340d0e-1385-41ee-a0dd-bda8b6003f21}} sits just above its {{fact:13194732-46fe-4a3a-afd0-41790b749b4f}} floor, leaving headroom of only {{fact:9e590747-9307-45f2-be07-cc4a806e601c}}. That is a thin short-term liquidity cushion. Alongside the leverage overshoot, it points to pressure on both debt capacity and near-term cash. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom slipped from {{fact:c016ad45-01b1-4a84-9ef1-bd2b68269efc}} in March to {{fact:f33cbd85-a873-4f98-99bf-bd4fb0d746df}} in June. It then fell sharply to {{fact:9e590747-9307-45f2-be07-cc4a806e601c}} by September. The deterioration is accelerating, which explains why the low-headroom signal fired and suggests the floor could be at risk if the trend continues. |
| `mosswell-robotics` | spreading | 1 | Note 1 (capitalised software roll-forward, month only) on page 5 was not spread; it has no corresponding template lines. |
| `mosswell-robotics` | spreading | none | The document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines are reported. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:39a70bb8-5c76-4578-b667-3bbacfdf24eb}} in August to {{fact:87a9e2f6-280b-4436-b792-a2bc7d3456c4}} in September and {{fact:08c4c464-d664-4f78-b775-4e9c2eaebc21}} in October. Cash of {{fact:6ac67879-e877-4543-a08b-598cab953c80}} still sits well above the {{fact:ddd5737d-8265-4ee1-b8d0-1de5eff6213f}} floor. The concern is the trend, a sign |
| `nimbusfield-security` | spreading | 1 | Note 1 on page 5 is a one-month capitalised software rollforward; no template line was taken from it. |
| `nimbusfield-security` | spreading | none | This document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines were spread. |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Cash runway has fallen to {{fact:0876a4c5-62e5-4171-8850-2564f739afc2}} months, so the borrower's time to reach profitability or raise new funding is getting short. The steadily falling runway and cash covenant headroom show this is a sustained trend, not a one-off. Revenue tracking ahead of plan suggests the pressure comes from cash burn rather than weak sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant has shrunk each month, from {{fact:85e42179-b128-45b9-8622-58c083af9a0e}} in August to {{fact:817703a5-ed3c-49e1-b9c0-55b878918d35}} in October. Runway of {{fact:5e075111-4594-4eda-9eeb-b1d483aab321}} months is still above the {{fact:caaa8855-1488-43ab-a0d9-d277f5ee9bea}}-month floor, but if the decline continues at this pace, the cushion would be gone withi |
| `nimbusfield-security` | early_warning | none | Unrestricted cash headroom fell from {{fact:62e6d8fc-98c7-419b-9206-889afb0aa3f4}} in August to {{fact:71bf8060-93da-4884-a4a3-fae49d106867}} in October. Cash of {{fact:1300f6f3-f9f0-4192-86c7-2b2024c61b06}} still clears the {{fact:f59c1e75-ca5d-4e05-a55c-f4d06b43784c}} minimum. The falling cash balance is the root of the shrinking runway, so this signal and the runway signals describe the same bu |
| `nimbusfield-security` | early_warning | none | This headroom is essentially flat, moving only from {{fact:973da0b7-3049-49dd-b547-9f41cace8037}} to {{fact:83a42716-5b75-41e8-a15f-2e31b29bc907}}. Revenue is running at {{fact:c113aae2-3896-4363-909b-a6c665eb7f7c}} of plan against an {{fact:c19644d5-7664-4763-b0b6-a0c4ceb67a4d}} floor. This is a mitigating point: it suggests the cash decline is not caused by a revenue shortfall. |
| `orbitline-systems` | spreading | 1 | Note 1 on page five is a one-month rollforward of capitalised software; it was not spread as it maps to no separate template line. |
| `orbitline-systems` | spreading | none | The document is a bank statement for the month ended October 31, 2026, not a set of financial statements, so only the two bank account summary totals were reported. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:468baa25-549f-48e8-b82c-79656e01b092}} in August to {{fact:0085414f-86dc-4304-8818-5ea0761e790e}} in September and {{fact:1e2a444b-ad46-4bff-b9c2-eb3b87211055}} in October. Cash of {{fact:17e92191-36ba-45ac-a5d5-1a5ea8b346f7}} remains well above the {{fact:4b28462c-0a45-4cbf-8e93-33a6a6f4bb0b}} floor, but the s |
| `pellham-grain` | spreading | none | Statements are interim, unaudited, management-prepared for the nine months ended September 30, 2026 with nine-month comparatives for 2025. |
| `pellham-grain` | spreading | none | Debt schedule rows on page 5 (revolving line of credit, term notes payable, total debt outstanding, term debt principal due within twelve months) were not placed; the template has no lines for them. |
| `pellham-grain` | spreading | none | The cover page also states the units as in thousands of U.S. dollars; the scale phrase was taken from the balance sheet page. |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | covenant | 1 | The Fixed Charge Coverage Ratio for the four quarters ended September 30, 2026 is {{fact:5b61399a-8531-42bb-a229-39ef26af3fee}}. The minimum under Section 6.1 is {{fact:77721a76-1ddd-4eb0-9539-9ed32d14186a}}, so the ratio falls short by {{fact:b37d8dd6-944b-4c18-b234-30e87bc1ee47}}. This looks like a real breach. The borrower's Q3 2026 compliance certificate reports the same ratio, {{fact:3a9a3c97 |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | The fixed charge coverage ratio of {{fact:5b61399a-8531-42bb-a229-39ef26af3fee}} sits below the {{fact:77721a76-1ddd-4eb0-9539-9ed32d14186a}} minimum, so headroom is negative at {{fact:b37d8dd6-944b-4c18-b234-30e87bc1ee47}}. This points to an outright shortfall, not just a thin cushion: cash flow is not covering fixed charges at the required level. No other signal fired this period to confirm or e |
| `pellucid-sensors` | spreading | 1 | Note 1 on page 5 is a month-only rollforward of capitalised software; it was not spread as it has no template lines beyond the balance already reported from the balance sheet. |
| `pellucid-sensors` | spreading | none | The document is a bank statement for October 1 to October 31, 2026, not a set of financial statements, so only the two bank account total lines are reported. |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Cushion over the minimum cash covenant has narrowed each month, from {{fact:57482fae-a321-4796-9584-18b8873e56b0}} in August to {{fact:01873dcf-8c7e-48d6-9d33-e2674db02b62}} in October, suggesting steady cash burn. Unrestricted cash of {{fact:a3fc1318-7943-4364-b576-965fe50b05e1}} still sits well above the {{fact:bcec0827-9b8b-471d-b72b-f6e0c945777c}} floor. It is the only signal this period, so t |
| `quillon-ai` | spreading | 1 | Note 1 on page 5 is a month-only capitalised software rollforward (start balance, additions, amortisation, end balance); it has no template line and was not spread. |
| `quillon-ai` | spreading | none | This document is a one-month bank statement (October 1 to October 31, 2026) from Bank of Stoic, not a set of financial statements. Only the two bank account total lines are reported. |
| `quillon-ai` | certificate | none | All three covenants are reported in the summary table on page one and agree with the calculation schedule on page two. |
| `quillon-ai` | certificate | none | In the summary table the Revenue to Plan requirement wraps across two lines; it is reported here as one phrase. |
| `quillon-ai` | certificate | none | The summary table header shows the Actual and In compliance column headings overlapping in the rendered page. |
| `quillon-ai` | early_warning | none | Unrestricted cash still sits well above the covenant minimum ({{fact:72a54126-6e8f-43f5-b3d9-c88af491f17c}} against {{fact:b79f0644-8b80-489b-bed3-1bdd778352e9}}), but headroom has narrowed each month, from {{fact:9bf395fe-cad9-4093-aea9-735725d4fc1e}} in August to {{fact:4bcce43f-2e0b-4cfc-b7e1-1bc139f695b9}} in October. For a borrower that may be burning cash, the trend matters more than the cur |
| `stripple-tech` | intake | none | Raw spreadsheet export of monthly recurring revenue and customer counts with no title, no borrower name and no stated report date; the borrower and period cannot be confirmed from the document itself, and the data shown ends in an earlier year than the other documents in this delivery. |
| `stripple-tech` | spreading | 1 | Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread. |
| `stripple-tech` | spreading | none | The document is a bank statement for the month of October 2026 rather than a set of financial statements, so only the two bank account total lines were spread. |
| `tessaract-labs` | spreading | 1 | Note 1 on page five is a single-month rollforward of capitalised software (opening balance, additions, amortisation, closing balance); its amortisation row has no template line and was not spread. |
| `tessaract-labs` | spreading | none | The document is a single-page bank statement from Bank of Stoic for the month of October 2026, not a set of financial statements. Only the two bank account totals are reported. |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Cash headroom has narrowed each month, from {{fact:4b37739c-9999-41ff-8506-13e0d10641e6}} in August to {{fact:b0944c84-9b0b-4812-882a-c9779a0e5366}} in September and {{fact:8c67eca2-8228-47eb-9b00-870ececfe2fc}} in October. Cash of {{fact:a4b95ad7-3fec-4d34-b09d-c4fa85296d11}} remains well above the {{fact:596fc38d-d1fc-426c-bfc8-5cd5ca81a2b7}} minimum, but the steady decline suggests ongoing cash |
| `tidewell-medical` | spreading | 1 | Note 1 (page 5) presents a one-month capitalised software roll-forward only; it was not spread, and its closing balance agrees in label to the balance sheet line already reported. |
| `tidewell-medical` | spreading | none | This document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines are reported. The balances are as at October 31, 2026, the requested period end. |
| `tidewell-medical` | spreading | 9002) | A new restricted escrow collateral account (ending 9002) was opened on October 14, 2026 under an escrow arrangement. It is included in the printed total of pledged and restricted accounts, and the reviewer may wish to confirm the related arrangement. |
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom fell from {{fact:c2914146-cfeb-479b-b943-e568509223c3}} to {{fact:05e182ac-c859-46a7-866c-57a6a1be9e48}}, most of it in October, leaving cash of {{fact:96b12a12-368d-4129-9236-712e7e3156e6}} against a floor of {{fact:761c7dcc-be1e-42c5-9a5e-26a784793936}}. This is the thinnest cushion of the three and moves with the shrinking runway. |
| `tidewell-medical` | early_warning | none | Runway headroom dropped from {{fact:ddf1fde1-cd39-4e90-b857-4ea3c52e0f87}} to {{fact:d9e898ae-2b1f-42ba-8999-f930ad36c25c}}, with the sharpest fall in October. Runway of {{fact:7c8c3773-efde-4e13-92a5-b513fb7c1581}} months is still well above the {{fact:1253ff82-d663-4110-9480-898c859a1ca6}}-month minimum. The October drop coincides with the cash decline, which points to faster burn. |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only from {{fact:39437d3e-cb04-4838-bbfe-ef4925e09d42}} to {{fact:61d46daf-6cf4-44b4-a43c-412e83f0fa84}}. Revenue is running at {{fact:470a6db8-749e-4b27-81a2-e1f4f213f28c}} of plan. That suggests the cash and runway pressure comes from spending or working capital rather than a sales shortfall. |
| `veridia-payments` | spreading | 1, | Page 5 (Note 1, capitalised software roll-forward) presents the month only and has no matching template lines; it was not spread. |
| `veridia-payments` | spreading | none | This document is a one-page bank statement (Bank of Stoic, statement period October 1, 2026 to October 31, 2026), not a set of financial statements, so only the two bank summary lines are reported. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Headroom on the minimum cash covenant narrowed each month, from {{fact:a56d6e09-60f7-42f2-8996-014564dc68aa}} at August 31 to {{fact:f5c4e11d-f469-43d3-b4be-4cf3278a59a6}} and then {{fact:8e3cc6ee-3f32-4372-8ffa-b56474e37f7b}} at October 31. Unrestricted cash of {{fact:6e1f9945-aca3-4aff-92b9-e5fc64446651}} remains well above the {{fact:a7dc4d4b-e463-4f7e-b37b-0776585b1b49}} floor, but the steady  |

## Observations

- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `briarstone-beverage`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `brightvane-energy`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `brightvane-energy`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `brightvane-energy`: guardrail note on review: fact_unknown -> section_dropped: summary: fact d3a61e1f-0098-40b9-86a5-b0e1e3f5df58 is not in scope
- `brightvane-energy`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact d3a61e1f-0098-40b9-86a5-b0e1e3f5df58 is not in scope
- `brightvane-energy`: guardrail note on review: fact_unknown -> section_dropped: risks: fact d3a61e1f-0098-40b9-86a5-b0e1e3f5df58 is not in scope
- `corvane-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `corvane-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `corvane-analytics`: guardrail note on covenant: quote_not_on_page -> claim_dropped: the cited document is not on file for this borrower
- `corvane-analytics`: guardrail note on covenant: quote_not_on_page -> claim_dropped: the cited document is not on file for this borrower
- `corvane-analytics`: guardrail note on covenant: quote_not_on_page -> claim_dropped: the cited document is not on file for this borrower
- `corvane-analytics`: guardrail note on covenant: no_claim_survived -> abstain: none of the cited quotes was found on its page
- `corvane-analytics`: guardrail note on covenant: fact_unknown -> abstain: fact 2aa946f7-88cb-43f5-9d81-36858ba826b6 is not in scope
- `corvane-analytics`: guardrail note on covenant: fact_unknown -> abstain: fact 86b794ce-e84e-4abc-994a-281808cbcc21 is not in scope
- `corvane-analytics`: guardrail note on covenant: fact_unknown -> abstain: fact 6571fa4a-90b8-4cb3-b718-3e9e95db9631 is not in scope
- `corvane-analytics`: guardrail note on covenant: fact_unknown -> abstain: fact 194229d5-2cee-41c8-a7b3-fc68f0dd8337 is not in scope
- `corvane-analytics`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `corvane-analytics`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `corvane-analytics`: guardrail note on covenant: number_in_words -> abstain: a quantity was stated in words; quantities come from fact references
- `corvane-analytics`: guardrail note on covenant: unknown_calc_id -> flagged: the answer names a calculation that was not run for this exception
- `corvane-analytics`: guardrail note on covenant: unknown_calc_id -> flagged: the answer names a calculation that was not run for this exception
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `corvane-analytics`: guardrail note on review: fact_unknown -> section_dropped: summary: fact d3c0308e-5362-4a2d-add5-7f48ba7438ce is not in scope
- `corvane-analytics`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact aa7e3900-d551-49f6-be00-77d22b097b20 is not in scope
- `corvane-analytics`: guardrail note on review: fact_unknown -> section_dropped: risks: fact d3c0308e-5362-4a2d-add5-7f48ba7438ce is not in scope
- `dataflake`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `dataflake`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `dataflake`: guardrail note on covenant: step_cap -> abstain: the run reached its step cap before giving an answer
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 73c01421-9204-426d-b39d-1b4aae36380a is not in scope
- `ferrogate-cloud`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact 73c01421-9204-426d-b39d-1b4aae36380a is not in scope
- `ferrogate-cloud`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact
- `halcyon-grid`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `halcyon-grid`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 2 signal(s) were left out of the ranking and were placed after the rest by severity
- `halcyon-grid`: guardrail note on review: fact_unknown -> section_dropped: summary: fact b9098cac-dcd5-4879-9df4-cb17ce63100f is not in scope
- `halcyon-grid`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact bd33e674-3558-427d-89ce-b61dec68bfd6 is not in scope
- `halcyon-grid`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 77ec4e2c-7742-43d8-8e63-8fbaa4771311 is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 6d06dcc5-63d4-4916-b022-ab56b87c671d is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: performance: fact aec7e8e1-7e93-4508-96bf-b2e38896fe8e is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact 2d143911-9533-4c9b-9e43-d23da7c27edc is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: collateral: fact 544ba8e2-841d-43c4-bc48-2b162effa319 is not in scope
- `harrowgate-precision`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact
- `kelvra-bio`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kelvra-bio`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kelvra-bio`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `kelvra-bio`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 0e40c1c4-1993-4343-bc36-6f621f1475db is not in scope
- `kelvra-bio`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact 43673429-d3a3-4c68-a155-8059a04b5fd9 is not in scope
- `kelvra-bio`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 0e40c1c4-1993-4343-bc36-6f621f1475db is not in scope
- `kestrel-bay-packaging`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kestrel-bay-packaging`: guardrail note on covenant: step_cap -> abstain: the run reached its step cap before giving an answer
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `kestrel-bay-packaging`: guardrail note on review: fact_unknown -> section_dropped: summary: fact cf09aa30-14d6-4214-b8dc-b7369f0a5824 is not in scope
- `kestrel-bay-packaging`: guardrail note on review: fact_unknown -> section_dropped: performance: fact 2269c04d-145c-44fc-b5e6-aa48355a0458 is not in scope
- `kestrel-bay-packaging`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact cf09aa30-14d6-4214-b8dc-b7369f0a5824 is not in scope
- `kestrel-bay-packaging`: guardrail note on review: fact_unknown -> section_dropped: risks: fact b1a2482c-4174-437b-956c-da582a08fa26 is not in scope
- `mosswell-robotics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `mosswell-robotics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `mosswell-robotics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `nimbusfield-security`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `nimbusfield-security`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `nimbusfield-security`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact 5e075111-4594-4eda-9eeb-b1d483aab321 is not in scope
- `nimbusfield-security`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 817703a5-ed3c-49e1-b9c0-55b878918d35 is not in scope
- `orbitline-systems`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `orbitline-systems`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `orbitline-systems`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `orbitline-systems`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 1e2a444b-ad46-4bff-b9c2-eb3b87211055 is not in scope
- `orbitline-systems`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact b4fc4dba-f28b-4384-af24-5ad3732b24fd is not in scope
- `orbitline-systems`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 1e2a444b-ad46-4bff-b9c2-eb3b87211055 is not in scope
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on covenant: quote_not_on_page -> claim_dropped: the cited document is not on file for this borrower
- `pellham-grain`: guardrail note on covenant: quote_not_on_page -> claim_dropped: the cited document is not on file for this borrower
- `pellham-grain`: guardrail note on covenant: no_claim_survived -> abstain: none of the cited quotes was found on its page
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact 5b61399a-8531-42bb-a229-39ef26af3fee is not in scope
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact 77721a76-1ddd-4eb0-9539-9ed32d14186a is not in scope
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact b37d8dd6-944b-4c18-b234-30e87bc1ee47 is not in scope
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact 3a9a3c97-f1e6-4f16-acce-83e6cc7bcddb is not in scope
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact cd827479-b981-4d4f-abb8-7c465667babf is not in scope
- `pellham-grain`: guardrail note on covenant: fact_unknown -> abstain: fact b46d3981-8152-4f52-9b6d-4958d3366057 is not in scope
- `pellham-grain`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `pellham-grain`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `pellham-grain`: guardrail note on covenant: unknown_calc_id -> flagged: the answer names a calculation that was not run for this exception
- `pellham-grain`: guardrail note on covenant: unknown_calc_id -> flagged: the answer names a calculation that was not run for this exception
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellham-grain`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellucid-sensors`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellucid-sensors`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellucid-sensors`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellucid-sensors`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 01873dcf-8c7e-48d6-9d33-e2674db02b62 is not in scope
- `pellucid-sensors`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact d7ad1423-b9a8-4940-80da-ad26b627acdf is not in scope
- `pellucid-sensors`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 01873dcf-8c7e-48d6-9d33-e2674db02b62 is not in scope
- `quillon-ai`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `quillon-ai`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `quillon-ai`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `stripple-tech`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `stripple-tech`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tessaract-labs`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tessaract-labs`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tessaract-labs`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tessaract-labs`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 8c67eca2-8228-47eb-9b00-870ececfe2fc is not in scope
- `tessaract-labs`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact a71da3f0-4437-4d98-b93d-1aea0a0c2445 is not in scope
- `tessaract-labs`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 8c67eca2-8228-47eb-9b00-870ececfe2fc is not in scope
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `veridia-payments`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `veridia-payments`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 8e3cc6ee-3f32-4372-8ffa-b56474e37f7b is not in scope
- `veridia-payments`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact e0a76f6f-ee24-482a-8ff9-2e3b7127843d is not in scope
- `veridia-payments`: guardrail note on review: fact_unknown -> section_dropped: risks: fact 8e3cc6ee-3f32-4372-8ffa-b56474e37f7b is not in scope


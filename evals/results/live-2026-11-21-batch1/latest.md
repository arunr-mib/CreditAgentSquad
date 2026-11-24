# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T02:52:26+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 4 borrower(s) (['brightvane-energy', 'corvane-analytics', 'ferrogate-cloud', 'halcyon-grid']); 1 pass(es); run time 444.2 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (250 of 250) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 75.0% (the book expects 75.0%) |
| Cycles reaching the signals stage or beyond | 4 of 4 |
| Cycles closed | 4 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 169,075 / 47,878 |

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
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `corvane-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `halcyon-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `corvane-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `corvane-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `halcyon-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `brightvane-energy` | spreading | 1 | Page 5 (Note 1 - Capitalised software) is a month-only rollforward of capitalised software; it was not spread because it is not a ten-month figure and the template has no lines for it. |
| `brightvane-energy` | spreading | none | The document is a bank account statement for the month of October 2026, not a set of financial statements. Only the two bank lines are reported, taken from closing balances at October 31, 2026. |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:e808f329-9ed2-4660-864e-85468337786f}} months at July end through {{fact:7c471ca8-9a09-435d-b265-5ad25f42b31b}} and {{fact:4e9ad01a-26dd-47bf-af8b-010049b697d1}} to {{fact:91ab4d4e-02f6-4093-9c9b-6fdd09d6ab06}} at October end. The steady decline means cash is being used faster than it is replenished. This underlying trend drives both covenant headroom  |
| `brightvane-energy` | early_warning | none | Headroom on the minimum cash covenant fell from {{fact:f4a47252-f39e-4885-b92c-2417cd690951}} to {{fact:2e29a2c8-d621-4b31-a025-495dc0a2fcb6}} to {{fact:70437476-3cba-47c4-968d-bf53abaeaf98}}, with unrestricted cash at {{fact:7146bbbd-8978-474c-9d9f-b125f7f7a94d}} against a floor of {{fact:9d60030b-f402-47e5-9c64-00df9f1582df}}. This is the thinner of the two covenant cushions. The cash burn behin |
| `brightvane-energy` | early_warning | none | Headroom on the minimum runway covenant narrowed from {{fact:406c40a8-c588-4040-af98-afe0429ccf53}} to {{fact:05172343-e33a-447f-929b-b97a25beb1f4}} to {{fact:d17b43e9-1b63-4865-9051-65f587a66bce}}. Runway of {{fact:d3a61e1f-0098-40b9-86a5-b0e1e3f5df58}} months still clears the {{fact:1ffb0178-4f03-45c9-945c-4f203f5e6270}}-month minimum comfortably. The signal mirrors the falling runway rather tha |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:e808f329-9ed2-4660-864e-85468337786f}} months at July end through {{fact:7c471ca8-9a09-435d-b265-5ad25f42b31b}} and {{fact:4e9ad01a-26dd-47bf-af8b-010049b697d1}} to {{fact:91ab4d4e-02f6-4093-9c9b-6fdd09d6ab06}} at October end. The steady decline means cash is being used faster than it is replenished. This underlying trend drives both covenant headroom  |
| `brightvane-energy` | early_warning | none | Headroom on the minimum cash covenant fell from {{fact:f4a47252-f39e-4885-b92c-2417cd690951}} to {{fact:2e29a2c8-d621-4b31-a025-495dc0a2fcb6}} to {{fact:70437476-3cba-47c4-968d-bf53abaeaf98}}, with unrestricted cash at {{fact:7146bbbd-8978-474c-9d9f-b125f7f7a94d}} against a floor of {{fact:9d60030b-f402-47e5-9c64-00df9f1582df}}. This is the thinner of the two covenant cushions. The cash burn behin |
| `brightvane-energy` | early_warning | none | Headroom on the minimum runway covenant narrowed from {{fact:406c40a8-c588-4040-af98-afe0429ccf53}} to {{fact:05172343-e33a-447f-929b-b97a25beb1f4}} to {{fact:d17b43e9-1b63-4865-9051-65f587a66bce}}. Runway of {{fact:d3a61e1f-0098-40b9-86a5-b0e1e3f5df58}} months still clears the minimum of {{fact:1ffb0178-4f03-45c9-945c-4f203f5e6270}} months comfortably. The signal mirrors the falling runway rather |
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

## Observations

- `brightvane-energy`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `brightvane-energy`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `corvane-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `corvane-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `corvane-analytics`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `corvane-analytics`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `corvane-analytics`: guardrail note on covenant: number_in_words -> abstain: a quantity was stated in words; quantities come from fact references
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `ferrogate-cloud`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact
- `halcyon-grid`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `halcyon-grid`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed


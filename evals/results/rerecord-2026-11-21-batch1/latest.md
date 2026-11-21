# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T07:53:10+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 4 borrower(s) (['brightvane-energy', 'corvane-analytics', 'ferrogate-cloud', 'halcyon-grid']); 1 pass(es); run time 198.8 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- pass 1: 5 invented-number

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
| Model tokens in / out | 166,659 / 46,329 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 5 |
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
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `corvane-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | 1 |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | 2 |
| `halcyon-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `brightvane-energy` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1 - Capitalised software) is a month-only rollforward of capitalised software; it was not spread because it is not a ten-month figure and the template has no lines for it.' |  |
| `corvane-analytics` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 (capitalised software roll-forward) covers only the single month and has no template lines; it was not spread.' |  |
| `ferrogate-cloud` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a single-month capitalised software rollforward (start balance, additions, amortisation, end balance); none of its rows were spread as they fit no template line for the ten-month period.' |  |
| `ferrogate-cloud` | invented-number | spreading note | a note shown to a person types a figure: 'The collateral account (ending 9001) is pledged under the venture loan agreement and is not available for withdrawal.' |  |
| `halcyon-grid` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1 - Capitalised software) is a one-month rollforward of capitalised software and was not spread; its closing balance agrees in wording to the balance sheet line.' |  |

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
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:4e6971f5-1058-4866-a2e0-af324ac4d0dc}} months at July 31 to {{fact:9cb8edab-f0ed-47d3-a593-3052389e5299}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:9e7601bb-0498-468a-bf82-c27e0f0ca1ac}} in August to {{fact:988eb01a-2ade-4939-b5a5-ae4ec33ab4dc}} in October, with runway at {{fact:03b5274b-ce22-44dc-a909-68cd4fb0797c}} months against a floor of {{fact:a3016cc7-c315-47bb-bba2-6eae70f903b9}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:f294dc87-0da8-4b48-a408-60e6282f193e}} still clears the {{fact:c2893b24-aaa2-48eb-b939-7efd5860a9b2}} minimum. However, headroom fell from {{fact:2261870b-4c6e-44ea-8d02-6cc05227247b}} to {{fact:d743013d-09b0-4c4a-ac7d-0103574bf33d}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:4e6971f5-1058-4866-a2e0-af324ac4d0dc}} months at the end of July to {{fact:9cb8edab-f0ed-47d3-a593-3052389e5299}} months at the end of October. This points to sustained cash burn without fresh funding. It is the likely driver of both covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:9e7601bb-0498-468a-bf82-c27e0f0ca1ac}} in August to {{fact:988eb01a-2ade-4939-b5a5-ae4ec33ab4dc}} in October, with runway at {{fact:03b5274b-ce22-44dc-a909-68cd4fb0797c}} months against a floor of {{fact:a3016cc7-c315-47bb-bba2-6eae70f903b9}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:f294dc87-0da8-4b48-a408-60e6282f193e}} still clears the {{fact:c2893b24-aaa2-48eb-b939-7efd5860a9b2}} minimum. However, headroom fell from {{fact:2261870b-4c6e-44ea-8d02-6cc05227247b}} in August to {{fact:d743013d-09b0-4c4a-ac7d-0103574bf33d}} in October and is now the thinner of the covenants. It reflects the same cash burn behind the shrinking runway and may be the fi |
| `corvane-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `corvane-analytics` | certificate | none | The borrower reports non-compliance with the Revenue to Plan covenant. |
| `corvane-analytics` | certificate | none | On page one the Revenue to Plan requirement wraps across two lines in the table. |
| `corvane-analytics` | certificate | none | No instructions were found in the document text. |
| `corvane-analytics` | covenant | 1, | The Revenue to Plan test fails for the three months ended October 31, 2026. Revenue was {{fact:2737650c-8e79-4228-994a-c72cc9df0fe9}} of the Approved Plan. Section 6.3 requires at least {{fact:b2d054c9-bf21-4d60-b8a2-a7ec5a3a8919}}. I reran the test under terms version 1, the only version on file, and it still fails, with headroom of {{fact:f28d0c06-d90c-4b24-a3b7-d3e43751dc72}}. The borrower's Oc |
| `corvane-analytics` | early_warning | none | Revenue reached {{fact:e959bfd5-abb7-47e5-a334-99dfbb8654e2}} of plan against a covenant floor of {{fact:3755719f-7547-4045-a3fd-6739b19e4094}}, so headroom is negative at {{fact:1fe991a3-04a0-442a-b354-f9570c0a7fb5}}. The covenant measure therefore sits below its threshold, not merely close to it. This is the covenant view of the same shortfall flagged by the revenue-below-plan signal. |
| `corvane-analytics` | early_warning | none | Revenue came in at {{fact:a0ab2814-6e71-4861-8936-838587855357}} of plan, a material miss for a subscription business whose plan underpins its cash runway. It is the operating cause behind the revenue covenant falling below its floor. If the miss persists, it may also explain the steady erosion in cash headroom. |
| `corvane-analytics` | early_warning | none | Unrestricted cash of {{fact:f6e501ae-5be2-4942-95b6-ecc0bf3ee257}} remains well above the {{fact:cf41bfe4-6836-4f51-aabf-2439f8c303cc}} minimum, but headroom has declined each month, from {{fact:b08244fb-64ac-46cf-989e-ab5bd9ef506f}} in August to {{fact:f08fbe81-7679-4c37-83bb-5be89804ee94}} in September and {{fact:808ba721-2a2c-424f-987c-32d347db04d9}} in October. Ongoing burn alongside the reven |
| `corvane-analytics` | early_warning | none | Revenue covenant headroom has deteriorated each month, from {{fact:77903ce4-ac26-4ad9-8797-33d708ef5b43}} in August to {{fact:bd775118-40c4-46b5-873b-efe55abc61ae}} in September and {{fact:1fe991a3-04a0-442a-b354-f9570c0a7fb5}} in October. It turned negative in September and the gap widened in October, showing the shortfall is worsening rather than a one-month miss. |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `halcyon-grid` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the Revenue to Plan requirement wraps across two lines in the table. |
| `halcyon-grid` | certificate | none | The summary table header for the actual and compliance columns appears overlapped in the rendering, but row values are legible. |
| `halcyon-grid` | certificate | none | No embedded instructions were found in the document. |
| `halcyon-grid` | early_warning | none | Cash headroom has fallen steadily, from {{fact:0ee5b457-8370-4eb9-854e-e46beb7d7aa9}} in August to {{fact:48ab5ad1-850d-426f-9455-dd7b3b7bd3fd}} in October, with unrestricted cash of {{fact:7c239e69-991c-46fc-a0f6-55507edb8e7b}} against a {{fact:031baf93-5cd6-4ac7-a7c0-46230cff716c}} floor. Revenue is running ahead of plan, so the burn seems to come from spending rather than a sales shortfall. If  |
| `halcyon-grid` | early_warning | none | Revenue is at {{fact:0a97fcef-3150-435f-b605-12ceb75fad9f}} of plan against an {{fact:ca916d4e-9eaa-40d4-a7ee-17d5d9e71083}} minimum. Headroom has only edged down, from {{fact:b3a2250f-5be1-470f-acb6-c548e53875fb}} to {{fact:e81f3395-aa39-4bda-a6e2-af0909d9a98e}}, which is a minor change. This signal mainly shows that the falling cash position is not explained by weak sales. |


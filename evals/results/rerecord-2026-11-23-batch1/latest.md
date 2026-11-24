# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-23T23:55:01+00:00; commit `9f0b401a44be878cf0089a52c9c473b8c740102a`; 4 borrower(s) (['tarnavi-ai', 'tavernel-grid', 'vantrell-labs', 'meridew-analytics']); 1 pass(es); run time 439.3 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (248 of 248) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 75.0% (the book expects 75.0%) |
| Cycles reaching the signals stage or beyond | 4 of 4 |
| Cycles closed | 4 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 175,748 / 45,165 |

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
| `meridew-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `tarnavi-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tavernel-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `vantrell-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `meridew-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `meridew-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tarnavi-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tavernel-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `vantrell-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `meridew-analytics` | spreading | 2, 4 | The one-month columns on pages 2 to 4 were not spread. |
| `meridew-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `meridew-analytics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `meridew-analytics` | certificate | none | The borrower reports non-compliance with Revenue to Plan. |
| `meridew-analytics` | covenant | 1, 1 | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:32b5f800-7ba4-40ae-a06e-98552fb2dd87}} of the Approved Plan, below the required minimum of {{fact:97c5f746-53de-4edc-8b8d-533a44d4b33e}}. The borrower's October certificate reports the same figure, {{fact:76cd453d-92fa-4e7f-9576-e17ea7ae2ed6}}, and states it was not in compliance. Approved terms ver |
| `meridew-analytics` | covenant | none | Revenue to Plan (Section 6.3) fails for the three months ended October 31, 2026. Revenue was {{fact:32b5f800-7ba4-40ae-a06e-98552fb2dd87}} of the Approved Plan, below the required minimum of {{fact:97c5f746-53de-4edc-8b8d-533a44d4b33e}}. The borrower's October certificate reports the same figure, {{fact:76cd453d-92fa-4e7f-9576-e17ea7ae2ed6}}, and states it was not in compliance. The approved terms |
| `meridew-analytics` | early_warning | none | Revenue reached {{fact:32b5f800-7ba4-40ae-a06e-98552fb2dd87}} of plan against a covenant floor of {{fact:97c5f746-53de-4edc-8b8d-533a44d4b33e}}. That leaves headroom of {{fact:ae43e3ef-1fea-4417-960e-f71e423237bb}}, so the covenant level is not being met rather than merely close. The revenue-below-plan and falling-headroom signals describe the same shortfall. |
| `meridew-analytics` | early_warning | none | Revenue came in at {{fact:4bf4d2f4-2224-4f95-9d8b-41d59d1dd898}} of plan. For a SaaS borrower, that points to weaker bookings, churn or delayed renewals. This is the operating cause behind the revenue covenant shortfall, and it may also explain the steady erosion in cash headroom. |
| `meridew-analytics` | early_warning | none | Revenue covenant headroom has slid each month: from {{fact:42050e4a-ce3c-4af0-ba42-72b6a00e7406}} in August, to {{fact:7811a1dd-1c93-4785-9b8d-f5db44b8c429}} in September, to {{fact:ae43e3ef-1fea-4417-960e-f71e423237bb}} in October. The shortfall began in September and deepened in October, so it is a worsening trend rather than a one-month miss. |
| `meridew-analytics` | early_warning | none | Unrestricted cash of {{fact:29cd8d28-78a3-4c0b-a29d-b33eca788e0c}} remains comfortably above the {{fact:69ddefe1-73f7-4ffa-9ce8-bbaef95ad183}} minimum. However, headroom has declined steadily, from {{fact:49054f80-7d19-4d2e-a0c2-66cc7628c4cd}} to {{fact:8ce31a07-18b0-4706-ae13-cb74dd1b2656}} to {{fact:8d80b4d7-54c2-4f69-a386-50366ce31c62}}. Taken together with the revenue shortfall, this suggests  |
| `tarnavi-ai` | certificate | none | All three covenants are reported in the page one summary table and match the calculation schedule on page two. |
| `tarnavi-ai` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tarnavi-ai` | early_warning | none | Unrestricted cash still sits well above the covenant minimum ({{fact:66afaff8-c6b3-497d-8c96-12123d42bb7e}} against {{fact:db22c1c9-42fa-48d7-8a1a-e9311c37eca8}}). However, headroom has shrunk steadily, from {{fact:33c345eb-1a5e-4a52-9bdd-448f8c00c2db}} in August to {{fact:a15673c9-b1b7-48e6-8435-3d5b72f181a1}} in October, which suggests ongoing cash burn. No other signal fired, so this trend stan |
| `tavernel-grid` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `tavernel-grid` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `tavernel-grid` | early_warning | none | Cash headroom has shrunk steadily, from {{fact:14f2cb5c-a299-4c98-b07f-26f6c522bfa7}} in August to {{fact:8be6e746-dc43-4b96-aecc-08d235db6b5b}} in October, with cash at {{fact:babfaa0c-ec08-429f-8055-ec6bc6e11692}} against a {{fact:88f34b53-998a-4771-8672-2e6c09998c39}} floor. The cushion is still comfortable, but the pace of decline matters. Revenue is running ahead of plan, so the cash drain li |
| `tavernel-grid` | early_warning | none | Headroom slipped only marginally, from {{fact:def82ec4-851e-46d9-b5d5-6ce0d5c3f318}} to {{fact:cb16809d-b762-499d-9bf6-cf6b3afbf507}}, and revenue sits at {{fact:442f16be-a50d-45ce-bd68-1b92f3bf5bee}} of plan versus a {{fact:fe18f623-95a9-4579-ad42-444fe67aed32}} minimum. This is close to flat and does not explain the falling cash balance. |
| `vantrell-labs` | certificate | none | All three covenants are reported in the summary table on page one and in Schedule 1 on page two. |
| `vantrell-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `vantrell-labs` | certificate | none | No embedded instructions were found in the document. |
| `vantrell-labs` | early_warning | none | Cushion over the minimum cash covenant has narrowed steadily, from {{fact:1f3b4a83-cbd3-4973-8006-23b979b2e4b1}} in August to {{fact:f34c8b04-9ad3-430a-ba6a-66e0882b68ff}} in September and {{fact:411e31f9-e3e0-4e1b-870f-67ed760b788c}} in October. Cash of {{fact:a506654a-cb2b-4bf7-875e-6944c8e8758d}} still sits well above the {{fact:46daa775-581b-4f9c-9ffa-ddd88a90cf30}} floor, so the concern is th |

## Observations

- `meridew-analytics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `meridew-analytics`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact


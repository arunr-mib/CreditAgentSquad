# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T03:04:48+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 4 borrower(s) (['orbitline-systems', 'pellham-grain', 'pellucid-sensors', 'quillon-ai']); 1 pass(es); run time 406.2 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (385 of 385) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 75.0% (the book expects 75.0%) |
| Cycles reaching the signals stage or beyond | 4 of 4 |
| Cycles closed | 4 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 166,368 / 44,418 |

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
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `quillon-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillon-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
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

## Observations

- `orbitline-systems`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `orbitline-systems`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellham-grain`: guardrail note on covenant: number_in_words -> claim_dropped: a claim stated a figure that is not a fact reference: a quantity was stated in words; quantities come from fact references
- `pellham-grain`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `pellham-grain`: guardrail note on covenant: figure_untraceable -> abstain: a figure was typed, not referenced, and matches no fact or cited quote
- `pellucid-sensors`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `pellucid-sensors`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `quillon-ai`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `quillon-ai`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed


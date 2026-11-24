# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T03:27:40+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 3 borrower(s) (['kestrel-bay-packaging', 'harrowgate-precision', 'briarstone-beverage']); 1 pass(es); run time 22.2 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- run-error: 1 cycle(s) failed on an error, so nothing was measured. First: briarstone-beverage (review run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (502 of 502) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 33.3% (the book expects 33.3%) |
| Cycles reaching the signals stage or beyond | 3 of 3 |
| Cycles closed | 0 of 3 |
| Other disagreements with the truth | 1 |
| Model tokens in / out | 123,645 / 40,656 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 2 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | review_prep (needs_person) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | 2 |
| `harrowgate-precision` | clean | review_prep (needs_person) | none | none | 100.0% (199/199) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | review_prep (needs_person) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `briarstone-beverage` | wrong-abstain | review run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json |  |
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run abstained: no answer |  |
| `briarstone-beverage` | run-error | review run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/review/briarstone-beverage/2026-09-30/02.json |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager REFUSED ValueError: there is no commentary to approve; write at least a summary first |

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
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | spreading | none | The cover page states units as 'In thousands of u.s. dollars'; the statement pages use the phrase reported as the scale statement. |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | early_warning | none | Total leverage of {{fact:cf09aa30-14d6-4214-b8dc-b7369f0a5824}} is above the {{fact:cf5ce94d-59c2-485d-ac3c-f864cf033957}} maximum, so headroom is negative at {{fact:b1a2482c-4174-437b-956c-da582a08fa26}}. On these figures the covenant appears already breached, not merely tight. Debt is high relative to earnings while the liquidity cushion is also shrinking. |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:0f340d0e-1385-41ee-a0dd-bda8b6003f21}} sits just above its {{fact:13194732-46fe-4a3a-afd0-41790b749b4f}} floor, leaving headroom of only {{fact:9e590747-9307-45f2-be07-cc4a806e601c}}. That is a thin short-term liquidity cushion. Alongside the leverage overshoot, it points to pressure on both debt capacity and near-term cash. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom slipped from {{fact:c016ad45-01b1-4a84-9ef1-bd2b68269efc}} in March to {{fact:f33cbd85-a873-4f98-99bf-bd4fb0d746df}} in June. It then fell sharply to {{fact:9e590747-9307-45f2-be07-cc4a806e601c}} by September. The deterioration is accelerating, which explains why the low-headroom signal fired and suggests the floor could be at risk if the trend continues. |

## Observations

- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `briarstone-beverage`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: summary: fact 6d06dcc5-63d4-4916-b022-ab56b87c671d is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: performance: fact aec7e8e1-7e93-4508-96bf-b2e38896fe8e is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: covenants: fact 2d143911-9533-4c9b-9e43-d23da7c27edc is not in scope
- `harrowgate-precision`: guardrail note on review: fact_unknown -> section_dropped: collateral: fact 544ba8e2-841d-43c4-bc48-2b162effa319 is not in scope
- `harrowgate-precision`: guardrail note on review: no_facts -> section_dropped: risks: makes no reference to any fact
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


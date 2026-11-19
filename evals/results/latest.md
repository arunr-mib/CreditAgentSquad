# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-19T18:41:00+00:00; commit `b96b0e7db5f37e1c82ca96ae7245f2a90ef86cc4`; 1 borrower(s) (['kestrel-bay-packaging']); 1 pass(es); run time 120.8 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (102 of 102) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 0.0%) |
| Cycles reaching the signals stage or beyond | 1 of 1 |
| Cycles closed | 1 of 1 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 42,519 / 13,110 |

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
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run abstained: no answer |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Schedule 1 leverage calculation adds back pro forma cost savings from plant consolidation to arrive at EBITDA as calculated by the Borrower; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | early_warning | none | Total leverage of {{fact:c601b895-84de-4c17-924d-3a457d9892bf}} is above the {{fact:4836287c-1df0-4096-9e1b-02a7553358db}} maximum, so headroom is negative at {{fact:63375695-c4ab-42c7-83aa-4c5a3acfd506}}. On these figures the covenant appears to be breached, not just tight. Debt is high relative to earnings, and this coincides with shrinking liquidity headroom on the current ratio. |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:ca57b164-5c32-4cfe-a039-7f0017a2a32a}} still clears the {{fact:7c9ed9aa-c5b8-49ec-90d5-6d3d9e2f105b}} minimum, but with only {{fact:f34ba902-b8c0-40ad-81a1-6424bca6a595}} headroom. Thin short-term liquidity on top of leverage already over its limit points to pressure on both debt load and near-term cash. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom slipped from {{fact:883e7a9a-0fe4-42ce-9bcc-c0fc09932e29}} in March to {{fact:590ebb45-361b-46f4-965b-14f83831998f}} in June, then fell sharply to {{fact:f34ba902-b8c0-40ad-81a1-6424bca6a595}} in September. This shows the thin liquidity cushion is a worsening trend rather than a one-off, with most of the deterioration in the third quarter. |

## Observations

- `kestrel-bay-packaging`: guardrail note on covenant: step_cap -> abstain: the run reached its step cap before giving an answer


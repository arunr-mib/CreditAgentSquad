# Evaluation scorecard: monitoring-cycle (live)

**Mode: live.** Mode live: answers came from a live model.

- Generated 2026-11-18T22:36:06+00:00; commit `fa9f7e07843396cf1d96e950e1fc18a082742c18`; 3 borrower(s) (['kestrel-bay-packaging', 'briarstone-beverage', 'harrowgate-precision']); 1 pass(es); run time 258.5 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 57.8% (290 of 502) |
| Extraction abstain rate (expected facts with no usable fact) | 42.2% |
| Covenant outcome accuracy | 28.6% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 71.4% |
| Exception precision | 20.0% |
| Exception recall | 50.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 33.3%) |
| Cycles reaching the signals stage or beyond | 1 of 3 |
| Cycles closed | 1 of 3 |
| Other disagreements with the truth | 1 |
| Model tokens in / out | 78,407 / 28,924 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 1 |
| false-exception | 4 |
| wrong-citation | 0 |
| wrong-abstain | 8 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | spreading (needs_person) | bb.over_advance | intake.unclassified, spread.value_unverified | 46.8% (94/201) | 0/2 | 7 |
| `harrowgate-precision` | clean | spreading (needs_person) | none | spread.value_unverified | 47.2% (94/199) | 0/3 | 5 |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch, intake.unclassified | 100.0% (102/102) | 2/2 | 2 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `briarstone-beverage` | missed-exception | bb.over_advance | expected for scenario over_advance; the cycle rests at spreading (needs_person) |  |
| `briarstone-beverage` | false-exception | intake.unclassified | not expected for scenario over_advance: bbc-2026-09-30.pdf: the Intake Agent raised a concern |  |
| `briarstone-beverage` | false-exception | spread.value_unverified | not expected for scenario over_advance: Briarstone Beverage Company interim financial statements, Q3 2026: 2 row(s) filed under a line their label does not name |  |
| `briarstone-beverage` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.73; the product recorded no test |  |
| `briarstone-beverage` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.97; the product recorded no test |  |
| `briarstone-beverage` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `harrowgate-precision` | false-exception | spread.value_unverified | not expected for scenario clean: Harrowgate Precision Components, Inc. interim financial statements, Q3 2026: 2 row(s) filed under a line their label does not name |  |
| `harrowgate-precision` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.51; the product recorded no test |  |
| `harrowgate-precision` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.89; the product recorded no test |  |
| `harrowgate-precision` | wrong-abstain | min_tnw @ 2026-09-30 | truth compliant at 22137000; the product recorded no test |  |
| `harrowgate-precision` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `kestrel-bay-packaging` | false-exception | intake.unclassified | not expected for scenario hidden_breach: cc-2026-09-30.pdf: the Intake Agent raised a concern |  |
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run abstained: no answer |  |
| `briarstone-beverage` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | spreading | intake.unclassified, spread.value_unverified | none (left open) |
| `harrowgate-precision` | spreading | spread.value_unverified | none (left open) |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch, intake.unclassified | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | intake.unclassified, review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Observations

- `briarstone-beverage`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `briarstone-beverage`: guardrail note on spreading: unknown_key -> dropped: stated.bs.total_equity is not a line the agent may fill
- `briarstone-beverage`: guardrail note on spreading: unknown_key -> dropped: stated.bs.total_equity is not a line the agent may fill
- `harrowgate-precision`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `harrowgate-precision`: guardrail note on spreading: unknown_key -> dropped: stated.bs.total_equity is not a line the agent may fill
- `harrowgate-precision`: guardrail note on spreading: unknown_key -> dropped: stated.bs.total_equity is not a line the agent may fill
- `kestrel-bay-packaging`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kestrel-bay-packaging`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kestrel-bay-packaging`: guardrail note on covenant: step_cap -> abstain: the run reached its step cap before giving an answer


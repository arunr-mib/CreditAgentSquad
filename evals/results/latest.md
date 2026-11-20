# Evaluation scorecard: monitoring-cycle (standin)

**STAND-IN RUN. NOT MODEL PERFORMANCE.** A perfect reader built from the synthetic book's ground truth answered in place of the model. This run proves the pipeline, the workflow and the grader end to end; it says nothing about how a model reads these documents.

- Generated 2026-11-20T17:48:33+00:00; commit `802e9e7f2024b9d876b00edcaada3818adc850fc`; 21 borrower(s) (whole book); 1 pass(es); run time 151.4 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; the stand-in suite must also agree with the truth in full, apart from listed known findings.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (2677 of 2677) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 47.6% (the book expects 47.6%) |
| Cycles reaching the signals stage or beyond | 17 of 21 |
| Cycles closed | 17 of 21 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | not measured / not measured |

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
| `ashgrove-fleet` | missing_page | spreading (needs_person) | spread.does_not_foot | spread.does_not_foot | 100.0% (72/72) | 3/3 | none |
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brindlewood-home-health` | clean | closed (closed) | none | none | 100.0% (105/105) | 3/3 | none |
| `calder-finch-staffing` | step_up | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (100/100) | 2/2 | none |
| `dunmore-industrial-supply` | clean | closed (closed) | none | none | 100.0% (187/187) | 3/3 | none |
| `eastmere-building` | late_reporting | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 2/2 | none |
| `halvorsen-plastics` | restated_comparative | closed (closed) | spread.restatement | spread.restatement | 100.0% (191/191) | 2/2 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | none |
| `larkspur-environmental` | clean | closed (closed) | none | none | 100.0% (103/103) | 3/3 | none |
| `marlowe-ridge-logistics` | clean | closed (closed) | none | none | 100.0% (107/107) | 3/3 | none |
| `northgale-electrical` | miscounted_ineligible | closed (closed) | bb.certificate_mismatch | bb.certificate_mismatch | 100.0% (189/189) | 2/2 | none |
| `ostrander-valley-foods` | clean | closed (closed) | none | none | 100.0% (201/201) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `quillfeather-bakery` | addback_over_cap | closed (closed) | none | none | 100.0% (104/104) | 2/2 | none |
| `sablewood-dental` | clean | closed (closed) | none | none | 100.0% (98/98) | 2/2 | none |
| `stanmoor-mechanical` | image_only | spreading (needs_person) | spread.image_only | spread.image_only | not measured (0/0) | 3/3 | none |
| `tallwater-foodservice` | clean | closed (closed) | none | none | 100.0% (202/202) | 2/2 | none |
| `thornbury-metal` | deteriorating_trend | closed (closed) | signal.high | signal.high | 100.0% (105/105) | 3/3 | none |
| `vantry-freight` | unapproved_amendment | covenant_testing (needs_person) | covenant.reported_mismatch, terms.unapproved_amendment | covenant.reported_mismatch, terms.unapproved_amendment | 100.0% (104/104) | 2/2 | none |
| `wrenfield-diagnostics` | scale_trap | closed (closed) | none | none | 100.0% (108/108) | 4/4 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `ashgrove-fleet` | spreading | spread.does_not_foot | none (left open) |
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brindlewood-home-health` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `calder-finch-staffing` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `calder-finch-staffing` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `dunmore-industrial-supply` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `eastmere-building` | awaiting_package | intake.missing_document | none (left open) |
| `halvorsen-plastics` | review_prep | review.commentary_approval, spread.restatement | spread.restatement: ask_borrower by analyst, review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `larkspur-environmental` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `marlowe-ridge-logistics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `northgale-electrical` | borrowing_base | bb.certificate_mismatch | bb.certificate_mismatch: bank_figures_stand by analyst |
| `northgale-electrical` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ostrander-valley-foods` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillfeather-bakery` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `sablewood-dental` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `stanmoor-mechanical` | spreading | spread.image_only | none (left open) |
| `tallwater-foodservice` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `thornbury-metal` | signals | signal.high | signal.high: acknowledged by analyst |
| `thornbury-metal` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `vantry-freight` | covenant_testing | covenant.reported_mismatch, terms.unapproved_amendment | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `vantry-freight` | covenant_testing | terms.unapproved_amendment | none (left open) |
| `wrenfield-diagnostics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Observations

- `briarstone-beverage`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `calder-finch-staffing`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `calder-finch-staffing`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `dunmore-industrial-supply`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `larkspur-environmental`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `quillfeather-bakery`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `thornbury-metal`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `vantry-freight`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `wrenfield-diagnostics`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `briarstone-beverage`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `calder-finch-staffing`: guardrail note on covenant: error -> abstain: the run did not finish
- `calder-finch-staffing`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `dunmore-industrial-supply`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `kestrel-bay-packaging`: guardrail note on covenant: error -> abstain: the run did not finish
- `kestrel-bay-packaging`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `larkspur-environmental`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `pellham-grain`: guardrail note on covenant: error -> abstain: the run did not finish
- `pellham-grain`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `quillfeather-bakery`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `thornbury-metal`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `vantry-freight`: guardrail note on covenant: error -> abstain: the run did not finish
- `wrenfield-diagnostics`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them


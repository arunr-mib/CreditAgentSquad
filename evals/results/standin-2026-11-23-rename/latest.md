# Evaluation scorecard: monitoring-cycle (standin)

**STAND-IN RUN. NOT MODEL PERFORMANCE.** A perfect reader built from the synthetic book's ground truth answered in place of the model. This run proves the pipeline, the workflow and the grader end to end; it says nothing about how a model reads these documents.

- Generated 2026-11-23T08:28:41+00:00; commit `f254a77f80765d6c6100a7571de7c28e2ed399f1`; 20 borrower(s) (whole book); 1 pass(es); run time 154.1 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; the stand-in suite must also agree with the truth in full, apart from listed known findings.

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
| `brackmere-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | none |
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `calvere-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `cindrel-tech` | cindrel_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `datamarrow` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | none |
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

None. Every borrower's outcome agrees with the book.

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
| `cindrel-tech` | intake | none | The file names no company and shows a different year. |

## Observations

- `brackmere-medical`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `briarstone-beverage`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `brightvane-energy`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `datamarrow`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `datamarrow`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kelvra-bio`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `meridew-analytics`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `meridew-analytics`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `mosswell-robotics`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `nimbusfield-security`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `orbitline-systems`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellucid-sensors`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `tarnavi-ai`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `tavernel-grid`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `vantrell-labs`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `veridia-payments`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `brackmere-medical`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `briarstone-beverage`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `brightvane-energy`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `datamarrow`: guardrail note on covenant: error -> abstain: the run did not finish
- `datamarrow`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `kelvra-bio`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `kestrel-bay-packaging`: guardrail note on covenant: error -> abstain: the run did not finish
- `kestrel-bay-packaging`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `meridew-analytics`: guardrail note on covenant: error -> abstain: the run did not finish
- `meridew-analytics`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `mosswell-robotics`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `nimbusfield-security`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `orbitline-systems`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `pellham-grain`: guardrail note on covenant: error -> abstain: the run did not finish
- `pellham-grain`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `pellucid-sensors`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `tarnavi-ai`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `tavernel-grid`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `vantrell-labs`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `veridia-payments`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them


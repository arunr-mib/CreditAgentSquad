# Evaluation scorecard: monitoring-cycle (standin)

**STAND-IN RUN. NOT MODEL PERFORMANCE.** A perfect reader built from the synthetic book's ground truth answered in place of the model. This run proves the pipeline, the workflow and the grader end to end; it says nothing about how a model reads these documents.

- Generated 2026-11-18T02:10:23+00:00; commit `bad7de29b7b0e266870ea663a2d8623cd81fa48f`; 21 borrower(s) (whole book); 1 pass(es); run time 104.0 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 76.
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
| `eastmere-building` | late_reporting | awaiting_package (needs_person) | intake.missing_document, signal.high | intake.missing_document, signal.high | not measured (0/0) | 2/2 | none |
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
| `eastmere-building` | awaiting_package | intake.missing_document, signal.high | signal.high: acknowledged by analyst |
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

## Mutation checks

Each check tampers with the stand-in's answer in one way a model could be wrong, runs the live cycle, and records who caught it. `product`: refused into a work item or a guardrail note. `grader`: accepted by the product and named only by the grader, which is a finding about the product. `recovered`: code reads that part from the page itself, so the reader's mistake has no effect. `SLIPPED`: caught by neither.

Totals: product 37, product and grader 9, recovered 1.

| Mutation | What the reader got wrong | Borrower | Caught by | Evidence |
|---|---|---|---|---|
| spread-wrong-figure | a figure with one digit wrong (it still parses) | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-figure-from-another-row | a real figure from the wrong row | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-prior-year-figure | a figure from the prior-year column under the current header | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-whole-prior-year-column | the whole prior-year column spread as the period | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-dropped-line | a printed line dropped and claimed absent | `harrowgate-precision` | product | work item: spread.does_not_foot |
| spread-dropped-line-and-totals | a line dropped together with the printed totals above it | `harrowgate-precision` | product | work item: spread.does_not_foot |
| spread-dropped-supplemental-line | a supplemental line (no total covers it) dropped and claimed absent | `harrowgate-precision` | product | work item: spread.does_not_foot |
| spread-units-omitted | the 'in thousands' phrase not reported | `harrowgate-precision` | product | work item: spread.value_unverified; guardrail note: spreading scale_conflict -> person |
| spread-rows-swapped-within-a-total | two rows of one subtotal mapped to each other's template lines | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-debt-mapped-to-payables | the line of credit and accounts payable mapped to each other's lines | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-prior-year-under-a-spanning-header | the prior-year column read under a header naming both periods | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-printed-totals-not-read | no printed total reported, so nothing could be footed | `harrowgate-precision` | product | work item: spread.does_not_foot |
| spread-supplemental-row-reported-twice | one printed row reported twice, so its figure would be added twice | `harrowgate-precision` | product | work item: spread.value_unverified |
| spread-note-types-a-figure | a note that types a figure | `harrowgate-precision` | product | guardrail note: spreading figure_untraceable -> dropped |
| cert-misread-threshold | a threshold misread (1.05x read as 1.50x) | `harrowgate-precision` | product | work item: spread.value_unverified |
| cert-threshold-from-another-row | a threshold taken from another covenant's row | `harrowgate-precision` | product | work item: spread.value_unverified |
| cert-units-omitted | the certificate's 'in thousands' phrase not reported | `harrowgate-precision` | product | work item: spread.value_unverified |
| cert-rows-swapped | two covenant rows attributed to each other's covenants | `harrowgate-precision` | product | work item: spread.value_unverified |
| bb-aging-note-dropped | an affiliate customer's note not reported | `harrowgate-precision` | recovered | nothing changed and nothing is wrong: code reads this from the page itself, so the reader's omission has no effect |
| bb-aging-figure-misread | an aging figure with one digit wrong | `harrowgate-precision` | product | work item: bb.certificate_mismatch |
| bb-aging-row-dropped | a customer left out of the aging | `harrowgate-precision` | product and grader | work item: bb.certificate_mismatch; grader: invented-number [bbc.ar.001.current @ 2026-09-30], invented-number [bbc.ar.001.days_31_60 @ 2026-09-30], invented-number [bbc.ar.001.days_61_90 @ 2026-09-30], invented-number [bbc.ar.001.over_90 @ 2026-09-30] and 59 more |
| bb-lines-misnamed | commitment and loans outstanding attributed to each other's lines | `harrowgate-precision` | product | work item: bb.certificate_mismatch |
| bb-affiliate-note-and-lines-dropped | an affiliate's note dropped and the certificate lines that would show it left out | `harrowgate-precision` | product | work item: bb.certificate_mismatch |
| bb-contra-note-and-lines-dropped | a contra note dropped and the certificate lines that would show it left out | `harrowgate-precision` | product | work item: bb.certificate_mismatch |
| intake-misclassified | a compliance certificate classified as interim statements | `harrowgate-precision` | product | work item: intake.missing_document, intake.unclassified |
| intake-statements-called-audited | management statements classified as audited | `harrowgate-precision` | product | guardrail note: intake audited_without_report -> quality_changed |
| intake-wrong-period | a certificate filed by its signing date instead of its period end | `harrowgate-precision` | product and grader | work item: intake.missing_document; grader: document-filing [cc-2026-09-30.pdf] |
| review-types-a-figure | commentary that types a figure | `harrowgate-precision` | product | guardrail note: review figure_untraceable -> section_dropped |
| review-figure-dressed-as-a-date | commentary with a figure placed so it reads as a date ('above 4 may') | `harrowgate-precision` | product | guardrail note: review figure_untraceable -> section_dropped |
| review-figure-as-a-list-marker | commentary with figures in brackets like list markers | `harrowgate-precision` | product | guardrail note: review figure_untraceable -> section_dropped |
| review-quantity-in-words | commentary stating a ratio in words | `harrowgate-precision` | product | guardrail note: review number_in_words -> section_dropped |
| review-figure-as-an-identifier | commentary with a change written like an identifier ('up-12 percent') | `harrowgate-precision` | product | guardrail note: review figure_untraceable -> section_dropped |
| review-figure-as-a-note-number | commentary with a ratio written as a note number | `harrowgate-precision` | product | guardrail note: review figure_untraceable -> section_dropped |
| review-cites-unknown-fact | commentary that references a fact that does not exist | `harrowgate-precision` | product | guardrail note: review fact_unknown -> section_dropped |
| spread-units-invented | an 'in thousands' phrase reported for a statement in whole dollars | `sablewood-dental` | product | work item: spread.value_unverified; guardrail note: spreading scale_quote -> person |
| spread-debt-mapped-to-payables-on-a-breach | the same mis-mapping on a borrower whose leverage fails | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-mapped-to-other-liabilities-on-a-breach | long-term debt and other liabilities mapped to each other's lines, hiding debt on a borrower whose leverage fails | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-swapped-with-label-fragments | long-term debt and other liabilities swapped, reporting only fragments of each row label | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-folded-into-other-liabilities | long-term debt filed as a second row of other liabilities and declared absent | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-principal-read-from-another-supplemental-row | scheduled principal read from the financed-capex row (no total covers supplemental lines) | `pellham-grain` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.breach], signals-not-run [signals @ 2026-09-30] |
| spread-cash-taxes-read-from-another-supplemental-row | cash taxes read from the financed-capex row | `pellham-grain` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.breach], signals-not-run [signals @ 2026-09-30] |
| cert-claims-compliance | a certificate read as claiming compliance where it reports a breach | `pellham-grain` | product | work item: spread.value_unverified |
| cert-breach-read-as-passing-value | the breaching covenant's reported value read as a passing one | `pellham-grain` | product | work item: spread.value_unverified |
| cert-flag-from-the-next-row | the compliance entry taken from a neighbouring row, with a label fragment found on every row | `pellham-grain` | product | work item: spread.value_unverified |
| bb-ineligible-inventory-named-by-a-fragment | work in process reported as 'process' with the inventory lines of the certificate left out, turning an over-advance into availability | `briarstone-beverage` | product | work item: bb.certificate_mismatch |
| bb-receivable-filed-as-inventory | a customer's receivable total added as an inventory row, certificate lines left out | `briarstone-beverage` | product and grader | work item: bb.certificate_mismatch; grader: borrowing-base-line [availability @ 2026-09-30], borrowing-base-line [borrowing_base @ 2026-09-30], borrowing-base-line [borrowing_limit @ 2026-09-30], borrowing-base-line [inventory_availability @ 2026-09-30] and 4 more |
| bb-letters-of-credit-from-an-empty-row | letters of credit read from another line's empty cell | `tallwater-foodservice` | product | work item: bb.certificate_mismatch |


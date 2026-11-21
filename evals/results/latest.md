# Evaluation scorecard: monitoring-cycle (standin)

**STAND-IN RUN. NOT MODEL PERFORMANCE.** A perfect reader built from the synthetic book's ground truth answered in place of the model. This run proves the pipeline, the workflow and the grader end to end; it says nothing about how a model reads these documents.

- Generated 2026-11-21T00:29:14+00:00; commit `aa93f32a25199fac3ba2740339e01fbb29e36a41`; 20 borrower(s) (whole book); 1 pass(es); run time 164.0 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 91.
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
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `corvane-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | none |
| `dataflake` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | none |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | none |
| `halcyon-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | none |
| `lumora-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | none |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `quillon-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `stripple-tech` | stripple_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | none |
| `tessaract-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `tidewell-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | none |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brightvane-energy` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `corvane-analytics` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `corvane-analytics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `dataflake` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `dataflake` | signals | signal.high | signal.high: acknowledged by analyst |
| `dataflake` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `ferrogate-cloud` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `halcyon-grid` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `lumora-health` | awaiting_package | intake.missing_document | none (left open) |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `pellucid-sensors` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillon-ai` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `stripple-tech` | intake | intake.unclassified | intake.unclassified: not_needed by analyst |
| `stripple-tech` | spreading | spread.value_unverified | none (left open) |
| `tessaract-labs` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `tidewell-medical` | review_prep | cash.statement_mismatch, review.commentary_approval | cash.statement_mismatch: reviewed by credit_officer, review.commentary_approval: approve by portfolio_manager |
| `veridia-payments` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Figures held for a person

| Borrower | Item | Filed under | Label the reader gave | Label on the page | Reason |
|---|---|---|---|---|---|
| `stripple-tech` | spread.value_unverified | `bs.capitalised_software` | Capitalised software development costs | Capitalised software development costs | mapping_doubt |
| `stripple-tech` | spread.value_unverified | `bs.deferred_revenue_current` | Contract liabilities | Contract liabilities | mapping_doubt |
| `stripple-tech` | spread.value_unverified | `cf.capitalised_software_spend` | Software development costs | Software development costs | mapping_doubt |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `stripple-tech` | intake | none | The file names no company and shows a different year. |

## Observations

- `briarstone-beverage`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `brightvane-energy`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `corvane-analytics`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `corvane-analytics`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `dataflake`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `dataflake`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `halcyon-grid`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kelvra-bio`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `kestrel-bay-packaging`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `mosswell-robotics`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `nimbusfield-security`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `orbitline-systems`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 covenant call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellham-grain`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `pellucid-sensors`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `quillon-ai`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `tessaract-labs`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `tidewell-medical`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `veridia-payments`: standin-unanswered: 1 early_warning call(s) were left unanswered by the stand-in; the product fell back without a recommendation or explanation
- `briarstone-beverage`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `brightvane-energy`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `corvane-analytics`: guardrail note on covenant: error -> abstain: the run did not finish
- `corvane-analytics`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `dataflake`: guardrail note on covenant: error -> abstain: the run did not finish
- `dataflake`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `halcyon-grid`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `kelvra-bio`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `kestrel-bay-packaging`: guardrail note on covenant: error -> abstain: the run did not finish
- `kestrel-bay-packaging`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `mosswell-robotics`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `nimbusfield-security`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `orbitline-systems`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `pellham-grain`: guardrail note on covenant: error -> abstain: the run did not finish
- `pellham-grain`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `pellucid-sensors`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `quillon-ai`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `tessaract-labs`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `tidewell-medical`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them
- `veridia-payments`: guardrail note on early_warning: error -> nothing_stored: the Early Warning Agent returned no usable answer; the signals stand as code fired them

## Mutation checks

Each check tampers with the stand-in's answer in one way a model could be wrong, runs the live cycle, and records who caught it. `product`: refused into a work item or a guardrail note. `grader`: accepted by the product and named only by the grader, which is a finding about the product. `recovered`: code reads that part from the page itself, so the reader's mistake has no effect. `SLIPPED`: caught by neither.

Totals: product 36, product and grader 9, recovered 1.

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
| spread-debt-mapped-to-payables-on-a-breach | the same mis-mapping on a borrower whose leverage fails | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-mapped-to-other-liabilities-on-a-breach | long-term debt and other liabilities mapped to each other's lines, hiding debt on a borrower whose leverage fails | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-swapped-with-label-fragments | long-term debt and other liabilities swapped, reporting only fragments of each row label | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-term-debt-folded-into-other-liabilities | long-term debt filed as a second row of other liabilities and declared absent | `kestrel-bay-packaging` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.reported_mismatch], signals-not-run [signals @ 2026-09-30] |
| spread-principal-read-from-another-supplemental-row | scheduled principal read from the financed-capex row (no total covers supplemental lines) | `pellham-grain` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.breach], signals-not-run [signals @ 2026-09-30] |
| spread-cash-taxes-read-from-another-supplemental-row | cash taxes read from the financed-capex row | `pellham-grain` | product and grader | work item: spread.value_unverified; grader: missed-exception [covenant.breach], signals-not-run [signals @ 2026-09-30] |
| cert-claims-compliance | a certificate read as claiming compliance where it reports a breach | `pellham-grain` | product | work item: spread.value_unverified |
| cert-breach-read-as-passing-value | the breaching covenant's reported value read as a passing one | `pellham-grain` | product | work item: spread.value_unverified |
| cert-flag-from-the-next-row | the compliance entry taken from a neighbouring row, with a label fragment found on every row | `pellham-grain` | product | work item: spread.value_unverified |
| cert-runway-reported-as-a-number | a not-meaningful runway reported with a figure | `ferrogate-cloud` | product | work item: spread.value_unverified |
| bb-ineligible-inventory-named-by-a-fragment | work in process reported as 'process' with the inventory lines of the certificate left out, turning an over-advance into availability | `briarstone-beverage` | product | work item: bb.certificate_mismatch |
| bb-receivable-filed-as-inventory | a customer's receivable total added as an inventory row, certificate lines left out | `briarstone-beverage` | product and grader | work item: bb.certificate_mismatch; grader: borrowing-base-line [availability @ 2026-09-30], borrowing-base-line [borrowing_base @ 2026-09-30], borrowing-base-line [borrowing_limit @ 2026-09-30], borrowing-base-line [inventory_availability @ 2026-09-30] and 4 more |


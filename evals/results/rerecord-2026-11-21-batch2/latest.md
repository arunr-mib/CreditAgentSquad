# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T07:55:50+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 4 borrower(s) (['kelvra-bio', 'mosswell-robotics', 'nimbusfield-security', 'orbitline-systems']); 1 pass(es); run time 150.3 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- pass 1: 4 invented-number

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
| Model tokens in / out | 152,313 / 40,286 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 4 |
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
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | 1 |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kelvra-bio` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread.' |  |
| `mosswell-robotics` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 (capitalised software roll-forward, month only) on page 5 was not spread; it has no corresponding template lines.' |  |
| `nimbusfield-security` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a one-month capitalised software rollforward; no template line was taken from it.' |  |
| `orbitline-systems` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page five is a one-month rollforward of capitalised software; it was not spread as it maps to no separate template line.' |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `orbitline-systems` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `kelvra-bio` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `kelvra-bio` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `kelvra-bio` | certificate | none | No embedded instructions were found in the document. |
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:0c73df68-653b-454b-8a58-9d81ac5c4e5f}} in August to {{fact:2a3a396e-3d99-40dd-a6cd-973f9f582c1e}} in October, suggesting steady cash burn. Cash of {{fact:8b2ad6fc-66e8-4b7e-bc70-62f77c422c5f}} still sits well above the {{fact:09128128-98ca-49cd-90bb-c8ebfa601184}} floor, so this stands alone as a trend to watch |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:5b3cadc2-4d3a-4705-9229-e009e5b4f1ab}} in August to {{fact:fbba13e9-a874-4dda-8bbd-babcbf4a25ce}} in October, suggesting ongoing cash burn. Cash of {{fact:fee82a9e-46a2-4939-b684-e43405c110d8}} still sits well above the {{fact:9ec6f709-1171-49be-8fdb-096740cfb82b}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:6c5e14bf-038d-451f-98a8-c96f8f96179b}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:d7362521-2c9c-44a5-a24a-e3f36a1e6809}} in August to {{fact:8775773d-469c-4c44-b02b-bade3d4452b3}} in October, with runway at {{fact:c746b4ed-8d18-4439-8674-1ff42a1f6bee}} months against a floor of {{fact:630c254d-1471-4fb0-8e22-60bc5dc8ed50}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:e53ca936-67bd-4911-accb-2b7340013477}} remains above the {{fact:b9b02449-0279-4f33-b9bb-4cf4e737fcaa}} minimum, but headroom dropped from {{fact:47def611-aadb-4032-968d-a723a25a8da2}} in August to {{fact:22dc8874-a5ff-4b77-812d-7550cf39f087}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:8a27379c-e6c9-4471-bbc9-18c9b4bc6883}} of plan against an {{fact:826cdbf2-11da-4955-be7c-8c70b9d676c4}} floor, and headroom has been essentially flat, moving only from {{fact:a97dd6de-e2d1-40f2-bae5-d195293e31b4}} to {{fact:3e767099-3ffd-499e-a3de-6ac1fec713a9}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:4aedce9f-55a4-47eb-9bb2-41b57a80afa9}} against {{fact:d6484092-cc24-4ebc-b93f-2506d3cd9a4a}}), but headroom has fallen steadily from {{fact:4d10c5d3-75ad-4f5c-b10a-cc269fc4c516}} to {{fact:52a5a022-0321-4421-96be-ab3750384dec}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |


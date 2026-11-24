# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T02:57:53+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 4 borrower(s) (['kelvra-bio', 'lumora-health', 'mosswell-robotics', 'nimbusfield-security']); 1 pass(es); run time 320.4 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (186 of 186) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 50.0% (the book expects 50.0%) |
| Cycles reaching the signals stage or beyond | 3 of 4 |
| Cycles closed | 3 of 4 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 117,744 / 33,260 |

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
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `lumora-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | none |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | none |

## Differences from the truth

None. Every borrower's outcome agrees with the book.

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `kelvra-bio` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `lumora-health` | awaiting_package | intake.missing_document | none (left open) |
| `mosswell-robotics` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `nimbusfield-security` | signals | signal.high | signal.high: acknowledged by analyst |
| `nimbusfield-security` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `kelvra-bio` | spreading | 1 | Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread. |
| `kelvra-bio` | spreading | none | This document is a bank account statement for October 2026, not a set of financial statements, so only the two bank account total lines were reported. |
| `kelvra-bio` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `kelvra-bio` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `kelvra-bio` | certificate | none | No embedded instructions were found in the document. |
| `kelvra-bio` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:a5cc90e5-6284-4ae0-959c-8aac343b2d28}} to {{fact:e849c4f5-c89e-46a2-a99e-69d7c5ef0e11}} to {{fact:0e40c1c4-1993-4343-bc36-6f621f1475db}}, consistent with steady cash burn. Cash of {{fact:e135f087-ef39-441e-a2d9-90b2e31308ea}} still sits well above the {{fact:5d992da1-7eea-48af-952f-cdbe15207cd7}} floor. No other signal fired, so this  |
| `mosswell-robotics` | spreading | 1 | Note 1 (capitalised software roll-forward, month only) on page 5 was not spread; it has no corresponding template lines. |
| `mosswell-robotics` | spreading | none | The document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines are reported. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:39a70bb8-5c76-4578-b667-3bbacfdf24eb}} in August to {{fact:87a9e2f6-280b-4436-b792-a2bc7d3456c4}} in September and {{fact:08c4c464-d664-4f78-b775-4e9c2eaebc21}} in October. Cash of {{fact:6ac67879-e877-4543-a08b-598cab953c80}} still sits well above the {{fact:ddd5737d-8265-4ee1-b8d0-1de5eff6213f}} floor. The concern is the trend, a sign |
| `nimbusfield-security` | spreading | 1 | Note 1 on page 5 is a one-month capitalised software rollforward; no template line was taken from it. |
| `nimbusfield-security` | spreading | none | This document is a bank statement for the month of October 2026, not a set of financial statements, so only the two bank account total lines were spread. |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Cash runway has fallen to {{fact:0876a4c5-62e5-4171-8850-2564f739afc2}} months, so the borrower's time to reach profitability or raise new funding is getting short. The steadily falling runway and cash covenant headroom show this is a sustained trend, not a one-off. Revenue tracking ahead of plan suggests the pressure comes from cash burn rather than weak sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant has shrunk each month, from {{fact:85e42179-b128-45b9-8622-58c083af9a0e}} in August to {{fact:817703a5-ed3c-49e1-b9c0-55b878918d35}} in October. Runway of {{fact:5e075111-4594-4eda-9eeb-b1d483aab321}} months is still above the {{fact:caaa8855-1488-43ab-a0d9-d277f5ee9bea}}-month floor, but if the decline continues at this pace, the cushion would be gone withi |
| `nimbusfield-security` | early_warning | none | Unrestricted cash headroom fell from {{fact:62e6d8fc-98c7-419b-9206-889afb0aa3f4}} in August to {{fact:71bf8060-93da-4884-a4a3-fae49d106867}} in October. Cash of {{fact:1300f6f3-f9f0-4192-86c7-2b2024c61b06}} still clears the {{fact:f59c1e75-ca5d-4e05-a55c-f4d06b43784c}} minimum. The falling cash balance is the root of the shrinking runway, so this signal and the runway signals describe the same bu |
| `nimbusfield-security` | early_warning | none | This headroom is essentially flat, moving only from {{fact:973da0b7-3049-49dd-b547-9f41cace8037}} to {{fact:83a42716-5b75-41e8-a15f-2e31b29bc907}}. Revenue is running at {{fact:c113aae2-3896-4363-909b-a6c665eb7f7c}} of plan against an {{fact:c19644d5-7664-4763-b0b6-a0c4ceb67a4d}} floor. This is a mitigating point: it suggests the cash decline is not caused by a revenue shortfall. |
| `nimbusfield-security` | early_warning | none | Cash runway has fallen to {{fact:0876a4c5-62e5-4171-8850-2564f739afc2}} months, so the borrower's time to reach profitability or raise new funding is getting short. The steadily falling runway and cash covenant headroom show this is a sustained trend, not a one-off. Revenue tracking ahead of plan suggests the pressure comes from cash burn rather than weak sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant has shrunk each month, from {{fact:85e42179-b128-45b9-8622-58c083af9a0e}} in August to {{fact:817703a5-ed3c-49e1-b9c0-55b878918d35}} in October. Runway of {{fact:5e075111-4594-4eda-9eeb-b1d483aab321}} months is still above the floor of {{fact:caaa8855-1488-43ab-a0d9-d277f5ee9bea}} months, but if the decline continues at this pace, the cushion would be gone w |
| `nimbusfield-security` | early_warning | none | Unrestricted cash headroom fell from {{fact:62e6d8fc-98c7-419b-9206-889afb0aa3f4}} in August to {{fact:71bf8060-93da-4884-a4a3-fae49d106867}} in October. Cash of {{fact:1300f6f3-f9f0-4192-86c7-2b2024c61b06}} still clears the {{fact:f59c1e75-ca5d-4e05-a55c-f4d06b43784c}} minimum. The falling cash balance is the root of the shrinking runway, so this signal and the runway signals describe the same bu |
| `nimbusfield-security` | early_warning | none | This headroom is essentially flat, moving only from {{fact:973da0b7-3049-49dd-b547-9f41cace8037}} to {{fact:83a42716-5b75-41e8-a15f-2e31b29bc907}}. Revenue is running at {{fact:c113aae2-3896-4363-909b-a6c665eb7f7c}} of plan against an {{fact:c19644d5-7664-4763-b0b6-a0c4ceb67a4d}} floor. This is a mitigating point: it suggests the cash decline is not caused by a revenue shortfall. |

## Observations

- `kelvra-bio`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `kelvra-bio`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `mosswell-robotics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `mosswell-robotics`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `nimbusfield-security`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `nimbusfield-security`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed


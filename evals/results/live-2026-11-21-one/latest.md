# Evaluation scorecard: monitoring-cycle (record)

**Mode: record.** Mode record: answers came from a live model.

- Generated 2026-11-21T02:44:45+00:00; commit `90fa2d718fa66b2232f7c5d3afb6ebb1be387e0d`; 1 borrower(s) (['dataflake']); 1 pass(es); run time 134.0 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: PASSED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (62 of 62) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 0.0% (the book expects 0.0%) |
| Cycles reaching the signals stage or beyond | 1 of 1 |
| Cycles closed | 1 of 1 |
| Other disagreements with the truth | 0 |
| Model tokens in / out | 49,777 / 12,342 |

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
| `dataflake` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `dataflake` | wrong-abstain | covenant run | the run abstained: no answer |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `dataflake` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `dataflake` | signals | signal.high | signal.high: acknowledged by analyst |
| `dataflake` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

## Agent text no person was shown

Prose from the raw model answer that is not among the shown notes: refused by a guardrail, or placed where the product does not show it. Read each one: a refused honest sentence is a defect, and the text is the test case.

| Borrower | Agent | Typed figures | Text |
|---|---|---|---|
| `dataflake` | spreading | 1 | Note 1 on page 5 is a one-month capitalised software rollforward; it was not spread as it covers the month only and has no template line beyond the balance sheet figure. |
| `dataflake` | spreading | none | The document is a bank statement for October 2026, not a set of financial statements, so only the two bank account total lines were reported. |
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | early_warning | none | Dataflake has about {{fact:78f6ae81-0bfe-4964-bff9-c570772de4ee}} months of cash at current burn, which limits its ability to absorb setbacks before it needs new funding. The low-severity runway covenant signal shows this has been shrinking quickly. The cash covenant signals show the same pressure on its balance sheet. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:c6b23fca-d829-47de-afb9-2c23d0a23106}} is below the {{fact:dfe07fca-0fbc-40ee-b40b-3a228a34e2f2}} minimum, giving headroom of {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}}. That means the level is past the threshold, not merely close to it, though the signal is rated medium. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Runway covenant headroom fell from {{fact:0ac55194-1dd2-43ef-8b72-a1df0510d927}} in August to {{fact:3caa60a2-0f31-4409-a26f-9fb416c6117f}} in September and {{fact:09bff13b-0bba-432a-8f89-e9c4a43c04b8}} in October. Runway of {{fact:88465eb6-1917-4cd2-b16b-08d16b705fd9}} months remains above the {{fact:629bd59a-680f-43d2-9cd0-1e4063fb047e}}-month floor, but at this pace the cushion is thin. This is |
| `dataflake` | early_warning | none | Cash covenant headroom moved from {{fact:c62ed519-9cd5-4290-86ff-3a880e7c459e}} in August to {{fact:34304bd5-0c7c-4ff3-a214-d8e31aa6b48b}} in September, then to {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}} in October. The steady decline crossed below the minimum. This shows the medium-severity cash signal reflects ongoing burn, not a one-month dip. |
| `dataflake` | early_warning | none | Dataflake has about {{fact:78f6ae81-0bfe-4964-bff9-c570772de4ee}} months of cash at current burn, which limits its ability to absorb setbacks before it needs new funding. The low-severity runway covenant signal shows this has been shrinking quickly. The cash covenant signals show the same pressure on its balance sheet. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:c6b23fca-d829-47de-afb9-2c23d0a23106}} is below the {{fact:dfe07fca-0fbc-40ee-b40b-3a228a34e2f2}} minimum, giving headroom of {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}}. That means the level is past the threshold, not merely close to it, though the signal is rated medium. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Runway covenant headroom fell from {{fact:0ac55194-1dd2-43ef-8b72-a1df0510d927}} in August to {{fact:3caa60a2-0f31-4409-a26f-9fb416c6117f}} in September and {{fact:09bff13b-0bba-432a-8f89-e9c4a43c04b8}} in October. Runway of {{fact:88465eb6-1917-4cd2-b16b-08d16b705fd9}} months remains above the floor of {{fact:629bd59a-680f-43d2-9cd0-1e4063fb047e}} months, but at this pace the cushion is thin. Thi |
| `dataflake` | early_warning | none | Cash covenant headroom moved from {{fact:c62ed519-9cd5-4290-86ff-3a880e7c459e}} in August to {{fact:34304bd5-0c7c-4ff3-a214-d8e31aa6b48b}} in September, then to {{fact:4485e2b5-96b8-4ad6-ba54-6343194e8b1c}} in October. The steady decline crossed below the minimum. This shows the medium-severity cash signal reflects ongoing burn, not a one-month dip. |

## Observations

- `dataflake`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `dataflake`: guardrail note on spreading: figure_untraceable -> dropped: a note from the agent contained a typed figure and was removed
- `dataflake`: guardrail note on covenant: step_cap -> abstain: the run reached its step cap before giving an answer


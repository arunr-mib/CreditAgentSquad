# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T08:08:38+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 20 borrower(s) (whole book); 1 pass(es); run time 186.5 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- run-error: 4 cycle(s) failed on an error, so nothing was measured. First: corvane-analytics (covenant run): RecordingStale: covenant/corvane-analytics/2026-10-31/revenue_vs_plan/06: the recorded answer cites b2a986eb-c7c6-413d-bef1-4650893c0e5a, described as {"formula_key": "covenant.revenue_vs_plan", "outputs": {"headroom": "-0.1479", "headroom_pct": "-0.1849", "passed": false, "raw_value": "0.6520653789; dataflake (covenant run): RecordingStale: covenant/dataflake/2026-10-31/min_unrestricted_cash/06: the recorded answer cites 42b95c3d-e261-4df8-8225-9c03419e5211, described as {"formula_key": "covenant.min_unrestricted_cash", "outputs": {"headroom": "-400000", "headroom_pct": "-0.08", "passed": false, "raw_value": "4600000", ; kestrel-bay-packaging (covenant run): RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": "-0.04", "passed": false, "raw_value": "2.5986031546731
- pass 1: 17 invented-number

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
| Other disagreements with the truth | 4 |
| Model tokens in / out | 763,814 / 208,566 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 17 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 8 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brightvane-energy` | runway_falling | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `corvane-analytics` | plan_miss | closed (closed) | covenant.breach | covenant.breach | 100.0% (62/62) | 3/3 | 4 |
| `dataflake` | pledged_cash | closed (closed) | covenant.reported_mismatch, signal.high | covenant.reported_mismatch, signal.high | 100.0% (62/62) | 3/3 | 4 |
| `ferrogate-cloud` | cash_flow_positive | closed (closed) | none | none | 100.0% (64/64) | 4/4 | 2 |
| `halcyon-grid` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kelvra-bio` | funding_expected | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 3 |
| `lumora-health` | late_package | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 3/3 | none |
| `mosswell-robotics` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `nimbusfield-security` | funding_slipped | closed (closed) | funding_slipped, signal.high | funding_slipped, signal.high | 100.0% (62/62) | 3/3 | 1 |
| `orbitline-systems` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | 3 |
| `pellucid-sensors` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `quillon-ai` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `stripple-tech` | stripple_package | spreading (needs_person) | intake.unclassified, spread.value_unverified | intake.unclassified, spread.value_unverified | 100.0% (50/50) | 0/3 | 1 |
| `tessaract-labs` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |
| `tidewell-medical` | restricted_account | closed (closed) | cash.statement_mismatch | cash.statement_mismatch | 100.0% (62/62) | 3/3 | 2 |
| `veridia-payments` | clean | closed (closed) | none | none | 100.0% (62/62) | 3/3 | 1 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `brightvane-energy` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1 - Capitalised software) is a month-only rollforward of capitalised software; it was not spread because it is not a ten-month figure and the template has no lines for it.' |  |
| `corvane-analytics` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 (capitalised software roll-forward) covers only the single month and has no template lines; it was not spread.' |  |
| `corvane-analytics` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/corvane-analytics/2026-10-31/revenue_vs_plan/06: the recorded answer cites b2a986eb-c7c6-413d-bef1-4650893c0e5a, described as {"formula_key": "covenant.revenue_vs_plan", "outputs": {"headroom": "-0.1479", "headroom_pct" |  |
| `corvane-analytics` | wrong-abstain | investigation of covenant.breach (revenue_vs_plan) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `dataflake` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a one-month capitalised software rollforward; it was not spread as it covers the month only and has no template line beyond the balance sheet figure.' |  |
| `dataflake` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/dataflake/2026-10-31/min_unrestricted_cash/06: the recorded answer cites 42b95c3d-e261-4df8-8225-9c03419e5211, described as {"formula_key": "covenant.min_unrestricted_cash", "outputs": {"headroom": "-400000", "headroom_ |  |
| `dataflake` | wrong-abstain | investigation of covenant.reported_mismatch (min_unrestricted_cash) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `ferrogate-cloud` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a single-month capitalised software rollforward (start balance, additions, amortisation, end balance); none of its rows were spread as they fit no template line for the ten-month period.' |  |
| `ferrogate-cloud` | invented-number | spreading note | a note shown to a person types a figure: 'The collateral account (ending 9001) is pledged under the venture loan agreement and is not available for withdrawal.' |  |
| `halcyon-grid` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1 - Capitalised software) is a one-month rollforward of capitalised software and was not spread; its closing balance agrees in wording to the balance sheet line.' |  |
| `kelvra-bio` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread.' |  |
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": |  |
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `mosswell-robotics` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 (capitalised software roll-forward, month only) on page 5 was not spread; it has no corresponding template lines.' |  |
| `nimbusfield-security` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a one-month capitalised software rollforward; no template line was taken from it.' |  |
| `orbitline-systems` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page five is a one-month rollforward of capitalised software; it was not spread as it maps to no separate template line.' |  |
| `pellham-grain` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/pellham-grain/2026-09-30/fccr/06: the recorded answer cites 1c16f09a-c51a-4b5b-9af7-5d83aab98236, described as {"formula_key": "covenant.fccr", "outputs": {"headroom": "-0.07", "headroom_pct": "-0.0519", "passed": false |  |
| `pellham-grain` | wrong-abstain | investigation of covenant.breach (fccr) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `pellucid-sensors` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a month-only rollforward of capitalised software; it was not spread as it has no template lines beyond the balance already reported from the balance sheet.' |  |
| `quillon-ai` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 is a month-only capitalised software rollforward (start balance, additions, amortisation, end balance); it has no template line and was not spread.' |  |
| `stripple-tech` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page 5 (capitalised software roll-forward) covers the month only and was not spread.' |  |
| `tessaract-labs` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 on page five is a single-month rollforward of capitalised software (opening balance, additions, amortisation, closing balance); its amortisation row has no template line and was not spread.' |  |
| `tidewell-medical` | invented-number | spreading note | a note shown to a person types a figure: 'Note 1 (page 5) presents a one-month capitalised software roll-forward only; it was not spread, and its closing balance agrees in label to the balance sheet line already reported.' |  |
| `tidewell-medical` | invented-number | spreading note | a note shown to a person types a figure: 'A new restricted escrow collateral account (ending 9002) was opened on October 14, 2026 under an escrow arrangement. It is included in the printed total of pledged and restricted accounts, and the reviewer may wish to  |  |
| `veridia-payments` | invented-number | spreading note | a note shown to a person types a figure: 'Page 5 (Note 1, capitalised software roll-forward) presents the month only and has no matching template lines; it was not spread.' |  |
| `corvane-analytics` | run-error | covenant run | RecordingStale: covenant/corvane-analytics/2026-10-31/revenue_vs_plan/06: the recorded answer cites b2a986eb-c7c6-413d-bef1-4650893c0e5a, described as {"formula_key": "covenant.revenue_vs_plan", "outputs": {"headroom": "-0.1479", "headroom_pct": "-0.1849", "pa |  |
| `dataflake` | run-error | covenant run | RecordingStale: covenant/dataflake/2026-10-31/min_unrestricted_cash/06: the recorded answer cites 42b95c3d-e261-4df8-8225-9c03419e5211, described as {"formula_key": "covenant.min_unrestricted_cash", "outputs": {"headroom": "-400000", "headroom_pct": "-0.08", " |  |
| `kestrel-bay-packaging` | run-error | covenant run | RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": "-0.04", "passe |  |
| `pellham-grain` | run-error | covenant run | RecordingStale: covenant/pellham-grain/2026-09-30/fccr/06: the recorded answer cites 1c16f09a-c51a-4b5b-9af7-5d83aab98236, described as {"formula_key": "covenant.fccr", "outputs": {"headroom": "-0.07", "headroom_pct": "-0.0519", "passed": false, "raw_value": " |  |

## Covenant tests not reached

These tests were not run because the cycle correctly rests on an item a person must settle first. They stay in the covenant accuracy denominator and count as not correct, so accuracy is below 100 percent for this reason alone; they are not failures.

- `stripple-tech`: 3 covenant test(s) not reached. The cycle rests at spreading (spread.value_unverified) on 3 figure(s) held for a person; counted as not correct.

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
| `briarstone-beverage` | certificate | none | Both covenants in the approved terms are reported in the summary table on the first page and are also shown in the calculation schedule on the second page. |
| `briarstone-beverage` | certificate | none | No embedded instructions were found in the document. |
| `briarstone-beverage` | collateral | none | The availability line is labeled as availability with over-advance in brackets and shows a bracketed negative figure; no separate over-advance line is printed, so over_advance is not reported. |
| `briarstone-beverage` | collateral | none | The inventory sublimit line on the certificate has no matching line name in the request and was not reported; advance rate percentage rows were skipped. |
| `briarstone-beverage` | collateral | none | The certification text states that revolving loans outstanding exceed the borrowing base. |
| `briarstone-beverage` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible and that quantities come from perpetual records last counted at the most recent fiscal year end. |
| `briarstone-beverage` | collateral | none | No embedded instructions directed at the reader were found in the document. |
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:5bb9936e-a79d-4b49-9379-61903a37164f}}, or {{fact:d1175779-495b-4a70-b537-690081f6935c}} of the {{fact:61fa02fd-7293-4339-aa3e-27849e762492}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `brightvane-energy` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `brightvane-energy` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `brightvane-energy` | certificate | none | No embedded instructions were found in the document. |
| `brightvane-energy` | early_warning | none | Runway has shortened every month, from {{fact:a9f270d1-d6de-4aa2-8d9c-084ef71741f7}} months at July 31 to {{fact:36557d72-4a03-41b0-aa94-5a89ebc70e80}} months at October 31. This points to sustained cash burn without fresh funding. It is the likely driver of the two covenant headroom signals, which show the same erosion against the runway and cash tests. |
| `brightvane-energy` | early_warning | none | This is the covenant view of the falling runway. Headroom has narrowed from {{fact:66e02d9d-425d-4ee7-b2e4-f4881636ef9d}} in August to {{fact:3eafa849-4199-450b-925a-77f98ac45f59}} in October, with runway at {{fact:7dce1650-b1ed-4218-8c5b-65157290a3eb}} months against a floor of {{fact:ae477cdc-bca7-4844-80cb-9471c7ed671e}}. It is still comfortably compliant, but the steady monthly decline matters |
| `brightvane-energy` | early_warning | none | Unrestricted cash of {{fact:6f1a44c3-2dcf-4ae5-8c8e-44ede76d834b}} still clears the {{fact:fa282cb5-796d-4b1d-a061-3a06e3d06841}} minimum. However, headroom fell from {{fact:7f1beb1e-d6c3-4292-b1ae-abe660c6b517}} to {{fact:a54c52e7-5ebc-434d-86a1-8c610b5bf2e1}} over two months and is now the thinner of the two covenants. It reflects the same cash burn behind the shrinking runway and may be the fir |
| `corvane-analytics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `corvane-analytics` | certificate | none | The borrower reports non-compliance with the Revenue to Plan covenant. |
| `corvane-analytics` | certificate | none | On page one the Revenue to Plan requirement wraps across two lines in the table. |
| `corvane-analytics` | certificate | none | No instructions were found in the document text. |
| `corvane-analytics` | early_warning | none | Revenue reached {{fact:0aaa5b27-efcb-4839-804c-1c59a49c411f}} of plan against a covenant floor of {{fact:eca4c588-7688-4281-9575-8463441228b7}}, so headroom is negative at {{fact:9fbccf4d-87ef-4598-a034-a13487f8717c}}. The covenant measure therefore sits below its threshold, not merely close to it. This is the covenant view of the same shortfall flagged by the revenue-below-plan signal. |
| `corvane-analytics` | early_warning | none | Revenue came in at {{fact:28941227-2608-41a8-a478-f1a9f00e2bc5}} of plan, a material miss for a subscription business whose plan underpins its cash runway. It is the operating cause behind the revenue covenant falling below its floor. If the miss persists, it may also explain the steady erosion in cash headroom. |
| `corvane-analytics` | early_warning | none | Unrestricted cash of {{fact:5da03e7c-2ccc-4aa4-a956-c7d1437979da}} remains well above the {{fact:c55c6808-815d-4430-81f1-4164dee8a892}} minimum, but headroom has declined each month, from {{fact:9010ca13-d259-4826-85b7-5fee1ff84e76}} in August to {{fact:e4d72f4a-96a1-456a-be76-45147818e5ae}} in September and {{fact:797ad210-91d6-4e17-8081-86c0ba735d1c}} in October. Ongoing burn alongside the reven |
| `corvane-analytics` | early_warning | none | Revenue covenant headroom has deteriorated each month, from {{fact:bac8ff7c-0908-4159-95a9-d53dfc264e01}} in August to {{fact:3841d838-1dd5-40ff-b672-5a661c38e3ea}} in September and {{fact:9fbccf4d-87ef-4598-a034-a13487f8717c}} in October. It turned negative in September and the gap widened in October, showing the shortfall is worsening rather than a one-month miss. |
| `dataflake` | certificate | none | The Schedule 1 calculation for Minimum Unrestricted Cash on page two includes cash held in the pledged collateral account within Unrestricted Cash; a reviewer may wish to confirm whether pledged collateral cash qualifies as unrestricted under the credit agreement. |
| `dataflake` | certificate | none | The requirement for Revenue to Plan wraps across two lines in the summary table on page one. |
| `dataflake` | early_warning | none | Runway stands at {{fact:0ff19b07-51ca-42d7-ae59-99a6e2d00cf5}} months at October 31, so at the current burn the cash on hand would be exhausted in well under a year. This is the core repayment concern, and the cash covenant shortfall and the shrinking runway covenant cushion both point the same way. |
| `dataflake` | early_warning | none | Unrestricted cash of {{fact:1dfe566f-e933-4616-a805-c381099cbf41}} is below the covenant minimum of {{fact:09e09a4d-ab73-4d18-b30e-95433fe98863}}, leaving headroom of {{fact:5fd30c26-c5aa-449c-8eea-9427e02d5f79}}. The cushion is not just thin but negative, which reads as the covenant level being crossed. It is the balance-sheet side of the short runway. |
| `dataflake` | early_warning | none | Cash covenant headroom has fallen steadily, from {{fact:460d8d1d-186b-41a1-b5e0-8a945c1a80bc}} in August to {{fact:11f9dc66-e0ef-4fb6-b7f1-f547a069afab}} in September and {{fact:5fd30c26-c5aa-449c-8eea-9427e02d5f79}} in October. The trend shows the shortfall is a sustained cash drain rather than a one-month dip, which reinforces the runway concern. |
| `dataflake` | early_warning | none | Runway covenant headroom has narrowed from {{fact:cec79ffa-c017-4d12-b92a-0c58d704c4be}} in August to {{fact:eb0f414f-949b-479f-9c43-14b72feecb31}} in September and {{fact:323f9be9-066d-432a-b14d-e44dc719a9f6}} in October. Runway of {{fact:2d489a47-c718-4bc3-aabc-c2d5ba9b5231}} months is still above the minimum of {{fact:055cca7a-2241-4355-8260-08a24a5a2a7f}}, but at this pace the cushion could di |
| `ferrogate-cloud` | certificate | none | Minimum Runway is reported as not meaningful because the borrower states it is cash-flow positive, yet the schedule on page two shows net burn figures in parentheses; a reviewer should confirm whether runway was properly assessed. |
| `ferrogate-cloud` | certificate | none | On page one the Required text for Revenue to Plan and Debt Service Coverage Ratio wraps across two lines in the summary table. |
| `ferrogate-cloud` | certificate | none | No instructions were found inside the document. |
| `halcyon-grid` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the Revenue to Plan requirement wraps across two lines in the table. |
| `halcyon-grid` | certificate | none | The summary table header for the actual and compliance columns appears overlapped in the rendering, but row values are legible. |
| `halcyon-grid` | certificate | none | No embedded instructions were found in the document. |
| `halcyon-grid` | early_warning | none | Cash headroom has fallen steadily, from {{fact:96d31d58-a519-41c5-a0a3-ea2ff4049fe2}} in August to {{fact:1d42283a-30eb-4c81-b2ed-f0902ed0954f}} in October, with unrestricted cash of {{fact:15cdc9a5-f8cc-4a7e-8578-f3966a4e3e01}} against a {{fact:17dc8b46-ed7b-4896-a7f2-fb807088e267}} floor. Revenue is running ahead of plan, so the burn seems to come from spending rather than a sales shortfall. If  |
| `halcyon-grid` | early_warning | none | Revenue is at {{fact:42307d48-5cda-4eea-9853-428a4f6f00a0}} of plan against an {{fact:16555855-a8d0-4445-afcb-f6642838c943}} minimum. Headroom has only edged down, from {{fact:01ae7be5-0e43-455b-af24-b2a45ca93927}} to {{fact:78e9da8b-1042-402a-8594-f05db6699342}}, which is a minor change. This signal mainly shows that the falling cash position is not explained by weak sales. |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kelvra-bio` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `kelvra-bio` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `kelvra-bio` | certificate | none | No embedded instructions were found in the document. |
| `kelvra-bio` | early_warning | none | Headroom on the minimum unrestricted cash covenant has narrowed each month, from {{fact:18c55cd9-c69c-416c-aa40-a0d84d16acbe}} in August to {{fact:7eb74764-1d18-4045-9639-27911cffac4c}} in October, suggesting steady cash burn. Cash of {{fact:e8a159d6-3147-484d-8c51-71855cd23f48}} still sits well above the {{fact:f1672478-9c87-416f-b0fd-9f101def0947}} floor, so this stands alone as a trend to watch |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:20342148-0db7-454c-b8ff-dbcc738aec69}}): total leverage of {{fact:e6c781d7-9902-4472-9d66-7df3cfe7063c}} sits above the {{fact:70cc0b6f-2587-4791-96fb-18f5947d647b}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:f9e19290-c927-4b93-b687-d321618e2d32}} is only slightly above the {{fact:58cfbf11-8e73-4657-969b-2e0ab0fa5f8b}} minimum, leaving headroom of {{fact:c774adbe-2675-4f7b-bb7f-081eb5c34399}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:608e75e4-4384-442a-967c-70dd1da6b4e2}} in March to {{fact:9889d52e-63ad-40f2-a65d-9ab102b10972}} in June, then dropped sharply to {{fact:c774adbe-2675-4f7b-bb7f-081eb5c34399}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `mosswell-robotics` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `mosswell-robotics` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `mosswell-robotics` | certificate | none | No instructions were found inside the document. |
| `mosswell-robotics` | early_warning | none | Unrestricted cash cushion over the covenant minimum has shrunk steadily, from {{fact:359dcee3-dfe9-4aea-95ca-2688e5aee3ef}} in August to {{fact:2826b8e1-d849-4795-b34a-5947347624fb}} in October, suggesting ongoing cash burn. Cash of {{fact:8c3790fb-5950-4866-9c63-c24db5bd93a1}} still sits well above the {{fact:45d07785-629d-4d8d-811c-b3aeeb41bda1}} floor. No other signal fired, so this trend stand |
| `nimbusfield-security` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `nimbusfield-security` | certificate | none | The Revenue to Plan requirement wraps across two lines in the page one table. |
| `nimbusfield-security` | early_warning | none | Runway stands at {{fact:96457812-d1c0-429d-9d16-87b660b4bfbb}} months, so on current burn the company has limited time to fund itself before needing new capital. The falling runway and cash covenant headroom signals show this position has worsened steadily since August, and with revenue holding above plan, the pressure appears to come from spending rather than sales. |
| `nimbusfield-security` | early_warning | none | Headroom on the minimum runway covenant fell from {{fact:bc8fb4ec-f035-40ee-bc97-b11529ffc8e5}} in August to {{fact:05059737-b720-4bbb-9634-97bb0b0378d5}} in October, with runway at {{fact:c48b10e3-d5e9-4d87-a55e-f8b5a07921c7}} months against a floor of {{fact:7d5f5264-29d1-46a6-8378-b0c04b8da0d3}}. This is the covenant view of the high-severity runway signal; if the monthly decline continues, the |
| `nimbusfield-security` | early_warning | none | Unrestricted cash of {{fact:c0983d48-1814-408e-9e88-7abf5af59aa6}} remains above the {{fact:d29117ce-3085-4939-89da-1beb799b1cc8}} minimum, but headroom dropped from {{fact:3e6b4bff-7c70-40a9-ba2e-419193ee1355}} in August to {{fact:7e858d92-345a-4d73-a271-9cc272ccf373}} in October. The steady cash drawdown is the direct driver behind the shrinking runway. |
| `nimbusfield-security` | early_warning | none | Revenue is running at {{fact:7b6d90b2-05ee-49fb-8549-8ee8edbc6142}} of plan against an {{fact:3b3a738c-f8d3-4c3f-847b-a13c7347daf9}} floor, and headroom has been essentially flat, moving only from {{fact:228d5271-8157-4087-ad88-dfbbd6892b64}} to {{fact:2ae769f2-eae3-425e-8b27-00ad51e4df01}}. This is a mitigating signal: sales are not the source of the cash and runway deterioration. |
| `orbitline-systems` | certificate | none | All three covenants are reported in the summary table on page one and repeated in Schedule 1 on page two. |
| `orbitline-systems` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table. |
| `orbitline-systems` | certificate | none | No embedded instructions were found in the document. |
| `orbitline-systems` | early_warning | none | Unrestricted cash still sits well above the covenant floor ({{fact:837f7f92-56b0-4160-8ce1-e7e31d7e7ef7}} against {{fact:6c91e081-1e51-4716-a704-0c4812caeeab}}), but headroom has fallen steadily from {{fact:0010d445-a7fd-4206-bc4e-cab10d095518}} to {{fact:af5ba436-200d-46d4-a8fd-4ceae5e1fe43}} over three month-ends. A cash-based covenant eroding month after month points to ongoing cash burn. No ot |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:9eb73de5-57fd-4a01-9170-5f80abb6bd64}} against a covenant minimum of {{fact:e1f7a4c6-e0c2-43cc-875c-2fe13a2a2c86}}, leaving headroom of {{fact:16b8dbfe-d664-4f0d-be50-ba6f9433dfff}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |
| `pellucid-sensors` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `pellucid-sensors` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `pellucid-sensors` | early_warning | none | Unrestricted cash headroom has narrowed steadily, from {{fact:be953511-0102-4fc2-ba71-0acf7ad7633e}} in August to {{fact:2d1caf8d-ab68-48d5-9d57-b5bf28d11a36}} in October, pointing to ongoing cash burn. Cash of {{fact:69c6b9c6-ebf6-43aa-ae7a-a08236d0e4bd}} still sits well above the {{fact:1d3a948e-22c9-45d4-a403-4826f6362b17}} minimum, so the concern is the trend rather than an imminent breach. No |
| `quillon-ai` | certificate | none | All three covenants are reported in the summary table on page one and agree with the calculation schedule on page two. |
| `quillon-ai` | certificate | none | In the summary table the Revenue to Plan requirement wraps across two lines; it is reported here as one phrase. |
| `quillon-ai` | certificate | none | The summary table header shows the Actual and In compliance column headings overlapping in the rendered page. |
| `quillon-ai` | early_warning | none | Headroom over the minimum cash covenant has narrowed steadily, from {{fact:38c3a1cf-31b5-40c9-96dd-f26b9efe536c}} in August to {{fact:5f3ebaf4-3a8f-4379-b453-8b9aadcb96ce}} in September and {{fact:9efbbfe1-8cc0-4cc1-b29f-24a797317b11}} in October. Cash of {{fact:711b1de4-d801-4d4a-8b27-d6e4c1f258d5}} remains well above the {{fact:43f4e9fb-afb9-4dc4-b18e-2155517d2dcc}} floor, but the steady decline |
| `stripple-tech` | intake | none | Raw spreadsheet export of monthly recurring revenue and customer counts with no title, no borrower name and no stated report date; the borrower and period cannot be confirmed from the document itself, and the data shown ends in an earlier year than the other documents in this delivery. |
| `tessaract-labs` | certificate | none | All listed covenants are reported in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on the first page. |
| `tessaract-labs` | certificate | none | The summary table's Actual and In compliance column headers overlap in the rendered image of the first page. |
| `tessaract-labs` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:2184655e-0ea2-4855-819e-921a6ce61c84}} in August to {{fact:c21d4f5d-9b27-4ec1-9867-24cd48dbb49b}} in October. Cash of {{fact:31c68805-dc87-4722-9f50-3b19d036a3b9}} is still well above the {{fact:58bf2f0b-8344-447d-b5ec-cf87b54eac5b}} minimum, so there is no near-term breach. The steady decline points to ongoing cash burn, and no other |
| `tidewell-medical` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one. |
| `tidewell-medical` | certificate | none | Schedule 1 shows that the reported Unrestricted Cash includes cash held in an escrow collateral account, which may not qualify as unrestricted; this should be reviewed by a person. |
| `tidewell-medical` | certificate | none | In the summary table the requirement for Revenue to Plan wraps across two lines. |
| `tidewell-medical` | certificate | none | No instructions directed at the reader were found in the document. |
| `tidewell-medical` | early_warning | none | Unrestricted cash headroom has narrowed each month, from {{fact:82c4fa6a-9ef4-41a6-bcee-82cec6438747}} to {{fact:0f0dc690-1466-449b-ac8a-8b100eff170f}} and then sharply to {{fact:e3d97db9-1a48-4757-a564-c51bd035342a}}. Cash of {{fact:62a90c81-aa0d-452a-afd6-e699875e1250}} against a {{fact:d305e307-8ce2-403c-856c-eec01d3713cd}} floor is the tightest cushion of the three. The same cash decline is li |
| `tidewell-medical` | early_warning | none | Runway headroom fell from {{fact:0a99d42f-cbae-4b40-8b53-448d5857a555}} to {{fact:f8e962f2-8046-4872-a73a-d664bed9e934}}, with the steepest drop in October. Runway of {{fact:55434351-61e4-42be-a1f8-e160b7e7aaa8}} months is still well above the {{fact:cfd1706d-354f-4fc5-b4a5-805d12dc7151}}-month minimum. The decline mirrors the shrinking cash cushion and points to faster burn rather than a separate |
| `tidewell-medical` | early_warning | none | Revenue headroom is essentially flat, slipping only marginally to {{fact:aa71807c-9059-40e9-9c80-b35bfdc14f93}}. Revenue of {{fact:547c9b75-e000-4a1b-a3c5-b4a21a4e6962}} of plan is comfortably above the {{fact:ff869876-62fc-4471-9147-fcf36af0bebf}} threshold. Because sales are on track, the falling cash and runway look driven by spending or working capital rather than weaker revenue. |
| `veridia-payments` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one and agree with the Schedule 1 calculations on page two. |
| `veridia-payments` | certificate | none | The Revenue to Plan requirement wraps across two lines in the summary table on page one. |
| `veridia-payments` | certificate | none | On page one the Actual and In compliance column headers overlap in the rendered table. |
| `veridia-payments` | early_warning | none | Unrestricted cash headroom narrowed steadily, from {{fact:696e6d2f-68bc-46c0-84d2-d169bd11b50d}} in August to {{fact:cef7aeb9-6f12-4ff0-b76b-d6adc0c9a729}} in September and {{fact:f4de959b-cc99-4338-967f-71d03778f053}} at October 31. Cash of {{fact:e026e7de-5e29-4af8-9994-da0c948cb756}} remains comfortably above the {{fact:7d5831ee-cc23-43f3-89a5-5685fbca5d46}} minimum, but the consistent drain ma |

## Observations

- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `briarstone-beverage`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `brightvane-energy`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `corvane-analytics`: guardrail note on covenant: error -> abstain: the run did not finish
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `corvane-analytics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `dataflake`: guardrail note on covenant: error -> abstain: the run did not finish
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `dataflake`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `halcyon-grid`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 2 signal(s) were left out of the ranking and were placed after the rest by severity
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kelvra-bio`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kelvra-bio`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `kestrel-bay-packaging`: guardrail note on covenant: error -> abstain: the run did not finish
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `mosswell-robotics`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `mosswell-robotics`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `nimbusfield-security`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 4 signal(s) were left out of the ranking and were placed after the rest by severity
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `orbitline-systems`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `orbitline-systems`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellham-grain`: guardrail note on covenant: error -> abstain: the run did not finish
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellham-grain`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellucid-sensors`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellucid-sensors`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `quillon-ai`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `quillon-ai`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tessaract-labs`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tessaract-labs`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `tidewell-medical`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `veridia-payments`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `veridia-payments`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity


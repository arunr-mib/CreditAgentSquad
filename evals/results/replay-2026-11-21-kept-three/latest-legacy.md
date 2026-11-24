# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T08:09:54+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 3 borrower(s) (['briarstone-beverage', 'harrowgate-precision', 'kestrel-bay-packaging']); 1 pass(es); run time 23.0 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- run-error: 1 cycle(s) failed on an error, so nothing was measured. First: kestrel-bay-packaging (covenant run): RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": "-0.04", "passed": false, "raw_value": "2.5986031546731

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 100.0% (502 of 502) |
| Extraction abstain rate (expected facts with no usable fact) | 0.0% |
| Covenant outcome accuracy | 100.0% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 0.0% |
| Exception precision | 100.0% |
| Exception recall | 100.0% |
| Cycles needing no person (beyond the commentary approval every review needs) | 33.3% (the book expects 33.3%) |
| Cycles reaching the signals stage or beyond | 3 of 3 |
| Cycles closed | 3 of 3 |
| Other disagreements with the truth | 1 |
| Model tokens in / out | 125,217 / 38,963 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 0 |
| false-exception | 0 |
| wrong-citation | 0 |
| wrong-abstain | 2 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 3 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": |  |
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `kestrel-bay-packaging` | run-error | covenant run | RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": "-0.04", "passe |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |

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
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:7043f426-02d6-4bc9-a120-68bb6cb3e54d}}, or {{fact:71ac99a4-b302-4021-8739-746099e28a98}} of the {{fact:f890cab8-8df5-4db6-be5a-52635b1214d7}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
| `harrowgate-precision` | certificate | none | All three covenants in the approved terms are reported in the summary table on page one; the calculation schedule on page two shows the same reported values. |
| `harrowgate-precision` | certificate | none | No instructions were found inside the document. |
| `harrowgate-precision` | collateral | none | The certificate prints a single combined line labelled Availability (over-advance); it is reported under availability, and no separate over-advance line is stated, so over_advance is not reported. |
| `harrowgate-precision` | collateral | none | The certificate's Inventory sublimit row does not match any requested line name and is not reported; the advance rate percentage rows were skipped. |
| `harrowgate-precision` | collateral | none | Cross-aged accounts, concentration in excess of limit, and letters of credit outstanding are printed as dashes on the certificate. |
| `harrowgate-precision` | collateral | none | The aging is stated as aged from invoice date; the inventory report is stated at lower of cost and market. |
| `harrowgate-precision` | collateral | none | The inventory page states that work in process and consignment inventory are not eligible, and that quantities come from perpetual records last counted at the most recent fiscal year end; no consignment category is listed separately. |
| `harrowgate-precision` | collateral | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | certificate | none | Both covenants in the approved terms are reported in the summary table on page one and in Schedule 1 on page two. |
| `kestrel-bay-packaging` | certificate | none | The Total Leverage Ratio calculation in Schedule 1 uses EBITDA as calculated by the Borrower, which adds back pro forma cost savings from plant consolidation; the credit team may wish to confirm this add-back is permitted under the Credit Agreement. |
| `kestrel-bay-packaging` | certificate | none | No embedded instructions were found in the document. |
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:7106db77-79c3-436b-8ba8-76bb71fc546c}}): total leverage of {{fact:69cf6de6-e092-4d1b-86d7-49650bdd0da8}} sits above the {{fact:c8509bc0-f534-4580-855f-201dd304b145}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:2ab83581-25b2-430f-b95d-c6b834c8530d}} is only slightly above the {{fact:839bd7fc-2ae9-4c15-81f5-ef942d2e2429}} minimum, leaving headroom of {{fact:c4c010da-49ff-4444-a74e-b62b5f1c3204}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:9b17dfc1-fbc7-4a1e-89fa-3d77d69d7221}} in March to {{fact:f816f141-f26d-421d-a429-7b64586656f9}} in June, then dropped sharply to {{fact:c4c010da-49ff-4444-a74e-b62b5f1c3204}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |

## Observations

- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `briarstone-beverage`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `briarstone-beverage`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity
- `kestrel-bay-packaging`: guardrail note on covenant: error -> abstain: the run did not finish
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `kestrel-bay-packaging`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 3 signal(s) were left out of the ranking and were placed after the rest by severity


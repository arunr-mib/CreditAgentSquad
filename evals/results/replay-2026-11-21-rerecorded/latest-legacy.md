# Evaluation scorecard: monitoring-cycle (recorded)

**Mode: recorded.** Mode recorded: answers came from recorded model responses.

- Generated 2026-11-21T08:05:31+00:00; commit `e6830878ac1906795f2e335c6423a3792f469513`; 21 borrower(s) (whole book); 1 pass(es); run time 123.8 seconds.
- Scripted decisions where a person is needed: yes.
- Oracle rows in scope not signed by the owner: 0.
- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.

## Gate: FAILED

Rule: any invented-number or false-compliant in any pass fails; any cycle that failed on an error fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated.
- run-error: 18 cycle(s) failed on an error, so nothing was measured. First: ashgrove-fleet (intake run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/ashgrove-fleet/2026-09-30/01.json; brindlewood-home-health (intake run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/brindlewood-home-health/2026-09-30/01.json; calder-finch-staffing (intake run): RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/calder-finch-staffing/2026-09-30/01.json
- nothing-read: 15 borrower(s) expected to have facts had none read: ashgrove-fleet (0 of 72), brindlewood-home-health (0 of 105), calder-finch-staffing (0 of 100), dunmore-industrial-supply (0 of 187), halvorsen-plastics (0 of 191)

## Headline numbers

| Measure | Value |
|---|---|
| Extraction accuracy (verified facts equal to truth, over facts expected) | 26.2% (701 of 2677) |
| Extraction abstain rate (expected facts with no usable fact) | 73.8% |
| Covenant outcome accuracy | 33.3% |
| Covenant abstain rate (cannot test where the truth has an outcome) | 66.7% |
| Exception precision | 11.1% |
| Exception recall | 33.3% |
| Cycles needing no person (beyond the commentary approval every review needs) | 4.8% (the book expects 47.6%) |
| Cycles reaching the signals stage or beyond | 4 of 21 |
| Cycles closed | 4 of 21 |
| Other disagreements with the truth | 25 |
| Model tokens in / out | 178,069 / 52,177 |

| Named failure | Count |
|---|---|
| invented-number (gated) | 0 |
| false-compliant (gated) | 0 |
| false-breach | 0 |
| missed-exception | 8 |
| false-exception | 32 |
| wrong-citation | 0 |
| wrong-abstain | 61 |
| missed-abstain | 0 |
| stale-terms | 0 |

## Borrowers

| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |
|---|---|---|---|---|---|---|---|
| `ashgrove-fleet` | missing_page | intake (needs_person) | spread.does_not_foot | intake.missing_document, intake.unclassified | 0.0% (0/72) | 3/3 | 5 |
| `briarstone-beverage` | over_advance | closed (closed) | bb.over_advance | bb.over_advance | 100.0% (201/201) | 2/2 | none |
| `brindlewood-home-health` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/105) | 0/3 | 7 |
| `calder-finch-staffing` | step_up | intake (needs_person) | covenant.reported_mismatch | intake.missing_document, intake.unclassified | 0.0% (0/100) | 0/2 | 8 |
| `dunmore-industrial-supply` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/187) | 0/3 | 9 |
| `eastmere-building` | late_reporting | awaiting_package (needs_person) | intake.missing_document | intake.missing_document | not measured (0/0) | 2/2 | none |
| `halvorsen-plastics` | restated_comparative | intake (needs_person) | spread.restatement | intake.missing_document, intake.unclassified | 0.0% (0/191) | 0/2 | 8 |
| `harrowgate-precision` | clean | closed (closed) | none | none | 100.0% (199/199) | 3/3 | none |
| `kestrel-bay-packaging` | hidden_breach | closed (closed) | covenant.reported_mismatch | covenant.reported_mismatch | 100.0% (102/102) | 2/2 | 3 |
| `larkspur-environmental` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/103) | 0/3 | 8 |
| `marlowe-ridge-logistics` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/107) | 0/3 | 7 |
| `northgale-electrical` | miscounted_ineligible | intake (needs_person) | bb.certificate_mismatch | intake.missing_document, intake.unclassified | 0.0% (0/189) | 0/2 | 8 |
| `ostrander-valley-foods` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/201) | 0/3 | 8 |
| `pellham-grain` | reported_breach | closed (closed) | covenant.breach | covenant.breach | 100.0% (199/199) | 3/3 | 3 |
| `quillfeather-bakery` | addback_over_cap | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/104) | 0/2 | 7 |
| `sablewood-dental` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/98) | 0/2 | 6 |
| `stanmoor-mechanical` | image_only | intake (needs_person) | spread.image_only | intake.missing_document, intake.unclassified | not measured (0/0) | 3/3 | 5 |
| `tallwater-foodservice` | clean | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/202) | 0/2 | 7 |
| `thornbury-metal` | deteriorating_trend | intake (needs_person) | signal.high | intake.missing_document, intake.unclassified | 0.0% (0/105) | 0/3 | 9 |
| `vantry-freight` | unapproved_amendment | intake (needs_person) | covenant.reported_mismatch, terms.unapproved_amendment | intake.missing_document, intake.unclassified | 0.0% (0/104) | 0/2 | 9 |
| `wrenfield-diagnostics` | scale_trap | intake (needs_person) | none | intake.missing_document, intake.unclassified | 0.0% (0/108) | 0/4 | 9 |

## Differences from the truth

| Borrower | Failure | Item | Detail | Known finding |
|---|---|---|---|---|
| `ashgrove-fleet` | missed-exception | spread.does_not_foot | expected for scenario missing_page; the cycle rests at intake (needs_person) |  |
| `ashgrove-fleet` | false-exception | intake.missing_document | not expected for scenario missing_page: Ashgrove Fleet Maintenance, LLC: reporting is 3 days past due |  |
| `ashgrove-fleet` | false-exception | intake.unclassified | not expected for scenario missing_page: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `ashgrove-fleet` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/ashgrove-fleet/2026-09-30/01.json |  |
| `brindlewood-home-health` | false-exception | intake.missing_document | not expected for scenario clean: Brindlewood Home Health Partners, LLC: reporting is 3 days past due |  |
| `brindlewood-home-health` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `brindlewood-home-health` | wrong-abstain | dscr @ 2026-09-30 | truth compliant at 3.04; the product recorded no test |  |
| `brindlewood-home-health` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.60; the product recorded no test |  |
| `brindlewood-home-health` | wrong-abstain | min_liquidity @ 2026-09-30 | truth compliant at 2291000; the product recorded no test |  |
| `brindlewood-home-health` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/brindlewood-home-health/2026-09-30/01.json |  |
| `calder-finch-staffing` | missed-exception | covenant.reported_mismatch | expected for scenario step_up; the cycle rests at intake (needs_person) |  |
| `calder-finch-staffing` | false-exception | intake.missing_document | not expected for scenario step_up: Calder & Finch Staffing Group, LLC: reporting is 3 days past due |  |
| `calder-finch-staffing` | false-exception | intake.unclassified | not expected for scenario step_up: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `calder-finch-staffing` | wrong-abstain | total_leverage @ 2026-09-30 | truth breach_reported_compliant at 1.94; the product recorded no test |  |
| `calder-finch-staffing` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.93; the product recorded no test |  |
| `calder-finch-staffing` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/calder-finch-staffing/2026-09-30/01.json |  |
| `dunmore-industrial-supply` | false-exception | intake.missing_document | not expected for scenario clean: Dunmore Industrial Supply Co.: reporting is 28 days past due |  |
| `dunmore-industrial-supply` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed; bbc-2026-09-30.pdf could not be filed |  |
| `dunmore-industrial-supply` | wrong-abstain | interest_coverage @ 2026-09-30 | truth compliant at 9.79; the product recorded no test |  |
| `dunmore-industrial-supply` | wrong-abstain | current_ratio @ 2026-09-30 | truth compliant at 1.34; the product recorded no test |  |
| `dunmore-industrial-supply` | wrong-abstain | debt_to_tnw @ 2026-09-30 | truth compliant at 1.74; the product recorded no test |  |
| `dunmore-industrial-supply` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `dunmore-industrial-supply` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/dunmore-industrial-supply/2026-09-30/01.json |  |
| `halvorsen-plastics` | missed-exception | spread.restatement | expected for scenario restated_comparative; the cycle rests at intake (needs_person) |  |
| `halvorsen-plastics` | false-exception | intake.missing_document | not expected for scenario restated_comparative: Halvorsen Plastics & Molding, Inc.: reporting is 28 days past due |  |
| `halvorsen-plastics` | false-exception | intake.unclassified | not expected for scenario restated_comparative: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed; bbc-2026-09-30.pdf could not be filed |  |
| `halvorsen-plastics` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.50; the product recorded no test |  |
| `halvorsen-plastics` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.91; the product recorded no test |  |
| `halvorsen-plastics` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `halvorsen-plastics` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/halvorsen-plastics/2026-09-30/01.json |  |
| `kestrel-bay-packaging` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": |  |
| `kestrel-bay-packaging` | wrong-abstain | investigation of covenant.reported_mismatch (total_leverage) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `larkspur-environmental` | false-exception | intake.missing_document | not expected for scenario clean: Larkspur Environmental Services, Inc.: reporting is 3 days past due |  |
| `larkspur-environmental` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `larkspur-environmental` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.47; the product recorded no test |  |
| `larkspur-environmental` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.40; the product recorded no test |  |
| `larkspur-environmental` | wrong-abstain | max_capex @ 2026-09-30 | truth compliant at 1307000; the product recorded no test |  |
| `larkspur-environmental` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/larkspur-environmental/2026-09-30/01.json |  |
| `marlowe-ridge-logistics` | false-exception | intake.missing_document | not expected for scenario clean: Marlowe Ridge Cold Storage & Logistics, Inc.: reporting is 3 days past due |  |
| `marlowe-ridge-logistics` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `marlowe-ridge-logistics` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.56; the product recorded no test |  |
| `marlowe-ridge-logistics` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.61; the product recorded no test |  |
| `marlowe-ridge-logistics` | wrong-abstain | max_capex @ 2026-09-30 | truth compliant at 5768000; the product recorded no test |  |
| `marlowe-ridge-logistics` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/marlowe-ridge-logistics/2026-09-30/01.json |  |
| `northgale-electrical` | missed-exception | bb.certificate_mismatch | expected for scenario miscounted_ineligible; the cycle rests at intake (needs_person) |  |
| `northgale-electrical` | false-exception | intake.missing_document | not expected for scenario miscounted_ineligible: Northgale Electrical Wholesale, Inc.: reporting is 28 days past due |  |
| `northgale-electrical` | false-exception | intake.unclassified | not expected for scenario miscounted_ineligible: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed; bbc-2026-09-30.pdf could not be filed |  |
| `northgale-electrical` | wrong-abstain | interest_coverage @ 2026-09-30 | truth compliant at 9.08; the product recorded no test |  |
| `northgale-electrical` | wrong-abstain | debt_to_tnw @ 2026-09-30 | truth compliant at 1.69; the product recorded no test |  |
| `northgale-electrical` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `northgale-electrical` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/northgale-electrical/2026-09-30/01.json |  |
| `ostrander-valley-foods` | false-exception | intake.missing_document | not expected for scenario clean: Ostrander Valley Foods, Inc.: reporting is 28 days past due |  |
| `ostrander-valley-foods` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed; bbc-2026-09-30.pdf could not be filed |  |
| `ostrander-valley-foods` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 1.63; the product recorded no test |  |
| `ostrander-valley-foods` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.71; the product recorded no test |  |
| `ostrander-valley-foods` | wrong-abstain | min_tnw @ 2026-09-30 | truth compliant at 44391000; the product recorded no test |  |
| `ostrander-valley-foods` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `ostrander-valley-foods` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/ostrander-valley-foods/2026-09-30/01.json |  |
| `pellham-grain` | wrong-abstain | covenant run | the run failed: RecordingStale: covenant/pellham-grain/2026-09-30/fccr/06: the recorded answer cites 1c16f09a-c51a-4b5b-9af7-5d83aab98236, described as {"formula_key": "covenant.fccr", "outputs": {"headroom": "-0.07", "headroom_pct": "-0.0519", "passed": false |  |
| `pellham-grain` | wrong-abstain | investigation of covenant.breach (fccr) | the Covenant Agent's investigation ended without a recommendation (abstain) |  |
| `quillfeather-bakery` | false-exception | intake.missing_document | not expected for scenario addback_over_cap: Quillfeather Bakery Brands, Inc.: reporting is 3 days past due |  |
| `quillfeather-bakery` | false-exception | intake.unclassified | not expected for scenario addback_over_cap: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `quillfeather-bakery` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant_variance at 1.96; the product recorded no test |  |
| `quillfeather-bakery` | wrong-abstain | fccr @ 2026-09-30 | truth compliant_variance at 1.45; the product recorded no test |  |
| `quillfeather-bakery` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/quillfeather-bakery/2026-09-30/01.json |  |
| `sablewood-dental` | false-exception | intake.missing_document | not expected for scenario clean: Sablewood Dental Management, LLC: reporting is 3 days past due |  |
| `sablewood-dental` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `sablewood-dental` | wrong-abstain | dscr @ 2026-09-30 | truth compliant at 3.26; the product recorded no test |  |
| `sablewood-dental` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.27; the product recorded no test |  |
| `sablewood-dental` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/sablewood-dental/2026-09-30/01.json |  |
| `stanmoor-mechanical` | missed-exception | spread.image_only | expected for scenario image_only; the cycle rests at intake (needs_person) |  |
| `stanmoor-mechanical` | false-exception | intake.missing_document | not expected for scenario image_only: Stanmoor Mechanical Contractors, Inc.: reporting is 3 days past due |  |
| `stanmoor-mechanical` | false-exception | intake.unclassified | not expected for scenario image_only: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `stanmoor-mechanical` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/stanmoor-mechanical/2026-09-30/01.json |  |
| `tallwater-foodservice` | false-exception | intake.missing_document | not expected for scenario clean: Tallwater Foodservice Supply, LLC: reporting is 28 days past due |  |
| `tallwater-foodservice` | false-exception | intake.unclassified | not expected for scenario clean: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed; bbc-2026-09-30.pdf could not be filed |  |
| `tallwater-foodservice` | wrong-abstain | fccr @ 2026-09-30 | truth compliant at 2.41; the product recorded no test |  |
| `tallwater-foodservice` | wrong-abstain | senior_leverage @ 2026-09-30 | truth compliant at 2.18; the product recorded no test |  |
| `tallwater-foodservice` | wrong-abstain | borrowing base @ 2026-09-30 | the truth has a recalculated base; the product recorded no review (stage pending) |  |
| `tallwater-foodservice` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/tallwater-foodservice/2026-09-30/01.json |  |
| `thornbury-metal` | missed-exception | signal.high | expected for scenario deteriorating_trend; the cycle rests at intake (needs_person) |  |
| `thornbury-metal` | false-exception | intake.missing_document | not expected for scenario deteriorating_trend: Thornbury Metal Fabricators, Inc.: reporting is 3 days past due |  |
| `thornbury-metal` | false-exception | intake.unclassified | not expected for scenario deteriorating_trend: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `thornbury-metal` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 3.92; the product recorded no test |  |
| `thornbury-metal` | wrong-abstain | interest_coverage @ 2026-09-30 | truth compliant at 3.64; the product recorded no test |  |
| `thornbury-metal` | wrong-abstain | current_ratio @ 2026-09-30 | truth compliant at 1.20; the product recorded no test |  |
| `thornbury-metal` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/thornbury-metal/2026-09-30/01.json |  |
| `vantry-freight` | missed-exception | covenant.reported_mismatch | expected for scenario unapproved_amendment; the cycle rests at intake (needs_person) |  |
| `vantry-freight` | missed-exception | terms.unapproved_amendment | expected for scenario unapproved_amendment; the cycle rests at intake (needs_person) |  |
| `vantry-freight` | false-exception | intake.missing_document | not expected for scenario unapproved_amendment: Vantry Freight Systems, LLC: reporting is 3 days past due |  |
| `vantry-freight` | false-exception | intake.unclassified | not expected for scenario unapproved_amendment: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `vantry-freight` | wrong-abstain | total_leverage @ 2026-09-30 | truth breach_reported_compliant at 2.09; the product recorded no test |  |
| `vantry-freight` | wrong-abstain | interest_coverage @ 2026-09-30 | truth compliant_variance at 6.72; the product recorded no test |  |
| `vantry-freight` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/vantry-freight/2026-09-30/01.json |  |
| `wrenfield-diagnostics` | false-exception | intake.missing_document | not expected for scenario scale_trap: Wrenfield Diagnostic Laboratories, Inc.: reporting is 3 days past due |  |
| `wrenfield-diagnostics` | false-exception | intake.unclassified | not expected for scenario scale_trap: ifs-2026-09-30.pdf could not be filed; cc-2026-09-30.pdf could not be filed |  |
| `wrenfield-diagnostics` | wrong-abstain | total_leverage @ 2026-09-30 | truth compliant at 1.61; the product recorded no test |  |
| `wrenfield-diagnostics` | wrong-abstain | min_tnw @ 2026-09-30 | truth compliant at 3699000; the product recorded no test |  |
| `wrenfield-diagnostics` | wrong-abstain | max_capex @ 2026-09-30 | truth compliant at 1772000; the product recorded no test |  |
| `wrenfield-diagnostics` | wrong-abstain | min_liquidity @ 2026-09-30 | truth compliant at 2013000; the product recorded no test |  |
| `wrenfield-diagnostics` | wrong-abstain | intake run | the run failed: RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/wrenfield-diagnostics/2026-09-30/01.json |  |
| `ashgrove-fleet` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/ashgrove-fleet/2026-09-30/01.json |  |
| `brindlewood-home-health` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/brindlewood-home-health/2026-09-30/01.json |  |
| `calder-finch-staffing` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |
| `calder-finch-staffing` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/calder-finch-staffing/2026-09-30/01.json |  |
| `dunmore-industrial-supply` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |
| `dunmore-industrial-supply` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/dunmore-industrial-supply/2026-09-30/01.json |  |
| `halvorsen-plastics` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/halvorsen-plastics/2026-09-30/01.json |  |
| `kestrel-bay-packaging` | run-error | covenant run | RecordingStale: covenant/kestrel-bay-packaging/2026-09-30/total_leverage/09: the recorded answer cites 99eeceb9-29fb-4de5-b615-ca46e2a2e792, described as {"formula_key": "covenant.total_leverage", "outputs": {"headroom": "-0.1", "headroom_pct": "-0.04", "passe |  |
| `larkspur-environmental` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |
| `larkspur-environmental` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/larkspur-environmental/2026-09-30/01.json |  |
| `marlowe-ridge-logistics` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/marlowe-ridge-logistics/2026-09-30/01.json |  |
| `northgale-electrical` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/northgale-electrical/2026-09-30/01.json |  |
| `ostrander-valley-foods` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/ostrander-valley-foods/2026-09-30/01.json |  |
| `pellham-grain` | run-error | covenant run | RecordingStale: covenant/pellham-grain/2026-09-30/fccr/06: the recorded answer cites 1c16f09a-c51a-4b5b-9af7-5d83aab98236, described as {"formula_key": "covenant.fccr", "outputs": {"headroom": "-0.07", "headroom_pct": "-0.0519", "passed": false, "raw_value": " |  |
| `quillfeather-bakery` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |
| `quillfeather-bakery` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/quillfeather-bakery/2026-09-30/01.json |  |
| `sablewood-dental` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/sablewood-dental/2026-09-30/01.json |  |
| `stanmoor-mechanical` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/stanmoor-mechanical/2026-09-30/01.json |  |
| `tallwater-foodservice` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/tallwater-foodservice/2026-09-30/01.json |  |
| `thornbury-metal` | signals-not-run | signals @ 2026-09-30 | 13 expected signal(s); the signals stage is pending |  |
| `thornbury-metal` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/thornbury-metal/2026-09-30/01.json |  |
| `vantry-freight` | signals-not-run | signals @ 2026-09-30 | 5 expected signal(s); the signals stage is pending |  |
| `vantry-freight` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/vantry-freight/2026-09-30/01.json |  |
| `wrenfield-diagnostics` | signals-not-run | signals @ 2026-09-30 | 1 expected signal(s); the signals stage is pending |  |
| `wrenfield-diagnostics` | run-error | intake run | RecordingMissing: no recorded model response at /home/user/arunr-mib/creditfleet/evals/recordings/intake/wrenfield-diagnostics/2026-09-30/01.json |  |

## Where a person was needed

| Borrower | Stage | Open items | Scripted decisions |
|---|---|---|---|
| `ashgrove-fleet` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `briarstone-beverage` | borrowing_base | bb.over_advance | bb.over_advance: paydown_required by credit_officer |
| `briarstone-beverage` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `brindlewood-home-health` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `calder-finch-staffing` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `dunmore-industrial-supply` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `eastmere-building` | awaiting_package | intake.missing_document | none (left open) |
| `halvorsen-plastics` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `harrowgate-precision` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `kestrel-bay-packaging` | covenant_testing | covenant.reported_mismatch | covenant.reported_mismatch: escalate_to_committee by credit_officer |
| `kestrel-bay-packaging` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `larkspur-environmental` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `marlowe-ridge-logistics` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `northgale-electrical` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `ostrander-valley-foods` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `pellham-grain` | covenant_testing | covenant.breach | covenant.breach: escalate_to_committee by credit_officer |
| `pellham-grain` | review_prep | review.commentary_approval | review.commentary_approval: approve by portfolio_manager |
| `quillfeather-bakery` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `sablewood-dental` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `stanmoor-mechanical` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `tallwater-foodservice` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `thornbury-metal` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `vantry-freight` | intake | intake.missing_document, intake.unclassified | none (left open) |
| `wrenfield-diagnostics` | intake | intake.missing_document, intake.unclassified | none (left open) |

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
| `briarstone-beverage` | early_warning | none | Availability is negative at {{fact:9e2dab62-4d73-4bda-b7e1-467cdf4c1f07}}, or {{fact:5f5be829-042c-4038-88a5-8e02289aeab0}} of the {{fact:8552d2bc-ccdd-4d8c-9268-90dd5a019406}} commitment. Advances exceed what the collateral supports, so the borrower is over-advanced and has no revolver headroom for working capital. No other signal fired, so these facts do not show whether collateral shrank or bor |
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
| `kestrel-bay-packaging` | early_warning | none | Headroom is negative ({{fact:d244409c-a353-432f-a267-dac29a6c83f3}}): total leverage of {{fact:7f1d14a5-6178-4b7b-be1f-768e73e5a9f5}} sits above the {{fact:52af138a-22de-4f34-80d0-e9e9d0229614}} maximum, so the covenant appears breached at September 30, 2026, not just tight. Debt is high relative to earnings, which limits capacity to absorb further weakness, and it coincides with thinning liquidit |
| `kestrel-bay-packaging` | early_warning | none | The current ratio of {{fact:2dc41a87-0592-441f-b50e-43e9149cef7f}} is only slightly above the {{fact:dd0fd424-6d8e-4f30-8a6c-dde1399b6ebd}} minimum, leaving headroom of {{fact:6c9788e7-b03b-41c3-a1c0-401bd00064e1}}. Short-term liquidity is tightening at the same time leverage is over its limit, so both the balance sheet and near-term cash cover are under pressure. |
| `kestrel-bay-packaging` | early_warning | none | Current ratio headroom has declined each quarter this year, from {{fact:8e37855c-a2c1-4d69-ada4-38a797eb07f7}} in March to {{fact:cad86925-4ebf-473c-8c65-5185301e70c7}} in June, then dropped sharply to {{fact:6c9788e7-b03b-41c3-a1c0-401bd00064e1}} in September. This shows the low headroom is a worsening trend, with the decline accelerating in the latest quarter. |
| `pellham-grain` | certificate | none | All three covenants in the approved terms are reported in the summary table on the first page; the borrower reports non-compliance with the Fixed Charge Coverage Ratio. |
| `pellham-grain` | certificate | none | No embedded instructions were found in the document. |
| `pellham-grain` | collateral | none | No separate over-advance line is printed; the certificate shows a single combined line labelled Availability (over-advance), reported under availability, so over_advance is omitted. |
| `pellham-grain` | collateral | none | The Inventory sublimit line on the certificate does not match any requested line name and was not reported; advance rate percentage rows were skipped. |
| `pellham-grain` | collateral | none | The aging and inventory pages also state units in U.S. dollars; the certificate page statement is reported. |
| `pellham-grain` | collateral | none | The aging total row and the inventory total row were excluded as instructed. |
| `pellham-grain` | collateral | none | The inventory page states that inventory was last counted at the most recent fiscal year end, with quantities from perpetual records. |
| `pellham-grain` | collateral | none | No embedded instructions were found in the document. |
| `pellham-grain` | early_warning | none | Fixed charge coverage was {{fact:2226066d-f15f-4bb4-87a3-f99e6fcd4dd2}} against a covenant minimum of {{fact:e1d1e659-5e30-4f98-978c-24ef2cd08265}}, leaving headroom of {{fact:b0071475-23ce-402f-909f-685ee99f0e1c}}. Because the headroom is negative, coverage sits below the required level rather than merely near it. Cash flow is covering fixed charges with less cushion than the lender required. No  |

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
- `pellham-grain`: guardrail note on covenant: error -> abstain: the run did not finish
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the answer explained a signal that code did not fire; it was ignored
- `pellham-grain`: guardrail note on early_warning: unknown_signal -> ignored: the ranking named a signal that code did not fire
- `pellham-grain`: guardrail note on early_warning: ranking_incomplete -> completed_by_code: 1 signal(s) were left out of the ranking and were placed after the rest by severity


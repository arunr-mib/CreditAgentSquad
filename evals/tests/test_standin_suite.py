"""The stand-in suite over the whole book: every borrower through the live monitoring cycle,
graded against the truth, with the gate asserted.

About two minutes (each borrower takes five to seven seconds, most of it loading history).
Deselect with: -m "not slow".

A stand-in run proves the pipeline, the workflow and the grader. It is not model performance.
"""
import json

import pytest
from app.domain.governance import EvalRun
from sqlalchemy import select
from sqlalchemy.orm import Session

from evals.book import load_book
from evals.grade import FAILURES, GATED, STAGES, STANDIN_UNANSWERED, load_known_findings
from evals.run import STANDIN_LABEL, save_eval_run, write_results
from evals.scorecard import render_markdown
from evals.standin import STANDIN_MODEL

pytestmark = pytest.mark.slow


def differences(results):
    found = set()
    for code, graded in results["borrowers"].items():
        found |= {(code, f["name"], f["item"]) for f in graded["failures"]}
        found |= {(code, d["kind"], d["item"]) for d in graded["disagreements"]}
    return found


def test_the_gate_passes(suite):
    assert suite["gate"]["passed"], suite["gate"]["reasons"] + suite["gate"]["unexplained"]


def test_no_invented_number_and_no_false_compliant_in_any_pass(suite):
    for n, one_pass in enumerate(suite["passes"], start=1):
        for name in GATED:
            assert one_pass["failure_counts"][name] == 0, f"pass {n}: {name}"
    assert set(suite["failure_counts"]) == set(FAILURES)


def test_every_borrower_ran_without_a_crash(suite, book_root):
    assert suite["meta"]["borrowers"] == len(suite["borrowers"]) == len(load_book(book_root))
    assert [c for c, g in suite["borrowers"].items() if g["error"]] == []
    assert all(g["ledger_ok"] for g in suite["borrowers"].values())


def test_every_cycle_reaches_signals_or_rests_on_an_item_its_scenario_expects(suite):
    problems = []
    for code, graded in suite["borrowers"].items():
        if STAGES.index(graded["stage_reached"]) >= STAGES.index("signals"):
            continue
        open_items = {i["type"] for i in graded["stops"][-1]["open_items"] if i["blocks_stage"]}
        if graded["stage_status"] != "needs_person" or not open_items or not open_items <= set(graded["expected_exceptions"]):
            problems.append((code, graded["stage_reached"], graded["stage_status"], sorted(open_items)))
    assert problems == []


def test_the_only_differences_from_the_truth_are_the_listed_known_findings(suite):
    known = {(k["borrower"], k["name"], k["item"]) for k in load_known_findings()}
    assert differences(suite) == known


def test_each_scenario_raises_its_expected_exceptions_and_clean_borrowers_raise_none(suite, book_root):
    known = {(k["borrower"], k["item"]) for k in load_known_findings() if k["name"].endswith("-exception")}
    problems = []
    for code, graded in suite["borrowers"].items():
        expected, raised = set(graded["expected_exceptions"]), set(graded["raised_exceptions"])
        unexplained = {kind for kind in expected ^ raised if (code, kind) not in known}
        if unexplained:
            problems.append((code, graded["scenario"], sorted(unexplained)))
    assert problems == []
    clean = [g for g in suite["borrowers"].values() if g["scenario"] == "clean"]
    assert len(clean) == len([b for b in load_book(book_root) if b.scenario == "clean"]) > 0


def test_every_expected_fact_was_extracted_and_equals_the_truth(suite, book_root):
    known = {k["borrower"] for k in load_known_findings() if k["name"] == "extraction-incomplete"}
    for code, graded in suite["borrowers"].items():
        extraction = graded["extraction"]
        if code not in known:
            assert extraction["correct"] == extraction["expected"], (code, extraction)
    from evals.grade import Truth
    assert suite["metrics"]["extraction_facts_expected"] == sum(len(Truth(b).expected_facts()) for b in load_book(book_root)) > 1000


def test_everything_the_stand_in_produced_is_labelled_as_stand_in(suite):
    assert suite["meta"]["mode"] == "standin" and suite["meta"]["standin"] is True
    assert suite["meta"]["label"] == STANDIN_LABEL
    runs = [r for g in suite["borrowers"].values() for r in g["agent_runs"]]
    assert len(runs) > 60
    assert {r["llm_mode"] for r in runs} == {"standin"}
    answered = [r for r in runs if r["status"] == "completed"]
    assert {r["served_model"] for r in answered} == {STANDIN_MODEL}
    # the agents the stand-in does not answer fail safely and are reported, never passed off as answers
    unanswered = [r for r in runs if r["status"] != "completed"]
    assert {r["agent"] for r in unanswered} <= STANDIN_UNANSWERED and {r["served_model"] for r in unanswered} <= {None}
    assert not any(w for g in suite["borrowers"].values() for w in g["failures"])
    # the stand-in read every document as printed: print and truth never disagreed
    assert suite["meta"]["standin_print_vs_truth_disagreements"] == []


def test_unmeasured_metrics_are_null_never_zero(suite):
    # no model was called, so there are no tokens to report
    assert suite["metrics"]["input_tokens"] is None and suite["metrics"]["output_tokens"] is None
    assert all(g["tokens"] is None for g in suite["borrowers"].values())
    # the late package has no document to extract from
    # (legacy book: eastmere-building; innovation book: lumora-health)
    code = next(c for c in ("eastmere-building", "lumora-health") if c in suite["borrowers"])
    late = suite["borrowers"][code]["extraction"]
    assert late["expected"] == 0 and late["accuracy"] is None


def test_scorecard_says_in_its_first_lines_that_it_is_a_stand_in(suite, tmp_path):
    json_path, md_path = write_results(suite, tmp_path)
    head = "\n".join(md_path.read_text().splitlines()[:4])
    assert "(standin)" in head and "STAND-IN RUN. NOT MODEL PERFORMANCE." in head
    document = json.loads(json_path.read_text())
    assert document["meta"]["mode"] == "standin" and "recordings" not in document
    body = render_markdown(document)
    for code, graded in suite["borrowers"].items():
        assert f"`{code}`" in body and graded["scenario"] in body


def test_scorecard_lists_the_stale_recordings_replayed_by_choice(suite):
    document = json.loads(json.dumps(suite))
    assert "Stale recordings replayed" not in render_markdown(document)
    document["meta"]["accepted_stale"] = ["intake", "spreading"]
    assert "Stale recordings replayed by choice: intake, spreading." in render_markdown(document)


def test_the_run_is_stored_as_an_eval_run_row(suite, engine):
    run_id = save_eval_run(engine, suite)
    with Session(engine) as db:
        row = db.execute(select(EvalRun).where(EvalRun.suite == "monitoring-cycle")
                         .order_by(EvalRun.created_at.desc())).scalars().first()
        assert str(row.id) == run_id and row.mode == "standin" and row.gate_passed == suite["gate"]["passed"]
        assert row.results["meta"]["standin"] is True and "recordings" not in row.results
        db.delete(row)
        db.commit()


def test_no_untraced_figures_and_no_disagreements(suite):
    for code, graded in suite["borrowers"].items():
        assert [o for o in graded["observations"] if o["kind"] == "untraced-figure"] == [], code
        assert graded["disagreements"] == [], code
    assert suite["meta"]["standin_print_vs_truth_disagreements"] == []


def test_the_scenarios_raise_exactly_what_the_book_expects(suite, book_name):
    if book_name != "innovation":
        pytest.skip("the legacy scenarios are covered by test_each_scenario_raises_its_expected_exceptions_and_clean_borrowers_raise_none")
    raised = {c: set(g["raised_exceptions"]) for c, g in suite["borrowers"].items()}
    assert "cash.statement_mismatch" in raised["tidewell-medical"]
    assert "funding_slipped" in raised["nimbusfield-security"]
    assert "intake.unclassified" in raised["stripple-tech"] and "spread.value_unverified" in raised["stripple-tech"]
    assert raised["ferrogate-cloud"] == set()  # compliant, runway "not meaningful", nothing raised


def test_scorecard_says_why_covenant_accuracy_is_below_100_percent(suite):
    body = render_markdown(json.loads(json.dumps(suite)))
    unreached = {c: [n for n in g["not_reached"] if n.startswith("covenant test")] for c, g in suite["borrowers"].items()}
    unreached = {c: n for c, n in unreached.items() if n}
    if not unreached:
        assert "Covenant tests not reached" not in body
    for code, names in unreached.items():
        assert "## Covenant tests not reached" in body and f"`{code}`: {len(names)} covenant test(s) not reached" in body

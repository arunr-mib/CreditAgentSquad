"""The evaluation keeps the evidence behind a hold: which figures were held and why, and the
prose a guardrail refused (the product stores only that a note was removed, never its text)."""
import json

from evals.grade import held_cells, unshown_text
from evals.run import CapturingClient


def test_held_cells_lists_each_cell_with_its_reason():
    items = [{"type": "spread.value_unverified", "evidence": {"cells": [
        {"key": "bs.total_equity", "printed_label": "Retained earnings", "row_label": "Retained earnings",
         "reason": "mapping_doubt", "page": 2}]}},
             {"type": "test.no_cells", "evidence": {"document_id": "x"}}]
    assert held_cells(items) == [{"item": "spread.value_unverified", "key": "bs.total_equity",
                                  "printed_label": "Retained earnings", "row_label": "Retained earnings",
                                  "reason": "mapping_doubt", "page": 2}]


def _rec(notes_out, shown):
    answer = {"cells": [{"key": "bs.cash", "printed_label": "Cash and equivalents", "printed_figure": "1,200"}],
              "absent_keys": ["bs.subordinated_debt"], "notes": notes_out}
    return {"agent_runs": [{"agent": "spreading", "guardrail_notes":
                            [{"check": "note", "action": "shown", "detail": s} for s in shown]
                            + [{"check": "figure_untraceable", "action": "dropped", "detail": "removed"}]}],
            "model_outputs": [{"record_key": "spreading/doc/0",
                               "content": [{"type": "text", "text": json.dumps(answer)}]}]}


def test_unshown_text_keeps_the_refused_note_and_skips_shown_ones():
    rec = _rec(["Statements are unaudited.", "Revenue rose 12% on the prior year."], ["Statements are unaudited."])
    out = unshown_text(rec)
    assert [t["text"] for t in out] == ["Revenue rose 12% on the prior year."]
    assert out[0]["agent"] == "spreading" and out[0]["typed_figures"] == ["12%"]


def test_unshown_text_ignores_cell_fields_and_line_keys():
    # printed labels, printed figures and absent keys are not prose the reader wrote
    assert unshown_text(_rec(["Statements are unaudited."], ["Statements are unaudited."])) == []


def test_unshown_text_reads_tool_use_input():
    rec = {"agent_runs": [{"agent": "intake", "guardrail_notes": []}],
           "model_outputs": [{"record_key": "intake/doc/0", "content": [
               {"type": "tool_use", "input": {"concerns": ["The page shows 3 signatures."]}}]}]}
    assert [t["text"] for t in unshown_text(rec)] == ["The page shows 3 signatures."]


def test_capturing_client_keeps_each_answer_and_passes_it_through():
    class Inner:
        mode = "standin"

        def create(self, request):
            return type("R", (), {"content": [{"type": "text", "text": "{}"}]})()

    class Req:
        record_key = "spreading/doc/0"

    cap = CapturingClient(Inner())
    response = cap.create(Req())
    assert response.content == [{"type": "text", "text": "{}"}]
    assert cap.mode == "standin"
    assert cap.outputs == [{"record_key": "spreading/doc/0", "content": [{"type": "text", "text": "{}"}]}]


def test_unshown_text_reads_a_concern_held_as_a_single_field():
    # the Intake Agent's answer, as recorded in the first live run (one concern per document)
    rec = {"agent_runs": [{"agent": "intake", "guardrail_notes": []}],
           "model_outputs": [{"record_key": "intake/x/01", "content": [{"type": "text", "text": json.dumps(
               {"documents": [{"doc_type": "interim_statements", "title_as_printed": "Interim Financial Statements",
                               "concern": "The document has five pages but only two were shown."},
                              {"doc_type": "compliance_certificate", "concern": ""}]})}]}]}
    assert [t["text"] for t in unshown_text(rec)] == ["The document has five pages but only two were shown."]


def test_unshown_text_skips_labels_that_are_not_prose():
    # aging bucket names and row labels are copied from the page, not written by the agent
    rec = {"agent_runs": [{"agent": "collateral", "guardrail_notes": []}],
           "model_outputs": [{"record_key": "collateral/x/01", "content": [{"type": "text", "text": json.dumps(
               {"buckets": ["0-30 days", "Over 90 days"], "rows": [{"label": "Eligible receivables"}]})}]}]}
    assert unshown_text(rec) == []


def test_unshown_text_skips_row_notes_and_ids_under_prose_fields():
    # an aging row's note ("Contra 20,800") and a bare fact id are copied, not written
    rec = {"agent_runs": [{"agent": "collateral", "guardrail_notes": []}],
           "model_outputs": [{"record_key": "collateral/x/01", "content": [{"type": "text", "text": json.dumps(
               {"rows": [{"note": "Contra 20,800"}, {"note": "Affiliate"}],
                "reason": "54e8fe6e-dcb1-4bce-a6c5-13c08f506ce3"})}]}]}
    assert unshown_text(rec) == []


# ---- stored spreading notes are judged by the product's rule with the document-structure allowance ----


def _run(allowance):
    return {"agent": "spreading", "note_allowance": allowance}


ALLOW = {"page_count": 6, "note_numbers": [1], "endings": ["9001"], "years": [2025], "echo": ""}


def test_an_honest_spreading_note_is_not_an_invented_number():
    from evals.grade import note_types_figure

    assert not note_types_figure(_run(ALLOW), "Note 1 on page 5 describes the revolver.")
    assert not note_types_figure(_run(ALLOW), "Cash is held in the operating account (ending 9001).")


def test_a_figure_the_product_would_refuse_is_still_an_invented_number():
    from evals.grade import note_types_figure

    assert note_types_figure(_run(ALLOW), "Revenue rose to 1,250,000 on page 5.")
    assert note_types_figure(_run(ALLOW), "Note 7 on page 5 describes the revolver.")  # no such note
    assert note_types_figure(_run(ALLOW), "See page 40.")  # no such page
    assert note_types_figure(_run(ALLOW), "Account (ending 1234) holds cash.")  # not printed in the document
    assert note_types_figure(_run(None), "Note 1 on page 5 describes the revolver.")  # no allowance, plain rule


def test_other_agents_notes_keep_the_plain_rule():
    from evals.grade import note_types_figure

    assert note_types_figure({"agent": "review"}, "Revenue was 4,000.")
    assert not note_types_figure({"agent": "review"}, "Nothing to report.")


def test_a_quoted_units_phrase_is_allowed_only_when_the_run_verified_it():
    from evals.grade import note_types_figure

    note = "The cover page states units as 'In thousands of U.S. dollars'."
    assert not note_types_figure(_run({**ALLOW, "echo": "In thousands of U.S. dollars"}), note)
    assert note_types_figure(_run({**ALLOW, "echo": ""}), note)

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

"""A recorded answer that cites ids is replayed by value: the harness maps each recorded id to the id
that stands for the same thing in the replay, or refuses to replay."""
import json
import uuid

import pytest
from app.agents.llm import (
    LLMRequest,
    LLMResponse,
    RecordedClient,
    RecordingClient,
    RecordingStale,
    ScriptedClient,
)

KEY = "review/b/2026-10-31/01"


def uid():
    return str(uuid.uuid4())


class Table:
    """A stand-in resolver: id -> descriptor, set per run."""

    def __init__(self, rows):
        self.rows = dict(rows)

    def __call__(self, ref):
        return self.rows.get(ref)


def request(*ids):
    return LLMRequest(model="m", system="s", record_key=KEY, spec="review@1:aaaaaaaaaaaa",
                      messages=[{"role": "user", "content": [{"type": "text", "text": json.dumps(list(ids))}]}])


def answer(text):
    return LLMResponse(content=[{"type": "text", "text": text}], stop_reason="end_turn", model="m")


REV = {"type": "fact", "key": "is.revenue", "period_end": "2026-10-31", "months": 10, "value": "48250", "page": 1}
COGS = {**REV, "key": "is.cogs", "value": "33775"}


def record(tmp_path, ids_then, text):
    a, b = uid(), uid()
    resolver = Table({a: REV, b: COGS})
    RecordingClient(ScriptedClient([answer(text.format(a=a, b=b))]), tmp_path, resolver=resolver).create(request(a, b))
    return a, b


def test_the_descriptors_are_saved_beside_the_response(tmp_path):
    a, b = record(tmp_path, None, "Revenue {{{{fact:{a}}}}} and {{{{fact:{b}}}}}")
    stored = json.loads((tmp_path / f"{KEY}.json").read_text())
    assert stored["_ids"] == {a: REV, b: COGS}


def test_recorded_ids_are_rewritten_to_the_ids_that_mean_the_same_thing(tmp_path):
    a, b = record(tmp_path, None, "Revenue {{{{fact:{a}}}}} then {{{{fact:{b}}}}} and again {{{{fact:{a}}}}}")
    a2, b2 = uid(), uid()
    out = RecordedClient(tmp_path, resolver=Table({a2: REV, b2: COGS})).create(request(b2, a2))  # order differs
    assert out.text() == f"Revenue {{{{fact:{a2}}}}} then {{{{fact:{b2}}}}} and again {{{{fact:{a2}}}}}"


def test_a_changed_value_refuses_to_replay(tmp_path):
    a, _ = record(tmp_path, None, "Revenue {{{{fact:{a}}}}}")
    a2, b2 = uid(), uid()
    with pytest.raises(RecordingStale, match="matches no id"):
        RecordedClient(tmp_path, resolver=Table({a2: {**REV, "value": "48251"}, b2: COGS})).create(request(a2, b2))


def test_an_ambiguous_match_refuses_to_replay(tmp_path):
    record(tmp_path, None, "Revenue {{{{fact:{a}}}}}")
    x, y = uid(), uid()
    with pytest.raises(RecordingStale, match="ambiguous"):
        RecordedClient(tmp_path, resolver=Table({x: REV, y: REV})).create(request(x, y))


def test_an_id_the_model_invented_stays_as_it_was_and_is_not_an_error(tmp_path):
    a, b = uid(), uid()
    invented = uid()
    RecordingClient(ScriptedClient([answer(f"{{{{fact:{a}}}}} {{{{fact:{invented}}}}}")]), tmp_path,
                    resolver=Table({a: REV, b: COGS})).create(request(a, b))
    a2, b2 = uid(), uid()
    out = RecordedClient(tmp_path, resolver=Table({a2: REV, b2: COGS})).create(request(a2, b2))
    assert out.text() == f"{{{{fact:{a2}}}}} {{{{fact:{invented}}}}}"


def test_ids_the_answer_does_not_cite_do_not_have_to_match(tmp_path):
    a, _ = record(tmp_path, None, "Revenue {{{{fact:{a}}}}}")
    a2 = uid()
    out = RecordedClient(tmp_path, resolver=Table({a2: REV})).create(request(a2))  # cogs gone: not cited
    assert out.text() == f"Revenue {{{{fact:{a2}}}}}"


def test_ids_in_tool_inputs_are_rewritten_too(tmp_path):
    a, _b = uid(), uid()
    call = LLMResponse(content=[{"type": "tool_use", "id": "t", "name": "read_page", "input": {"document_id": a}}],
                       stop_reason="tool_use")
    doc = {"type": "document", "sha256": "ab" * 32}
    RecordingClient(ScriptedClient([call]), tmp_path, resolver=Table({a: doc})).create(request(a))
    a2 = uid()
    out = RecordedClient(tmp_path, resolver=Table({a2: doc})).create(request(a2))
    assert out.content[0]["input"]["document_id"] == a2


def test_a_recording_without_descriptors_and_a_client_without_a_resolver_replay_as_before(tmp_path):
    a = uid()
    RecordingClient(ScriptedClient([answer(f"{{{{fact:{a}}}}}")]), tmp_path).create(request(a))
    assert "_ids" not in json.loads((tmp_path / f"{KEY}.json").read_text())
    assert RecordedClient(tmp_path, resolver=Table({})).create(request(uid())).text() == f"{{{{fact:{a}}}}}"
    RecordingClient(ScriptedClient([answer(f"{{{{fact:{a}}}}}")]), tmp_path, resolver=Table({a: REV})).create(request(a))
    assert RecordedClient(tmp_path).create(request(a)).text() == f"{{{{fact:{a}}}}}"


# ---- the eval-side resolver, on real rows ------------------------------------------------------------------


def test_the_resolver_describes_an_id_by_what_it_stands_for_never_by_the_id(db):
    from datetime import date
    from decimal import Decimal

    from app.domain.credit import Borrower
    from app.domain.facts import CalcRun
    from app.domain.facts_service import add_fact

    from evals.idmap import describe

    borrower = Borrower(code="IDM", name="Idmap Co")
    db.add(borrower)
    db.flush()
    end = date(2026, 10, 31)
    a = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=end, months=10, value=Decimal("48250000"),
                 kind="seeded")
    b = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=end, months=10, value=Decimal("48250000.00"),
                 kind="seeded")
    c = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=end, months=10, value=Decimal("1"),
                 kind="seeded")
    da, db_, dc = (describe(db, str(f.id)) for f in (a, b, c))
    assert da == db_ != dc  # the same value written two ways is the same descriptor
    assert str(a.id) not in json.dumps(da) and da["key"] == "is.revenue" and da["type"] == "fact"
    calc = CalcRun(borrower_id=borrower.id, formula_key="metric.leverage", formula_version="1", period_end=end,
                   engine_version="t", outputs={"value": "2.5", "passed": True, "fact_id": str(a.id)})
    db.add(calc)
    db.flush()
    desc = describe(db, str(calc.id))
    assert desc["formula_key"] == "metric.leverage" and desc["outputs"] == {"value": "2.5", "passed": True}
    assert describe(db, str(uuid.uuid4())) is None and describe(db, "not-a-uuid") is None

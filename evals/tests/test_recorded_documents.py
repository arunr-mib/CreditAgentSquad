from types import SimpleNamespace

from evals.run import filed_by_intake


def _doc(source, meta):
    return SimpleNamespace(doc_type_source=source, meta=meta)


def test_a_document_intake_filed_is_recorded_whatever_its_source():
    docs = [_doc("agent", {"title_as_printed": "Balance Sheet"}),
            _doc("system", {"title_as_printed": "Balance Sheet", "quality": "internal"}),  # rule-agreed
            _doc("system", {"external_id": "seeded-1"})]  # seeded before the cycle: not the cycle's to grade
    assert [filed_by_intake(d) for d in docs] == [True, True, False]
    assert sum(filed_by_intake(d) for d in docs) == 2  # the filed count, not the agent-source count

"""A book whose generated documents are missing must stop the seed. Loading it anyway gives
borrowers with no files, which looks like a product fault (see the fresh-worktree lesson)."""
import json

import pytest
from app.seed_book import seed_book


def _book(tmp_path, *, write: list[str]):
    (tmp_path / "truth").mkdir()
    documents = [{"path": "documents/acme/credit-agreement.pdf", "period_end": None},
                 {"path": "documents/acme/export.pdf", "period_end": None, "held": True,
                  "workbook": {"path": "documents/acme/export.xlsx"}}]
    (tmp_path / "truth" / "acme.json").write_text(json.dumps({"borrower": {"id": "acme"}, "documents": documents}))
    (tmp_path / "truth" / "other.json").write_text(json.dumps(
        {"borrower": {"id": "other"}, "documents": [{"path": "documents/other/afs.pdf"}]}))
    for name in write:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b"x")
    return tmp_path


def test_seed_refuses_a_book_whose_documents_are_missing_before_writing_anything(tmp_path):
    book = _book(tmp_path, write=["documents/acme/export.pdf"])
    with pytest.raises(FileNotFoundError) as refused:
        seed_book(None, root=book, only=["acme"])  # no session: it must stop before the database is touched
    message = str(refused.value)
    assert "2 of 3 documents" in message  # the agreement and the workbook; the print is there
    assert "documents/acme/credit-agreement.pdf" in message and "documents/acme/export.xlsx" in message
    assert "documents/other" not in message  # a borrower that is not being loaded is not checked
    assert "generate" in message

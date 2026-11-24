"""Rebuild the example review package in docs/examples/ from a cycle run end to end.

    uv run python -m evals.examples [--borrower kestrel-bay-packaging]

The borrower is loaded in live mode and its current cycle is run with the stand-in reader (see
evals/standin.py: a perfect reader built from the book's ground truth, not a model), with the
scripted decisions the evaluation uses. The package is then rendered from what the cycle stored,
so figures for the current period cite the document and page they were read from. Everything is
rolled back afterwards; only the three files are written.
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from evals.book import BOOKS, REPO, load_book
from evals.run import LoadedBorrower, default_database_url, ensure_schema, scratch_file_store
from evals.standin import StandInReader

OUT = REPO / "docs" / "examples"


def build(code: str, out: Path = OUT) -> dict[str, int]:
    from app.domain import stages
    from app.domain.credit import Borrower
    from app.publishing.service import build_content, content_hash, render_files

    book = load_book(BOOKS["legacy"], [code])  # the examples are legacy borrowers
    engine = create_engine(default_database_url())
    try:
        with scratch_file_store():
            ensure_schema(engine)
            with LoadedBorrower(engine, book, book.get(code)) as loaded:
                db = Session(bind=loaded.conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
                previous, stages.LLM_FACTORY = stages.LLM_FACTORY, lambda: StandInReader(book)
                try:
                    recording: dict = {}
                    loaded._cycle(db, recording, decide=True)
                    row = db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()
                    content = build_content(db, scope="borrower", period_end=book.get(code).current_period,
                                            borrower_id=row.id)
                    content["snapshot_sha256"] = content_hash(content)
                    files = render_files(content, ("docx", "xlsx", "pptx"))
                finally:
                    stages.LLM_FACTORY = previous
                    db.close()
        out.mkdir(parents=True, exist_ok=True)
        for item in files:
            (out / item["name"]).write_bytes(item["data"])
        facts = content["facts"].values() if isinstance(content["facts"], dict) else content["facts"]
        kinds: dict[str, int] = {}
        for fact in facts:
            kinds[fact.get("kind", "?")] = kinds.get(fact.get("kind", "?"), 0) + 1
        cited = sum(1 for fact in facts if fact.get("document_id") and fact.get("page"))
        return {"files": len(files), "facts": len(kinds) and sum(kinds.values()), "cite_a_page": cited, **kinds}
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--borrower", default="kestrel-bay-packaging")
    args = parser.parse_args(argv)
    summary = build(args.borrower)
    print("STAND-IN reader, not a model. Wrote", summary["files"], "files to", OUT)
    print({k: v for k, v in summary.items() if k != "files"})
    return 0


if __name__ == "__main__":
    sys.exit(main())

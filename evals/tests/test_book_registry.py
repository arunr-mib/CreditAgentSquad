"""The harness knows both books and reads the oracle that belongs to the one it runs."""
import csv

from evals.book import BOOKS, DEFAULT_BOOK, load_book, oracle_for, unsigned_oracle_rows


def test_both_books_are_registered_and_innovation_is_the_default():
    assert set(BOOKS) == {"legacy", "innovation"}
    assert DEFAULT_BOOK == BOOKS["innovation"]
    assert (BOOKS["legacy"] / "truth").is_dir() and (BOOKS["innovation"] / "truth").is_dir()


def test_each_book_has_its_own_oracle_and_covers_every_borrower_in_it():
    for name, root in BOOKS.items():
        oracle = oracle_for(root)
        assert oracle.name == "oracle.csv" and oracle.is_file(), name
        codes = [b.code for b in load_book(root)]
        rows = list(csv.DictReader(oracle.open(newline="")))
        assert {r["borrower_id"] for r in rows} >= set(codes), name


def _unsigned_copy(src, dest):
    """The real key is signed; tests that need unsigned rows work on a copy with every row unsigned."""
    with src.open(newline="") as f:
        rows = list(csv.DictReader(f))
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({**r, "owner_signed_off": "no"} for r in rows)
    return dest


def test_the_legacy_oracle_is_not_consulted_for_an_innovation_borrower(tmp_path):
    new = _unsigned_copy(oracle_for(BOOKS["innovation"]), tmp_path / "oracle.csv")
    unsigned = unsigned_oracle_rows(["datamarrow"], new)
    assert unsigned and all(r["borrower_id"] == "datamarrow" for r in unsigned)
    assert unsigned_oracle_rows(["datamarrow"], oracle_for(BOOKS["legacy"]))[0]["item"] == "no oracle row"

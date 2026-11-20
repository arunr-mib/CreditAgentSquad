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


def test_the_legacy_oracle_is_not_consulted_for_an_innovation_borrower():
    new = oracle_for(BOOKS["innovation"])
    unsigned = unsigned_oracle_rows(["dataflake"], new)
    assert unsigned and all(r["borrower_id"] == "dataflake" for r in unsigned)
    assert unsigned_oracle_rows(["dataflake"], oracle_for(BOOKS["legacy"]))[0]["item"] == "no oracle row"

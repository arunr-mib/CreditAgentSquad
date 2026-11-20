from evals.book import BOOKS, load_book
from evals.run import LoadedBorrower
from evals.standin import StandInReader


def test_a_funding_item_raised_at_seed_time_reaches_the_recording(engine, file_store):
    book = load_book(BOOKS["innovation"], ["nimbusfield-security"])
    borrower = book.get("nimbusfield-security")
    with LoadedBorrower(engine, book, borrower) as loaded:
        recording = loaded.run(lambda: StandInReader(book), decide=False)
    assert "funding_slipped" in {w["type"] for w in recording["work_items"]}

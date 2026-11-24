"""Fixtures for the evaluation tests. The stand-in suite needs Postgres (TEST_DATABASE_URL) and
the generated book; nothing here ever calls a model.

Slow tests are marked `slow`; deselect them with: -m "not slow".
"""
import os

import pytest
from app import models
from app.core.config import get_settings
from app.core.ledger import install_guards
from sqlalchemy import create_engine, text

from evals.book import generate_book, load_book
from evals.run import run_pass, run_suite
from evals.standin import StandInReader

# a clean borrower with a borrowing base, a hidden breach, a missing page, a late package
SMALL = ["harrowgate-precision", "kestrel-bay-packaging", "ashgrove-fleet", "eastmere-building"]


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: takes a minute or more (the full stand-in suite, the mutation checks)")


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(get_settings().test_database_url)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        models.Base.metadata.create_all(conn)
        install_guards(conn)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session", params=["legacy", "innovation"])
def book_name(request):
    return request.param


@pytest.fixture(scope="session")
def book_root(book_name, tmp_path_factory):
    # `out` inside its own directory, so each book's oracle.csv lands beside it and the two never collide
    return generate_book(tmp_path_factory.mktemp(f"book-{book_name}") / "out", book_name)


@pytest.fixture(scope="session")
def legacy_book_root(tmp_path_factory):
    """The legacy book, for tests whose borrowers (SMALL, the mutation checks) are legacy ones."""
    return generate_book(tmp_path_factory.mktemp("book-legacy-fixed") / "out", "legacy")


@pytest.fixture(scope="session")
def file_store(tmp_path_factory):
    """Documents loaded during a run are kept in a scratch directory, not in the repository."""
    previous = os.environ.get("FILE_STORE_DIR")
    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    yield
    if previous is None:
        os.environ.pop("FILE_STORE_DIR", None)
    else:
        os.environ["FILE_STORE_DIR"] = previous
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def suite(engine, book_root):
    """The whole stand-in suite, run once: every borrower of a book (21 legacy, 20 innovation) through the live cycle (about two minutes)."""
    return run_suite(mode="standin", book_root=book_root, engine=engine, decide=True, keep_recordings=True)


@pytest.fixture(scope="session")
def small(engine, legacy_book_root, file_store):
    """Recordings of four borrowers (about 25 seconds), for tests that tamper with a recording."""
    book = load_book(legacy_book_root, SMALL)
    reader = StandInReader(book)
    return book, run_pass(engine, book, reader, decide=True)

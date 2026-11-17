"""A seeded world shared by the publishing tests: four borrowers loaded once through the real
services. Each test runs inside a savepoint that is rolled back, so packages do not leak."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.seed_book import seed_book
from app.seed_users import seed_users
from publishing.world import CODES
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="package")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    return out


@pytest.fixture(scope="package")
def seeded(engine, book, tmp_path_factory):
    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    seed_users(session, password="pw")
    seed_book(session, root=book, current="seeded", only=list(CODES))
    session.flush()
    yield session
    session.close()
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


@pytest.fixture()
def pub(seeded):
    """The seeded session inside a savepoint. Code under test flushes; nothing here commits."""
    savepoint = seeded.begin_nested()
    try:
        yield seeded
    finally:
        if savepoint.is_active:
            savepoint.rollback()
        seeded.expire_all()


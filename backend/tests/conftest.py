"""Test database setup. Each test runs inside a transaction that is rolled back at the end,
so service code may commit freely without leaking between tests."""
import pytest
from app import models
from app.core.config import get_settings
from app.core.db import get_db
from app.core.ledger import install_guards
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


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


@pytest.fixture()
def db(engine):
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


@pytest.fixture()
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c

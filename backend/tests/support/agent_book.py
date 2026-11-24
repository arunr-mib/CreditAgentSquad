"""Shared setup for agent tests that run against borrowers from the synthetic book, and a
scripted model whose later responses can read what the tools returned."""
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from app.agents.llm import LLMRequest, LLMResponse, RecordingMissing
from app.core.config import get_settings
from app.domain import hooks  # noqa: F401
from app.seed_book import seed_book
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[3]
BORROWERS = ["vantry-freight", "kestrel-bay-packaging", "pellham-grain", "thornbury-metal"]


@pytest.fixture(scope="module")
def book_db(engine, tmp_path_factory):
    """The four scenario borrowers, seeded once per test module inside a transaction that is
    rolled back at the end. Yields (session, truth by borrower id)."""
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    seed_book(db, root=out, current="seeded", only=BORROWERS)
    db.flush()
    truths = {code: json.loads((out / "truth" / f"{code}.json").read_text()) for code in BORROWERS}
    yield db, truths
    db.close()
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


@pytest.fixture()
def book(book_db):
    """One test's view of the seeded book: whatever the test writes is rolled back."""
    db, truths = book_db
    savepoint = db.begin_nested()
    try:
        yield db, truths
    finally:
        if savepoint.is_active:
            savepoint.rollback()
        db.expire_all()


Step = LLMResponse | Callable[[LLMRequest], LLMResponse]


class FlowClient:
    """Scripted responses in order. A step may be a function of the request, so a scripted answer
    can use ids that only exist once the tools have run."""

    mode = "scripted"

    def __init__(self, steps: list[Step]):
        self._steps = list(steps)
        self.requests: list[LLMRequest] = []

    def create(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._steps:
            raise RecordingMissing("the scripted client has no more responses")
        step = self._steps.pop(0)
        return step(request) if callable(step) else step


def tool_call(name: str, inp: dict | None = None) -> LLMResponse:
    return LLMResponse(content=[{"type": "tool_use", "id": uuid.uuid4().hex, "name": name, "input": inp or {}}],
                       stop_reason="tool_use", usage={"input_tokens": 10, "output_tokens": 5})


def answer(body: dict | str) -> LLMResponse:
    text = body if isinstance(body, str) else json.dumps(body)
    return LLMResponse(content=[{"type": "text", "text": text}], stop_reason="end_turn",
                       usage={"input_tokens": 10, "output_tokens": 5})


def tool_results(request: LLMRequest) -> list[dict]:
    """Every tool result the model has been shown so far, parsed, in order."""
    out = []
    for message in request.messages:
        if message["role"] != "user":
            continue
        for block in message["content"]:
            if block.get("type") == "tool_result":
                out.append(json.loads(block["content"]) if block["content"].startswith("{") else {"text": block["content"]})
    return out

# Phase 4a: The Squad Experience (backend, shell, home, threads, questions, drafts, evidence) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the cockpit with Credit Squad's conversation-first experience: a briefing home, one thread per client rebuilt from the record, Squad asks, drafts that only a person sends, free questions with sources, and an evidence drawer that pushes content aside, in five switchable looks.

**Architecture:** Every backend addition is a new module under `backend/app/squad/` behind one new router (`backend/app/api/routes_squad.py`); read models are folded from existing tables and the ledger, so a thread cannot drift from the record. Questions reuse the work-item table and the existing `decide_work_item` path; drafts are ledger events (no migration). The front end lives in `frontend/src/squad/` inside the existing Vite app and reuses `client.ts`, `SourceProvider`/`SourceDrawer`, `AgentBody`, `CommandPalette` and `useAuth`; its look is a separate `--sq-*` token set applied from one TypeScript table, so the retired cockpit screens keep working untouched until Phase 4b removes them.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, pytest (`uv run pytest`); React 19, Vite, TypeScript, TanStack Router and Query, Radix, vitest + Testing Library; Playwright (the globally installed one, as `frontend/e2e/run.mjs` already does) and axe-core.

**Spec:** `docs/specs/2026-11-20-squad-experience-design.md` (sections 3–14; section 15 owner decisions apply). Visual and behavioural reference: `docs/product/prototype/carly-morning.html` (frozen) and `docs/product/redesign-direction.md`. Lesson that shapes the tests: `docs/lessons/test-every-entry-route-not-just-the-guided-path.md`.

## Decisions taken at the top of this plan

**Where the new front end lives: inside `frontend/`, replacing the cockpit in two steps.** `frontend/` already has what the spec says to reuse: the cookie-session client and error handling (`src/api/client.ts`), the figure/source machinery (`SourceProvider`, `SourceDrawer`, `PdfPage`, `CalculationBreakdown`, `AgentBody` rendering `{{fact:…}}` through stored facts), the auth context, the command palette primitive, Tailwind tokens and a working vitest/Playwright/axe setup. A second app would copy all of it and drift. The cockpit screens themselves are not reused as screens (owner decision 2: client file views are redesigned, not restyled).
- **Phase 4a (this plan):** new code in `frontend/src/squad/`; `SquadShell` replaces `AppShell` as the shell for every route; `/` becomes Squad home; the old cockpit routes stay registered but are unlinked from the nav. They stay because `SourceDrawer` and `AgentBody` still deep-link to `/borrowers/$code/…` for "open in client file"; those links are redirected through one function (`src/squad/links.ts`) so Phase 4b retargets them in one place.
- **Phase 4b:** the redesigned client file replaces those routes; the cockpit screens, `AppShell`, `Rail` and old command-centre code are then deleted (v1 lives on in its own deployment and in git history at 2292b38).
- **Phase 4a is an integration milestone, not a release.** Until 4b ships, the interim client-file and portfolio links land on cockpit screens that look different from Squad's looks. Do not deploy 4a alone.

**Shared files this phase touches** (everything else is new). Phases 2–3 change `synthetic/`, `evals/`, `backend/app/seed_book.py` and nothing below, so conflicts are not expected; each edit is small and listed so a merge can be checked by eye.
- `backend/app/main.py`: one word added to `OPTIONAL_ROUTERS` (`"routes_squad"`).
- `backend/app/api/routes_work.py`: `list_ledger` gains an `after_seq` parameter (the spec's `GET /ledger?after_seq=`; the path already exists, so it cannot live in a new module).
- `frontend/src/router.tsx`: new routes, `/` redirect, sign-in redirect target.
- `frontend/src/styles.css`: one import line for `squad/squad.css`.
- `frontend/package.json`: scripts `e2e:squad`.
- Not touched: `seed_book.py`, any migration. Squad's demo data for the e2e journeys comes from a new file, `backend/app/squad_demo.py`, run after the book is seeded.

## Global Constraints

- The ledger is append-only and the engine decides who may do what (`core/roles.py`, `domain/workflow.py`); no Squad endpoint or screen makes a permission or two-person decision of its own. An answer to a question, a decision and a send all go through `can()` / `decide_work_item`.
- Squad never sends to a client on its own. "Send" records `draft.sent` on the ledger with the sending person as actor and delivers nothing; real email is a later connector (spec 9).
- A figure is never typed: agent text carries `{{fact:<id>}}` and is rendered by `AgentBody`. Free questions go through `POST /copilot/ask`; its refusal is shown as a refusal, never softened (spec 7).
- State is computed from the record, never assumed: badges, "needs you" counts and state words come from `GET /me/briefing` / `GET /threads/{id}`; no screen derives them from a step number or local flag (lesson: test every entry route).
- Product name on screen: "Credit Squad" (presence label, sign-in, document title); "Squad" elsewhere (spec 15.1).
- Looks: Night (analyst default), Warm paper (credit officer default), Cool slate, Lavender mist, Sage. Anyone can switch. Text at least 4.5:1 against ground, surface and sunk in every look (the spec's floor is 3:1; this plan holds a stricter bar and tests it); non-text marks at least 3:1.
- Evidence documents are always paper-white (`--sq-paper`) in every look. Ink (not ember) primary buttons; ember only for needs-you; lavender for Squad and agent-written work.
- Reduced motion (`prefers-reduced-motion: reduce`) turns every animation off, including the Squad mark.
- Confirmations appear in the reserved presence line; nothing is ever placed over content.
- The drawer pushes the conversation aside; works at widths 1000 to 1920 px with no horizontal page scroll.
- Money and ratios are Decimal strings from the API; the front end never parses them to floats for display (use `formatFigure` from `@/design`).
- No import of `app.calc` or `app.guardrails` from `backend/app/squad/` writes anything; Squad modules only read, or call existing domain functions (`raise_item`, `decide_work_item`, `record_lesson`, `ledger.record`).
- Backend: `uv run pytest` from the repo root with Postgres started (`service postgresql start`); the existing suite stays green after every task. Front end: `pnpm test`, `pnpm typecheck`, `pnpm lint` from `frontend/`, all green after every task. Do not run the whole e2e against a database you want to keep: journeys write (an answer, a draft send, a lesson).
- Owner defaults taken where the spec was silent (each can be overruled; see the final list in the self-review): default look is Warm paper for `credit_officer` only and Night for every other role; thread "case" cards exist for non-question work items; draft ids and states are ledger-derived.

## Review Focus

1. **Entering a client by every route lands in the same client's thread, at the right case** (home item, nav "Open cases", portfolio row, palette, deep link `?case=`). A deep link with an unknown or already-decided case id must show the thread, not an error or another client's case. Tested in Tasks 1, 11, 15.
2. **A badge or "needs you" count must equal the number of actionable items actually listed**, for the analyst and for the officer, and must fall when an item is answered, without a reload (polling). Tested in Tasks 2, 10, 15.
3. **Answering a question twice, or answering with an option not offered, or answering a decided item** is refused with a plain message; "Remember" writes exactly one lesson and only when ticked; a person without `decide_work_item` cannot answer. Tested in Task 3.
4. **A sent draft cannot be edited or sent again; a draft cannot be sent by someone without the permission; "Send" must not claim delivery.** Tested in Tasks 4, 13.
5. **A client with no history, no open items or no documents** (new innovation borrower) shows an honest empty thread and an empty briefing line ("Nothing needs you"), not a blank page or a count of zero in an error colour. Tested in Tasks 1, 2, 10, 11.
6. **Polling must stop when the tab is hidden or the person signs out, must not stack requests, and a failed poll must not blank the thread.** Tested in Task 9.
7. **Contrast and motion in every look**: a token edit that drops any text pair below 4.5:1 fails the unit test; the mark under reduced motion does not animate. Tested in Tasks 6, 7, 15.

---

## File map

| File | Change |
|---|---|
| `backend/app/squad/__init__.py` | New package |
| `backend/app/squad/threads.py` | `build_thread(db, borrower_id)`; message mapping (spec 6) |
| `backend/app/squad/briefing.py` | `build_briefing(db, user)` |
| `backend/app/squad/questions.py` | `raise_question`, `answer_question` |
| `backend/app/squad/drafts.py` | `create_draft`, `edit_draft`, `send_draft`, `drafts_for(db, borrower_id)` (ledger-derived) |
| `backend/app/squad/trail.py` | `case_trail(db, item)` |
| `backend/app/squad/track_record.py` | `track_record(db, borrower_id)` |
| `backend/app/api/routes_squad.py` | The new endpoints |
| `backend/app/api/routes_work.py` | `list_ledger(after_seq=…)` (shared) |
| `backend/app/main.py` | `"routes_squad"` in `OPTIONAL_ROUTERS` (shared) |
| `backend/app/squad_demo.py` | `seed_squad_demo(db)` for the e2e and demos |
| `backend/tests/squad/` | `conftest.py`, `test_ledger_after.py`, `test_threads.py`, `test_briefing.py`, `test_questions.py`, `test_drafts.py`, `test_trail_track.py` |
| `frontend/src/squad/looks.ts`, `useLook.tsx`, `LookMenu.tsx`, `squad.css` | Looks, role default, switcher, mark/motion CSS |
| `frontend/src/squad/mark/SquadMark.tsx`, `presence/Presence.tsx` | The mark and the presence line |
| `frontend/src/squad/shell/SquadShell.tsx`, `SquadNav.tsx`, `commands.ts` | Shell, collapsible nav, palette commands |
| `frontend/src/squad/api/types.ts`, `hooks.ts` | Typed endpoints, polling |
| `frontend/src/squad/links.ts` | One place for "open in client file" targets |
| `frontend/src/squad/home/SquadHome.tsx` | Briefing |
| `frontend/src/squad/thread/ClientThread.tsx`, `messages.tsx`, `AskMessage.tsx`, `QaMessage.tsx`, `Composer.tsx`, `DraftMessage.tsx` | Thread |
| `frontend/src/squad/evidence/EvidenceResizer.tsx` | Resizable drawer edge |
| `frontend/src/squad/**/__tests__/*.test.tsx` | Component tests |
| `frontend/e2e/squad.mjs` | Journeys, contrast scan, widths |
| `frontend/src/router.tsx`, `src/styles.css`, `package.json` | Shared edits listed above |

---

### Task 1: Ledger polling cursor and the client thread read model

**Files:**
- Modify: `backend/app/api/routes_work.py` (`list_ledger`, around line 300)
- Create: `backend/app/squad/__init__.py`, `backend/app/squad/threads.py`, `backend/app/api/routes_squad.py`
- Modify: `backend/app/main.py` (`OPTIONAL_ROUTERS`)
- Create: `backend/tests/squad/__init__.py`, `backend/tests/squad/conftest.py`, `backend/tests/squad/test_ledger_after.py`, `backend/tests/squad/test_threads.py`

**Interfaces:**
- Produces: `GET /api/v1/ledger?after_seq=<int>` (ascending, only newer than the cursor; the existing descending behaviour is unchanged without it). `GET /api/v1/threads/{borrower_id}` returning `{"borrower": {"id","code","name","template_id"}, "head_seq": int, "messages": [Message]}`. `build_thread(db: Session, borrower_id: uuid.UUID) -> dict` in `app.squad.threads`.
- Message shape: `{"id": str, "type": "report"|"case"|"ask"|"document"|"held"|"draft"|"decision"|"handoff"|"qa", "ts": iso str, ...type fields}`. Type fields: `report`: `agent_name, task, text, run_id`. `case`: `work_item_id, item_type, title, question, severity, status`. `ask`: `work_item_id, title, question, options, status, choice, chosen_by`. `document`: `document_id, title, doc_type, period_end, pages`. `held`: `document_id, title, reason`. `decision`: `work_item_id, decision, reason, by, by_id`. `handoff`: `work_item_id, assigned_to, assigned_to_id, by`. `qa`: `question, answer, fact_ids, citations, status, run_id, asked_by`. `draft`: added by Task 4 (this task leaves the hook `drafts_messages` returning `[]`).
- Messages are ordered oldest first by `(ts, id)`; `head_seq` is the highest ledger `seq` when the thread was read (0 if the ledger is empty), the cursor the browser polls with.
- Test helpers in `conftest.py`: fixture `world(db)` returns a dict with `analyst`, `officer`, `admin` (Users), `borrower` (Borrower "QFL"), `other` (a second Borrower "ZZZ"); function `sign_in(client, who)` (`who` is the part before `@bankofstoic.example`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/squad/conftest.py
import pytest
from app.domain.credit import Borrower
from app.domain.org import User
from app.seed_users import seed_users
from sqlalchemy import select

PASSWORD = "pw"


def sign_in(client, who: str):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": PASSWORD})
    assert r.status_code == 200, r.text


def _user(db, email_start: str) -> User:
    return db.execute(select(User).where(User.email.like(f"{email_start}@%"))).scalar_one()


@pytest.fixture()
def world(db):
    seed_users(db, password=PASSWORD)
    borrower = Borrower(code="QFL", name="Quillfeather Labs, Inc.", template_id="vc-1")
    other = Borrower(code="ZZZ", name="Zephyr Zinc Works, Inc.")
    db.add_all([borrower, other])
    db.flush()
    return {"analyst": _user(db, "priya.raman"), "officer": _user(db, "helen.strand"),
            "admin": _user(db, "admin"), "borrower": borrower, "other": other}
```

```python
# backend/tests/squad/test_ledger_after.py
from app.core import ledger

from .conftest import sign_in


def _event(db, n):
    return ledger.record(db, actor_type="system", actor_id="t", action="test.event", entity_type="t", entity_id=str(n))


def test_after_seq_returns_only_newer_events_oldest_first(db, client, world):
    first = _event(db, 1)
    second = _event(db, 2)
    third = _event(db, 3)
    db.commit()
    sign_in(client, "priya.raman")
    rows = client.get(f"/api/v1/ledger?after_seq={first.seq}").json()
    assert [r["seq"] for r in rows] == [second.seq, third.seq]


def test_after_seq_at_the_head_is_empty_not_an_error(db, client, world):
    last = _event(db, 1)
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/ledger?after_seq={last.seq}").json() == []


def test_without_after_seq_the_list_is_still_newest_first(db, client, world):
    a, b = _event(db, 1), _event(db, 2)
    db.commit()
    sign_in(client, "priya.raman")
    seqs = [r["seq"] for r in client.get("/api/v1/ledger?entity_type=t").json()]
    assert seqs == [b.seq, a.seq]


def test_after_seq_rejects_a_negative_cursor(client, world):
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/ledger?after_seq=-1").status_code == 422
```

```python
# backend/tests/squad/test_threads.py
import uuid
from datetime import date

from app.core import ledger
from app.domain import workflow
from app.domain.documents import Document
from app.domain.work_items import raise_item
from app.squad.threads import build_thread

from .conftest import sign_in


def _item(db, borrower, title="Confirm revenue"):
    return raise_item(db, borrower_id=borrower.id, item_type="funding_slipped", title=title,
                      question="Should the runway outlook be reviewed?", allowed_decisions=["reviewed", "escalate_to_committee"])


def _doc(db, borrower, status="indexed", title="October compliance certificate"):
    d = Document(borrower_id=borrower.id, title=title, file_name="c.pdf", storage_path="x", sha256="a" * 64,
                 page_count=2, doc_type="compliance_certificate", period_end=date(2026, 10, 31), status=status)
    db.add(d)
    db.flush()
    ledger.record(db, actor_type="system", actor_id="intake", action="document.received", entity_type="document",
                  entity_id=d.id, payload={"borrower_id": borrower.id, "file_name": "c.pdf"})
    return d


def test_an_empty_client_has_an_empty_thread_not_an_error(db, world):
    thread = build_thread(db, world["borrower"].id)
    assert thread["messages"] == []
    assert thread["borrower"]["code"] == "QFL"
    assert isinstance(thread["head_seq"], int)


def test_thread_maps_documents_cases_and_decisions_in_time_order(db, world):
    doc = _doc(db, world["borrower"])
    item = _item(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    kinds = [m["type"] for m in build_thread(db, world["borrower"].id)["messages"]]
    assert kinds == ["document", "case", "decision"]
    document = build_thread(db, world["borrower"].id)["messages"][0]
    assert document["document_id"] == str(doc.id) and document["pages"] == 2


def test_a_set_aside_document_is_a_held_message_with_its_reason(db, world):
    doc = _doc(db, world["borrower"], status="rejected")
    ledger.record(db, actor_type="user", actor_id=world["analyst"].id, action="document.set_aside",
                  entity_type="document", entity_id=doc.id, payload={"reason": "Not this client's file"})
    held = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "held"]
    assert held and held[0]["reason"] == "Not this client's file"


def test_another_clients_records_never_appear(db, world):
    _item(db, world["other"], title="Zinc item")
    _doc(db, world["other"])
    assert build_thread(db, world["borrower"].id)["messages"] == []


def test_copilot_exchange_becomes_a_qa_message_for_that_client_only(db, world):
    run_id = uuid.uuid4()
    for borrower, text in ((world["borrower"], "What is cash?"), (world["other"], "What is zinc?")):
        ledger.record(db, actor_type="user", actor_id=world["analyst"].id, action="copilot.asked",
                      entity_type="agent_run", entity_id=run_id if borrower is world["borrower"] else uuid.uuid4(),
                      payload={"question": text, "borrower_id": borrower.id, "status": "answered",
                               "answer_with_references": "Cash was {{fact:abc}}.", "fact_ids": ["abc"],
                               "citations": [{"document_id": "d1", "page": 3}]})
    qa = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "qa"]
    assert len(qa) == 1 and qa[0]["question"] == "What is cash?" and qa[0]["fact_ids"] == ["abc"]
    assert qa[0]["asked_by"] == "Priya Raman"


def test_thread_endpoint_requires_sign_in_and_404s_an_unknown_client(db, client, world):
    assert client.get(f"/api/v1/threads/{world['borrower'].id}").status_code == 401
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/threads/{uuid.uuid4()}").status_code == 404
    body = client.get(f"/api/v1/threads/{world['borrower'].id}").json()
    assert body["messages"] == [] and body["borrower"]["name"] == "Quillfeather Labs, Inc."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest backend/tests/squad -v`
Expected: FAIL (`ModuleNotFoundError: app.squad`, and `after_seq` ignored).

- [ ] **Step 3: Implement**

In `backend/app/api/routes_work.py` change `list_ledger` (keep everything else):

```python
@router.get("/ledger")
def list_ledger(entity_type: str | None = None, entity_id: str | None = None, action: str | None = None,
                before_seq: int | None = Query(default=None, ge=1, le=2**63 - 1),
                after_seq: int | None = Query(default=None, ge=0, le=2**63 - 1), limit: int = 100,
                db: Session = Depends(get_db),
                _: User = Depends(current_user)) -> list[dict]:
    """Newest first. With `after_seq` (the polling cursor) only events after it, oldest first."""
    limit = max(1, min(limit, 500))
    query = select(LedgerEvent)
    if after_seq is not None:
        query = query.where(LedgerEvent.seq > after_seq).order_by(LedgerEvent.seq.asc())
    else:
        query = query.order_by(LedgerEvent.seq.desc())
    query = query.limit(limit)
    if entity_type:
        query = query.where(LedgerEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(LedgerEvent.entity_id == entity_id)
    if action:
        query = query.where(LedgerEvent.action.like(action + "%"))
    if before_seq:
        query = query.where(LedgerEvent.seq < before_seq)
    return [row(e) for e in db.execute(query).scalars()]
```

In `backend/app/main.py` add `"routes_squad"` to the end of `OPTIONAL_ROUTERS`.

```python
# backend/app/squad/__init__.py
"""The Squad experience's read models and write helpers. Everything here is derived from the record."""
```

```python
# backend/app/squad/threads.py
"""A client's thread: the record, mapped to the message types the conversation shows (spec 6).
Nothing here is stored; the thread is rebuilt on every read so it cannot drift from the ledger."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.serialize import plain
from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.work_items import offered

RANK = {"document": 0, "held": 0, "report": 1, "case": 2, "ask": 2, "draft": 3, "qa": 4, "handoff": 5, "decision": 6}
REPORT_TEXT_KEYS = ("narrative", "summary", "explanation")  # an agent's written output, with {{fact:…}} references


def _names(db: Session) -> dict[str, str]:
    return {str(u.id): u.name for u in db.execute(select(User)).scalars()}


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _events(db: Session, action_prefix: str, ids: list[str] | None = None, entity_type: str | None = None):
    query = select(LedgerEvent).where(LedgerEvent.action.like(action_prefix + "%")).order_by(LedgerEvent.seq)
    if ids is not None:
        query = query.where(LedgerEvent.entity_id.in_(ids or ["-"]))
    if entity_type:
        query = query.where(LedgerEvent.entity_type == entity_type)
    return db.execute(query).scalars().all()


def drafts_messages(db: Session, borrower_id: uuid.UUID, names: dict[str, str]) -> list[dict[str, Any]]:
    """Replaced in Task 4 by the ledger-derived drafts."""
    return []


def build_thread(db: Session, borrower_id: uuid.UUID) -> dict[str, Any]:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise LookupError("borrower not found")
    names = _names(db)
    bid = str(borrower_id)
    messages: list[dict[str, Any]] = []

    docs = db.execute(select(Document).where(Document.borrower_id == borrower_id)).scalars().all()
    aside = {e.entity_id: e for e in _events(db, "document.set_aside", [str(d.id) for d in docs])}
    for d in docs:
        base = {"id": f"doc:{d.id}", "ts": _iso(d.created_at), "document_id": str(d.id), "title": d.title}
        if d.status == "rejected":
            event = aside.get(str(d.id))
            messages.append({**base, "type": "held", "reason": (event.payload or {}).get("reason", "") if event else ""})
        else:
            messages.append({**base, "type": "document", "doc_type": d.doc_type, "pages": d.page_count,
                             "period_end": plain(d.period_end)})

    items = db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower_id)).scalars().all()
    item_ids = [str(i.id) for i in items]
    for i in items:
        if i.item_type == "question":
            options = (i.evidence or {}).get("options", [])
            chosen = next((o for o in options if o["id"] == i.decision), None)
            messages.append({"id": f"ask:{i.id}", "type": "ask", "ts": _iso(i.created_at), "work_item_id": str(i.id),
                             "title": i.title, "question": i.question, "options": options, "status": i.status,
                             "choice": chosen["label"] if chosen else None,
                             "chosen_by": names.get(str(i.decided_by)) if i.decided_by else None})
        else:
            messages.append({"id": f"case:{i.id}", "type": "case", "ts": _iso(i.created_at), "work_item_id": str(i.id),
                             "item_type": i.item_type, "title": i.title, "question": i.question,
                             "severity": i.severity, "status": i.status,
                             "allowed_decisions": offered(i.item_type, i.allowed_decisions)})

    for e in _events(db, "work_item.decided", item_ids):
        p = e.payload or {}
        messages.append({"id": f"decision:{e.seq}", "type": "decision", "ts": _iso(e.ts), "work_item_id": e.entity_id,
                         "decision": p.get("decision"), "reason": p.get("reason", ""),
                         "by": names.get(e.actor_id, e.actor_id), "by_id": e.actor_id})
    for e in _events(db, "work_item.assigned", item_ids):
        to = (e.payload or {}).get("assigned_to")
        messages.append({"id": f"handoff:{e.seq}", "type": "handoff", "ts": _iso(e.ts), "work_item_id": e.entity_id,
                         "assigned_to": names.get(str(to)) if to else None, "assigned_to_id": to,
                         "by": names.get(e.actor_id, e.actor_id)})

    for run in db.execute(select(AgentRun).where(AgentRun.borrower_id == borrower_id, AgentRun.status == "completed",
                                                 AgentRun.agent_name != "copilot")).scalars():
        out = run.output or {}
        text = next((out[k] for k in REPORT_TEXT_KEYS if isinstance(out.get(k), str) and out[k].strip()), None)
        if text:
            messages.append({"id": f"run:{run.id}", "type": "report", "ts": _iso(run.finished_at or run.created_at),
                             "agent_name": run.agent_name, "task": run.task, "text": text, "run_id": str(run.id)})

    for e in _events(db, "copilot.asked"):
        p = e.payload or {}
        if p.get("borrower_id") != bid:
            continue
        messages.append({"id": f"qa:{e.seq}", "type": "qa", "ts": _iso(e.ts), "question": p.get("question", ""),
                         "answer": p.get("answer_with_references", ""), "fact_ids": p.get("fact_ids", []),
                         "citations": p.get("citations", []), "status": p.get("status", "answered"),
                         "run_id": e.entity_id, "asked_by": names.get(e.actor_id, e.actor_id)})

    messages += drafts_messages(db, borrower_id, names)
    # Ledger instants are whole seconds while rows carry microseconds, so order by the second and then by
    # how a case unfolds (documents in, then the case, then who it was handed to, then the decision).
    messages.sort(key=lambda m: (datetime.fromisoformat(m["ts"]).replace(microsecond=0), RANK[m["type"]], m["id"]))
    head = db.execute(select(func.coalesce(func.max(LedgerEvent.seq), 0))).scalar_one()
    return {"borrower": {"id": bid, "code": borrower.code, "name": borrower.name, "template_id": borrower.template_id},
            "head_seq": int(head), "messages": messages}
```

```python
# backend/app/api/routes_squad.py
"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.db import get_db
from app.domain.org import User
from app.squad.threads import build_thread

router = APIRouter(tags=["squad"])


@router.get("/threads/{borrower_id}")
def get_thread(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    try:
        return build_thread(db, borrower_id)
    except LookupError as exc:
        raise HTTPException(404, "Client not found.") from exc
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest backend/tests/squad backend/tests/api/test_routes.py -v`
Expected: PASS (the existing ledger route tests still pass).

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad backend/app/api/routes_squad.py backend/app/api/routes_work.py backend/app/main.py backend/tests/squad
git commit -m "feat(squad): ledger polling cursor and the client thread read model"
```

---

### Task 2: The briefing (`GET /me/briefing`)

**Files:**
- Create: `backend/app/squad/briefing.py`, `backend/tests/squad/test_briefing.py`
- Modify: `backend/app/api/routes_squad.py`

**Interfaces:**
- Consumes: `world`, `sign_in` (Task 1); `raise_item`, `workflow.decide_work_item`.
- Produces: `build_briefing(db, user) -> dict` and `GET /api/v1/me/briefing`:
  `{"as_of": "YYYY-MM-DD", "needs_you": int, "items": [Item], "overnight": [{"agent_name","text","borrower_id","borrower_code","borrower_name","finished_at"}], "open_clients": [{"borrower_id","code","name","open"}]}`.
  `Item = {"key","kind","borrower_id","borrower_code","borrower_name","title","state","severity","needs_you": bool,"work_item_id": str|None}`. `kind` is one of `breach`, `overdue_report`, `signal`, `question`, `review`, `funding`, `decided`. Order is by consequence: breach, overdue report, signal, question, review, funding, decided; within a kind by severity then due date. `needs_you` is the number of items with `needs_you: true`; it is computed from the same list the page shows.
- Rules: an open work item is the user's to act on when `can(user.role, item.required_permission)` and it is unassigned or assigned to the user. An open item assigned to someone else that the user prepared (`prepared_by_id`) is listed with state `with <name>` and `needs_you: false`. An item decided in the last two days (real time, `decided_at`) is listed as `decided` with state `<decision words> by <name>` and `needs_you: false`. Overdue obligations and open signals are listed for every user, `needs_you` true for roles holding `decide_work_item`; a signal is listed once per borrower. `breach` = item types `covenant.breach`, `covenant.reported_breach_unconfirmed`, `bb.over_advance`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/squad/test_briefing.py
from datetime import date, timedelta

from app.domain import workflow
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing

from .conftest import sign_in


def _breach(db, borrower, title="Cash below minimum"):
    return raise_item(db, borrower_id=borrower.id, item_type="covenant.breach", title=title, severity="critical",
                      question="Is this a breach?", allowed_decisions=["waiver_requested", "not_a_breach"],
                      required_permission="decide_breach")


def _review(db, borrower, title="Confirm revenue"):
    return raise_item(db, borrower_id=borrower.id, item_type="funding_slipped", title=title,
                      question="Should the runway outlook be reviewed?", allowed_decisions=["reviewed", "escalate_to_committee"])


def test_an_empty_book_says_nothing_needs_you(db, world):
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == 0 and b["items"] == [] and b["open_clients"] == []


def test_the_count_equals_the_actionable_items_listed(db, world):
    _review(db, world["borrower"])
    _review(db, world["other"], title="Second")
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == sum(1 for i in b["items"] if i["needs_you"]) == 2
    assert {c["code"] for c in b["open_clients"]} == {"QFL", "ZZZ"}


def test_the_analyst_cannot_act_on_a_breach_the_officer_can(db, world):
    _breach(db, world["borrower"])
    analyst = build_briefing(db, world["analyst"])
    officer = build_briefing(db, world["officer"])
    assert analyst["needs_you"] == 0 and officer["needs_you"] == 1
    assert officer["items"][0]["kind"] == "breach" and officer["items"][0]["state"] == "waiting for you"


def test_ordering_is_by_consequence_breach_before_review(db, world):
    _review(db, world["borrower"])
    _breach(db, world["other"])
    kinds = [i["kind"] for i in build_briefing(db, world["officer"])["items"]]
    assert kinds.index("breach") < kinds.index("review")


def test_an_item_with_the_officer_reads_with_her_to_the_analyst_who_prepared_it(db, world):
    item = _breach(db, world["borrower"])
    item.prepared_by_id = str(world["analyst"].id)
    item.assigned_to = world["officer"].id
    db.flush()
    mine = [i for i in build_briefing(db, world["analyst"])["items"] if i["work_item_id"] == str(item.id)]
    assert mine and mine[0]["state"] == "with Helen Strand" and mine[0]["needs_you"] is False


def test_a_recent_decision_is_listed_with_who_decided_and_does_not_count(db, world):
    item = _review(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    b = build_briefing(db, world["analyst"])
    assert b["needs_you"] == 0
    assert b["items"][0]["kind"] == "decided" and b["items"][0]["state"] == "reviewed by Priya Raman"


def test_a_decision_older_than_two_days_drops_off(db, world):
    item = _review(db, world["borrower"])
    workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="reviewed")
    item.decided_at = item.decided_at - timedelta(days=3)
    db.flush()
    assert build_briefing(db, world["analyst"])["items"] == []


def test_briefing_endpoint_follows_the_signed_in_user(db, client, world):
    _breach(db, world["borrower"])
    db.commit()
    sign_in(client, "helen.strand")
    assert client.get("/api/v1/me/briefing").json()["needs_you"] == 1
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/me/briefing").json()["needs_you"] == 0
    assert isinstance(date.fromisoformat(client.get("/api/v1/me/briefing").json()["as_of"]), date)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest backend/tests/squad/test_briefing.py -v`
Expected: FAIL (`No module named app.squad.briefing`).

- [ ] **Step 3: Implement**

```python
# backend/app/squad/briefing.py
"""What Squad tells the signed-in person on opening: what needs them, ordered by consequence,
and what agents finished overnight. Every count is taken from the list that is returned."""
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.roles import Permission, can
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.funding import FundingEvent
from app.domain.monitoring import Signal, WorkItem
from app.domain.org import User
from app.domain.terms import ReportingObligation
from app.squad.threads import REPORT_TEXT_KEYS

BREACH_TYPES = frozenset({"covenant.breach", "covenant.reported_breach_unconfirmed", "bb.over_advance"})
KIND_RANK = {"breach": 0, "overdue_report": 1, "signal": 2, "question": 3, "review": 4, "funding": 5, "decided": 6}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
RECENT = timedelta(days=2)
FUNDING_WINDOW_DAYS = 14


def _words(decision: str | None) -> str:
    return (decision or "decided").replace("_", " ")


def build_briefing(db: Session, user: User) -> dict[str, Any]:
    today = clock.today(db)
    borrowers = {b.id: b for b in db.execute(select(Borrower)).scalars()}
    names = {u.id: u.name for u in db.execute(select(User)).scalars()}
    can_decide = can(user.role, Permission.DECIDE_WORK_ITEM)

    def ref(borrower_id) -> dict[str, Any]:
        b = borrowers[borrower_id]
        return {"borrower_id": str(b.id), "borrower_code": b.code, "borrower_name": b.name}

    items: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for w in db.execute(select(WorkItem)).scalars():
        if w.borrower_id not in borrowers:
            continue
        kind = "question" if w.item_type == "question" else "breach" if w.item_type in BREACH_TYPES else "review"
        base = {**ref(w.borrower_id), "title": w.title, "severity": w.severity, "work_item_id": str(w.id)}
        if w.status == "open":
            actionable = can(user.role, Permission(w.required_permission)) and w.assigned_to in (None, user.id)
            if actionable:
                state = "Squad asks" if kind == "question" else "waiting for you"
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": state, "needs_you": True,
                              "_due": w.due_date})
            elif w.assigned_to and w.assigned_to != user.id and w.prepared_by_id == str(user.id):
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": f"with {names.get(w.assigned_to, 'a colleague')}",
                              "needs_you": False, "_due": w.due_date})
        elif w.status == "decided" and w.decided_at and now - w.decided_at <= RECENT:
            items.append({**base, "key": f"item:{w.id}", "kind": "decided",
                          "state": f"{_words(w.decision)} by {names.get(w.decided_by, 'a colleague')}",
                          "needs_you": False, "_due": None})

    for ob in db.execute(select(ReportingObligation).where(ReportingObligation.status == "overdue")).scalars():
        if ob.borrower_id in borrowers:
            days = (today - ob.due_date).days
            items.append({**ref(ob.borrower_id), "key": f"overdue:{ob.id}", "kind": "overdue_report",
                          "title": f"{ob.document_type.replace('_', ' ').capitalize()} for {ob.period_end:%B %Y} is overdue",
                          "state": f"{days} days overdue", "severity": "medium", "needs_you": can_decide,
                          "work_item_id": None, "_due": ob.due_date})

    seen_signals: set = set()
    for s in db.execute(select(Signal).where(Signal.status == "open")).scalars():
        if s.borrower_id in borrowers and s.borrower_id not in seen_signals:
            seen_signals.add(s.borrower_id)
            items.append({**ref(s.borrower_id), "key": f"signal:{s.borrower_id}", "kind": "signal",
                          "title": "A signal needs a look", "state": "new signal", "severity": s.severity,
                          "needs_you": can_decide, "work_item_id": None, "_due": None})

    horizon = today + timedelta(days=FUNDING_WINDOW_DAYS)
    for f in db.execute(select(FundingEvent).where(FundingEvent.status.in_(("expected", "signed")),
                                                   FundingEvent.expected_close <= horizon)).scalars():
        if f.borrower_id in borrowers:
            items.append({**ref(f.borrower_id), "key": f"funding:{f.id}", "kind": "funding",
                          "title": f"Expected {f.kind.replace('_', ' ')} closes {f.expected_close:%d %B}",
                          "state": f.status, "severity": "low", "needs_you": False, "work_item_id": None,
                          "_due": f.expected_close})

    items.sort(key=lambda i: (KIND_RANK[i["kind"]], SEVERITY_RANK.get(i["severity"], 9), i["_due"] or today))
    for i in items:
        i.pop("_due")

    overnight = []
    since = now - timedelta(hours=18)
    for run in db.execute(select(AgentRun).where(AgentRun.status == "completed", AgentRun.agent_name != "copilot",
                                                 AgentRun.borrower_id.is_not(None)).order_by(AgentRun.finished_at.desc())).scalars():
        done = run.finished_at or run.created_at
        out = run.output or {}
        text = next((out[k] for k in REPORT_TEXT_KEYS if isinstance(out.get(k), str) and out[k].strip()), None)
        if done >= since and text and run.borrower_id in borrowers:
            overnight.append({"agent_name": run.agent_name, "text": text, "finished_at": done.isoformat(),
                              **ref(run.borrower_id)})
        if len(overnight) == 8:
            break

    open_clients: dict[str, dict[str, Any]] = {}
    for i in items:
        if i["kind"] != "decided":
            c = open_clients.setdefault(i["borrower_id"], {"borrower_id": i["borrower_id"], "code": i["borrower_code"],
                                                            "name": i["borrower_name"], "open": 0})
            c["open"] += 1
    return {"as_of": today.isoformat(), "needs_you": sum(1 for i in items if i["needs_you"]), "items": items,
            "overnight": overnight, "open_clients": sorted(open_clients.values(), key=lambda c: c["name"])}
```

Add to `backend/app/api/routes_squad.py`:

```python
from app.squad.briefing import build_briefing


@router.get("/me/briefing")
def my_briefing(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return build_briefing(db, user)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest backend/tests/squad/test_briefing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad/briefing.py backend/app/api/routes_squad.py backend/tests/squad/test_briefing.py
git commit -m "feat(squad): GET /me/briefing, ordered by consequence, counted from what it lists"
```

---

### Task 3: Squad asks: the `question` work item and `POST /work-items/{id}/answer`

**Files:**
- Create: `backend/app/squad/questions.py`, `backend/tests/squad/test_questions.py`
- Modify: `backend/app/api/routes_squad.py`

**Interfaces:**
- Consumes: `raise_item`, `workflow.decide_work_item`, `record_lesson` (`app.domain.lessons`), `world`, `sign_in`.
- Produces: `raise_question(db, *, borrower_id, title, question, options, evidence=None, topic="question", cycle_id=None, severity="medium", actor=("agent","squad")) -> WorkItem` where `options` is a list of 2 to 6 `{"id": slug, "label": str, "evidence": str}` (ids unique, `[a-z0-9_]+`); the item has `item_type="question"`, `allowed_decisions` equal to the option ids, `evidence["options"]`, `evidence["topic"]`, `blocks_stage=False`. `answer_question(db, item, user, option_id, *, remember=False, note="") -> WorkItem`. `POST /api/v1/work-items/{id}/answer` body `{"option_id": str, "remember": bool=false, "note": str=""}` returning the work item JSON plus `"lesson_id": str | null`. Errors: 404 unknown item, 422 not a question / option not offered / already answered, 403 role cannot decide it.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/squad/test_questions.py
import pytest
from app.core.ledger import LedgerEvent
from app.domain.agents import Lesson
from app.squad.questions import answer_question, raise_question
from sqlalchemy import func, select

from .conftest import sign_in

OPTIONS = [
    {"id": "map_to_arr", "label": "Map to ARR", "evidence": "Page 3 labels it ARR."},
    {"id": "map_to_mrr", "label": "Map to MRR", "evidence": "Page 3 also shows monthly."},
]


def _ask(db, borrower):
    return raise_question(db, borrower_id=borrower.id, title="How should I map this line?",
                          question="Is 'Recurring revenue' ARR or MRR?", options=OPTIONS, topic="line_mapping")


def _lessons(db):
    return db.execute(select(func.count()).select_from(Lesson)).scalar_one()


def test_raising_a_question_offers_exactly_its_options(db, world):
    item = _ask(db, world["borrower"])
    assert item.item_type == "question" and item.allowed_decisions == ["map_to_arr", "map_to_mrr"]
    assert item.evidence["options"][0]["label"] == "Map to ARR" and item.blocks_stage is False


@pytest.mark.parametrize("bad", [[], OPTIONS[:1], OPTIONS + [{"id": "map_to_arr", "label": "dup", "evidence": ""}],
                                 [{"id": "Has Space", "label": "x", "evidence": ""}, OPTIONS[1]]])
def test_a_question_needs_two_to_six_distinct_slug_options(db, world, bad):
    with pytest.raises(ValueError):
        raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?", options=bad)


def test_answering_records_the_choice_with_her_name_and_no_lesson_by_default(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr")
    assert item.status == "decided" and item.decision == "map_to_arr" and item.decided_by == world["analyst"].id
    assert _lessons(db) == 0


def test_remember_writes_exactly_one_lesson_naming_her_choice(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr", remember=True)
    lessons = db.execute(select(Lesson)).scalars().all()
    assert len(lessons) == 1 and lessons[0].topic == "line_mapping" and "Map to ARR" in lessons[0].text
    assert lessons[0].work_item_id == item.id and lessons[0].written_by == world["analyst"].id


def test_an_option_not_offered_is_refused_and_nothing_is_recorded(db, world):
    item = _ask(db, world["borrower"])
    with pytest.raises(ValueError):
        answer_question(db, item, world["analyst"], "map_to_nothing", remember=True)
    assert item.status == "open" and _lessons(db) == 0


def test_answering_twice_is_refused_and_writes_no_second_lesson(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr", remember=True)
    with pytest.raises(ValueError):
        answer_question(db, item, world["analyst"], "map_to_mrr", remember=True)
    assert _lessons(db) == 1


def test_only_a_question_can_be_answered_this_way(db, world):
    from app.domain.work_items import raise_item
    other = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                       question="Review it?", allowed_decisions=["reviewed", "escalate_to_committee"])
    with pytest.raises(ValueError):
        answer_question(db, other, world["analyst"], "reviewed")


def test_endpoint_answers_remembers_and_the_ledger_has_her_name(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr", "remember": True})
    assert r.status_code == 200 and r.json()["lesson_id"]
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.decided")).scalars().one()
    assert event.actor_id == str(world["analyst"].id)
    again = client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr"})
    assert again.status_code == 422


def test_endpoint_refuses_a_role_that_cannot_decide_and_an_unknown_item(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "admin")
    assert client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr"}).status_code == 403
    import uuid
    assert client.post(f"/api/v1/work-items/{uuid.uuid4()}/answer", json={"option_id": "x"}).status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest backend/tests/squad/test_questions.py -v`
Expected: FAIL (`No module named app.squad.questions`).

- [ ] **Step 3: Implement**

```python
# backend/app/squad/questions.py
"""Squad asks: a work item whose allowed decisions are the options the agent proposes (spec 8).
Answering goes through the engine's own `decide_work_item`, so permissions, the ledger record and
the actor's name are the engine's. "Remember" additionally writes one lesson in the person's name."""
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.domain import workflow
from app.domain.lessons import record_lesson
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.work_items import raise_item

QUESTION = "question"
_SLUG = re.compile(r"^[a-z0-9_]+$")


def _check_options(options: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not 2 <= len(options) <= 6:
        raise ValueError("a question offers two to six options")
    seen: set[str] = set()
    clean = []
    for option in options:
        oid, label = str(option.get("id", "")), str(option.get("label", "")).strip()
        if not _SLUG.match(oid) or not label:
            raise ValueError("each option needs a lowercase id and a label")
        if oid in seen:
            raise ValueError(f"option {oid!r} is offered twice")
        seen.add(oid)
        clean.append({"id": oid, "label": label, "evidence": str(option.get("evidence", ""))})
    return clean


def raise_question(db: Session, *, borrower_id: uuid.UUID, title: str, question: str, options: list[dict[str, Any]],
                   evidence: dict[str, Any] | None = None, topic: str = "question", cycle_id: uuid.UUID | None = None,
                   severity: str = "medium", actor: tuple[str, str] = ("agent", "squad")) -> WorkItem:
    clean = _check_options(options)
    return raise_item(
        db, borrower_id=borrower_id, item_type=QUESTION, title=title, question=question,
        allowed_decisions=[o["id"] for o in clean], severity=severity, cycle_id=cycle_id, blocks_stage=False,
        evidence={**(evidence or {}), "options": clean, "topic": topic}, actor=actor)


def answer_question(db: Session, item: WorkItem, user: User, option_id: str, *, remember: bool = False,
                    note: str = "") -> WorkItem:
    if item.item_type != QUESTION:
        raise ValueError("this item is not a question from Squad")
    workflow.decide_work_item(db, item, user_id=user.id, user_role=user.role, decision=option_id, reason=note)
    if remember:  # reached only after the decision was accepted, so a refused answer teaches nothing
        label = next(o["label"] for o in item.evidence["options"] if o["id"] == option_id)
        text = (note.strip() or f"{user.name} chose “{label}” when asked: {item.question}")
        lesson = record_lesson(db, borrower_id=item.borrower_id, topic=item.evidence.get("topic", QUESTION),
                               text=text, written_by=user.id, work_item_id=item.id, tag=option_id)
        item.evidence = {**item.evidence, "lesson_id": str(lesson.id)}
    return item
```

Add to `backend/app/api/routes_squad.py`:

```python
from pydantic import BaseModel

from app.core.roles import SecondPersonRequired
from app.domain.monitoring import WorkItem
from app.api.routes_work import _item
from app.squad.questions import answer_question


class AnswerIn(BaseModel):
    option_id: str
    remember: bool = False
    note: str = ""


@router.post("/work-items/{item_id}/answer")
def answer(item_id: uuid.UUID, body: AnswerIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Question not found.")
    try:
        answer_question(db, item, user, body.option_id, remember=body.remember, note=body.note)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SecondPersonRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**_item(item), "lesson_id": item.evidence.get("lesson_id")}
```

Note: `item.evidence` is a JSON column; the reassignment above (new dict) is what marks it changed.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest backend/tests/squad/test_questions.py backend/tests/test_lessons.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad/questions.py backend/app/api/routes_squad.py backend/tests/squad/test_questions.py
git commit -m "feat(squad): question work items and the answer endpoint with optional remember"
```

---

### Task 4: Drafts: create, edit, send (recording only), shown in the thread

**Files:**
- Create: `backend/app/squad/drafts.py`, `backend/tests/squad/test_drafts.py`
- Modify: `backend/app/squad/threads.py` (replace the `drafts_messages` stub), `backend/app/api/routes_squad.py`

**Interfaces:**
- Consumes: `ledger.record`, `world`, `sign_in`, `build_thread`.
- Produces: ledger events `draft.created` / `draft.edited` / `draft.sent` with `entity_type="draft"`, `entity_id=<draft uuid>`, and `borrower_id` in every payload. `create_draft(db, *, borrower_id, to, subject, body, kind="message", work_item_id=None, actor=("agent","squad")) -> dict`, `edit_draft(db, draft_id, user, *, subject=None, body=None) -> dict`, `send_draft(db, draft_id, user) -> dict`, `drafts_for(db, borrower_id) -> list[dict]` (folded: `{"draft_id","borrower_id","to","subject","body","kind","work_item_id","status": "draft"|"sent","created_by","sent_by","sent_at","edited_by"}`). Thread message type `draft` carries the same fields plus `id`, `type`, `ts` (creation time). Routes: `POST /borrowers/{id}/drafts`, `PATCH`-free: `POST /drafts/{draft_id}/edit`, `POST /drafts/{draft_id}/send`, all requiring `Permission.EDIT_COMMENTARY`. `send` returns the draft with `"delivered": false` (recording only).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/squad/test_drafts.py
import uuid

import pytest
from app.core.ledger import LedgerEvent
from app.squad.drafts import create_draft, drafts_for, edit_draft, send_draft
from app.squad.threads import build_thread
from sqlalchemy import select

from .conftest import sign_in


def _draft(db, borrower):
    return create_draft(db, borrower_id=borrower.id, to="cfo@quillfeather.example", subject="October MRR",
                        body="Hi Priya, could you send the October MRR report?", kind="reminder")


def test_a_new_draft_is_unsent_and_written_by_squad(db, world):
    d = _draft(db, world["borrower"])
    assert d["status"] == "draft" and d["created_by"] == "Squad" and d["sent_by"] is None


def test_editing_changes_the_body_and_keeps_the_history_on_the_ledger(db, world):
    d = _draft(db, world["borrower"])
    edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="Hi Priya, October MRR please.")
    [now] = drafts_for(db, world["borrower"].id)
    assert now["body"] == "Hi Priya, October MRR please." and now["edited_by"] == "Priya Raman"
    actions = [e.action for e in db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft").order_by(LedgerEvent.seq)).scalars()]
    assert actions == ["draft.created", "draft.edited"]


def test_send_records_the_person_and_claims_no_delivery(db, world):
    d = _draft(db, world["borrower"])
    sent = send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    assert sent["status"] == "sent" and sent["sent_by"] == "Priya Raman"
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "draft.sent")).scalars().one()
    assert event.actor_type == "user" and event.payload["delivery"] == "recorded_only"


def test_a_sent_draft_cannot_be_edited_or_sent_again(db, world):
    d = _draft(db, world["borrower"])
    send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])
    with pytest.raises(ValueError):
        edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="late change")
    with pytest.raises(ValueError):
        send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])


def test_an_empty_body_cannot_be_sent(db, world):
    d = _draft(db, world["borrower"])
    edit_draft(db, uuid.UUID(d["draft_id"]), world["analyst"], body="   ")
    with pytest.raises(ValueError):
        send_draft(db, uuid.UUID(d["draft_id"]), world["analyst"])


def test_drafts_are_per_client_and_appear_in_the_thread(db, world):
    _draft(db, world["borrower"])
    assert drafts_for(db, world["other"].id) == []
    message = [m for m in build_thread(db, world["borrower"].id)["messages"] if m["type"] == "draft"]
    assert len(message) == 1 and message[0]["subject"] == "October MRR"


def test_unknown_draft_is_a_lookup_error(db, world):
    with pytest.raises(LookupError):
        send_draft(db, uuid.uuid4(), world["analyst"])


def test_endpoints_enforce_the_permission_and_never_deliver(db, client, world):
    d = _draft(db, world["borrower"])
    db.commit()
    sign_in(client, "helen.strand")  # an officer may not send client email
    assert client.post(f"/api/v1/drafts/{d['draft_id']}/send").status_code == 403
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/drafts/{d['draft_id']}/send")
    assert r.status_code == 200 and r.json()["delivered"] is False
    assert client.post(f"/api/v1/drafts/{d['draft_id']}/send").status_code == 422
    assert client.post(f"/api/v1/drafts/{uuid.uuid4()}/send").status_code == 404
    created = client.post(f"/api/v1/borrowers/{world['borrower'].id}/drafts",
                          json={"to": "a@b.example", "subject": "s", "body": "b"})
    assert created.status_code == 201 and created.json()["created_by"] == "Priya Raman"

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest backend/tests/squad/test_drafts.py -v`
Expected: FAIL (`No module named app.squad.drafts`).

- [ ] **Step 3: Implement**

```python
# backend/app/squad/drafts.py
"""Drafts to a client. Squad writes them; only a person sends (spec 9). A draft is a short run of
ledger events, so its history cannot be rewritten and no migration is needed. "Send" records that
a person sent it; nothing is delivered (a mail connector is a later phase)."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.domain.org import User


def _names(db: Session) -> dict[str, str]:
    return {str(u.id): u.name for u in db.execute(select(User)).scalars()}


def _who(names: dict[str, str], event: LedgerEvent) -> str:
    return "Squad" if event.actor_type == "agent" else names.get(event.actor_id, event.actor_id)


def _fold(events: list[LedgerEvent], names: dict[str, str]) -> dict[str, Any]:
    first = events[0]
    p = first.payload
    draft = {"draft_id": first.entity_id, "borrower_id": p["borrower_id"], "to": p["to"], "subject": p["subject"],
             "body": p["body"], "kind": p.get("kind", "message"), "work_item_id": p.get("work_item_id"),
             "status": "draft", "created_by": _who(names, first), "created_at": first.ts.isoformat(),
             "edited_by": None, "sent_by": None, "sent_at": None}
    for event in events[1:]:
        if event.action == "draft.edited":
            draft["subject"] = event.payload.get("subject", draft["subject"])
            draft["body"] = event.payload.get("body", draft["body"])
            draft["edited_by"] = _who(names, event)
        elif event.action == "draft.sent":
            draft.update(status="sent", sent_by=_who(names, event), sent_at=event.ts.isoformat())
    return draft


def _events(db: Session, draft_id: uuid.UUID) -> list[LedgerEvent]:
    return list(db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft",
                                                     LedgerEvent.entity_id == str(draft_id)).order_by(LedgerEvent.seq)).scalars())


def get_draft(db: Session, draft_id: uuid.UUID) -> dict[str, Any]:
    events = _events(db, draft_id)
    if not events:
        raise LookupError("draft not found")
    return _fold(events, _names(db))


def drafts_for(db: Session, borrower_id: uuid.UUID) -> list[dict[str, Any]]:
    events = db.execute(select(LedgerEvent).where(LedgerEvent.entity_type == "draft",
                                                  LedgerEvent.payload["borrower_id"].astext == str(borrower_id))
                        .order_by(LedgerEvent.seq)).scalars()
    by_draft: dict[str, list[LedgerEvent]] = {}
    for event in events:
        by_draft.setdefault(event.entity_id, []).append(event)
    names = _names(db)
    return [_fold(group, names) for group in by_draft.values()]


def create_draft(db: Session, *, borrower_id: uuid.UUID, to: str, subject: str, body: str, kind: str = "message",
                 work_item_id: uuid.UUID | None = None, actor: tuple[str, str] = ("agent", "squad")) -> dict[str, Any]:
    if not to.strip() or not subject.strip():
        raise ValueError("a draft needs a recipient and a subject")
    draft_id = uuid.uuid4()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="draft.created", entity_type="draft",
                  entity_id=draft_id, payload={"borrower_id": borrower_id, "to": to.strip(), "subject": subject.strip(),
                                               "body": body, "kind": kind, "work_item_id": work_item_id})
    db.flush()
    return get_draft(db, draft_id)


def edit_draft(db: Session, draft_id: uuid.UUID, user: User, *, subject: str | None = None,
               body: str | None = None) -> dict[str, Any]:
    current = get_draft(db, draft_id)
    if current["status"] == "sent":
        raise ValueError("this draft has been sent and cannot be changed")
    payload: dict[str, Any] = {"borrower_id": current["borrower_id"]}
    if subject is not None:
        payload["subject"] = subject.strip()
    if body is not None:
        payload["body"] = body
    ledger.record(db, actor_type="user", actor_id=user.id, action="draft.edited", entity_type="draft",
                  entity_id=draft_id, payload=payload)
    db.flush()
    return get_draft(db, draft_id)


def send_draft(db: Session, draft_id: uuid.UUID, user: User) -> dict[str, Any]:
    current = get_draft(db, draft_id)
    if current["status"] == "sent":
        raise ValueError("this draft has already been sent")
    if not current["body"].strip():
        raise ValueError("an empty message cannot be sent")
    ledger.record(db, actor_type="user", actor_id=user.id, action="draft.sent", entity_type="draft", entity_id=draft_id,
                  payload={"borrower_id": current["borrower_id"], "to": current["to"], "delivery": "recorded_only"})
    db.flush()
    return get_draft(db, draft_id)
```

In `backend/app/squad/threads.py` replace the stub:

```python
def drafts_messages(db: Session, borrower_id: uuid.UUID, names: dict[str, str]) -> list[dict[str, Any]]:
    from app.squad.drafts import drafts_for

    return [{"id": f"draft:{d['draft_id']}", "type": "draft", "ts": d["created_at"], **d}
            for d in drafts_for(db, borrower_id)]
```

Add to `backend/app/api/routes_squad.py`:

```python
from app.api.deps import require
from app.core.roles import Permission
from app.domain.credit import Borrower
from app.squad import drafts


class DraftIn(BaseModel):
    to: str
    subject: str
    body: str
    kind: str = "message"
    work_item_id: uuid.UUID | None = None


class DraftEditIn(BaseModel):
    subject: str | None = None
    body: str | None = None


def _draft_call(db: Session, fn, *args, **kwargs) -> dict:
    try:
        out = fn(db, *args, **kwargs)
    except LookupError as exc:
        raise HTTPException(404, "Draft not found.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return out


@router.post("/borrowers/{borrower_id}/drafts", status_code=201)
def new_draft(borrower_id: uuid.UUID, body: DraftIn, db: Session = Depends(get_db),
              user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return _draft_call(db, drafts.create_draft, borrower_id=borrower_id, to=body.to, subject=body.subject,
                       body=body.body, kind=body.kind, work_item_id=body.work_item_id, actor=("user", str(user.id)))


@router.post("/drafts/{draft_id}/edit")
def edit_draft_route(draft_id: uuid.UUID, body: DraftEditIn, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    return _draft_call(db, drafts.edit_draft, draft_id, user, subject=body.subject, body=body.body)


@router.post("/drafts/{draft_id}/send")
def send_draft_route(draft_id: uuid.UUID, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    return {**_draft_call(db, drafts.send_draft, draft_id, user), "delivered": False}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest backend/tests/squad -v`
Expected: PASS (Tasks 1 to 4).

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad backend/app/api/routes_squad.py backend/tests/squad/test_drafts.py
git commit -m "feat(squad): drafts as ledger events; send records the person and delivers nothing"
```

---

### Task 5: The case trail, the track record, and Squad's demo data

**Files:**
- Create: `backend/app/squad/trail.py`, `backend/app/squad/track_record.py`, `backend/app/squad_demo.py`, `backend/tests/squad/test_trail_track.py`
- Modify: `backend/app/api/routes_squad.py`

**Interfaces:**
- Consumes: `world`, `sign_in`, `add_fact` (`app.domain.facts_service.add_fact(db, borrower_id=, key=, period_end=, months=, value=, kind=, ...)`), `raise_item`.
- Produces: `case_trail(db, item) -> dict` and `GET /api/v1/cases/{work_item_id}/trail` returning `{"work_item_id", "steps": [{"n","who","role_line","text","check","run_id"}], "calculation": {"id","formula_key","inputs","outputs"} | None, "checks": [{"layer","check","action","detail"}]}`. `who` is `Intake agent`, `Spreading agent`, `Covenant agent`, `Squad`, or `Code` (calculation, no AI); `role_line` is one plain sentence on what that specialist does. `track_record(db, borrower_id) -> list[dict]` and `GET /api/v1/borrowers/{id}/track-record` returning rows `{"task","agent_name","checked","right","corrected","last_correction_at","since"}`: `checked` counts extracted facts the run produced; `corrected` counts those a person later superseded (ledger `fact.superseded`, actor type `user`); `right = checked - corrected`; nothing is a constant. `seed_squad_demo(db) -> dict` creating, idempotently, one question (for the first borrower by name), one draft reminder (for the second) and returning `{"question_borrower_code","draft_borrower_code","work_item_id","draft_id"}`; CLI `uv run python -m app.squad_demo`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/squad/test_trail_track.py
import uuid
from datetime import date
from decimal import Decimal as D

from app.core import ledger
from app.domain.agents import AgentRun
from app.domain.facts import CalcRun
from app.domain.facts_service import add_fact
from app.domain.work_items import raise_item
from app.squad.trail import case_trail
from app.squad.track_record import track_record

from .conftest import sign_in

PERIOD = date(2026, 10, 31)


def _run(db, borrower, agent="spreading", task="read_statements"):
    run = AgentRun(agent_name=agent, agent_version="1", model="m", task=task, borrower_id=borrower.id,
                   status="completed", guardrail_notes=[{"layer": "quotes", "check": "quote_on_page",
                                                         "action": "pass", "detail": "found on p. 3"}])
    db.add(run)
    db.flush()
    return run


def _calc(db, borrower):
    calc = CalcRun(borrower_id=borrower.id, formula_key="cov.min_unrestricted_cash", formula_version="1",
                   period_end=PERIOD, inputs=[{"name": "cash", "value": "4600000"}], outputs={"result": "4600000"},
                   trace={}, engine_version="1")
    db.add(calc)
    db.flush()
    return calc


def test_trail_lists_the_run_the_calculation_and_the_guardrail_checks(db, world):
    run = _run(db, world["borrower"])
    calc = _calc(db, world["borrower"])
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                      question="Review it?", allowed_decisions=["reviewed"], agent_run_id=run.id,
                      evidence={"calc_run_id": str(calc.id)})
    trail = case_trail(db, item)
    assert [s["who"] for s in trail["steps"]] == ["Spreading agent", "Code"]
    assert trail["calculation"]["formula_key"] == "cov.min_unrestricted_cash"
    assert trail["checks"][0]["check"] == "quote_on_page"


def test_a_case_with_no_run_has_an_honest_empty_trail(db, world):
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                      question="Review it?", allowed_decisions=["reviewed"])
    trail = case_trail(db, item)
    assert trail["steps"] == [] and trail["calculation"] is None and trail["checks"] == []


def _extracted(db, borrower, run, key):
    from app.domain.documents import Document
    doc = Document(borrower_id=borrower.id, title="t", file_name="f", storage_path="p", sha256="b" * 64, page_count=1)
    db.add(doc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, key=key, period_end=PERIOD, months=1, value=D("100"),
                    kind="extracted", document_id=doc.id, page=1, quote="100", agent_run_id=run.id)


def test_track_record_counts_checked_and_corrected_from_the_record(db, world):
    run = _run(db, world["borrower"])
    good = _extracted(db, world["borrower"], run, "is.total_revenue")
    bad = _extracted(db, world["borrower"], run, "bs.cash")
    ledger.record(db, actor_type="user", actor_id=world["analyst"].id, action="fact.superseded", entity_type="fact",
                  entity_id=bad.id, payload={"old_value": "100", "new_value": "90"})
    [row] = track_record(db, world["borrower"].id)
    assert (row["task"], row["checked"], row["corrected"], row["right"]) == ("read_statements", 2, 1, 1)
    assert row["last_correction_at"] is not None and good.id != bad.id


def test_track_record_is_empty_for_a_client_nothing_has_read(db, world):
    assert track_record(db, world["other"].id) == []


def test_endpoints_return_404_for_unknown_ids(db, client, world):
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/cases/{uuid.uuid4()}/trail").status_code == 404
    assert client.get(f"/api/v1/borrowers/{uuid.uuid4()}/track-record").status_code == 404
    assert client.get(f"/api/v1/borrowers/{world['borrower'].id}/track-record").json() == []


def test_squad_demo_seed_is_idempotent_and_visible_in_the_briefing(db, client, world):
    from app.squad_demo import seed_squad_demo
    first = seed_squad_demo(db)
    second = seed_squad_demo(db)
    assert first["work_item_id"] == second["work_item_id"] and first["draft_id"] == second["draft_id"]
    db.commit()
    sign_in(client, "priya.raman")
    kinds = {i["kind"] for i in client.get("/api/v1/me/briefing").json()["items"]}
    assert "question" in kinds

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest backend/tests/squad/test_trail_track.py -v`
Expected: FAIL (`No module named app.squad.trail`).

- [ ] **Step 3: Implement**

```python
# backend/app/squad/trail.py
"""The work trail under a case ("How I got here"): which specialist did what, and which checks it passed."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.agents import AgentRun
from app.domain.facts import CalcRun
from app.domain.monitoring import CovenantTest, WorkItem

ROLE_LINES = {
    "intake": "files incoming documents",
    "spreading": "reads figures from documents",
    "covenant": "tests covenants against the loan terms",
    "terms": "reads the loan agreement",
    "code": "calculation, no AI",
}


def _who(agent_name: str) -> str:
    return f"{agent_name.capitalize()} agent"


def case_trail(db: Session, item: WorkItem) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    run = db.get(AgentRun, item.agent_run_id) if item.agent_run_id else None
    if run is not None:
        steps.append({"n": len(steps) + 1, "who": _who(run.agent_name),
                      "role_line": ROLE_LINES.get(run.agent_name, "works for Squad"),
                      "text": f"Ran {run.task.replace('_', ' ')}.", "check": run.status, "run_id": str(run.id)})
        checks += [{"layer": n.get("layer"), "check": n.get("check"), "action": n.get("action"), "detail": n.get("detail")}
                   for n in (run.guardrail_notes or []) if isinstance(n, dict)]
    checks += [{"layer": n.get("layer"), "check": n.get("check"), "action": n.get("action"), "detail": n.get("detail")}
               for n in (item.guardrail_notes or []) if isinstance(n, dict)]
    calc = None
    calc_id = (item.evidence or {}).get("calc_run_id")
    if not calc_id and (item.evidence or {}).get("covenant_test_id"):
        test = db.get(CovenantTest, item.evidence["covenant_test_id"])
        calc_id = str(test.calc_run_id) if test and test.calc_run_id else None
    calc_row = db.get(CalcRun, calc_id) if calc_id else None
    if calc_row is not None:
        calc = {"id": str(calc_row.id), "formula_key": calc_row.formula_key, "inputs": calc_row.inputs,
                "outputs": calc_row.outputs}
        steps.append({"n": len(steps) + 1, "who": "Code", "role_line": ROLE_LINES["code"],
                      "text": f"Applied {calc_row.formula_key} to {len(calc_row.inputs)} stored figures.",
                      "check": "exact arithmetic", "run_id": None})
    return {"work_item_id": str(item.id), "steps": steps, "calculation": calc, "checks": checks}
```

```python
# backend/app/squad/track_record.py
"""How well each task has gone for one client, counted from the record: figures an agent read, and
how many a person later corrected. No constant, no estimate."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun
from app.domain.facts import Fact


def track_record(db: Session, borrower_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.execute(select(Fact, AgentRun).join(AgentRun, AgentRun.id == Fact.agent_run_id)
                      .where(Fact.borrower_id == borrower_id, Fact.kind == "extracted")).all()
    if not rows:
        return []
    corrections = {e.entity_id: e for e in db.execute(
        select(LedgerEvent).where(LedgerEvent.action == "fact.superseded", LedgerEvent.actor_type == "user",
                                  LedgerEvent.entity_id.in_([str(f.id) for f, _ in rows]))).scalars()}
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for fact, run in rows:
        row = out.setdefault((run.agent_name, run.task), {"task": run.task, "agent_name": run.agent_name, "checked": 0,
                                                          "corrected": 0, "last_correction_at": None,
                                                          "since": fact.created_at.isoformat()})
        row["checked"] += 1
        row["since"] = min(row["since"], fact.created_at.isoformat())
        event = corrections.get(str(fact.id))
        if event is not None:
            row["corrected"] += 1
            when = event.ts.isoformat()
            row["last_correction_at"] = max(row["last_correction_at"] or when, when)
    return [{**r, "right": r["checked"] - r["corrected"]} for r in out.values()]
```

```python
# backend/app/squad_demo.py
"""Squad's own demonstration data for the end-to-end journeys: one question and one draft reminder.
Run after the book is seeded: `uv run python -m app.squad_demo`. Idempotent. A separate file so the
seeded book (seed_book.py, changed by other phases) stays untouched."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_engine
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.squad import drafts
from app.squad.questions import raise_question

DEMO_KEY = "squad_demo:line_mapping"
OPTIONS = [
    {"id": "map_to_arr", "label": "Map it to ARR", "evidence": "The statement labels the line annual recurring revenue."},
    {"id": "map_to_mrr", "label": "Map it to MRR", "evidence": "The same page also shows a monthly column."},
]


def seed_squad_demo(db: Session) -> dict:
    names = db.execute(select(Borrower).order_by(Borrower.name)).scalars().all()
    if len(names) < 2:
        raise RuntimeError("seed the book first: Squad's demonstration needs two clients")
    asked, reminded = names[0], names[1]
    item = raise_question(db, borrower_id=asked.id, title="How should I map this line?",
                          question="Is 'Recurring revenue' on page 3 ARR or MRR?", options=OPTIONS,
                          topic="line_mapping", evidence={"dedupe_key": DEMO_KEY})
    existing = db.execute(select(WorkItem).where(WorkItem.borrower_id == asked.id, WorkItem.item_type == "question",
                                                 WorkItem.evidence["dedupe_key"].astext == DEMO_KEY)).scalars().first()
    item = existing or item
    found = [d for d in drafts.drafts_for(db, reminded.id) if d["kind"] == "demo_reminder"]
    draft = found[0] if found else drafts.create_draft(
        db, borrower_id=reminded.id, to="finance@client.example", subject="October MRR report",
        body="Hi,\n\nThanks for the October package. Could you send the October MRR report when you have a moment?\n\nThanks",
        kind="demo_reminder")
    db.commit()
    return {"question_borrower_code": asked.code, "draft_borrower_code": reminded.code,
            "work_item_id": str(item.id), "draft_id": draft["draft_id"]}


if __name__ == "__main__":
    with Session(get_engine()) as session:
        print(json.dumps(seed_squad_demo(session)))
```

The CLI opens a session on `get_engine()` as `app/cli.py` does. `raise_item` only honours `dedupe_key` through its own argument; the explicit lookup above makes the seed idempotent regardless.

Add to `backend/app/api/routes_squad.py`:

```python
from app.domain.monitoring import WorkItem  # already imported in Task 3
from app.squad.track_record import track_record
from app.squad.trail import case_trail


@router.get("/cases/{work_item_id}/trail")
def trail(work_item_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    item = db.get(WorkItem, work_item_id)
    if item is None:
        raise HTTPException(404, "Case not found.")
    return case_trail(db, item)


@router.get("/borrowers/{borrower_id}/track-record")
def borrower_track_record(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return track_record(db, borrower_id)
```

- [ ] **Step 4: Run the tests to verify they pass, then the whole backend suite**

Run: `uv run pytest backend/tests/squad -v && uv run pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad backend/app/squad_demo.py backend/app/api/routes_squad.py backend/tests/squad/test_trail_track.py
git commit -m "feat(squad): case trail, track record read model, demonstration data"
```

---

### Task 6: Looks: five palettes, role default, switcher, contrast test

**Files:**
- Create: `frontend/src/squad/looks.ts`, `frontend/src/squad/useLook.tsx`, `frontend/src/squad/LookMenu.tsx`, `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/looks.test.tsx`
- Modify: `frontend/src/styles.css` (add `@import './squad/squad.css';` after the existing imports)

**Interfaces:**
- Produces: `LOOKS: Record<LookId, Look>`, `LOOK_IDS: LookId[]`, `contrast(a: string, b: string): number`, `defaultLookFor(role: string): LookId`, `applyLook(id: LookId, root?: HTMLElement): void` (sets `data-look` and every `--sq-*` variable), `LookProvider({ children })`, `useLook(): { look: LookId; setLook(id: LookId): void }`, `LookMenu`. Tokens in each look: `ground, surface, sunk, line, ink, ink2, ink3, onInk, squad, squadSoft, squadLine, ok, warn, bad, ember, paper, paperInk`. Choice stored in `localStorage["squad.look.<userId>"]`, every access in try/catch.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/looks.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext, type AuthValue } from '@/auth/context';
import { LookMenu } from '../LookMenu';
import { applyLook, contrast, defaultLookFor, LOOK_IDS, LOOKS } from '../looks';
import { LookProvider, useLook } from '../useLook';

const TEXT = ['ink', 'ink2', 'ink3', 'squad', 'ok', 'warn', 'bad'] as const;
const SURFACES = ['ground', 'surface', 'sunk'] as const;

describe('looks', () => {
  it('has the five looks of the spec', () => {
    expect(LOOK_IDS).toEqual(['night', 'warm', 'cool', 'lavender', 'sage']);
  });

  it.each(LOOK_IDS.flatMap((id) => TEXT.flatMap((t) => SURFACES.map((s) => [id, t, s] as const))))(
    '%s: %s on %s is at least 4.5:1',
    (id, t, s) => {
      expect(contrast(LOOKS[id].vars[t], LOOKS[id].vars[s])).toBeGreaterThanOrEqual(4.5);
    },
  );

  it.each(LOOK_IDS)('%s: the ink button text and the needs-you ember hold their contrast', (id) => {
    const v = LOOKS[id].vars;
    expect(contrast(v.onInk, v.ink)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(v.ember, v.ground)).toBeGreaterThanOrEqual(3);
    expect(contrast(v.onEmber, v.ember)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(LOOK_IDS)('%s: evidence paper is the same white-ish paper in every look', (id) => {
    expect(LOOKS[id].vars.paper).toBe('#fbfaf6');
    expect(contrast(LOOKS[id].vars.paperInk, LOOKS[id].vars.paper)).toBeGreaterThanOrEqual(7);
  });

  it('defaults to Warm paper for credit officers and Night for everyone else', () => {
    expect(defaultLookFor('credit_officer')).toBe('warm');
    for (const role of ['analyst', 'portfolio_manager', 'credit_admin', 'credit_review', 'admin']) expect(defaultLookFor(role)).toBe('night');
  });

  it('applyLook sets the attribute and the variables', () => {
    applyLook('lavender');
    expect(document.documentElement.dataset.look).toBe('lavender');
    expect(document.documentElement.style.getPropertyValue('--sq-ground')).toBe(LOOKS.lavender.vars.ground);
  });
});

const user = (role: string, id = 'u-1'): ApiUser => ({ id, email: 'x@y', name: 'X', title: '', role, permissions: [] });
const auth = (u: ApiUser): AuthValue => ({ user: u, status: 'signed-in', can: () => true, signIn: async () => u, signOut: async () => {}, retry: () => {} });

function Probe() {
  const { look } = useLook();
  return <span data-testid="look">{look}</span>;
}

describe('LookProvider', () => {
  beforeEach(() => localStorage.clear());

  it('starts from the role default and remembers a switch per person', async () => {
    const view = render(
      <AuthContext.Provider value={auth(user('credit_officer'))}>
        <LookProvider>
          <Probe />
          <LookMenu />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('warm');
    await userEvent.click(screen.getByRole('button', { name: /look/i }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: /sage/i }));
    expect(screen.getByTestId('look')).toHaveTextContent('sage');
    expect(localStorage.getItem('squad.look.u-1')).toBe('sage');
    view.unmount();
    render(
      <AuthContext.Provider value={auth(user('credit_officer'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('sage');
  });

  it('still works when storage throws', () => {
    const spy = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error('blocked');
    };
    render(
      <AuthContext.Provider value={auth(user('analyst'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('night');
    Storage.prototype.getItem = spy;
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `frontend/`): `pnpm vitest run src/squad/__tests__/looks.test.tsx`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement**

```ts
// frontend/src/squad/looks.ts
/** The five looks. Source of truth for colour in the Squad experience; applied as --sq-* variables. */
export type LookId = 'night' | 'warm' | 'cool' | 'lavender' | 'sage';
export type TokenName =
  | 'ground' | 'surface' | 'sunk' | 'line' | 'ink' | 'ink2' | 'ink3' | 'onInk' | 'onEmber'
  | 'squad' | 'squadSoft' | 'squadLine' | 'ok' | 'warn' | 'bad' | 'ember' | 'paper' | 'paperInk';
export interface Look {
  id: LookId;
  label: string;
  dark: boolean;
  swatch: [string, string];
  vars: Record<TokenName, string>;
}

const LIGHT = { onInk: '#ffffff', onEmber: '#ffffff', squad: '#3d2a9e', squadSoft: '#f2efff', squadLine: '#ddd5ff', ok: '#1c6e42', warn: '#8f5a00', bad: '#a8261c', ember: '#c4421a', paper: '#fbfaf6', paperInk: '#2b2925' };

export const LOOKS: Record<LookId, Look> = {
  night: {
    id: 'night', label: 'Night', dark: true, swatch: ['#141318', '#8f7bf0'],
    vars: { ground: '#141318', surface: '#1d1c22', sunk: '#25242b', line: '#2f2e36', ink: '#f1eff5', ink2: '#bbb7c6', ink3: '#9a96a6', onInk: '#141318', onEmber: '#1c0c05',
      squad: '#cbbfff', squadSoft: '#262140', squadLine: '#3d3561', ok: '#7fd3a0', warn: '#f0c06a', bad: '#ff9b8f', ember: '#f2643a', paper: '#fbfaf6', paperInk: '#2b2925' },
  },
  warm: {
    id: 'warm', label: 'Warm paper', dark: false, swatch: ['#f5f3ee', '#2f2d28'],
    vars: { ...LIGHT, ground: '#f5f3ee', surface: '#ffffff', sunk: '#efebe3', line: '#e3ded3', ink: '#161513', ink2: '#4f4a42', ink3: '#6f695f' },
  },
  cool: {
    id: 'cool', label: 'Cool slate', dark: false, swatch: ['#f1f3f6', '#33557a'],
    vars: { ...LIGHT, ground: '#f1f3f6', surface: '#ffffff', sunk: '#e7ebf0', line: '#dce1e8', ink: '#13161b', ink2: '#49505b', ink3: '#5d6776' },
  },
  lavender: {
    id: 'lavender', label: 'Lavender mist', dark: false, swatch: ['#f4f2fb', '#4a35b8'],
    vars: { ...LIGHT, ground: '#f4f2fb', surface: '#ffffff', sunk: '#ebe7f7', line: '#e0dbf0', ink: '#1a1726', ink2: '#4d4862', ink3: '#625c79' },
  },
  sage: {
    id: 'sage', label: 'Sage', dark: false, swatch: ['#f0f3ee', '#3f6b4a'],
    vars: { ...LIGHT, ground: '#f0f3ee', surface: '#ffffff', sunk: '#e5eae1', line: '#d9e0d4', ink: '#151a14', ink2: '#4a5347', ink3: '#5c6656' },
  },
};

export const LOOK_IDS = Object.keys(LOOKS) as LookId[];

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * (channels[0] ?? 0) + 0.7152 * (channels[1] ?? 0) + 0.0722 * (channels[2] ?? 0);
}

/** WCAG contrast ratio of two six-digit hex colours. */
export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Owner decision 3: Warm paper for credit officers, Night for everyone else. */
export function defaultLookFor(role: string): LookId {
  return role === 'credit_officer' ? 'warm' : 'night';
}

const cssName = (token: string) => `--sq-${token.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;

export function applyLook(id: LookId, root: HTMLElement = document.documentElement): void {
  root.dataset.look = id;
  root.style.colorScheme = LOOKS[id].dark ? 'dark' : 'light';
  for (const [token, value] of Object.entries(LOOKS[id].vars)) root.style.setProperty(cssName(token), value);
}
```

```tsx
// frontend/src/squad/useLook.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from '@/auth/context';
import { applyLook, defaultLookFor, LOOK_IDS, type LookId } from './looks';

interface LookValue {
  look: LookId;
  setLook: (id: LookId) => void;
}
const LookContext = createContext<LookValue>({ look: 'night', setLook: () => {} });
export const useLook = () => useContext(LookContext);

const storageKey = (userId: string) => `squad.look.${userId}`;

function remembered(userId: string | undefined): LookId | null {
  if (!userId) return null;
  try {
    const value = localStorage.getItem(storageKey(userId));
    return LOOK_IDS.includes(value as LookId) ? (value as LookId) : null;
  } catch {
    return null;
  }
}

export function LookProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const initial = remembered(user?.id) ?? defaultLookFor(user?.role ?? '');
  const [look, setLookState] = useState<LookId>(initial);
  useEffect(() => applyLook(look), [look]);
  const setLook = useCallback(
    (id: LookId) => {
      setLookState(id);
      try {
        if (user) localStorage.setItem(storageKey(user.id), id);
      } catch {
        /* a blocked store only means the choice is not remembered */
      }
    },
    [user],
  );
  const value = useMemo(() => ({ look, setLook }), [look, setLook]);
  return <LookContext.Provider value={value}>{children}</LookContext.Provider>;
}
```

```tsx
// frontend/src/squad/LookMenu.tsx
import { Palette } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import { LOOK_IDS, LOOKS } from './looks';
import { useLook } from './useLook';

export function LookMenu() {
  const { look, setLook } = useLook();
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="sq-iconbtn" aria-label={`Look: ${LOOKS[look].label}`}>
        <Palette size={16} aria-hidden />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="sq-menu" align="end" sideOffset={6}>
          <DropdownMenu.RadioGroup value={look} onValueChange={(v) => setLook(v as (typeof LOOK_IDS)[number])}>
            {LOOK_IDS.map((id) => (
              <DropdownMenu.RadioItem key={id} value={id} className="sq-menuitem">
                <span className="sq-swatch" style={{ background: `linear-gradient(135deg, ${LOOKS[id].swatch[0]} 50%, ${LOOKS[id].swatch[1]} 50%)` }} aria-hidden />
                {LOOKS[id].label}
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
```

```css
/* frontend/src/squad/squad.css — the Squad experience's own classes, built only from --sq-* variables. */
.sq-root { background: var(--sq-ground); color: var(--sq-ink); font-family: 'Inter Variable', system-ui, sans-serif; font-size: 15px; line-height: 1.5; }
.sq-root * { box-sizing: border-box; }
.sq-iconbtn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--sq-line); background: var(--sq-surface); color: var(--sq-ink2); cursor: pointer; }
.sq-iconbtn:hover { color: var(--sq-ink); }
.sq-iconbtn:focus-visible, .sq-btn:focus-visible, .sq-navlink:focus-visible { outline: 2px solid var(--sq-squad); outline-offset: 2px; }
.sq-menu { background: var(--sq-surface); border: 1px solid var(--sq-line); border-radius: 10px; padding: 4px; min-width: 190px; color: var(--sq-ink); z-index: 60; }
.sq-menuitem { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px; cursor: pointer; outline: none; }
.sq-menuitem[data-highlighted] { background: var(--sq-sunk); }
.sq-menuitem[data-state='checked'] { font-weight: 600; }
.sq-swatch { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--sq-line); }
.sq-btn { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border-radius: 9px; border: 1px solid var(--sq-line); background: var(--sq-surface); color: var(--sq-ink); font: inherit; font-weight: 500; cursor: pointer; }
.sq-btn[disabled] { opacity: 0.55; cursor: not-allowed; }
.sq-btn-primary { background: var(--sq-ink); color: var(--sq-on-ink); border-color: var(--sq-ink); }
.sq-card { background: var(--sq-surface); border: 1px solid var(--sq-line); border-radius: 14px; padding: 14px 16px; }
.sq-squad { background: var(--sq-squad-soft); border: 1px solid var(--sq-squad-line); }
.sq-muted { color: var(--sq-ink2); }
.sq-faint { color: var(--sq-ink3); }
.sq-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.sq-paper { background: var(--sq-paper); color: var(--sq-paper-ink); }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad/__tests__/looks.test.tsx && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad frontend/src/styles.css
git commit -m "feat(squad-ui): five looks, role defaults, switcher and a contrast test for every text pair"
```

---

### Task 7: The Squad mark and the presence line

**Files:**
- Create: `frontend/src/squad/mark/SquadMark.tsx`, `frontend/src/squad/presence/Presence.tsx`
- Modify: `frontend/src/squad/squad.css` (append the mark and presence rules)
- Test: `frontend/src/squad/__tests__/presence.test.tsx`

**Interfaces:**
- Produces: `type MarkState = 'rest' | 'working' | 'needs' | 'responding'`; `SquadMark({ size?: number; state?: MarkState; label?: string })` (decorative and `aria-hidden` unless `label` is given); `PresenceProvider({ needs: number; children })`; `usePresence(): { state: MarkState; say(text: string, ms?: number): void; beginWork(): () => void; pulse(): void }`; `PresenceLine()` (the mark at 42 px, the words "Credit Squad", a visually hidden state sentence, and one reserved `role="status"` line that is always in the DOM so nothing shifts when a confirmation appears). State priority: working, then responding, then needs (when `needs > 0`), then rest.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/presence.test.tsx
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import css from '../squad.css?raw';
import { SquadMark } from '../mark/SquadMark';
import { PresenceLine, PresenceProvider, usePresence } from '../presence/Presence';

describe('SquadMark', () => {
  it('draws four dots around one core in every state', () => {
    for (const state of ['rest', 'working', 'needs', 'responding'] as const) {
      const { container, unmount } = render(<SquadMark state={state} />);
      expect(container.querySelectorAll('circle.sq-dot')).toHaveLength(4);
      expect(container.querySelectorAll('circle.sq-core')).toHaveLength(1);
      expect(container.querySelector('svg')).toHaveAttribute('data-state', state);
      unmount();
    }
  });

  it('shows the ember ring only when the squad needs you', () => {
    const needs = render(<SquadMark state="needs" />);
    expect(needs.container.querySelector('circle.sq-core')).toHaveAttribute('stroke', 'var(--sq-ember)');
    needs.unmount();
    const rest = render(<SquadMark state="rest" />);
    expect(rest.container.querySelector('circle.sq-core')).not.toHaveAttribute('stroke');
  });

  it('is hidden from assistive tech unless it has a label', () => {
    const { container, rerender } = render(<SquadMark />);
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    rerender(<SquadMark label="Credit Squad" />);
    expect(screen.getByRole('img', { name: 'Credit Squad' })).toBeInTheDocument();
  });

  it('turns every movement off under reduced motion', () => {
    const block = css.slice(css.indexOf('@media (prefers-reduced-motion: reduce)'));
    for (const selector of ['.sq-orbit', '.sq-core-breathe', '.sq-ripple']) expect(block).toContain(selector);
    expect(block).toMatch(/animation:\s*none/);
  });
});

function Controls() {
  const p = usePresence();
  return (
    <>
      <button onClick={() => p.say('Recorded as Priya')}>say</button>
      <button
        onClick={() => {
          const end = p.beginWork();
          (window as unknown as { end: () => void }).end = end;
        }}
      >
        work
      </button>
      <button onClick={() => p.pulse()}>pulse</button>
    </>
  );
}
const mount = (needs = 0) =>
  render(
    <PresenceProvider needs={needs}>
      <PresenceLine />
      <Controls />
    </PresenceProvider>,
  );
const mark = () => document.querySelector('svg[data-state]') as SVGElement;

describe('presence line', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('always has a reserved status line, empty until Squad says something', () => {
    mount();
    expect(screen.getByRole('status')).toHaveTextContent('');
    act(() => screen.getByText('say').click());
    expect(screen.getByRole('status')).toHaveTextContent('Recorded as Priya');
    act(() => void vi.advanceTimersByTime(6100));
    expect(screen.getByRole('status')).toHaveTextContent('');
  });

  it('names the product "Credit Squad" and says its state in words', () => {
    mount(2);
    expect(screen.getByText('Credit Squad')).toBeInTheDocument();
    expect(screen.getByText(/needs you/i)).toBeInTheDocument();
    expect(mark()).toHaveAttribute('data-state', 'needs');
  });

  it('is working while work is under way and returns to needs-you afterwards', () => {
    mount(1);
    act(() => screen.getByText('work').click());
    expect(mark()).toHaveAttribute('data-state', 'working');
    act(() => (window as unknown as { end: () => void }).end());
    expect(mark()).toHaveAttribute('data-state', 'needs');
  });

  it('responds briefly and then settles', () => {
    mount(0);
    act(() => screen.getByText('pulse').click());
    expect(mark()).toHaveAttribute('data-state', 'responding');
    act(() => void vi.advanceTimersByTime(1000));
    expect(mark()).toHaveAttribute('data-state', 'rest');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/presence.test.tsx`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/mark/SquadMark.tsx
export type MarkState = 'rest' | 'working' | 'needs' | 'responding';

const DOTS: Array<[number, number]> = [[50, 18], [82, 50], [50, 82], [18, 50]];

/**
 * Four specialist dots around one core (lavender: dots #8F7BF0, core #4A35B8), the same at every size.
 * Needs you adds an ember ring round the core, never a separate shape. Decorative: the words beside it carry the meaning.
 */
export function SquadMark({ size = 28, state = 'rest', label }: { size?: number; state?: MarkState; label?: string }) {
  const working = state === 'working';
  const needs = state === 'needs';
  const a11y = label ? ({ role: 'img', 'aria-label': label } as const) : ({ 'aria-hidden': true } as const);
  return (
    <svg className={`sq-mk sq-mk-${state}`} width={size} height={size} viewBox="0 0 100 100" data-state={state} {...a11y}>
      {state === 'responding' ? <circle className="sq-ripple" cx="50" cy="50" r="30" fill="none" stroke="#8f7bf0" strokeWidth="3" /> : null}
      <g className={working ? 'sq-orbit' : undefined} fill="#8f7bf0">
        {DOTS.map(([x, y], i) => (
          <circle key={i} className="sq-dot" cx={x} cy={y} r={working && i % 2 ? 8 : 11} opacity={working && i % 2 ? 0.7 : 1} />
        ))}
      </g>
      <circle
        className={working ? 'sq-core sq-core-breathe' : 'sq-core'}
        cx="50"
        cy="50"
        r={needs ? 15 : 17}
        fill="#4a35b8"
        {...(needs ? { stroke: 'var(--sq-ember)', strokeWidth: size < 24 ? 7 : 5.5 } : {})}
      />
    </svg>
  );
}
```

```tsx
// frontend/src/squad/presence/Presence.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { SquadMark, type MarkState } from '../mark/SquadMark';

interface PresenceApi {
  state: MarkState;
  said: string;
  say: (text: string, ms?: number) => void;
  beginWork: () => () => void;
  pulse: () => void;
}
const PresenceContext = createContext<PresenceApi>({ state: 'rest', said: '', say: () => {}, beginWork: () => () => {}, pulse: () => {} });
export const usePresence = () => useContext(PresenceContext);

const SAY_MS = 6000;
const PULSE_MS = 900;

export function PresenceProvider({ needs, children }: { needs: number; children: ReactNode }) {
  const [busy, setBusy] = useState(0);
  const [responding, setResponding] = useState(false);
  const [said, setSaid] = useState('');
  const sayTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const pulseTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => {
    clearTimeout(sayTimer.current);
    clearTimeout(pulseTimer.current);
  }, []);

  const say = useCallback((text: string, ms = SAY_MS) => {
    clearTimeout(sayTimer.current);
    setSaid(text);
    sayTimer.current = setTimeout(() => setSaid(''), ms);
  }, []);
  const beginWork = useCallback(() => {
    setBusy((n) => n + 1);
    let ended = false;
    return () => {
      if (!ended) {
        ended = true;
        setBusy((n) => Math.max(0, n - 1));
      }
    };
  }, []);
  const pulse = useCallback(() => {
    clearTimeout(pulseTimer.current);
    setResponding(true);
    pulseTimer.current = setTimeout(() => setResponding(false), PULSE_MS);
  }, []);

  const state: MarkState = busy > 0 ? 'working' : responding ? 'responding' : needs > 0 ? 'needs' : 'rest';
  const value = useMemo(() => ({ state, said, say, beginWork, pulse }), [state, said, say, beginWork, pulse]);
  return <PresenceContext.Provider value={value}>{children}</PresenceContext.Provider>;
}

const WORDS: Record<MarkState, string> = { rest: 'watching your clients', working: 'working', needs: 'needs you', responding: 'answering' };

/** Centred above the conversation. The status line is reserved, so a confirmation never moves or covers content. */
export function PresenceLine() {
  const { state, said } = usePresence();
  return (
    <div className="sq-presence">
      <div className="sq-presence-id" title={`Credit Squad · ${WORDS[state]}`}>
        <SquadMark size={42} state={state} />
        <b>Credit Squad</b>
        <span className="sq-sr">: {WORDS[state]}</span>
        {state === 'needs' ? <span className="sq-faint" aria-hidden>needs you</span> : null}
      </div>
      <div className="sq-say" role="status" aria-live="polite">
        {said}
      </div>
    </div>
  );
}
```

Append to `frontend/src/squad/squad.css`:

```css
.sq-presence { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 14px 0 6px; }
.sq-presence-id { display: inline-flex; align-items: center; gap: 10px; font-weight: 600; color: var(--sq-squad); }
.sq-say { min-height: 24px; font-size: 13px; color: var(--sq-ink2); }
@keyframes sq-spin { to { transform: rotate(360deg); } }
@keyframes sq-breathe { 50% { transform: scale(0.86); } }
@keyframes sq-ripple { from { opacity: 0.5; transform: scale(0.7); } to { opacity: 0; transform: scale(1.5); } }
.sq-mk { flex-shrink: 0; display: block; }
.sq-orbit { transform-box: view-box; transform-origin: 50% 50%; animation: sq-spin 9s linear infinite; }
.sq-core-breathe { transform-box: fill-box; transform-origin: center; animation: sq-breathe 2.4s ease-in-out infinite; }
.sq-ripple { transform-box: fill-box; transform-origin: center; animation: sq-ripple 0.9s ease-out; }
.sq-mk-responding .sq-dot { transform-box: view-box; transform-origin: 50% 50%; }
@media (prefers-reduced-motion: reduce) {
  .sq-orbit, .sq-core-breathe, .sq-ripple { animation: none; }
}
```

(The reduced-motion block must be the last `@media (prefers-reduced-motion` in the file the test slices from; later tasks append their own selectors inside this one block rather than adding a second block.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad
git commit -m "feat(squad-ui): the Squad mark with four states and the presence line"
```

---

### Task 8: The shell: collapsible nav, palette commands, routes

**Files:**
- Create: `frontend/src/squad/shell/SquadShell.tsx`, `frontend/src/squad/shell/SquadNav.tsx`, `frontend/src/squad/shell/commands.ts`, `frontend/src/squad/links.ts`, `frontend/src/squad/api/types.ts`, `frontend/src/squad/api/hooks.ts` (briefing and thread hooks only; Task 9 adds polling and mutations)
- Modify: `frontend/src/router.tsx`
- Test: `frontend/src/squad/__tests__/shell.test.tsx`

**Interfaces:**
- Consumes: `LookProvider`, `LookMenu`, `PresenceProvider`, `PresenceLine`, `SquadMark`; `useAuth`; `CommandPalette`, `useCommandPaletteShortcut` and `Command` from `@/design`; `Link`, `Outlet` from TanStack Router.
- Produces: `Briefing`, `BriefingItem`, `Thread`, `ThreadMessage` types (below); `useBriefing()`; `SquadNav({ collapsed, onToggle, needs, openClients, pathname, userName, role, onSignOut })`; `buildCommands({ clients, go, setLook, role }): Command[]`; `SquadShell()`; `links.ts`: `clientFile(code: string, view?: 'documents' | 'covenants' | 'spreads' | 'timeline'): string` (returns the interim cockpit path `/borrowers/${code}` + view in 4a; Phase 4b retargets), `threadHref(code: string, caseId?: string): { to: '/clients/$code'; params: { code: string }; search: { case?: string } }`. Routes: `/` is Squad home (placeholder component until Task 10: `() => <h1>Squad</h1>`), `/clients/$code` with `validateSearch` for `case`, the sign-in redirect target becomes `/`, `Root` renders `SquadShell` instead of `AppShell`.

Types (`frontend/src/squad/api/types.ts`):

```ts
export interface BriefingItem {
  key: string;
  kind: 'breach' | 'overdue_report' | 'signal' | 'question' | 'review' | 'funding' | 'decided';
  borrower_id: string;
  borrower_code: string;
  borrower_name: string;
  title: string;
  state: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  needs_you: boolean;
  work_item_id: string | null;
}
export interface Briefing {
  as_of: string;
  needs_you: number;
  items: BriefingItem[];
  overnight: Array<{ agent_name: string; text: string; borrower_id: string; borrower_code: string; borrower_name: string; finished_at: string }>;
  open_clients: Array<{ borrower_id: string; code: string; name: string; open: number }>;
}
export interface AskOption { id: string; label: string; evidence: string }
interface MessageBase { id: string; ts: string }
export type ThreadMessage = MessageBase &
  (
    | { type: 'report'; agent_name: string; task: string; text: string; run_id: string }
    | { type: 'case'; work_item_id: string; item_type: string; title: string; question: string; severity: string; status: string; allowed_decisions: string[] }
    | { type: 'ask'; work_item_id: string; title: string; question: string; options: AskOption[]; status: string; choice: string | null; chosen_by: string | null }
    | { type: 'document'; document_id: string; title: string; doc_type: string | null; pages: number; period_end: string | null }
    | { type: 'held'; document_id: string; title: string; reason: string }
    | { type: 'draft'; draft_id: string; to: string; subject: string; body: string; kind: string; status: 'draft' | 'sent'; created_by: string; edited_by: string | null; sent_by: string | null; sent_at: string | null; work_item_id: string | null }
    | { type: 'decision'; work_item_id: string; decision: string | null; reason: string; by: string; by_id: string }
    | { type: 'handoff'; work_item_id: string; assigned_to: string | null; assigned_to_id: string | null; by: string }
    | { type: 'qa'; question: string; answer: string; fact_ids: string[]; citations: Array<{ document_id: string; page: number }>; status: string; run_id: string; asked_by: string }
  );
export interface Thread {
  borrower: { id: string; code: string; name: string; template_id: string };
  head_seq: number;
  messages: ThreadMessage[];
}
export interface TrailStep { n: number; who: string; role_line: string; text: string; check: string; run_id: string | null }
export interface Trail {
  work_item_id: string;
  steps: TrailStep[];
  calculation: { id: string; formula_key: string; inputs: unknown[]; outputs: Record<string, unknown> } | null;
  checks: Array<{ layer: string | null; check: string | null; action: string | null; detail: string | null }>;
}
```

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/shell.test.tsx
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { buildCommands } from '../shell/commands';
import { clientFile, threadHref } from '../links';
import { SquadNav } from '../shell/SquadNav';

const clients = [{ code: 'QFL', name: 'Quillfeather Labs, Inc.' }, { code: 'ZZZ', name: 'Zephyr Zinc Works, Inc.' }];

function mountNav(props: Partial<Parameters<typeof SquadNav>[0]> = {}) {
  const root = createRootRoute({
    component: () => (
      <SquadNav collapsed={false} onToggle={() => {}} needs={2} openClients={[{ borrower_id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', open: 2 }]}
        pathname="/" userName="Priya Raman" role="analyst" onSignOut={() => {}} {...props} />
    ),
  });
  const routes = ['/', '/portfolio', '/clients/$code', '/governance', '/agent-activity'].map((path) => createRoute({ getParentRoute: () => root, path, component: () => null }));
  const router = createRouter({ routeTree: root.addChildren(routes), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(<RouterProvider router={router} />);
}

describe('SquadNav', () => {
  it('has the Squad row with its needs-you count, My Portfolio, and only clients with something open', async () => {
    mountNav();
    const home = await screen.findByRole('link', { name: /squad.*2 need you/i });
    expect(home).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /my portfolio/i })).toHaveAttribute('href', '/portfolio');
    const cases = screen.getByRole('navigation', { name: /open cases/i });
    expect(within(cases).getAllByRole('link')).toHaveLength(1);
    expect(within(cases).getByRole('link', { name: /quillfeather/i })).toHaveAttribute('href', '/clients/QFL');
  });

  it('shows no needs-you count when nothing needs her, and no Open cases list when nothing is open', async () => {
    mountNav({ needs: 0, openClients: [] });
    expect(await screen.findByRole('link', { name: /^squad$/i })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /open cases/i })).not.toBeInTheDocument();
  });

  it('collapses and expands from one button that says which', async () => {
    const onToggle = vi.fn();
    mountNav({ collapsed: true, onToggle });
    const toggle = await screen.findByRole('button', { name: /expand navigation/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(onToggle).toHaveBeenCalled();
  });

  it('lists oversight only for the roles that have it', async () => {
    const { unmount } = mountNav({ role: 'analyst' });
    await screen.findByRole('link', { name: /my portfolio/i });
    expect(screen.queryByRole('link', { name: /oversight|agent activity/i })).not.toBeInTheDocument();
    unmount();
    mountNav({ role: 'admin' });
    expect(await screen.findByRole('link', { name: /agent activity/i })).toBeInTheDocument();
  });
});

describe('palette commands', () => {
  const run = vi.fn();
  beforeEach(() => run.mockClear());

  it('offers navigation, every client by name (search only), and the five looks', () => {
    const commands = buildCommands({ clients, go: run, setLook: run, role: 'analyst' });
    expect(commands.filter((c) => c.group === 'Look')).toHaveLength(5);
    const client = commands.find((c) => c.label === 'Quillfeather Labs, Inc.')!;
    expect(client.searchOnly).toBe(true);
    client.run();
    expect(run).toHaveBeenCalledWith('/clients/QFL');
    expect(commands.find((c) => c.label === 'My Portfolio')).toBeTruthy();
    expect(commands.find((c) => c.label === 'Squad')).toBeTruthy();
  });

  it('hides oversight commands from roles without it', () => {
    expect(buildCommands({ clients, go: run, setLook: run, role: 'analyst' }).some((c) => c.group === 'Oversight')).toBe(false);
    expect(buildCommands({ clients, go: run, setLook: run, role: 'credit_review' }).some((c) => c.group === 'Oversight')).toBe(true);
  });
});

describe('links', () => {
  it('addresses a thread and a case in one place', () => {
    expect(threadHref('QFL', 'abc')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: { case: 'abc' } });
    expect(threadHref('QFL')).toEqual({ to: '/clients/$code', params: { code: 'QFL' }, search: {} });
    expect(clientFile('QFL', 'covenants')).toBe('/borrowers/QFL/covenants');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/shell.test.tsx`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement**

```ts
// frontend/src/squad/links.ts
/** Where "Open in client file" and a thread go. One place, so Phase 4b retargets the client file in one edit. */
export type ClientFileView = 'documents' | 'covenants' | 'spreads' | 'timeline';

export function clientFile(code: string, view?: ClientFileView): string {
  return view ? `/borrowers/${code}/${view}` : `/borrowers/${code}`;
}

export function threadHref(code: string, caseId?: string) {
  return { to: '/clients/$code' as const, params: { code }, search: caseId ? { case: caseId } : {} };
}
```

```ts
// frontend/src/squad/shell/commands.ts
import type { Command } from '@/design';
import { LOOK_IDS, LOOKS, type LookId } from '../looks';

export const OVERSIGHT_ROLES = ['admin', 'credit_review', 'credit_admin'];

export interface CommandInput {
  clients: Array<{ code: string; name: string }>;
  go: (path: string) => void;
  setLook: (id: LookId) => void;
  role: string;
}

export function buildCommands({ clients, go, setLook, role }: CommandInput): Command[] {
  const commands: Command[] = [
    { id: 'go-squad', group: 'Go to', label: 'Squad', hint: 'The briefing', run: () => go('/') },
    { id: 'go-portfolio', group: 'Go to', label: 'My Portfolio', hint: 'All clients with trend', run: () => go('/portfolio') },
  ];
  if (OVERSIGHT_ROLES.includes(role)) {
    commands.push(
      { id: 'go-activity', group: 'Oversight', label: 'Agent activity', run: () => go('/agent-activity') },
      { id: 'go-governance', group: 'Oversight', label: 'Governance and the ledger', run: () => go('/governance') },
    );
  }
  for (const c of clients) commands.push({ id: `client-${c.code}`, group: 'Clients', label: c.name, hint: c.code, searchOnly: true, run: () => go(`/clients/${c.code}`) });
  for (const id of LOOK_IDS) commands.push({ id: `look-${id}`, group: 'Look', label: LOOKS[id].label, hint: 'Change the look', keywords: 'theme colour', run: () => setLook(id) });
  return commands;
}
```

```tsx
// frontend/src/squad/shell/SquadNav.tsx
import { Link } from '@tanstack/react-router';
import { ChevronsLeft, ChevronsRight, ChartNoAxesColumn, LogOut } from 'lucide-react';
import { SquadMark } from '../mark/SquadMark';
import { LookMenu } from '../LookMenu';
import { OVERSIGHT_ROLES } from './commands';
import type { Briefing } from '../api/types';

export interface SquadNavProps {
  collapsed: boolean;
  onToggle: () => void;
  needs: number;
  openClients: Briefing['open_clients'];
  pathname: string;
  userName: string;
  role: string;
  onSignOut: () => void;
}

export function SquadNav({ collapsed, onToggle, needs, openClients, pathname, userName, role, onSignOut }: SquadNavProps) {
  const initials = userName.split(/\s+/).map((p) => p[0]).slice(0, 2).join('');
  return (
    <aside className="sq-nav" data-collapsed={collapsed} aria-label="Credit Squad">
      <Link to="/" className="sq-navlink sq-navhome" aria-current={pathname === '/' ? 'page' : undefined}>
        <SquadMark size={collapsed ? 30 : 34} state={needs > 0 ? 'needs' : 'rest'} />
        <span className="sq-navlabel">Squad</span>
        {needs > 0 ? (
          <span className="sq-badge" aria-label={`${needs} ${needs === 1 ? 'needs' : 'need'} you`}>
            {needs}
          </span>
        ) : null}
      </Link>
      <Link to="/portfolio" className="sq-navlink" aria-current={pathname.startsWith('/portfolio') ? 'page' : undefined} title="My Portfolio">
        <ChartNoAxesColumn size={18} aria-hidden />
        <span className="sq-navlabel">My Portfolio</span>
      </Link>
      {openClients.length > 0 ? (
        <nav aria-label="Open cases" className="sq-cases">
          <p className="sq-navhead sq-navlabel">Open cases</p>
          {openClients.map((c) => (
            <Link key={c.borrower_id} to="/clients/$code" params={{ code: c.code }} className="sq-navlink" title={c.name}
              aria-current={pathname === `/clients/${c.code}` ? 'page' : undefined}>
              <span className="sq-initial" aria-hidden>{c.name[0]}</span>
              <span className="sq-navlabel">{c.name}</span>
              <span className="sq-count sq-navlabel">{c.open}</span>
            </Link>
          ))}
        </nav>
      ) : null}
      {OVERSIGHT_ROLES.includes(role) ? (
        <div className="sq-cases">
          <p className="sq-navhead sq-navlabel">Oversight</p>
          <Link to="/agent-activity" className="sq-navlink"><span className="sq-initial" aria-hidden>A</span><span className="sq-navlabel">Agent activity</span></Link>
          <Link to="/governance" className="sq-navlink"><span className="sq-initial" aria-hidden>G</span><span className="sq-navlabel">Governance</span></Link>
        </div>
      ) : null}
      <div className="sq-navfoot">
        <span className="sq-avatar" title={userName}>{initials}</span>
        <span className="sq-navlabel sq-grow">{userName}</span>
        <LookMenu />
        <button type="button" className="sq-iconbtn" onClick={onSignOut} aria-label="Sign out"><LogOut size={16} aria-hidden /></button>
        <button type="button" className="sq-iconbtn" onClick={onToggle} aria-expanded={!collapsed} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}>
          {collapsed ? <ChevronsRight size={16} aria-hidden /> : <ChevronsLeft size={16} aria-hidden />}
        </button>
      </div>
    </aside>
  );
}
```

```ts
// frontend/src/squad/api/hooks.ts
import { useQuery } from '@tanstack/react-query';
import { get } from '@/api/client';
import type { Briefing, Thread, Trail } from './types';

export const useBriefing = () => useQuery({ queryKey: ['briefing'], queryFn: () => get<Briefing>('/me/briefing') });
export const useThread = (borrowerId?: string) =>
  useQuery({ queryKey: ['thread', borrowerId], queryFn: () => get<Thread>(`/threads/${borrowerId}`), enabled: Boolean(borrowerId) });
export const useTrail = (workItemId: string, enabled: boolean) =>
  useQuery({ queryKey: ['trail', workItemId], queryFn: () => get<Trail>(`/cases/${workItemId}/trail`), enabled });
```

```tsx
// frontend/src/squad/shell/SquadShell.tsx
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { useCallback, useState } from 'react';
import { CommandPalette, useCommandPaletteShortcut } from '@/design';
import { useAuth } from '@/auth/context';
import { useBorrowers } from '@/api/hooks';
import { useBriefing } from '../api/hooks';
import { LookProvider, useLook } from '../useLook';
import { PresenceLine, PresenceProvider } from '../presence/Presence';
import { buildCommands } from './commands';
import { SquadNav } from './SquadNav';

const NAV_KEY = 'squad.nav.collapsed';
function storedCollapsed(): boolean {
  try {
    return localStorage.getItem(NAV_KEY) !== 'false'; // collapsed unless the person opened it
  } catch {
    return true;
  }
}

function Frame() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const briefing = useBriefing();
  const borrowers = useBorrowers();
  const { setLook } = useLook();
  const [collapsed, setCollapsed] = useState(storedCollapsed);
  const [paletteOpen, setPaletteOpen] = useState(false);
  useCommandPaletteShortcut(useCallback(() => setPaletteOpen((o) => !o), []));
  const toggle = () =>
    setCollapsed((c) => {
      try {
        localStorage.setItem(NAV_KEY, String(!c));
      } catch {
        /* not remembered */
      }
      return !c;
    });
  const commands = buildCommands({
    clients: (borrowers.data ?? []).map((b) => ({ code: b.code, name: b.name })),
    go: (path) => void navigate({ to: path }),
    setLook,
    role: user?.role ?? '',
  });
  const needs = briefing.data?.needs_you ?? 0;
  return (
    <PresenceProvider needs={needs}>
      <div className="sq-root sq-shell" data-collapsed={collapsed}>
        <a href="#main" className="sq-skip">Skip to content</a>
        <SquadNav collapsed={collapsed} onToggle={toggle} needs={needs} openClients={briefing.data?.open_clients ?? []}
          pathname={pathname} userName={user?.name ?? ''} role={user?.role ?? ''} onSignOut={() => void signOut()} />
        <div className="sq-stage">
          <main id="main" tabIndex={-1} className="sq-main">
            <PresenceLine />
            <Outlet />
          </main>
        </div>
        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} placeholder="Search clients and commands" />
      </div>
    </PresenceProvider>
  );
}

export function SquadShell() {
  return (
    <LookProvider>
      <Frame />
    </LookProvider>
  );
}
```

Append shell layout rules to `squad.css`:

```css
.sq-shell { display: flex; min-height: 100vh; }
.sq-skip { position: absolute; left: -9999px; }
.sq-skip:focus { left: 8px; top: 8px; z-index: 80; background: var(--sq-surface); padding: 6px 10px; border-radius: 8px; }
.sq-nav { width: 248px; flex-shrink: 0; display: flex; flex-direction: column; gap: 2px; padding: 12px 10px; background: var(--sq-surface); border-right: 1px solid var(--sq-line); position: sticky; top: 0; height: 100vh; overflow-y: auto; }
.sq-nav[data-collapsed='true'] { width: 64px; align-items: center; }
.sq-nav[data-collapsed='true'] .sq-navlabel, .sq-nav[data-collapsed='true'] .sq-navhead { display: none; }
.sq-nav[data-collapsed='true'] .sq-navfoot { flex-direction: column; }
.sq-navlink { display: flex; align-items: center; gap: 10px; min-height: 38px; padding: 4px 8px; border-radius: 10px; color: var(--sq-ink); text-decoration: none; position: relative; }
.sq-navlink:hover { background: var(--sq-sunk); }
.sq-navlink[aria-current='page'] { background: var(--sq-sunk); font-weight: 600; }
.sq-navhome { font-weight: 600; margin-bottom: 6px; }
.sq-navhead { margin: 14px 8px 4px; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--sq-ink3); }
.sq-cases { display: flex; flex-direction: column; gap: 2px; width: 100%; }
.sq-badge { margin-left: auto; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 11px; background: var(--sq-ember); color: var(--sq-on-ember); font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
.sq-nav[data-collapsed='true'] .sq-badge { position: absolute; top: 0; right: 0; min-width: 18px; height: 18px; font-size: 11px; }
.sq-initial, .sq-avatar { width: 24px; height: 24px; border-radius: 50%; background: var(--sq-squad-soft); color: var(--sq-squad); font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sq-count { margin-left: auto; font-size: 12px; color: var(--sq-ink2); }
.sq-grow { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sq-navfoot { margin-top: auto; display: flex; align-items: center; gap: 6px; padding-top: 10px; border-top: 1px solid var(--sq-line); width: 100%; }
.sq-stage { flex: 1; min-width: 0; }
.sq-main { max-width: 860px; margin: 0 auto; padding: 0 24px 48px; outline: none; }
```

Router edits in `frontend/src/router.tsx` (shared file): import `SquadShell` and render it in `Root` in place of `AppShell`; `indexRoute` becomes the Squad home route (component `SquadHomeRoute`, replaced by `SquadHome` in Task 10), the redirect target after sign-in becomes `'/'`; add

```tsx
export const clientRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code',
  component: lazyRouteComponent(() => import('@/squad/thread/ClientThread'), 'ClientThread'),
  validateSearch: (search: Record<string, unknown>): { case?: string } => clean({ case: str(search.case) }),
});
```
and register `clientRoute` in the tree. Until Task 11, `ClientThread` is a stub exporting `export function ClientThread() { return <h1>Client</h1>; }` in `frontend/src/squad/thread/ClientThread.tsx`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm vitest run && pnpm typecheck && pnpm lint`
Expected: PASS (existing cockpit tests still pass; they do not mount `AppShell`'s replacement).

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(squad-ui): shell with collapsible nav, Ctrl K commands and the new routes"
```

---

### Task 9: Live updates (ledger polling) and the write hooks

**Files:**
- Create: `frontend/src/squad/api/polling.ts`
- Modify: `frontend/src/squad/api/hooks.ts` (add mutations), `frontend/src/squad/shell/SquadShell.tsx` (start the heartbeat)
- Test: `frontend/src/squad/__tests__/polling.test.tsx`

**Interfaces:**
- Consumes: `get`, `post` from `@/api/client`; `useAuth`.
- Produces: `useLedgerHeartbeat({ intervalMs?: number; enabled?: boolean })`: after a first read of the ledger head it asks `GET /ledger?after_seq=<cursor>` every `intervalMs` (default 4000) and, when anything new has arrived, invalidates the queries `['briefing']`, `['thread']`, `['trail']`, `['borrowers']`. It never has two requests in flight, skips a tick while `document.hidden`, keeps its cursor on a failed poll (no invalidation, nothing blanked) and stops when unmounted or `enabled` is false. Mutations in `hooks.ts`: `useAnswer(workItemId)` -> `POST /work-items/{id}/answer` with `{ option_id, remember, note }` returning `{ lesson_id: string | null }`; `useAskCopilot()` -> `POST /copilot/ask` with `{ question, borrower_id }`; `useCreateDraft(borrowerId)`, `useEditDraft()`, `useSendDraft()` -> the draft routes, each returning `ThreadMessage & { type: 'draft' }`-shaped fields plus `delivered?: false`. Every mutation invalidates `['briefing']`, `['thread']` on success.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/polling.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as client from '@/api/client';
import { useLedgerHeartbeat } from '../api/polling';

const wrap = (qc: QueryClient) => ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;

describe('useLedgerHeartbeat', () => {
  let qc: QueryClient;
  let invalidate: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    qc = new QueryClient();
    invalidate = vi.spyOn(qc, 'invalidateQueries');
  });
  afterEach(() => vi.restoreAllMocks());

  it('reads the head once, then refreshes the briefing and threads when something new arrives', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 5 }]); // the head
    get.mockResolvedValueOnce([]); // nothing new
    get.mockResolvedValue([{ seq: 6 }]); // something new
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 5, limit: 500 }, undefined));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['briefing'] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] });
    // the cursor moved on to 6 after the event
    await waitFor(() => expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 6, limit: 500 }, undefined));
  });

  it('never stacks requests while one is slow', async () => {
    let inFlight = 0;
    let peak = 0;
    vi.spyOn(client, 'get').mockImplementation(async () => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 40));
      inFlight -= 1;
      return [];
    });
    renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 200));
    expect(peak).toBe(1);
  });

  it('survives a failed poll without invalidating or giving up', async () => {
    const get = vi.spyOn(client, 'get');
    get.mockResolvedValueOnce([{ seq: 1 }]);
    get.mockRejectedValueOnce(new Error('offline'));
    get.mockResolvedValue([{ seq: 2 }]);
    renderHook(() => useLedgerHeartbeat({ intervalMs: 10 }), { wrapper: wrap(qc) });
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['thread'] }));
    expect(get).toHaveBeenCalledWith('/ledger', { after_seq: 1, limit: 500 }, undefined);
  });

  it('stops when disabled or unmounted, and waits while the tab is hidden', async () => {
    const get = vi.spyOn(client, 'get').mockResolvedValue([]);
    const off = renderHook(() => useLedgerHeartbeat({ intervalMs: 5, enabled: false }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 40));
    expect(get).not.toHaveBeenCalled();
    off.unmount();
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    const hidden = renderHook(() => useLedgerHeartbeat({ intervalMs: 5 }), { wrapper: wrap(qc) });
    await new Promise((r) => setTimeout(r, 40));
    const callsWhileHidden = get.mock.calls.length;
    expect(callsWhileHidden).toBeLessThanOrEqual(1); // at most the head read
    hidden.unmount();
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/polling.test.tsx`
Expected: FAIL (`../api/polling` not found).

- [ ] **Step 3: Implement**

```ts
// frontend/src/squad/api/polling.ts
import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { get } from '@/api/client';

interface Options {
  intervalMs?: number;
  enabled?: boolean;
}
const REFRESH = [['briefing'], ['thread'], ['trail'], ['borrowers']] as const;

/**
 * No push channel exists (spec 6), so the browser asks the ledger for anything after its cursor.
 * One request at a time, paused while the tab is hidden, and a failed poll changes nothing.
 */
export function useLedgerHeartbeat({ intervalMs = 4000, enabled = true }: Options = {}) {
  const qc = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let cursor: number | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => REFRESH.forEach((queryKey) => void qc.invalidateQueries({ queryKey: [...queryKey] }));

    async function tick() {
      if (stopped) return;
      if (!document.hidden) {
        try {
          if (cursor === null) {
            const [newest] = await get<Array<{ seq: number }>>('/ledger', { limit: 1 });
            cursor = newest?.seq ?? 0;
            refresh(); // anything that landed between the page's first read and this one
          } else {
            const rows = await get<Array<{ seq: number }>>('/ledger', { after_seq: cursor, limit: 500 }, undefined);
            if (rows.length > 0) {
              cursor = rows[rows.length - 1]!.seq;
              refresh();
            }
          }
        } catch {
          /* keep the cursor and what is on screen; try again next time */
        }
      }
      if (!stopped) timer = setTimeout(() => void tick(), intervalMs);
    }
    void tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [qc, intervalMs, enabled]);
}
```

(The test expects the head read to be `get('/ledger', { limit: 1 })`; the second argument shape in the first assertion applies to the `after_seq` call only. In the first test the mocked head is `[{ seq: 5 }]`, then `[]`, then `[{ seq: 6 }]`.)

Append to `frontend/src/squad/api/hooks.ts`:

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { post } from '@/api/client';

function useWrite<TIn, TOut>(path: (input: TIn) => string, body: (input: TIn) => unknown) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: TIn) => post<TOut>(path(input), body(input)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['briefing'] });
      void qc.invalidateQueries({ queryKey: ['thread'] });
    },
  });
}

export interface AnswerInput { option_id: string; remember: boolean; note?: string }
export const useAnswer = (workItemId: string) =>
  useWrite<AnswerInput, { lesson_id: string | null }>(() => `/work-items/${workItemId}/answer`, (i) => i);

export const useAskCopilot = () =>
  useWrite<{ question: string; borrower_id: string }, { status: string; answer: string }>(() => '/copilot/ask', (i) => ({ ...i, history: [] }));

interface DraftResult { draft_id: string; status: 'draft' | 'sent'; delivered?: false }
export const useCreateDraft = (borrowerId: string) =>
  useWrite<{ to: string; subject: string; body: string; kind?: string }, DraftResult>(() => `/borrowers/${borrowerId}/drafts`, (i) => i);
export const useEditDraft = () =>
  useWrite<{ draft_id: string; subject?: string; body?: string }, DraftResult>((i) => `/drafts/${i.draft_id}/edit`, ({ draft_id: _id, ...rest }) => rest);
export const useSendDraft = () => useWrite<{ draft_id: string }, DraftResult>((i) => `/drafts/${i.draft_id}/send`, () => ({}));
```

In `SquadShell.tsx`'s `Frame` call `useLedgerHeartbeat({ enabled: Boolean(user) })` after `useAuth()`; add the import.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad
git commit -m "feat(squad-ui): ledger heartbeat that never stacks, and the write hooks"
```

---

### Task 10: Squad home: the briefing

**Files:**
- Create: `frontend/src/squad/home/SquadHome.tsx`
- Modify: `frontend/src/router.tsx` (the `/` route renders `SquadHome`)
- Modify: `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/home.test.tsx`

**Interfaces:**
- Consumes: `useBriefing`, `Briefing`, `BriefingItem`; `threadHref`; `useAuth`; `AgentBody` from `@/source/AgentBody`.
- Produces: `SquadHome()` (route `/`). Each item is one link to `threadHref(item.borrower_code, item.work_item_id ?? undefined)`; its accessible name is `"<client>: <title>. <state>"`. The needs-you sentence is computed from the items rendered: `n` items with `needs_you` true read "n need you" ("1 needs you"); none reads "Nothing needs you." A `decided` item shows its state in words ("reviewed by Priya Raman") and is never counted. An "Overnight" section lists what agents finished.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/home.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import type { Briefing, BriefingItem } from '../api/types';
import { SquadHome } from '../home/SquadHome';

const mockBriefing = vi.hoisted(() => ({ data: undefined as unknown, isPending: false, error: null as unknown }));
vi.mock('../api/hooks', () => ({ useBriefing: () => mockBriefing }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));

const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: [] };
const item = (over: Partial<BriefingItem>): BriefingItem => ({
  key: 'k', kind: 'review', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', title: 'Confirm revenue',
  state: 'waiting for you', severity: 'medium', needs_you: true, work_item_id: 'w1', ...over,
});
const briefing = (items: BriefingItem[], overnight: Briefing['overnight'] = []): Briefing => ({
  as_of: '2026-11-20', needs_you: items.filter((i) => i.needs_you).length, items, overnight, open_clients: [],
});

function mount(b: Briefing) {
  mockBriefing.data = b;
  const root = createRootRoute({ component: SquadHome });
  const client = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([client]), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => true, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('SquadHome', () => {
  it('says plainly that nothing needs her, and does not paint zero as an alarm', async () => {
    mount(briefing([]));
    expect(await screen.findByText('Nothing needs you.')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: /needs you/i })).not.toBeInTheDocument();
  });

  it('counts exactly the needs-you items it lists', async () => {
    mount(briefing([
      item({ key: 'a', work_item_id: 'w1' }),
      item({ key: 'b', work_item_id: 'w2', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.', kind: 'question', state: 'Squad asks' }),
      item({ key: 'c', work_item_id: 'w3', kind: 'decided', state: 'reviewed by Priya Raman', needs_you: false }),
    ]));
    expect(await screen.findByText('2 need you')).toBeInTheDocument();
    const list = screen.getByRole('list', { name: /needs you/i });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('reviewed by Priya Raman')).toBeInTheDocument();
  });

  it('opens the client thread at the case, not the first screen of someone else', async () => {
    mount(briefing([item({ work_item_id: 'w9', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.' })]));
    const link = await screen.findByRole('link', { name: /zephyr zinc works.*confirm revenue/i });
    expect(link).toHaveAttribute('href', '/clients/ZZZ?case=w9');
  });

  it('opens an item without a case (a signal) at the client thread alone', async () => {
    mount(briefing([item({ kind: 'signal', work_item_id: null, title: 'A signal needs a look' })]));
    expect(await screen.findByRole('link', { name: /signal/i })).toHaveAttribute('href', '/clients/QFL');
  });

  it('lists what agents did overnight with the client named', async () => {
    mount(briefing([], [{ agent_name: 'spreading', text: 'Read the October package.', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', finished_at: '2026-11-20T02:00:00Z' }]));
    expect(await screen.findByText('Read the October package.')).toBeInTheDocument();
    expect(screen.getByText(/spreading agent/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/home.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/home/SquadHome.tsx
import { Link } from '@tanstack/react-router';
import { useAuth } from '@/auth/context';
import { AgentBody } from '@/source/AgentBody';
import { useBriefing } from '../api/hooks';
import type { BriefingItem } from '../api/types';
import { threadHref } from '../links';

const word = (n: number) => (n === 1 ? '1 needs you' : `${n} need you`);

function Row({ item }: { item: BriefingItem }) {
  const href = threadHref(item.borrower_code, item.work_item_id ?? undefined);
  return (
    <li>
      <Link {...href} className="sq-row" aria-label={`${item.borrower_name}: ${item.title}. ${item.state}`}>
        <span className={`sq-dotmark sq-sev-${item.severity}`} aria-hidden />
        <span className="sq-grow">
          <b>{item.borrower_name}</b>
          <span className="sq-muted"> · {item.title}</span>
        </span>
        <span className={item.needs_you ? 'sq-state sq-state-needs' : 'sq-state'}>{item.state}</span>
      </Link>
    </li>
  );
}

export function SquadHome() {
  const { user } = useAuth();
  const briefing = useBriefing();
  if (briefing.isPending) return <p role="status" className="sq-muted">Squad is reading the overnight record.</p>;
  if (briefing.error || !briefing.data) return <p role="alert">The briefing could not be loaded. Try again in a moment.</p>;
  const { items, overnight } = briefing.data;
  const needs = items.filter((i) => i.needs_you);
  const rest = items.filter((i) => !i.needs_you);
  return (
    <div className="sq-home">
      <h1 className="sq-h1">Hello, {user?.name.split(' ')[0] ?? 'there'}.</h1>
      <p className="sq-lede">{needs.length ? word(needs.length) : 'Nothing needs you.'}</p>
      {needs.length > 0 ? (
        <ul className="sq-list" aria-label="Needs you">
          {needs.map((i) => <Row key={i.key} item={i} />)}
        </ul>
      ) : null}
      {rest.length > 0 ? (
        <>
          <h2 className="sq-h2">Also on the record</h2>
          <ul className="sq-list" aria-label="Also on the record">
            {rest.map((i) => <Row key={i.key} item={i} />)}
          </ul>
        </>
      ) : null}
      {overnight.length > 0 ? (
        <>
          <h2 className="sq-h2">What Squad did overnight</h2>
          <ul className="sq-list" aria-label="Overnight">
            {overnight.map((o, n) => (
              <li key={n} className="sq-card sq-squad">
                <p className="sq-faint"><b>{o.agent_name.charAt(0).toUpperCase() + o.agent_name.slice(1)} agent</b> · {o.borrower_name}</p>
                <AgentBody text={o.text} />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
```

Append to `squad.css`:

```css
.sq-h1 { font-size: 26px; font-weight: 650; margin: 8px 0 2px; }
.sq-h2 { font-size: 13px; letter-spacing: 0.05em; text-transform: uppercase; color: var(--sq-ink2); margin: 26px 0 8px; }
.sq-lede { font-size: 17px; color: var(--sq-ink2); margin: 0 0 14px; }
.sq-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sq-row { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 12px; background: var(--sq-surface); border: 1px solid var(--sq-line); color: var(--sq-ink); text-decoration: none; }
.sq-row:hover { border-color: var(--sq-ink3); }
.sq-row:focus-visible { outline: 2px solid var(--sq-squad); outline-offset: 2px; }
.sq-dotmark { width: 10px; height: 10px; border-radius: 50%; background: var(--sq-ink3); flex-shrink: 0; }
.sq-sev-critical, .sq-sev-high { background: var(--sq-ember); }
.sq-state { font-size: 13px; color: var(--sq-ink2); white-space: nowrap; }
.sq-state-needs { color: var(--sq-ink); font-weight: 600; }
```

In `router.tsx` the `/` route: `component: lazyRouteComponent(() => import('@/squad/home/SquadHome'), 'SquadHome')` (replacing the Task 8 placeholder).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(squad-ui): Squad home briefing, counted from the items it lists"
```

---

### Task 11: A client's thread: messages, case focus, evidence from a document

**Files:**
- Modify (replace the Task 8 stub): `frontend/src/squad/thread/ClientThread.tsx`
- Create: `frontend/src/squad/thread/messages.tsx`, `frontend/src/squad/thread/Trail.tsx`
- Modify: `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/thread.test.tsx`

**Interfaces:**
- Consumes: `useBorrowerByCode` (`@/api/hooks`), `useThread`, `useTrail`, `ThreadMessage`, `useSource` (`@/source/context`), `AgentBody`, `clientFile`, `SquadMark`.
- Produces: `ClientThread()` (route `/clients/$code?case=`), `MessageView({ message, focused, borrowerCode })` handling `report`, `case`, `document`, `held`, `decision`, `handoff` (the `ask`, `qa` and `draft` types are rendered by Tasks 12 and 13 and, until then, by a `Fallback` that renders nothing), `Trail({ workItemId })` (a "How I got here" disclosure that loads `GET /cases/{id}/trail` only when opened, one row per step: who, role line, text, check).
- Focus rule: the message whose `work_item_id` equals `?case=` gets `data-focused="true"` and `aria-current="true"` and is scrolled into view; an unknown id focuses nothing and shows the whole thread.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/thread.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Thread, ThreadMessage } from '../api/types';
import { ClientThread } from '../thread/ClientThread';

const state = vi.hoisted(() => ({ thread: undefined as unknown, notFound: false, open: vi.fn(), trail: undefined as unknown }));
vi.mock('@/api/hooks', () => ({
  useBorrowerByCode: (code: string) => ({ borrower: state.notFound ? undefined : { id: 'b1', code, name: 'Quillfeather Labs, Inc.' }, notFound: state.notFound, isPending: false }),
}));
vi.mock('../api/hooks', () => ({
  useThread: () => ({ data: state.thread, isPending: false, error: null }),
  useTrail: () => ({ data: state.trail, isPending: false }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));
vi.mock('../thread/Composer', () => ({ Composer: () => null }));
vi.mock('../thread/AskMessage', () => ({ AskMessage: () => null }));
vi.mock('../thread/QaMessage', () => ({ QaMessage: () => null }));
vi.mock('../thread/DraftMessage', () => ({ DraftMessage: () => null }));

const base = { ts: '2026-11-20T08:00:00Z' };
const messages: ThreadMessage[] = [
  { ...base, id: 'doc:1', type: 'document', document_id: 'd1', title: 'October compliance certificate', doc_type: 'compliance_certificate', pages: 2, period_end: '2026-10-31' },
  { ...base, id: 'held:1', type: 'held', document_id: 'd2', title: 'Unknown scan', reason: "Not this client's file" },
  { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'covenant.breach', title: 'Cash below minimum', question: 'Is this a breach?', severity: 'critical', status: 'open', allowed_decisions: [] },
  { ...base, id: 'case:2', type: 'case', work_item_id: 'w2', item_type: 'funding_slipped', title: 'Funding slipped', question: 'Review the outlook?', severity: 'high', status: 'open', allowed_decisions: [] },
  { ...base, id: 'decision:1', type: 'decision', work_item_id: 'w2', decision: 'reviewed', reason: 'Close is signed.', by: 'Priya Raman', by_id: 'u1' },
  { ...base, id: 'handoff:1', type: 'handoff', work_item_id: 'w1', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman' },
  { ...base, id: 'run:1', type: 'report', agent_name: 'spreading', task: 'read_statements', text: 'Read the October package.', run_id: 'r1' },
];
const thread = (m: ThreadMessage[]): Thread => ({ borrower: { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' }, head_seq: 9, messages: m });

function mount(search = '') {
  const root = createRootRoute();
  const route = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: ClientThread, validateSearch: (s: Record<string, unknown>) => ({ case: typeof s.case === 'string' ? s.case : undefined }) });
  const router = createRouter({ routeTree: root.addChildren([route]), history: createMemoryHistory({ initialEntries: [`/clients/QFL${search}`] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

beforeEach(() => {
  state.notFound = false;
  state.thread = thread(messages);
  state.trail = undefined;
  state.open.mockClear();
});

describe('ClientThread', () => {
  it('names the client and offers the client file', async () => {
    mount();
    expect(await screen.findByRole('heading', { name: 'Quillfeather Labs, Inc.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open in client file/i })).toHaveAttribute('href', '/borrowers/QFL');
  });

  it('renders each message type in words a person can act on', async () => {
    mount();
    expect(await screen.findByText('October compliance certificate')).toBeInTheDocument();
    expect(screen.getByText(/Not this client's file/)).toBeInTheDocument();
    expect(screen.getByText('Cash below minimum')).toBeInTheDocument();
    expect(screen.getByText(/Priya Raman handed this to Helen Strand/)).toBeInTheDocument();
    expect(screen.getByText(/Priya Raman: reviewed/)).toBeInTheDocument();
    expect(screen.getByText('Close is signed.')).toBeInTheDocument();
    expect(screen.getByText('Read the October package.')).toBeInTheDocument();
  });

  it('opens a document in the evidence drawer from the thread', async () => {
    mount();
    await userEvent.click(await screen.findByRole('button', { name: /open october compliance certificate/i }));
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 1 }));
  });

  it('focuses the case named in the address and no other', async () => {
    mount('?case=w1');
    const focused = await screen.findByText('Cash below minimum');
    expect(focused.closest('[data-work-item]')).toHaveAttribute('data-focused', 'true');
    expect(screen.getByText('Funding slipped').closest('[data-work-item]')).not.toHaveAttribute('data-focused');
  });

  it('shows the whole thread, without an error, for a case id that is not there', async () => {
    mount('?case=does-not-exist');
    expect(await screen.findByText('Cash below minimum')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(document.querySelector('[data-focused]')).toBeNull();
  });

  it('is honest about an empty thread', async () => {
    state.thread = thread([]);
    mount();
    expect(await screen.findByText(/nothing here yet/i)).toBeInTheDocument();
  });

  it('says so, and offers the way home, for a client that does not exist', async () => {
    state.notFound = true;
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent(/no client with that code/i);
    expect(screen.getByRole('link', { name: /back to squad/i })).toHaveAttribute('href', '/');
  });

  it('loads "How I got here" only when it is opened', async () => {
    state.trail = { work_item_id: 'w1', steps: [{ n: 1, who: 'Spreading agent', role_line: 'reads figures from documents', text: 'Ran read statements.', check: 'completed', run_id: 'r1' }, { n: 2, who: 'Code', role_line: 'calculation, no AI', text: 'Applied cov.min_unrestricted_cash.', check: 'exact arithmetic', run_id: null }], calculation: null, checks: [] };
    mount();
    const card = (await screen.findByText('Cash below minimum')).closest('[data-work-item]') as HTMLElement;
    expect(within(card).queryByText('Spreading agent')).not.toBeInTheDocument();
    await userEvent.click(within(card).getByRole('button', { name: /how i got here/i }));
    expect(within(card).getByText('Spreading agent')).toBeInTheDocument();
    expect(within(card).getByText(/calculation, no AI/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/thread.test.tsx`
Expected: FAIL (the stub renders no thread; `thread/Composer` etc. do not exist yet, so create the empty modules in step 3).

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/thread/Trail.tsx
import { useState } from 'react';
import { useTrail } from '../api/hooks';

/** "How I got here": which specialist did what, in plain words, loaded only when asked for. */
export function Trail({ workItemId }: { workItemId: string }) {
  const [open, setOpen] = useState(false);
  const trail = useTrail(workItemId, open);
  return (
    <div className="sq-trail">
      <button type="button" className="sq-link" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        How I got here
      </button>
      {open ? (
        trail.data ? (
          trail.data.steps.length === 0 ? (
            <p className="sq-muted">No agent work is recorded behind this case.</p>
          ) : (
            <ol className="sq-steps">
              {trail.data.steps.map((s) => (
                <li key={s.n}>
                  <b>{s.who}</b> <small className="sq-faint">{s.role_line}</small>
                  <span>{s.text}</span>
                  <span className="sq-check">✓ {s.check}</span>
                </li>
              ))}
            </ol>
          )
        ) : (
          <p role="status" className="sq-muted">Loading the trail.</p>
        )
      ) : null}
    </div>
  );
}
```

```tsx
// frontend/src/squad/thread/messages.tsx
import { Link } from '@tanstack/react-router';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { clientFile } from '../links';
import { SquadMark } from '../mark/SquadMark';
import { AskMessage } from './AskMessage';
import { DraftMessage } from './DraftMessage';
import { QaMessage } from './QaMessage';
import { Trail } from './Trail';

const words = (s: string | null) => (s ?? 'decided').replace(/_/g, ' ');
const agent = (name: string) => `${name.charAt(0).toUpperCase()}${name.slice(1)} agent`;

export function MessageView({ message, focused, borrowerCode }: { message: ThreadMessage; focused: boolean; borrowerCode: string }) {
  const source = useSource();
  switch (message.type) {
    case 'report':
      return (
        <article className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b> <span className="sq-faint">{agent(message.agent_name)}</span></header>
          <AgentBody text={message.text} />
        </article>
      );
    case 'case':
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
          <header className="sq-msghead"><b>{message.title}</b> <span className="sq-tag">{message.status}</span></header>
          <p>{message.question}</p>
          <div className="sq-actions">
            <Link to={clientFile(borrowerCode)} className="sq-link">Open in client file</Link>
          </div>
          <Trail workItemId={message.work_item_id} />
        </article>
      );
    case 'document':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Document arrived</b></header>
          <button type="button" className="sq-link" aria-label={`Open ${message.title}`} onClick={() => source.open({ type: 'document', documentId: message.document_id, page: 1, title: message.title, borrowerCode })}>
            {message.title}
          </button>
          <p className="sq-muted">{message.doc_type ? words(message.doc_type) : 'Not yet classified'} · {message.pages} {message.pages === 1 ? 'page' : 'pages'}</p>
        </article>
      );
    case 'held':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Held</b></header>
          <p>{message.title}</p>
          <p className="sq-muted">{message.reason || 'No reason was written.'}</p>
        </article>
      );
    case 'decision':
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id}>
          <p><b>{message.by}: {words(message.decision)}</b></p>
          {message.reason ? <blockquote className="sq-quote">{message.reason}</blockquote> : null}
        </article>
      );
    case 'handoff':
      return <p className="sq-msg sq-faint" data-work-item={message.work_item_id}>{message.by} handed this to {message.assigned_to ?? 'no one in particular'}.</p>;
    case 'ask':
      return <AskMessage message={message} focused={focused} />;
    case 'qa':
      return <QaMessage message={message} borrowerCode={borrowerCode} />;
    case 'draft':
      return <DraftMessage message={message} />;
  }
}
```

Only a `case` or `ask` card sets `data-focused`; `decision` and `handoff` carry `data-work-item` so tests and the e2e can find them by case.

```tsx
// frontend/src/squad/thread/ClientThread.tsx
import { Link, useParams, useSearch } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useBorrowerByCode } from '@/api/hooks';
import { useThread } from '../api/hooks';
import { clientFile } from '../links';
import { Composer } from './Composer';
import { MessageView } from './messages';

export function ClientThread() {
  const { code } = useParams({ strict: false }) as { code: string };
  const { case: focusId } = useSearch({ strict: false }) as { case?: string };
  const { borrower, notFound } = useBorrowerByCode(code);
  const thread = useThread(borrower?.id);

  useEffect(() => {
    if (!focusId || !thread.data) return;
    document.querySelector(`[data-work-item="${CSS.escape(focusId)}"][data-focused="true"]`)?.scrollIntoView({ block: 'center' });
  }, [focusId, thread.data]);

  if (notFound) {
    return (
      <div role="alert" className="sq-card">
        <p>There is no client with that code.</p>
        <Link to="/" className="sq-link">Back to Squad</Link>
      </div>
    );
  }
  if (!borrower || thread.isPending) return <p role="status" className="sq-muted">Opening the thread.</p>;
  if (thread.error || !thread.data) return <p role="alert">The thread could not be loaded. Try again in a moment.</p>;
  const messages = thread.data.messages;
  return (
    <section className="sq-thread" aria-label={`${borrower.name} thread`}>
      <header className="sq-threadhead">
        <h1 className="sq-h1">{borrower.name}</h1>
        <Link to={clientFile(borrower.code)} className="sq-link">Open in client file</Link>
      </header>
      {messages.length === 0 ? <p className="sq-muted">Nothing here yet. Squad will write here as documents arrive and work is done.</p> : null}
      <div className="sq-messages">
        {messages.map((m) => (
          <MessageView key={m.id} message={m} borrowerCode={borrower.code}
            focused={Boolean(focusId) && 'work_item_id' in m && m.work_item_id === focusId && (m.type === 'case' || m.type === 'ask')} />
        ))}
      </div>
      <Composer borrowerId={borrower.id} borrowerName={borrower.name} />
    </section>
  );
}
```

Create the three not-yet-built message modules as minimal stubs so this task compiles and its tests can run; Tasks 12 and 13 replace them with their real contents (each stub is exactly one line of working code, not a placeholder in the deliverable):

```tsx
// frontend/src/squad/thread/Composer.tsx
export function Composer(_props: { borrowerId: string; borrowerName: string }) { return null; }
// frontend/src/squad/thread/AskMessage.tsx
import type { ThreadMessage } from '../api/types';
export function AskMessage(_props: { message: Extract<ThreadMessage, { type: 'ask' }>; focused: boolean }) { return null; }
// frontend/src/squad/thread/QaMessage.tsx
import type { ThreadMessage } from '../api/types';
export function QaMessage(_props: { message: Extract<ThreadMessage, { type: 'qa' }>; borrowerCode: string }) { return null; }
// frontend/src/squad/thread/DraftMessage.tsx
import type { ThreadMessage } from '../api/types';
export function DraftMessage(_props: { message: Extract<ThreadMessage, { type: 'draft' }> }) { return null; }
```

Append to `squad.css`:

```css
.sq-threadhead { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.sq-messages { display: flex; flex-direction: column; gap: 12px; margin: 14px 0 24px; }
.sq-msg { margin: 0; }
.sq-msghead { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.sq-msg[data-focused='true'] { outline: 2px solid var(--sq-ember); outline-offset: 3px; }
.sq-link { background: none; border: none; padding: 0; font: inherit; color: var(--sq-squad); text-decoration: underline; cursor: pointer; }
.sq-tag { font-size: 12px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--sq-line); color: var(--sq-ink2); }
.sq-quote { margin: 6px 0 0; padding-left: 10px; border-left: 3px solid var(--sq-squad-line); color: var(--sq-ink2); }
.sq-actions { display: flex; gap: 12px; align-items: center; margin-top: 8px; }
.sq-steps { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sq-steps li { display: grid; gap: 2px; }
.sq-check { color: var(--sq-ok); font-size: 13px; }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad
git commit -m "feat(squad-ui): client threads with message types, case focus and the work trail"
```

---

### Task 12: Questions to Squad (with sources) and Squad asks

**Files:**
- Replace the Task 11 stubs: `frontend/src/squad/thread/Composer.tsx`, `AskMessage.tsx`, `QaMessage.tsx`
- Modify: `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/questions.test.tsx`

**Interfaces:**
- Consumes: `useAskCopilot`, `useAnswer`, `usePresence`, `useAuth` (`can`), `useSource`, `AgentBody`, `clientFile`, `ApiError`/`errorMessage` from `@/api/client`.
- Produces: `Composer({ borrowerId, borrowerName })`: a labelled textarea ("Ask Squad about <client>") and an Ask button; while a question is out, the presence is working (`beginWork`) and the button is disabled; when the answer arrives the presence pulses; an error (for example 503 "The Copilot's model is not available.") is shown inline as an alert, never as a made-up answer. `QaMessage({ message, borrowerCode })`: the person's question, then Squad's answer through `AgentBody` (figures are stored facts rendered by code), a line "Checked by code: N stored figures" when `fact_ids` is non-empty, one "Source: page P" button per citation opening the evidence drawer at that page, and, when `status !== 'answered'`, a refusal block with "Open the client file" (and "Show the source" when a citation exists); a refusal is never restyled as an answer. `AskMessage({ message, focused })`: the question, the options as radio buttons each with its evidence line, a "Remember this for next time" checkbox, and an ink "Confirm" button disabled until an option is chosen and while sending. On success the presence says `Recorded as <first name>` plus ` · remembered` when ticked. An answered ask is read-only ("You chose X" with `chosen_by`). A user without `decide_work_item` sees the options read-only with "Waiting for an analyst."

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/questions.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { ApiError } from '@/api/client';
import { AuthContext } from '@/auth/context';
import type { ThreadMessage } from '../api/types';
import { PresenceProvider, usePresence } from '../presence/Presence';
import { AskMessage } from '../thread/AskMessage';
import { Composer } from '../thread/Composer';
import { QaMessage } from '../thread/QaMessage';

const calls = vi.hoisted(() => ({ ask: vi.fn(), answer: vi.fn(), open: vi.fn() }));
vi.mock('../api/hooks', () => ({
  useAskCopilot: () => ({ mutateAsync: calls.ask, isPending: false }),
  useAnswer: () => ({ mutateAsync: calls.answer, isPending: false }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: calls.open, close: () => {}, current: null }) }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p data-testid="body">{text}</p> }));

const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: ['decide_work_item'] };
function Say() {
  return <span data-testid="said">{usePresence().said}</span>;
}
const mount = (ui: React.ReactNode, can = true) =>
  render(
    <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => can, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
      <PresenceProvider needs={0}>
        {ui}
        <Say />
      </PresenceProvider>
    </AuthContext.Provider>,
  );
beforeEach(() => Object.values(calls).forEach((c) => c.mockReset()));

describe('Composer', () => {
  it('sends the question scoped to the client and clears the box', async () => {
    calls.ask.mockResolvedValue({ status: 'answered', answer: 'x' });
    mount(<Composer borrowerId="b1" borrowerName="Quillfeather Labs, Inc." />);
    await userEvent.type(screen.getByLabelText(/ask squad about quillfeather/i), 'What is cash?');
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }));
    expect(calls.ask).toHaveBeenCalledWith({ question: 'What is cash?', borrower_id: 'b1' });
    await waitFor(() => expect(screen.getByLabelText(/ask squad about/i)).toHaveValue(''));
  });

  it('does not send an empty question', async () => {
    mount(<Composer borrowerId="b1" borrowerName="Q" />);
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeDisabled();
  });

  it('shows the server\'s own words when Squad cannot be reached, and keeps the question', async () => {
    calls.ask.mockRejectedValue(new ApiError(503, "The Copilot's model is not available."));
    mount(<Composer borrowerId="b1" borrowerName="Q" />);
    await userEvent.type(screen.getByLabelText(/ask squad about/i), 'What is cash?');
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent("The Copilot's model is not available.");
    expect(screen.getByLabelText(/ask squad about/i)).toHaveValue('What is cash?');
  });
});

const qa = (over: Partial<Extract<ThreadMessage, { type: 'qa' }>> = {}): Extract<ThreadMessage, { type: 'qa' }> => ({
  id: 'qa:1', ts: 't', type: 'qa', question: 'What is cash?', answer: 'Cash was {{fact:f1}}.', fact_ids: ['f1', 'f1', 'f2'],
  citations: [{ document_id: 'd1', page: 3 }], status: 'answered', run_id: 'r1', asked_by: 'Priya Raman', ...over,
});

describe('QaMessage', () => {
  it('shows the question, the answer with its sources, and how many figures code checked', () => {
    mount(<QaMessage message={qa()} borrowerCode="QFL" />);
    expect(screen.getByText('What is cash?')).toBeInTheDocument();
    expect(screen.getByTestId('body')).toHaveTextContent('Cash was {{fact:f1}}.');
    expect(screen.getByText(/checked by code: 2 stored figures/i)).toBeInTheDocument();
  });

  it('opens the cited page in the evidence drawer', async () => {
    mount(<QaMessage message={qa()} borrowerCode="QFL" />);
    await userEvent.click(screen.getByRole('button', { name: /source: page 3/i }));
    expect(calls.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 3 }));
  });

  it('shows a refusal as a refusal, with the way to the evidence', () => {
    mount(<QaMessage message={qa({ status: 'refused', answer: 'I cannot answer that from what is on file. No grounding.', fact_ids: [], citations: [] })} borrowerCode="QFL" />);
    expect(screen.getByRole('group', { name: /squad could not answer/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open the client file/i })).toHaveAttribute('href', '/borrowers/QFL');
    expect(screen.queryByText(/checked by code/i)).not.toBeInTheDocument();
  });
});

const ask = (over: Partial<Extract<ThreadMessage, { type: 'ask' }>> = {}): Extract<ThreadMessage, { type: 'ask' }> => ({
  id: 'ask:1', ts: 't', type: 'ask', work_item_id: 'w1', title: 'How should I map this line?', question: "Is 'Recurring revenue' ARR or MRR?",
  options: [{ id: 'map_to_arr', label: 'Map it to ARR', evidence: 'Page 3 says ARR.' }, { id: 'map_to_mrr', label: 'Map it to MRR', evidence: 'Page 3 also shows monthly.' }],
  status: 'open', choice: null, chosen_by: null, ...over,
});

describe('AskMessage', () => {
  it('cannot be confirmed until an option is chosen', async () => {
    mount(<AskMessage message={ask()} focused={false} />);
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    expect(confirm).toBeEnabled();
  });

  it('records the choice, says so in the presence line and remembers only when ticked', async () => {
    calls.answer.mockResolvedValue({ lesson_id: 'l1' });
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    await userEvent.click(screen.getByRole('checkbox', { name: /remember/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(calls.answer).toHaveBeenCalledWith({ option_id: 'map_to_arr', remember: true });
    expect(await screen.findByText('Recorded as Priya · remembered')).toBeInTheDocument();
  });

  it('does not remember unless asked to', async () => {
    calls.answer.mockResolvedValue({ lesson_id: null });
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to mrr/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(calls.answer).toHaveBeenCalledWith({ option_id: 'map_to_mrr', remember: false });
  });

  it('shows the engine\'s refusal and leaves the question open', async () => {
    calls.answer.mockRejectedValue(new ApiError(422, 'this item has already been decided'));
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('already been decided');
    expect(screen.getByRole('button', { name: /confirm/i })).toBeEnabled();
  });

  it('is read-only once answered, with who chose what', () => {
    mount(<AskMessage message={ask({ status: 'decided', choice: 'Map it to ARR', chosen_by: 'Priya Raman' })} focused={false} />);
    expect(screen.getByText(/Priya Raman chose Map it to ARR/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
  });

  it('is read-only for a person who cannot decide it', () => {
    mount(<AskMessage message={ask()} focused={false} />, false);
    expect(screen.getByText(/waiting for an analyst/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/questions.test.tsx`
Expected: FAIL (the stubs render nothing).

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/thread/Composer.tsx
import { useId, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAskCopilot } from '../api/hooks';
import { usePresence } from '../presence/Presence';

/** A free question, answered by the engine's Copilot under its own guarantees (spec 7). */
export function Composer({ borrowerId, borrowerName }: { borrowerId: string; borrowerName: string }) {
  const id = useId();
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const ask = useAskCopilot();
  const { beginWork, pulse } = usePresence();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = text.trim();
    if (!question) return;
    setError(null);
    const done = beginWork();
    try {
      await ask.mutateAsync({ question, borrower_id: borrowerId });
      setText('');
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      done();
    }
  }
  return (
    <form onSubmit={(e) => void submit(e)} className="sq-composer">
      <label htmlFor={id} className="sq-sr">Ask Squad about {borrowerName}</label>
      <textarea id={id} value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder={`Ask Squad about ${borrowerName}`} />
      <button type="submit" className="sq-btn sq-btn-primary" disabled={!text.trim() || ask.isPending}>Ask</button>
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
    </form>
  );
}
```

```tsx
// frontend/src/squad/thread/QaMessage.tsx
import { Link } from '@tanstack/react-router';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { clientFile } from '../links';
import { SquadMark } from '../mark/SquadMark';

export function QaMessage({ message, borrowerCode }: { message: Extract<ThreadMessage, { type: 'qa' }>; borrowerCode: string }) {
  const source = useSource();
  const checked = new Set(message.fact_ids).size;
  const refused = message.status !== 'answered';
  const open = (c: { document_id: string; page: number }) => source.open({ type: 'document', documentId: c.document_id, page: c.page, borrowerCode });
  return (
    <div className="sq-qa">
      <p className="sq-me"><b>{message.asked_by}</b> {message.question}</p>
      {refused ? (
        <div role="group" aria-label="Squad could not answer" className="sq-msg sq-card sq-refusal">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b></header>
          <p>{message.answer}</p>
          <div className="sq-actions">
            {message.citations[0] ? <button type="button" className="sq-link" onClick={() => open(message.citations[0]!)}>Show the source</button> : null}
            <Link to={clientFile(borrowerCode)} className="sq-link">Open the client file</Link>
          </div>
        </div>
      ) : (
        <div className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b></header>
          <AgentBody text={message.answer} />
          {checked > 0 ? <p className="sq-faint">Checked by code: {checked} stored {checked === 1 ? 'figure' : 'figures'}</p> : null}
          <div className="sq-actions">
            {message.citations.map((c, i) => (
              <button key={i} type="button" className="sq-link" onClick={() => open(c)}>Source: page {c.page}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/squad/thread/AskMessage.tsx
import { useId, useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { useAnswer } from '../api/hooks';
import type { ThreadMessage } from '../api/types';
import { SquadMark } from '../mark/SquadMark';
import { usePresence } from '../presence/Presence';
import { Trail } from './Trail';

type Ask = Extract<ThreadMessage, { type: 'ask' }>;

/** Squad asks: options with their evidence, one choice, an optional "Remember". The engine records it with her name. */
export function AskMessage({ message, focused }: { message: Ask; focused: boolean }) {
  const { user, can } = useAuth();
  const answer = useAnswer(message.work_item_id);
  const { say, pulse } = usePresence();
  const group = useId();
  const [choice, setChoice] = useState<string | null>(null);
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const open = message.status === 'open';
  const mayAnswer = can('decide_work_item');

  async function confirm() {
    if (!choice) return;
    setError(null);
    try {
      await answer.mutateAsync({ option_id: choice, remember });
      say(`Recorded as ${user?.name.split(' ')[0] ?? 'you'}${remember ? ' · remembered' : ''}`);
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <article className="sq-msg sq-card sq-squad" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
      <header className="sq-msghead"><SquadMark size={22} /> <b>Squad asks</b></header>
      <p>{message.question}</p>
      {open ? (
        <fieldset className="sq-options" disabled={!mayAnswer}>
          <legend className="sq-sr">{message.question}</legend>
          {message.options.map((o) => (
            <label key={o.id} className="sq-option">
              <input type="radio" name={group} value={o.id} checked={choice === o.id} onChange={() => setChoice(o.id)} />
              <span><b>{o.label}</b><br /><span className="sq-muted">{o.evidence}</span></span>
            </label>
          ))}
        </fieldset>
      ) : (
        <p><b>{message.chosen_by} chose {message.choice}</b></p>
      )}
      {open && mayAnswer ? (
        <div className="sq-actions">
          <label className="sq-check-label"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember this for next time</label>
          <button type="button" className="sq-btn sq-btn-primary" disabled={!choice || answer.isPending} onClick={() => void confirm()}>Confirm</button>
        </div>
      ) : null}
      {open && !mayAnswer ? <p className="sq-muted">Waiting for an analyst.</p> : null}
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
      <Trail workItemId={message.work_item_id} />
    </article>
  );
}
```

Append to `squad.css`:

```css
.sq-composer { position: sticky; bottom: 0; display: flex; gap: 8px; align-items: flex-end; padding: 12px 0; background: var(--sq-ground); flex-wrap: wrap; }
.sq-composer textarea { flex: 1; min-width: 220px; resize: vertical; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--sq-line); background: var(--sq-surface); color: var(--sq-ink); font: inherit; }
.sq-error { color: var(--sq-bad); width: 100%; margin: 4px 0 0; }
.sq-me { margin: 0 0 6px; color: var(--sq-ink2); }
.sq-refusal { border-color: var(--sq-warn); }
.sq-options { border: none; margin: 8px 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sq-option { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border: 1px solid var(--sq-line); border-radius: 10px; background: var(--sq-surface); cursor: pointer; }
.sq-check-label { display: inline-flex; gap: 6px; align-items: center; }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad
git commit -m "feat(squad-ui): free questions with sources and refusals, and Squad asks with remember"
```

---

### Task 13: Drafts: edit, then "Send as <user>" (recorded, not emailed)

**Files:**
- Replace the Task 11 stub: `frontend/src/squad/thread/DraftMessage.tsx`
- Modify: `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/drafts.test.tsx`

**Interfaces:**
- Consumes: `useEditDraft`, `useSendDraft`, `usePresence`, `useAuth`, `errorMessage`, the `draft` thread message.
- Produces: `DraftMessage({ message })`: header "Draft to <to>" with "drafted by Squad"; subject; a body textarea (labelled "Message"); "Save changes" appears only when the text differs from what is stored; the ink button reads "Send as <first name>" and, when the text is unsaved, saves first and sends only if the save succeeded. After sending: a "Sent" tag, read-only text, and the presence line says `Send recorded as <first name> · not emailed (no mail connector yet)`. A person without `edit_commentary` sees the draft read-only with "Only an analyst can send this."

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/drafts.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import type { ThreadMessage } from '../api/types';
import { PresenceProvider, usePresence } from '../presence/Presence';
import { DraftMessage } from '../thread/DraftMessage';

const calls = vi.hoisted(() => ({ edit: vi.fn(), send: vi.fn() }));
vi.mock('../api/hooks', () => ({
  useEditDraft: () => ({ mutateAsync: calls.edit, isPending: false }),
  useSendDraft: () => ({ mutateAsync: calls.send, isPending: false }),
}));
const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: [] };
const Say = () => <span data-testid="said">{usePresence().said}</span>;
const mount = (m: Extract<ThreadMessage, { type: 'draft' }>, can = true) =>
  render(
    <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => can, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
      <PresenceProvider needs={0}><DraftMessage message={m} /><Say /></PresenceProvider>
    </AuthContext.Provider>,
  );
const draft = (over: Partial<Extract<ThreadMessage, { type: 'draft' }>> = {}): Extract<ThreadMessage, { type: 'draft' }> => ({
  id: 'draft:d1', ts: 't', type: 'draft', draft_id: 'd1', to: 'cfo@quillfeather.example', subject: 'October MRR', body: 'Hi, could you send the October MRR?',
  kind: 'reminder', status: 'draft', created_by: 'Squad', edited_by: null, sent_by: null, sent_at: null, work_item_id: null, ...over,
});
beforeEach(() => Object.values(calls).forEach((c) => c.mockReset()));

describe('DraftMessage', () => {
  it('shows who drafted it and offers to send as the signed-in person', () => {
    mount(draft());
    expect(screen.getByText(/drafted by squad/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send as Priya' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save changes/i })).not.toBeInTheDocument();
  });

  it('offers to save only once the text has changed', async () => {
    mount(draft());
    await userEvent.type(screen.getByLabelText('Message'), ' Thanks.');
    expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument();
  });

  it('sends as the person and says it was recorded, not emailed', async () => {
    calls.send.mockResolvedValue({ status: 'sent', delivered: false });
    mount(draft());
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(calls.send).toHaveBeenCalledWith({ draft_id: 'd1' });
    expect(calls.edit).not.toHaveBeenCalled();
    expect(await screen.findByText('Send recorded as Priya · not emailed (no mail connector yet)')).toBeInTheDocument();
  });

  it('saves her edit first and sends only when the save worked', async () => {
    calls.edit.mockResolvedValue({ status: 'draft' });
    calls.send.mockResolvedValue({ status: 'sent', delivered: false });
    mount(draft());
    const box = screen.getByLabelText('Message');
    await userEvent.clear(box);
    await userEvent.type(box, 'Shorter.');
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(calls.edit).toHaveBeenCalledWith({ draft_id: 'd1', body: 'Shorter.' });
    expect(calls.send).toHaveBeenCalled();
  });

  it('does not send when the save is refused', async () => {
    calls.edit.mockRejectedValue(new ApiError(422, 'this draft has been sent and cannot be changed'));
    mount(draft());
    await userEvent.type(screen.getByLabelText('Message'), ' more');
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be changed');
    expect(calls.send).not.toHaveBeenCalled();
  });

  it('is read-only once sent, with who sent it, and cannot be sent again', () => {
    mount(draft({ status: 'sent', sent_by: 'Priya Raman', sent_at: '2026-11-20T09:00:00Z' }));
    expect(screen.getByText('Sent')).toBeInTheDocument();
    expect(screen.getByText(/sent by Priya Raman/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toHaveAttribute('readonly');
    expect(screen.queryByRole('button', { name: /send as/i })).not.toBeInTheDocument();
  });

  it('is read-only for a person who may not send', () => {
    mount(draft(), false);
    expect(screen.getByText(/only an analyst can send this/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /send as/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/drafts.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/thread/DraftMessage.tsx
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { useEditDraft, useSendDraft } from '../api/hooks';
import type { ThreadMessage } from '../api/types';
import { SquadMark } from '../mark/SquadMark';
import { usePresence } from '../presence/Presence';

type Draft = Extract<ThreadMessage, { type: 'draft' }>;

/** Squad drafts; only a person sends. "Send" records the send on the ledger; nothing is emailed in v2. */
export function DraftMessage({ message }: { message: Draft }) {
  const { user, can } = useAuth();
  const edit = useEditDraft();
  const send = useSendDraft();
  const { say, pulse } = usePresence();
  const [body, setBody] = useState(message.body);
  const [error, setError] = useState<string | null>(null);
  const sent = message.status === 'sent';
  const mayWrite = can('edit_commentary');
  const dirty = body !== message.body;
  const first = user?.name.split(' ')[0] ?? 'you';

  async function save(): Promise<boolean> {
    try {
      await edit.mutateAsync({ draft_id: message.draft_id, body });
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    }
  }
  async function sendIt() {
    setError(null);
    if (dirty && !(await save())) return;
    try {
      await send.mutateAsync({ draft_id: message.draft_id });
      say(`Send recorded as ${first} · not emailed (no mail connector yet)`);
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <article className="sq-msg sq-card sq-email">
      <header className="sq-msghead">
        <SquadMark size={22} /> <b>Draft to {message.to}</b>
        <span className="sq-faint">drafted by Squad</span>
        {sent ? <span className="sq-tag">Sent</span> : null}
      </header>
      <p className="sq-muted">Subject: {message.subject}</p>
      <label htmlFor={`draft-${message.draft_id}`} className="sq-sr">Message</label>
      <textarea id={`draft-${message.draft_id}`} aria-label="Message" value={body} readOnly={sent || !mayWrite} onChange={(e) => setBody(e.target.value)} rows={6} className="sq-paper sq-draftbox" />
      {sent ? <p className="sq-faint">Sent by {message.sent_by}. Recorded on the ledger.</p> : null}
      {!sent && mayWrite ? (
        <div className="sq-actions">
          <button type="button" className="sq-btn sq-btn-primary" disabled={!body.trim() || send.isPending || edit.isPending} onClick={() => void sendIt()}>
            Send as {first}
          </button>
          {dirty ? <button type="button" className="sq-btn" disabled={edit.isPending} onClick={() => void save().then((ok) => ok && say('Draft saved'))}>Save changes</button> : null}
        </div>
      ) : null}
      {!sent && !mayWrite ? <p className="sq-muted">Only an analyst can send this.</p> : null}
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
    </article>
  );
}
```

Note: `aria-label="Message"` is used (not only the sr-only label) so `getByLabelText('Message')` resolves once; remove the `<label>` element if the test reports two matches.

Append to `squad.css`:

```css
.sq-draftbox { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--sq-line); font: inherit; font-family: Georgia, 'Newsreader', serif; resize: vertical; }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run src/squad && pnpm vitest run && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/squad
git commit -m "feat(squad-ui): drafts that only a person sends, recorded and never claimed as delivered"
```

---

### Task 14: The evidence drawer: pushes content, resizable, in the look

**Files:**
- Create: `frontend/src/squad/evidence/EvidenceResizer.tsx`
- Modify: `frontend/src/squad/looks.ts` (the legacy-token bridge in `applyLook`), `frontend/src/squad/shell/SquadShell.tsx` (render the resizer), `frontend/src/squad/squad.css`
- Test: `frontend/src/squad/__tests__/evidence.test.tsx`

**Interfaces:**
- Consumes: `useSource` (its `current` says whether the drawer is open), `applyLook`, `LOOKS`.
- Produces: `clampWidth(px: number, viewport: number): number` (360 at least, at most the smaller of 760 and 60 percent of the viewport); `EvidenceResizer()`: renders only while a source is open, a `role="separator"` `aria-orientation="vertical"` `aria-valuenow` handle fixed at the drawer's left edge (`right: var(--source-w)`), dragged with the pointer or moved with ArrowLeft/ArrowRight (24 px), Home (widest) and End (narrowest); sets `--source-w` on the root and remembers it in `localStorage["squad.source.w"]` (try/catch). `applyLook` now also sets the legacy variables the reused drawer reads: `--canvas`, `--surface`, `--surface-sunken`, `--surface-hover`, `--ink-900`, `--ink-700`, `--ink-500`, `--hairline`, `--hairline-strong`, `--iris`, `--red`, `--amber`, `--green`, so `SourceDrawer`, `AgentBody` and the interim cockpit screens follow the active look. The CSS pushes the stage aside from 1000 px (the old rule only did from 1200 px).

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/evidence.test.tsx
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import css from '../squad.css?raw';
import { applyLook, contrast, LOOKS, LOOK_IDS } from '../looks';
import { clampWidth, EvidenceResizer } from '../evidence/EvidenceResizer';

const source = vi.hoisted(() => ({ current: null as unknown }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: () => {}, close: () => {}, current: source.current }) }));

describe('clampWidth', () => {
  it('keeps the drawer between 360 px and the smaller of 760 px and 60 percent of the window', () => {
    expect(clampWidth(100, 1400)).toBe(360);
    expect(clampWidth(2000, 1400)).toBe(760);
    expect(clampWidth(2000, 1000)).toBe(600);
    expect(clampWidth(500, 1400)).toBe(500);
  });
});

describe('EvidenceResizer', () => {
  beforeEach(() => {
    source.current = null;
    document.documentElement.style.removeProperty('--source-w');
    localStorage.clear();
  });

  it('is absent while no evidence is open', () => {
    render(<EvidenceResizer />);
    expect(screen.queryByRole('separator')).not.toBeInTheDocument();
  });

  it('moves the edge with the arrow keys and remembers the width', async () => {
    source.current = { type: 'fact', id: 'f1' };
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1400 });
    render(<EvidenceResizer />);
    const handle = screen.getByRole('separator', { name: /resize the evidence/i });
    handle.focus();
    const before = Number(handle.getAttribute('aria-valuenow'));
    await userEvent.keyboard('{ArrowLeft}');
    expect(Number(handle.getAttribute('aria-valuenow'))).toBe(before + 24);
    expect(document.documentElement.style.getPropertyValue('--source-w')).toBe(`${before + 24}px`);
    expect(localStorage.getItem('squad.source.w')).toBe(String(before + 24));
    await userEvent.keyboard('{End}');
    expect(handle.getAttribute('aria-valuenow')).toBe('360');
  });

  it('never goes below the minimum however far it is dragged', () => {
    source.current = { type: 'fact', id: 'f1' };
    render(<EvidenceResizer />);
    const handle = screen.getByRole('separator');
    act(() => {
      handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 800 }));
      window.dispatchEvent(new PointerEvent('pointermove', { clientX: 5000 }));
      window.dispatchEvent(new PointerEvent('pointerup'));
    });
    expect(Number(handle.getAttribute('aria-valuenow'))).toBeGreaterThanOrEqual(360);
  });
});

describe('the evidence drawer follows the look', () => {
  it.each(LOOK_IDS)('%s: the reused drawer reads the look\'s own surface and ink', (id) => {
    applyLook(id);
    const root = document.documentElement.style;
    expect(root.getPropertyValue('--surface')).toBe(LOOKS[id].vars.surface);
    expect(root.getPropertyValue('--ink-900')).toBe(LOOKS[id].vars.ink);
    expect(contrast(LOOKS[id].vars.ink2, LOOKS[id].vars.surface)).toBeGreaterThanOrEqual(4.5);
  });

  it('pushes the conversation aside from 1000 px, not only from 1200 px', () => {
    expect(css).toMatch(/@media \(min-width: 1000px\)\s*\{\s*html\[data-source-open\] \.sq-stage/);
  });

  it('keeps evidence documents on paper in every look', () => {
    expect(css).toMatch(/\[data-source-drawer\] canvas[^{]*\{[^}]*background:\s*var\(--sq-paper\)/);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/squad/__tests__/evidence.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/squad/evidence/EvidenceResizer.tsx
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSource } from '@/source/context';

const MIN = 360;
const MAX = 760;
const STEP = 24;
const KEY = 'squad.source.w';

export function clampWidth(px: number, viewport: number): number {
  return Math.round(Math.max(MIN, Math.min(px, MAX, viewport * 0.6)));
}

function initialWidth(): number {
  try {
    const stored = Number(localStorage.getItem(KEY));
    if (stored > 0) return clampWidth(stored, window.innerWidth);
  } catch {
    /* ignore */
  }
  const fromCss = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--source-w'), 10);
  return clampWidth(Number.isFinite(fromCss) ? fromCss : 590, window.innerWidth);
}

/** A handle on the evidence drawer's left edge. The drawer itself is the reused SourceDrawer; this only sets its width. */
export function EvidenceResizer() {
  const { current } = useSource();
  const [width, setWidth] = useState(initialWidth);
  const dragging = useRef(false);

  const apply = useCallback((px: number) => {
    const next = clampWidth(px, window.innerWidth);
    setWidth(next);
    document.documentElement.style.setProperty('--source-w', `${next}px`);
    try {
      localStorage.setItem(KEY, String(next));
    } catch {
      /* not remembered */
    }
  }, []);

  useEffect(() => {
    if (current) document.documentElement.style.setProperty('--source-w', `${width}px`);
  }, [current, width]);

  useEffect(() => {
    const move = (event: PointerEvent) => dragging.current && apply(window.innerWidth - event.clientX);
    const up = () => {
      dragging.current = false;
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
  }, [apply]);

  if (!current) return null;
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the evidence"
      aria-valuemin={MIN}
      aria-valuemax={Math.min(MAX, Math.round(window.innerWidth * 0.6))}
      aria-valuenow={width}
      tabIndex={0}
      className="sq-resizer"
      style={{ right: `${width}px` }}
      onPointerDown={() => {
        dragging.current = true;
      }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowLeft') apply(width + STEP);
        else if (e.key === 'ArrowRight') apply(width - STEP);
        else if (e.key === 'Home') apply(MAX);
        else if (e.key === 'End') apply(MIN);
        else return;
        e.preventDefault();
      }}
    />
  );
}
```

In `looks.ts`, extend `applyLook` (after the `--sq-*` loop):

```ts
  // The reused source drawer, AgentBody and the interim cockpit screens read the older token names.
  const v = LOOKS[id].vars;
  const legacy: Record<string, string> = {
    '--canvas': v.ground, '--surface': v.surface, '--surface-sunken': v.sunk, '--surface-hover': v.sunk,
    '--ink-900': v.ink, '--ink-700': v.ink2, '--ink-500': v.ink2, '--hairline': v.line, '--hairline-strong': v.line,
    '--iris': v.squad, '--red': v.bad, '--amber': v.warn, '--green': v.ok,
  };
  for (const [name, value] of Object.entries(legacy)) root.style.setProperty(name, value);
```

In `SquadShell.tsx` render `<EvidenceResizer />` inside `Frame`'s root div (after the stage). Append to `squad.css` (and inside the existing single reduced-motion block add nothing here):

```css
.sq-resizer { position: fixed; top: 0; bottom: 0; width: 8px; margin-right: -4px; cursor: col-resize; z-index: 45; background: transparent; }
.sq-resizer:hover, .sq-resizer:focus-visible { background: var(--sq-squad-line); outline: none; }
@media (min-width: 1000px) {
  html[data-source-open] .sq-stage { padding-right: var(--source-w); }
}
@media (max-width: 999px) {
  .sq-resizer { display: none; }
}
[data-source-drawer] canvas, [data-source-drawer] .pdf-page { background: var(--sq-paper); }
```

(The existing `styles.css` rule `html[data-source-open] div:has(> #main)` still pads from 1200 px; both rules target the same wrapper's padding and agree, so there is no double padding because `.sq-stage` is the element that contains `#main` and the old rule's selector (`div:has(> #main)`) matches the element whose direct child is `#main`, which in `SquadShell` is `.sq-stage`. Set the same property, so the larger specificity wins and the result is one `padding-right`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm vitest run && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(squad-ui): evidence drawer that pushes the conversation aside, resizable, following the look"
```

---

### Task 15: End-to-end journeys for every way into a client, contrast and widths

**Files:**
- Create: `frontend/e2e/squad.mjs`
- Modify: `frontend/package.json` (add `"e2e:squad": "node e2e/squad.mjs"`)

**Interfaces:**
- Consumes: the running seeded stack (API on 8000, workspace on 5173; `BASE_URL`, `SQUAD_DEMO_PASSWORD` as in `e2e/run.mjs`), `uv run python -m app.squad_demo` run once beforehand (it prints `{question_borrower_code, draft_borrower_code, work_item_id, draft_id}`), Playwright (global) and `axe-core`.
- Produces: `pnpm e2e:squad`, exit code 1 on the first failed journey with a screenshot in `frontend/e2e/failures/`. What a run changes: it answers the demo question (once; a second run finds it decided and skips that step), records one `draft.sent`, and may write one lesson. Reseed (`uv run python -m app.squad_demo` after a fresh seed) to repeat.

This is a script, so the "failing test" is the journey run before the UI exists; each journey asserts the **rendered state against the record read through the API**, never against the step number (lesson: test every entry route).

- [ ] **Step 1: Write the journeys**

```js
// frontend/e2e/squad.mjs
// Journeys for the Squad experience (docs/specs/2026-11-20-squad-experience-design.md section 14).
// Usage: pnpm e2e:squad     (BASE_URL=http://localhost:5173; HEADED=1 to watch)
// Run `uv run python -m app.squad_demo` once on a freshly seeded book first.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const BASE = process.env.BASE_URL ?? 'http://localhost:5173';
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const ANALYST = 'priya.raman@bankofstoic.example';
const OFFICER = 'helen.strand@bankofstoic.example';
const LOOKS = ['Night', 'Warm paper', 'Cool slate', 'Lavender mist', 'Sage'];
const WIDTHS = [1000, 1280, 1440, 1920];
const failuresDir = resolve(dirname(fileURLToPath(import.meta.url)), 'failures');

const assert = (ok, message) => {
  if (!ok) throw new Error(message);
};

async function signIn(page, email) {
  await page.goto(`${BASE}/sign-in`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(`${BASE}/`);
}

const api = (page, path, init) => page.request.fetch(`${BASE}/api/v1${path}`, init).then((r) => r.json());

/** What the record says needs this person, read through the same API the page reads. */
async function record(page) {
  const b = await api(page, '/me/briefing');
  return { b, needs: b.items.filter((i) => i.needs_you), clients: b.open_clients };
}

const journeys = [];
const journey = (name, fn) => journeys.push({ name, fn });

journey('home: the count equals the items listed, and each item opens its own client at its case', async ({ page }) => {
  await signIn(page, ANALYST);
  const { b, needs } = await record(page);
  const sentence = needs.length ? (needs.length === 1 ? '1 needs you' : `${needs.length} need you`) : 'Nothing needs you.';
  await page.getByText(sentence, { exact: true }).waitFor();
  assert((await page.getByRole('list', { name: 'Needs you' }).getByRole('listitem').count()) === needs.length, 'listed items differ from the count');
  assert(needs.length > 0, 'the seeded book should leave the analyst something to do (run app.squad_demo)');
  for (const item of needs) {
    await page.goto(`${BASE}/`);
    await page.getByRole('link', { name: new RegExp(`${item.borrower_name}: ${item.title}`) }).first().click();
    await page.waitForURL(new RegExp(`/clients/${item.borrower_code}`));
    await page.getByRole('heading', { level: 1, name: item.borrower_name }).waitFor();
    if (item.work_item_id) {
      const card = page.locator(`[data-work-item="${item.work_item_id}"][data-focused="true"]`);
      await card.waitFor();
      // no other client's name appears as a message heading on this thread
      const others = b.items.filter((i) => i.borrower_code !== item.borrower_code).map((i) => i.borrower_name);
      const text = await page.locator('.sq-messages').innerText();
      for (const name of others) assert(!text.includes(name), `another client's case (${name}) is on ${item.borrower_name}'s thread`);
    }
  }
});

journey('nav: "Open cases" lists exactly the clients with something open, and each lands in its thread', async ({ page }) => {
  await signIn(page, ANALYST);
  const { clients } = await record(page);
  await page.getByRole('button', { name: /expand navigation/i }).click();
  const links = page.getByRole('navigation', { name: 'Open cases' }).getByRole('link');
  assert((await links.count()) === clients.length, 'Open cases differs from the clients with open work');
  for (const c of clients) {
    await page.getByRole('navigation', { name: 'Open cases' }).getByRole('link', { name: new RegExp(c.name) }).click();
    await page.waitForURL(new RegExp(`/clients/${c.code}$`));
    await page.getByRole('heading', { level: 1, name: c.name }).waitFor();
  }
});

journey('palette: Ctrl K reaches any client by name, from any screen', async ({ page }) => {
  await signIn(page, ANALYST);
  const [first] = (await api(page, '/borrowers')).slice(0, 1);
  await page.keyboard.press('Control+K');
  await page.getByRole('combobox').fill(first.name.split(',')[0].slice(0, 8));
  await page.getByRole('option', { name: new RegExp(first.name.slice(0, 8)) }).first().click();
  await page.waitForURL(new RegExp(`/clients/${first.code}$`));
});

journey('portfolio: the nav row opens My Portfolio and a row opens that client', async ({ page }) => {
  await signIn(page, ANALYST);
  await page.getByRole('link', { name: /my portfolio/i }).click();
  await page.waitForURL(`${BASE}/portfolio`);
  // Phase 4b redesigns the screen; here we only require the route to load without an error alert.
  assert((await page.getByRole('alert').count()) === 0, 'portfolio route shows an error');
});

journey('deep link: an unknown case id shows the thread, not an error', async ({ page }) => {
  await signIn(page, ANALYST);
  const [first] = await api(page, '/borrowers');
  await page.goto(`${BASE}/clients/${first.code}?case=00000000-0000-0000-0000-000000000000`);
  await page.getByRole('heading', { level: 1, name: first.name }).waitFor();
  assert((await page.getByRole('alert').count()) === 0, 'unknown case id raised an alert');
  assert((await page.locator('[data-focused]').count()) === 0, 'an unknown case id focused something');
});

journey('deep link: an unknown client says so and offers the way home', async ({ page }) => {
  await signIn(page, ANALYST);
  await page.goto(`${BASE}/clients/NOPE`);
  await page.getByRole('alert').getByText(/no client with that code/i).waitFor();
  await page.getByRole('link', { name: /back to squad/i }).click();
  await page.waitForURL(`${BASE}/`);
});

journey('Squad asks: answering with Remember writes the choice with her name, one lesson, and the badge falls', async ({ page }) => {
  await signIn(page, ANALYST);
  const asks = (await api(page, '/work-items?item_type=question')).filter((i) => i.status === 'open');
  if (asks.length === 0) return console.log('  (no open question: already answered on an earlier run; skipping)');
  const ask = asks[0];
  const before = (await record(page)).needs.length;
  await page.goto(`${BASE}/clients/${(await api(page, `/borrowers/${ask.borrower_id}`)).code}?case=${ask.id}`);
  const card = page.locator(`[data-work-item="${ask.id}"]`);
  await card.getByRole('radio').first().check();
  await card.getByRole('checkbox', { name: /remember/i }).check();
  await card.getByRole('button', { name: /confirm/i }).click();
  await page.getByRole('status').filter({ hasText: /Recorded as Priya · remembered/ }).waitFor();
  const decided = await api(page, `/work-items/${ask.id}`);
  assert(decided.status === 'decided' && decided.decided_by, 'the answer was not recorded with a person');
  const lessons = await api(page, '/ledger?action=lesson.recorded&limit=50');
  assert(lessons.some((e) => e.payload.work_item_id === ask.id), 'Remember wrote no lesson');
  await page.waitForFunction(() => !document.body.innerText.includes('How should I map this line?') || !document.querySelector('input[type=radio]'));
  assert((await record(page)).needs.length === before - 1, 'the needs-you count did not fall by one');
});

journey('drafts: edit then Send as Priya records the send and claims no delivery', async ({ page }) => {
  await signIn(page, ANALYST);
  const [row] = (await api(page, '/ledger?action=draft.created&limit=20')).filter((e) => e.payload.kind === 'demo_reminder');
  if (!row) return console.log('  (no demo draft; run app.squad_demo)');
  const draftId = row.entity_id;
  const folded = await api(page, `/threads/${row.payload.borrower_id}`);
  const draft = folded.messages.find((m) => m.type === 'draft' && m.draft_id === draftId);
  if (draft.status === 'sent') return console.log('  (draft already sent on an earlier run; skipping)');
  await page.goto(`${BASE}/clients/${folded.borrower.code}`);
  await page.getByLabel('Message').fill('Hi, October MRR please. Thanks.');
  await page.getByRole('button', { name: 'Send as Priya' }).click();
  await page.getByRole('status').filter({ hasText: /Send recorded as Priya · not emailed/ }).waitFor();
  const sent = (await api(page, `/ledger?entity_id=${draftId}&limit=10`)).find((e) => e.action === 'draft.sent');
  assert(sent && sent.payload.delivery === 'recorded_only' && sent.actor_type === 'user', 'draft.sent was not recorded as a person, recording only');
  assert((await page.getByRole('button', { name: /send as/i }).count()) === 0, 'a sent draft can be sent again');
});

journey('evidence: a document opens beside the thread and pushes it aside, at every width', async ({ browser }) => {
  for (const width of WIDTHS) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    await signIn(page, ANALYST);
    const withDoc = (await api(page, '/borrowers')).find(Boolean);
    const docs = await api(page, `/borrowers/${withDoc.id}/documents`);
    if (docs.length) {
      await page.goto(`${BASE}/clients/${withDoc.code}`);
      const before = (await page.locator('.sq-main').boundingBox()).width;
      await page.getByRole('button', { name: new RegExp(`^Open ${docs[0].title}`) }).first().click();
      await page.locator('[data-source-drawer]').waitFor();
      const after = (await page.locator('.sq-main').boundingBox()).width;
      assert(after <= before, `the drawer did not push the thread aside at ${width}px`);
    }
    assert((await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)), `horizontal page scroll at ${width}px`);
    await context.close();
  }
});

journey('looks: every look keeps text readable and the officer starts in Warm paper', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await signIn(page, OFFICER);
  assert((await page.evaluate(() => document.documentElement.dataset.look)) === 'warm', 'the officer did not start in Warm paper');
  await context.close();
  const analyst = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await analyst.newPage();
  await signIn(p, ANALYST);
  assert((await p.evaluate(() => document.documentElement.dataset.look)) === 'night', 'the analyst did not start in Night');
  for (const look of LOOKS) {
    await p.getByRole('button', { name: /^look:/i }).click();
    await p.getByRole('menuitemradio', { name: look }).click();
    await p.addScriptTag({ content: axeSource });
    const result = await p.evaluate(() => window.axe.run(document.body, { runOnly: ['color-contrast', 'label', 'button-name', 'link-name'] }));
    const bad = result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
    assert(bad.length === 0, `${look}: accessibility violations: ${bad.join(', ')}`);
  }
  await analyst.close();
});

journey('motion: with reduced motion the mark does not move', async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await context.newPage();
  await signIn(page, ANALYST);
  const names = await page.evaluate(() => [...document.querySelectorAll('.sq-mk *')].map((el) => getComputedStyle(el).animationName));
  assert(names.every((n) => n === 'none'), `animation still running under reduced motion: ${names.join(',')}`);
  await context.close();
});

journey('the officer sees only what she can act on, and the count agrees', async ({ page }) => {
  await signIn(page, OFFICER);
  const { needs } = await record(page);
  const sentence = needs.length ? (needs.length === 1 ? '1 needs you' : `${needs.length} need you`) : 'Nothing needs you.';
  await page.getByText(sentence, { exact: true }).waitFor();
});

mkdirSync(failuresDir, { recursive: true });
const browser = await chromium.launch({ headless: !process.env.HEADED });
let failed = 0;
for (const { name, fn } of journeys) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  try {
    await fn({ page, browser });
    console.log(`PASS  ${name}`);
  } catch (error) {
    failed += 1;
    console.error(`FAIL  ${name}\n      ${error.message}`);
    await page.screenshot({ path: resolve(failuresDir, `${name.replace(/\W+/g, '-').slice(0, 60)}.png`) }).catch(() => {});
  }
  await context.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
```

- [ ] **Step 2: Run the journeys against the stack before they can pass**

Start the stack (`service postgresql start`; API on 8000; `pnpm dev` on 5173), seed the book, then `uv run python -m app.squad_demo`. Run `pnpm e2e:squad` from `frontend/` with only Tasks 1 to 8 merged.
Expected: FAIL at the home journey (placeholder home), proving the journeys detect a missing feature.

- [ ] **Step 3: Fix what the journeys find**

With Tasks 9 to 14 in place, run again. Every failure is a real defect in a component or endpoint: fix it in the owning task's files and add a unit test for it there. Known places the script depends on: the `Open <title>` button name (Task 11), `data-work-item` / `data-focused` (Tasks 11, 12), the status line texts (Tasks 12, 13), `.sq-main` and `.sq-messages` (Tasks 8, 11), the look button name `Look: <name>` (Task 6).

- [ ] **Step 4: Run the full verification**

Run: `uv run pytest -q` (repo root), then from `frontend/`: `pnpm test && pnpm typecheck && pnpm lint && pnpm build && pnpm e2e:squad`
Expected: all green; the journeys print `PASS` lines for every journey.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/squad.mjs frontend/package.json
git commit -m "test(squad-ui): journeys for every entry route, contrast in every look, widths 1000 to 1920"
```

---

## Phase 4b outline (to be expanded into its own plan once 4a is merged)

Write `docs/plans/2026-11-2x-phase-4b-squad-approvals-and-client-file.md` with the same header, Global Constraints and Review Focus. Tasks to cover, in this order:

1. **Hand-off with the analyst's view and the officer's approval screen.** Backend: `POST /work-items/{id}/assign` (or a new `POST /work-items/{id}/route`) takes a required `view` text recorded in the `work_item.assigned` payload and surfaced in the thread's `handoff` message; `GET /me/approvals` for the officer (the case, the evidence, the analyst's view). Front end: `ApprovalsScreen` for credit officers (Warm paper), reason box required (button disabled and server-side `needs_reason` honoured), approve / reserve rights / return; a **return** brings the case back into the same client thread with her reason, Squad gathers what was asked (attached as evidence on the case), the analyst sends it back, the officer decides again. The four-eyes rule stays the engine's (`SecondPersonRequired` is shown, never pre-empted).
2. **Client file: redesigned detail views** (owner decision 2): spread beside its source page (the evidence drawer pushes), covenants (with RML and runway for `vc-1`), documents, funding events (`GET /borrowers/{id}/funding-events`), history (the ledger for the client). Retarget `src/squad/links.ts` to the new routes, redirect the old `/borrowers/$code/…` addresses.
3. **My Portfolio:** all clients with trend, RML for `vc-1` borrowers and headroom for `ci-1`; a row opens the client's thread (portfolio entry point); track records from `GET /borrowers/{id}/track-record` shown per client and task, and remembered habits (lessons) shown where they are used.
4. **Oversight (admin, credit review):** agent activity, ledger, governance, evaluation results in Squad's looks; admins take no credit decisions (screens offer none).
5. **Retire the cockpit:** delete `AppShell`, `Rail`, `CommandCentre`, `WorkspaceDrawer`, the cockpit borrower screens and their tests; remove the legacy-token bridge only if nothing reads those names; update `README.md`, `docs/HANDOFF.md`, `frontend/DESIGN.md`.
6. **Polish and the full e2e:** every entry point of **every** client in the seeded book (all 25 or more, C&I and innovation) walked end to end in both roles (a data-driven journey generated from `GET /borrowers`), contrast scan on every screen in all five looks, widths 1000 to 1920 on every screen, the eval gate green, a manual pass on the owner's screen (lesson: look at it on the owner's screen), then the release.

---

## Self-review

**Spec coverage (sections 3 to 14).**
- 3 Structure: Squad home (Task 10), client threads (11), My Portfolio and Approvals, Client file, Oversight (4b outline items 1 to 4), evidence drawer (14), nav and looks and palette (6, 8). The nav's My Portfolio and Oversight links point at the interim cockpit routes in 4a (stated at the top).
- 4 Presence: mark, four states, reduced motion, the "Credit Squad" label and the reserved confirmation line (7); confirmations in it (12, 13).
- 5 Briefing: Task 2 and 10 (open items by role and assignment, overdue reporting, signals, funding due, overnight, ordered by consequence, state in words, opens the thread at the case).
- 6 Threads and polling: Tasks 1, 9, 11, 12, 13 (every message type of the table: report, work trail, asks, document arrived/held, draft, decision/handoff, Q&A). Approval/return with reason is the 4b `decision` rendering beyond what 4a shows.
- 7 Free questions: Task 12 (Copilot, sources, checked figures, refusal offers evidence or client file).
- 8 Squad asks: Tasks 3 and 12. 9 Drafts: Tasks 4 and 13. 10 Approvals: 4b item 1. 11 Teach once and track records: lesson via remember (3), track-record read model (5), UI in 4b item 3. 12 Backend list: all seven items present (`/me/briefing` T2; `/threads`, `/ledger?after_seq` T1; `/cases/{id}/trail` T5; question + answer T3; drafts T4; `POST /lessons` already exists and is reached through remember in T3; track record T5). 13 Visual rules: T6, 7, 14 (ink primary buttons, ember for needs-you only, lavender for Squad, paper evidence, drawer pushes, 3:1 held at 4.5:1). 14 Testing: unit and component tests in every task; e2e journeys and contrast scan in T15 for the entry points that exist in 4a (home item, nav, palette, deep link, Squad asks, drafts) and the portfolio row/officer screens in 4b.

**Placeholder scan.** No "TBD". Intentional stubs: Task 8's temporary home and thread components and Task 11's four one-line modules are replaced in Tasks 10, 12 and 13 and are named as such. The e2e script contains no unfinished branches (the two "skip" lines handle a repeat run on an already-used database, by design).

**Type consistency checked.** `ThreadMessage` field names in Task 8's types match the server's message shapes in Task 1 (`work_item_id`, `document_id`, `draft_id`, `chosen_by`, `asked_by`, `fact_ids`, `citations`). `useAnswer` sends `{ option_id, remember }` (server `AnswerIn`). `threadHref`/`clientFile` names are the same in Tasks 8, 10, 11, 12. `usePresence` members (`say`, `beginWork`, `pulse`, `said`, `state`) match their uses in Tasks 12 and 13. `drafts_for`/`create_draft` names match between Tasks 4, 5 and the demo seed. `Look` token names (`onEmber` added in Task 6) match the CSS variable names (`--sq-on-ember` from `onEmber` via `cssName`).

**Risks the executor must check once** (not guessed): (a) that `python -m app.squad_demo` finds the database settings the way `app/cli.py` does; (b) the exact accessible name of the palette input and options in `CommandPalette` for the Task 15 palette journey (read `src/design/CommandPalette.tsx` and adjust the two selectors); (c) that `work-items?item_type=question` returns `borrower_id` (it does: `_item` serialises all columns) and that `GET /borrowers/{id}` returns `code`; (d) `pnpm e2e:squad` needs the globally installed Playwright, as `pnpm e2e` does.

**Rulings where the spec was silent**, repeated in the final report: question work items reuse `decide_work_item` (no new table); drafts are ledger events (no migration); thread `case` cards exist for non-question work items; copilot exchanges appear in a client's thread only when scoped to that client; "decided" items stay in the briefing for two days as non-counting lines; the default look is Warm paper for `credit_officer` only and Night for every other role; text contrast is held at 4.5:1 although the spec's floor is 3:1; the nav starts collapsed for everyone; "Send" says it recorded and did not email (no connector) instead of the demo's "Email sent"; the legacy-token bridge re-themes the reused source drawer and the interim cockpit screens; the ledger heartbeat refreshes the briefing and open threads together (one cursor) rather than one poll per thread.

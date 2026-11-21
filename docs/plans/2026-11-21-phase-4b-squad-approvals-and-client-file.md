# Phase 4b: Credit Squad — Approvals, Client File, Portfolio, Oversight, Cockpit Retired — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish Credit Squad on this branch: an analyst routes a case with her view and the credit officer decides, reserves rights or returns it in the same client thread; a redesigned client file, My Portfolio and Oversight replace the cockpit screens; the cockpit is deleted; every client is walked end to end in both roles, and the branch is merge-ready.

**Architecture:** The hand-off rules (who may receive a case, who may return it, the router becomes the preparer so the engine's two-person rule keeps her from deciding it) are a new engine module, `backend/app/domain/routing.py`, beside `decide_work_item`; Squad's read models stay under `backend/app/squad/` (`cases.py`, `client_file.py`, `portfolio.py`) behind `backend/app/api/routes_squad.py`, and every "may" they return is the engine's rule read for the viewer. No migration: routing uses the existing `work_items` columns and new ledger actions. The front end adds `src/squad/case/`, `approvals/`, `clientfile/`, `portfolio/`, `oversight/` and retargets `src/squad/links.ts`; Task 5 then deletes the cockpit (`src/shell/`, `src/drawer/`, the cockpit screens) after moving the few parts Squad still uses.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, pytest (`uv run pytest`); React 19, Vite, TypeScript, TanStack Router and Query, vitest + Testing Library; the globally installed Playwright (as `frontend/e2e/squad.mjs` already uses it) with axe-core.

**Spec:** `docs/specs/2026-11-20-squad-experience-design.md` (sections 3, 5, 6, 10, 11, 13, 14; section 15 owner decisions apply), and `docs/specs/2026-11-18-cockpit-design.md` for the design rules the Squad spec defers to (figures, provenance glyphs, colour meaning, tags). Phase 4a plan (interfaces reused here): `docs/plans/2026-11-20-phase-4-squad-experience.md`. First-look findings folded in: `docs/product/v2-first-look-findings.md` with `docs/product/screens/*.png`.

## Decisions taken at the top of this plan

- **Scope is the 4a plan's "Phase 4b outline", in its order**, with the first-look findings placed in the task that owns the code (table below). "Release" in Task 6 means merge-ready on `slice-1/monitoring-cycle`; hosting is Phase 5.
- **A route is not an assignment.** `POST /work-items/{id}/assign` (owner and due date, `work_item.assigned`) stays as it is. Routing is a new engine action, `work_item.routed`, which needs the router's view, assigns the case to a person who may decide it and makes the router its preparer (`prepared_by_id`, `requires_second_person`). `decide_work_item` then refuses her with `SecondPersonRequired` (409) exactly as it does today; no screen decides this.
- **A return is not a decision.** `work_item.returned` sends the open case back to the person who routed it, with a reason; the case stays open; the officer decides only after it is routed again. Decisions remain the item's own allowed decisions (for a breach: waiver requested, reservation of rights, escalate to committee, not a breach). The spec's "approve / reserve rights / return" maps to those decisions plus Return.
- **"Squad gathers what was asked" means code gathers, a person attaches.** The case view lists the client's documents not yet attached, newest first; the analyst attaches one (`work_item.evidence_attached`) or drafts a request to the client with the 4a drafts. Nothing is attached without a person (lesson: the model must not choose its evidence).
- **Signals are listed, not counted** (finding 5). A signal that needs a decision already has a work item (`signal.high`, raised by the engine), and that item counts. The briefing lists the rest under "Watching", one row per client naming every open signal.
- **Retiring the cockpit keeps every repair path.** `HeldFigures`, `KeyFigures`, `UploadDocument`, `RunStage` and the commentary editor move into `src/squad/`; only screens whose job a Squad screen now does are deleted. Packages, the review room and the calendar have no place in the Squad spec's structure (section 3); they are deleted with the cockpit and stay in v1 (git 2292b38). This is owner question 1 below; Task 5 has an explicit branch if the owner says keep.
- **No migration, no billable run.** Nothing in this plan calls a model. The eval gate in Task 6 is the stand-in run and the recorded replay (no model call).

**Findings and carry items, and where each goes**

| Item | Where |
|---|---|
| "Needs your call" not role-aware in threads (asks still enabled by role alone) | Task 1 (asks carry the server's `needs_you` and state words) |
| Thread opens on old documents; group arrivals | Task 2 (`opening_id`, `arrivals` message) |
| Wording: "Mrr report", document types in plain words, "bank statement" vs "Account statement" | Task 2 (`document_type_words`, used by thread, briefing and client file) |
| Briefing too busy ("16 need you"); signals counted; group by client | Task 3 |
| Nav shows 20 initial-letter circles when collapsed | Task 3 |
| Bugs 1–3 of the findings | Already fixed (ad4e591, 0f49333, 7a2d71c); Task 6's journeys re-check 2 and 3 |
| Agents do not read figures from spreadsheets | **Out of scope.** A new reading capability for an agent (prompt, guardrail for cell citations, recordings), not part of the Squad experience; Squad already shows Stripple's held sheet with its one question. Owner question 2 |
| Kestrel Bay `total_leverage` covenant investigation ends in abstain (wrong-abstain 1, not gated) | **Out of scope.** Covenant Agent behaviour; any fix can only be shown by a new record pass, which is billable. Owner question 3 |
| Pellham re-recorded covenant narrative cites a year and a version the run's references lack (`backend/tests/guardrails/test_structure.py` pins the refusal) | **Out of scope.** The product refuses it correctly; a fix belongs in the references builder or the prompt and needs a re-record to show. Owner question 3 |

**Shared files this phase touches outside `squad/`** (each edit small and named in its task): `backend/app/squad/*` from 4a; `backend/app/api/routes_squad.py`; `frontend/src/router.tsx`; `frontend/src/source/SourceDrawer.tsx` (one link); `frontend/src/__tests__/workspace.test.tsx` (one import); `frontend/package.json` (scripts); `frontend/scripts/serve.mjs`; `README.md`, `docs/HANDOFF.md`, `frontend/DESIGN.md`.

## Global Constraints

- The model never types a number: agent text carries `{{fact:<id>}}` and is rendered by `AgentBody`; every figure on a screen is a stored fact (`FactFigure`) or a stored record field (`SourcedFigure` with a `record` source). Titles written by code that contain figures are not re-parsed by the front end.
- `backend/app/calc/` and `backend/app/guardrails/` are not touched and are not imported by anything new except through existing domain functions (`metrics_service.runway_not_meaningful`).
- The ledger is append-only. Every new write (`work_item.routed`, `work_item.returned`, `work_item.evidence_attached`) is one `ledger.record` call; nothing updates or deletes a ledger row.
- The two-person rule and permissions are the engine's (`core/roles.py`, `domain/workflow.py`, `domain/routing.py`). Squad read models return what the engine allows (`may_route`, `may_return`, `may_attach`, `decisions[].permitted`, `decisions[].needs_reason`); screens show the server's refusal in its own words (403, 409, 422) and never pre-empt it.
- A missing input is an error, never zero; an unmeasured figure is shown as "Not measured" (or the stored "not meaningful" wording), never as 0 or as a bar at zero.
- Synthetic data only; lender Bank of Stoic; no real bank or product names anywhere, including test strings and copy.
- No live model run. Tests use recorded responses only; if a step would need a model, stop and ask the owner.
- Front-end design rules (CLAUDE.md, cockpit spec): one typeface (Inter), JetBrains Mono only for identifiers, tabular numerals for figures; colour carries meaning only (red breach or critical, amber needs attention or high, green verified pass or recorded resolution, lavender/iris for Squad and agent-written work, ember only for needs-you, ink primary buttons); provenance is a glyph; capsule tags only for severity and actionable status; bars show plot positions only and every number beside them comes from the API; no coloured side stripes on cards, at most two shadow steps, no animation over 240 ms; "Recommends resolve", never "Resolved"; never "AI thinks".
- Looks: Night (analyst default), Warm paper (credit officer default), Cool slate, Lavender mist, Sage; text at least 4.5:1 and non-text marks at least 3:1 in every look; evidence documents always on `--sq-paper`; confirmations only in the presence line; the evidence drawer pushes content; widths 1000 to 1920 px with no horizontal page scroll; reduced motion turns every animation off.
- Money and ratios stay Decimal strings from the API; the front end parses a value only to place a bar (plot position), never to display it (`formatFigure`, `FactFigure`).
- Product name on screen "Credit Squad"; "Squad" elsewhere.
- Tests: generic workflow tests use item types starting with `test.` (lesson: tests must not borrow real item types). Chain test and commit with `&&` (lesson: run tests before commit in one chain).
- Test commands: run only the targeted commands each task names. The full `uv run pytest` takes about 70 minutes and runs once, in Task 6. One pytest or eval process at a time (they share the test database and deadlock). Start Postgres first: `service postgresql start`.
- Playwright: always `--trace off` where a CLI flag applies; the journeys in `frontend/e2e/squad.mjs` launch Chromium themselves and record no trace. Journeys write to the database (routes, returns, decisions): run them against a freshly seeded book.
- Alembic runs only from `backend/` with `DATABASE_URL` exported. This plan adds no migration; if a task finds it needs one, stop and ask.
- Commit after every task with the `p4b` scope (`feat(p4b): …`, `test(p4b): …`, `chore(p4b): …`), each message ending with the two attribution lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq`. Do not push.

## Review Focus

1. **A case's state after every hand-off step must read the same everywhere, for both people.** Routed, returned, re-routed, decided: the home count, the case card's words and button, the Approvals list and the presence line agree for the analyst and for the officer, and the analyst can never decide what she routed (the 409 is shown in the server's words). Tests: Task 1 (`test_routing.py`, `case.test.tsx`, the hand-off journey).
2. **Opening a client lands at what is new, not at the oldest document.** With no `?case=`, the thread scrolls to the first open case, open ask or unsent draft; with only documents, to the newest arrivals; with `?case=`, the case wins. Tests: Task 2 (`test_thread_opening.py`, `thread.test.tsx`).
3. **Unmeasured figures stay unmeasured.** A venture client that is cash-flow positive shows "not meaningful" for runway, a period with no stored figure shows "Not measured", and neither draws a bar at zero, in the client file and in My Portfolio. Tests: Task 2 (`test_client_file.py`), Task 3 (`portfolio.test.tsx`).
4. **Every old address still lands somewhere sensible.** `/borrowers/<code>/covenants`, `/borrowers/<code>/documents/<id>?page=3`, `/borrowers`, `/command-centre`, `/agent-activity`, `/governance` redirect to the Squad place that replaced them; an unknown client code says so and offers the way home. Tests: Task 2 (`redirects.test.tsx`), Task 5 (journey "old addresses").
5. **People who take no credit decision are offered none.** An administrator and a credit reviewer see no decide, route, return or attach control on any case, in the thread, in Approvals or in Oversight, and the API refuses them if called directly. Tests: Task 1 (`test_case_view_says_what_each_person_may_do`, route API 403), Task 4 (`oversight.test.tsx`).

---

## File map

| File | Task | Change |
|---|---|---|
| `backend/app/domain/routing.py` | 1 | New: `route_work_item`, `return_work_item`, `attach_evidence`, `may_receive`, `ROUTING_ACTIONS` |
| `backend/app/squad/rules.py` | 1 | `awaits_reroute`, `needs`; `state_words(item, names, borrower=None)` |
| `backend/app/squad/cases.py` | 1 | New: `build_case`, `build_approvals` |
| `backend/app/squad/threads.py` | 1, 2, 3 | Routed/returned/attached messages and `seq` ordering (1); arrivals, `opening_id`, document words (2); habits on asks (3) |
| `backend/app/squad/briefing.py` | 1, 2, 3 | "returned to you" (1); document words (2); signals listed not counted, one row per client (3) |
| `backend/app/squad/words.py` | 2 | `document_type_words` |
| `backend/app/squad/client_file.py` | 2 | New: `measure_series` |
| `backend/app/squad/portfolio.py` | 3 | New: `build_portfolio`, `lessons_for` |
| `backend/app/api/routes_squad.py` | 1, 2, 3 | New endpoints |
| `backend/tests/squad/test_routing.py`, `test_cases.py` | 1 | New |
| `backend/tests/squad/test_thread_opening.py`, `test_client_file.py` | 2 | New |
| `backend/tests/squad/test_portfolio.py` | 3 | New; `test_briefing.py` updated for the signal rule |
| `frontend/src/squad/api/types.ts`, `hooks.ts`, `polling.ts` | 1–4 | Types, queries, writes, refresh keys |
| `frontend/src/squad/case/CasePanel.tsx` | 1 | New; Task 5 moves `HeldFigures.tsx`, `KeyFigures.tsx` beside it |
| `frontend/src/squad/approvals/Approvals.tsx` | 1 | New |
| `frontend/src/squad/thread/messages.tsx`, `AskMessage.tsx`, `ClientThread.tsx` | 1, 2 | Case opens inline; new messages; asks per viewer; opening position; arrivals |
| `frontend/src/squad/clientfile/*` | 2 | New: `ClientFile.tsx`, `views.tsx`, `Measure.tsx`; Task 5 moves `UploadDocument`, `RunStage`, review editor here |
| `frontend/src/squad/links.ts` | 2 | Client file addresses |
| `frontend/src/squad/portfolio/Portfolio.tsx`, `home/SquadHome.tsx`, `shell/SquadNav.tsx` | 3 | New portfolio; calmer briefing; nav |
| `frontend/src/squad/oversight/*` | 4 | New: `Oversight.tsx`, `describeEvent.ts` |
| `frontend/src/squad/shell/surface.ts`, `commands.ts`, `SquadShell.tsx` | 1–5 | Surfaces, commands, nav props; drawer removed (5) |
| `frontend/src/router.tsx` | 1–5 | Routes and redirects |
| `frontend/src/shell/`, `src/drawer/`, cockpit screens, `e2e/run.mjs`, `e2e/repair.mjs`, `e2e/seed_repair.py` | 5 | Deleted |
| `frontend/e2e/squad.mjs`, `frontend/scripts/serve.mjs` | 1, 5, 6 | Journeys; Squad pages for screenshots and a11y |
| `README.md`, `docs/HANDOFF.md`, `frontend/DESIGN.md` | 5, 6 | Docs |

---

### Task 1: Hand-off with the analyst's view, the officer's Approvals, returns

**Files:**
- Create: `backend/app/domain/routing.py`, `backend/app/squad/cases.py`
- Modify: `backend/app/squad/rules.py`, `backend/app/squad/threads.py`, `backend/app/squad/briefing.py`, `backend/app/api/routes_squad.py`
- Test: `backend/tests/squad/test_routing.py`, `backend/tests/squad/test_cases.py`
- Create: `frontend/src/squad/case/CasePanel.tsx`, `frontend/src/squad/approvals/Approvals.tsx`, `frontend/src/squad/__tests__/case.test.tsx`, `frontend/src/squad/__tests__/approvals.test.tsx`
- Modify: `frontend/src/squad/api/types.ts`, `hooks.ts`, `polling.ts`, `frontend/src/squad/thread/messages.tsx`, `AskMessage.tsx`, `frontend/src/squad/shell/surface.ts`, `SquadNav.tsx`, `SquadShell.tsx`, `commands.ts`, `frontend/src/squad/squad.css`, `frontend/src/router.tsx`, `frontend/src/squad/__tests__/thread.test.tsx`, `cockpitSurface.test.tsx`, `frontend/e2e/squad.mjs`

**Interfaces:**
- Consumes (4a): `rules.can_act(user, item, borrower)`, `rules.holds_permission`, `rules.second_person_blocked`, `rules.prepared_by`; `workflow.decide_work_item`, `workflow.needs_reason(item_type, decision)`, `workflow.DECISION_PERMISSIONS`; `work_items.offered`; `build_thread(db, borrower_id, viewer)`; `build_briefing(db, user)`; front end `useWrite` in `squad/api/hooks.ts`, `threadHref(code, caseId)`, `usePresence().say`, `Time`.
- Produces (backend): `app.domain.routing.route_work_item(db, item, *, user: User, to_user_id: uuid.UUID, view: str) -> WorkItem`; `return_work_item(db, item, *, user: User, reason: str) -> WorkItem`; `attach_evidence(db, item, *, user: User, document_id: uuid.UUID, note: str = "") -> WorkItem`; `may_receive(person: User, item) -> bool`; `ROUTING_ACTIONS: tuple[str, str, str]`. `app.squad.rules.awaits_reroute(user, item) -> bool`, `needs(user, item, borrower) -> bool`, `state_words(item, names, borrower=None) -> str`. `app.squad.cases.build_case(db, item, viewer) -> dict` (shape `CaseView` below), `build_approvals(db, user) -> list[dict]` (shape `ApprovalRow`).
- Produces (API): `GET /api/v1/cases/{id}` → `CaseView`; `GET /api/v1/me/approvals` → `ApprovalRow[]`; `POST /api/v1/work-items/{id}/route` `{to: uuid, view: str}`; `POST /api/v1/work-items/{id}/return` `{reason: str}`; `POST /api/v1/work-items/{id}/attach` `{document_id: uuid, note?: str}`. Refusals: 403 permission, 409 second person, 422 rule, 404 unknown.
- Produces (thread messages): `handoff` gains `view: str | null` and `seq`; new `returned` `{work_item_id, reason, by, to, seq}`; new `attached` `{work_item_id, document_id, title, note, by, seq}`; `ask` gains `needs_you: bool`, `state_words: str`. Ordering key is `(second, RANK, seq, id)`.
- Produces (front end): `CasePanel({ workItemId })` in `src/squad/case/CasePanel.tsx`; `refusal(error) -> { title, text }`; hooks `useCase(id)`, `useApprovals()`, `useDecideCase(id)`, `useRouteCase(id)`, `useReturnCase(id)`, `useAttachEvidence(id)`; route `/approvals?case=<id>`; `Surface = 'conversation' | 'squad' | 'cockpit'`; `SquadNav` prop `showApprovals: boolean`; `CommandInput.approvals: boolean`.

- [ ] **Step 1: Write the failing backend tests**

```python
# backend/tests/squad/test_routing.py
from datetime import date

import pytest
from app.core.roles import SecondPersonRequired
from app.domain import workflow
from app.domain.documents import Document
from app.domain.routing import attach_evidence, return_work_item, route_work_item
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing
from app.squad.threads import build_thread

from .conftest import sign_in

VIEW = "Unrestricted cash fell under the floor; recommend reserving rights."


def _case(db, borrower, permission="decide_breach", title="Cash below minimum"):
    # a type reserved for tests: real types gain decision hooks later
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title=title, severity="high",
                      question="How should the bank respond?", allowed_decisions=["reserve_rights", "no_action"],
                      required_permission=permission)


def _doc(db, borrower, title="Signed term sheet"):
    d = Document(borrower_id=borrower.id, title=title, file_name="t.pdf", storage_path="x", sha256="b" * 64,
                 page_count=1, doc_type="term_sheet", period_end=date(2026, 10, 31), status="indexed")
    db.add(d)
    db.flush()
    return d


def test_routing_needs_a_view_and_a_person_who_may_decide(db, world):
    item = _case(db, world["borrower"])
    with pytest.raises(ValueError, match="your view"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="   ")
    with pytest.raises(ValueError, match="cannot decide"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["admin"].id, view=VIEW)
    with pytest.raises(ValueError, match="someone else"):
        route_work_item(db, item, user=world["analyst"], to_user_id=world["analyst"].id, view=VIEW)
    assert item.assigned_to is None


def test_routing_records_the_view_and_the_engine_keeps_the_router_from_deciding(db, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    assert item.assigned_to == world["officer"].id
    assert item.prepared_by_id == str(world["analyst"].id) and item.requires_second_person is True
    with pytest.raises(SecondPersonRequired):
        workflow.decide_work_item(db, item, user_id=world["analyst"].id, user_role="analyst", decision="no_action")


def test_routing_keeps_an_earlier_preparer(db, world):
    item = _case(db, world["borrower"])
    item.prepared_by_id = "terms-agent-run"
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    assert item.prepared_by_id == "terms-agent-run"


def test_a_case_with_someone_else_cannot_be_routed_by_another(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    from .conftest import _user
    tomas = _user(db, "tomas.keller")
    with pytest.raises(ValueError, match="with someone else"):
        route_work_item(db, item, user=tomas, to_user_id=world["officer"].id, view=VIEW)


def test_a_return_goes_back_to_the_router_with_the_reason_and_needs_her(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    with pytest.raises(PermissionError):
        return_work_item(db, item, user=world["analyst"], reason="x")
    with pytest.raises(ValueError, match="reason"):
        return_work_item(db, item, user=world["officer"], reason="  ")
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    assert item.assigned_to == world["analyst"].id and item.status == "open"
    mine = [i for i in build_briefing(db, world["analyst"])["items"] if i["work_item_id"] == str(item.id)]
    assert mine and mine[0]["needs_you"] is True and mine[0]["state"] == "returned to you"
    officer = [i for i in build_briefing(db, world["officer"])["items"] if i["work_item_id"] == str(item.id)]
    assert not any(i["needs_you"] for i in officer)


def test_a_case_never_routed_cannot_be_returned(db, world):
    item = _case(db, world["borrower"])
    item.assigned_to = world["officer"].id
    with pytest.raises(ValueError, match="not routed to you"):
        return_work_item(db, item, user=world["officer"], reason="Why is this mine?")


def test_attach_takes_only_this_clients_documents_and_each_once(db, world):
    item = _case(db, world["borrower"])
    mine, theirs = _doc(db, world["borrower"]), _doc(db, world["other"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    with pytest.raises(ValueError, match="not on this client's file"):
        attach_evidence(db, item, user=world["analyst"], document_id=theirs.id)
    attach_evidence(db, item, user=world["analyst"], document_id=mine.id, note="As asked.")
    with pytest.raises(ValueError, match="already attached"):
        attach_evidence(db, item, user=world["analyst"], document_id=mine.id)
    assert [a["document_id"] for a in item.evidence["attached"]] == [str(mine.id)]


def test_the_whole_loop_reads_in_order_in_the_thread_and_ends_with_two_people(db, world):
    item = _case(db, world["borrower"])
    doc = _doc(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    return_work_item(db, item, user=world["officer"], reason="Attach the signed term sheet first.")
    attach_evidence(db, item, user=world["analyst"], document_id=doc.id, note="As asked.")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view="Term sheet attached.")
    workflow.decide_work_item(db, item, user_id=world["officer"].id, user_role="credit_officer",
                              decision="reserve_rights", reason="Rights reserved pending the close.")
    thread = build_thread(db, world["borrower"].id, world["analyst"])
    msgs = [m for m in thread["messages"] if m.get("work_item_id") == str(item.id)]
    assert [m["type"] for m in msgs] == ["case", "handoff", "returned", "attached", "handoff", "decision"]
    assert msgs[1]["view"] == VIEW and msgs[2]["reason"] == "Attach the signed term sheet first."
    assert msgs[3]["title"] == "Signed term sheet" and msgs[5]["by"] == "Helen Strand"


def test_route_api_refuses_an_administrator(db, client, world):
    item = _case(db, world["borrower"])
    db.commit()
    sign_in(client, "admin")
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(world["officer"].id), "view": VIEW})
    assert r.status_code == 403


def test_route_api_refuses_an_empty_view_in_words(db, client, world):
    item = _case(db, world["borrower"])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/route", json={"to": str(world["officer"].id), "view": " "})
    assert r.status_code == 422 and "your view" in r.json()["detail"]


def test_the_router_is_refused_through_the_decide_api_with_409(db, client, world):
    item = _case(db, world["borrower"], permission="decide_work_item")
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/decide", json={"decision": "no_action"})
    assert r.status_code == 409


def test_return_api_needs_the_person_the_case_is_with(db, client, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/work-items/{item.id}/return", json={"reason": "x"}).status_code == 403
```

```python
# backend/tests/squad/test_cases.py
from app.domain.routing import route_work_item
from app.domain.work_items import raise_item
from app.squad.cases import build_approvals, build_case
from app.squad.questions import raise_question
from app.squad.threads import build_thread

from .conftest import _user, sign_in

VIEW = "Recommend reserving rights."


def _case(db, borrower, permission="decide_breach"):
    return raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title="Cash below minimum",
                      severity="high", question="How should the bank respond?",
                      allowed_decisions=["reserve_rights", "no_action"], required_permission=permission)


def test_the_case_view_says_what_each_person_may_do(db, world):
    item = _case(db, world["borrower"])
    analyst = build_case(db, item, world["analyst"])
    assert analyst["may_route"] and not analyst["may_return"]
    assert not any(d["permitted"] for d in analyst["decisions"])
    assert {d["id"]: d["needs_reason"] for d in analyst["decisions"]} == {"reserve_rights": True, "no_action": False}
    assert [p["name"] for p in analyst["route_to"]] == ["Helen Strand"]
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    officer = build_case(db, item, world["officer"])
    assert officer["may_return"] and all(d["permitted"] for d in officer["decisions"])
    assert officer["view"]["text"] == VIEW and officer["view"]["by"] == "Priya Raman"
    assert officer["needs_you"] is True
    admin = build_case(db, item, world["admin"])
    assert not (admin["may_route"] or admin["may_return"] or admin["may_attach"])
    assert not any(d["permitted"] for d in admin["decisions"])


def test_an_extra_permission_on_one_decision_is_the_engines(db, world):
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="Round slipped",
                      question="What should the bank do?", allowed_decisions=["note_and_watch", "reserve_rights"])
    view = {d["id"]: d["permitted"] for d in build_case(db, item, world["analyst"])["decisions"]}
    assert view == {"note_and_watch": True, "reserve_rights": False}


def test_approvals_list_what_was_routed_to_the_officer_with_the_view(db, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    rows = build_approvals(db, world["officer"])
    assert [r["work_item_id"] for r in rows] == [str(item.id)]
    assert rows[0]["view"] == VIEW and rows[0]["routed_by"] == "Priya Raman" and rows[0]["returns"] == 0
    assert build_approvals(db, world["analyst"]) == []


def test_an_ask_says_whose_it_is_for_each_viewer(db, world):
    world["borrower"].analyst_id = world["analyst"].id
    raise_question(db, borrower_id=world["borrower"].id, title="Map a line", question="ARR or MRR?",
                   options=[{"id": "arr", "label": "ARR", "evidence": "Labelled annual."},
                            {"id": "mrr", "label": "MRR", "evidence": "A monthly column."}])
    tomas = _user(db, "tomas.keller")

    def ask(who):
        return next(m for m in build_thread(db, world["borrower"].id, who)["messages"] if m["type"] == "ask")

    assert ask(world["analyst"])["needs_you"] is True
    other = ask(tomas)
    assert other["needs_you"] is False and other["state_words"] == "With Priya Raman"


def test_case_and_approvals_endpoints(db, client, world):
    item = _case(db, world["borrower"])
    route_work_item(db, item, user=world["analyst"], to_user_id=world["officer"].id, view=VIEW)
    db.commit()
    sign_in(client, "helen.strand")
    assert client.get(f"/api/v1/cases/{item.id}").json()["may_return"] is True
    assert [r["work_item_id"] for r in client.get("/api/v1/me/approvals").json()] == [str(item.id)]
    assert client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000").status_code == 404
```

Note for the implementer: `funding_slipped` is a real type (decisions in `backend/app/domain/funding.py::SLIPPED_DECISIONS`); `test_an_extra_permission_on_one_decision_is_the_engines` only reads its permission table and never decides it, so no hook runs.

- [ ] **Step 2: Run the tests to see them fail**

Run: `service postgresql start; uv run pytest backend/tests/squad/test_routing.py backend/tests/squad/test_cases.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'app.domain.routing'`.

- [ ] **Step 3: Write the routing module**

```python
# backend/app/domain/routing.py
"""Routing a case to a person who may decide it, with the router's view; returning it with a reason; attaching
what was asked for. These are engine rules, beside `decide_work_item`:
- who may receive a case is who may decide it;
- a person who routes a case with her view becomes its preparer, so the two-person rule in `decide_work_item`
  keeps her from deciding it later (an earlier preparer, for example the terms that were prepared, is kept);
- a return is not a decision: the case stays open and goes back to the person who routed it."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.core.roles import Permission, can
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User

ROUTED, RETURNED, ATTACHED = "work_item.routed", "work_item.returned", "work_item.evidence_attached"
ROUTING_ACTIONS = (ROUTED, RETURNED, ATTACHED)
MAX_TEXT = 4000
MAX_NOTE = 500


def _require_open(item: WorkItem) -> None:
    if item.status != "open":
        raise ValueError("This case has already been decided.")


def may_receive(person: User, item: WorkItem) -> bool:
    try:
        permission = Permission(item.required_permission)
    except ValueError:
        return False
    return bool(person.is_active) and can(person.role, permission)


def latest_route(db: Session, item: WorkItem) -> LedgerEvent | None:
    return db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id), LedgerEvent.action == ROUTED)
        .order_by(LedgerEvent.seq.desc()).limit(1)).scalar_one_or_none()


def route_work_item(db: Session, item: WorkItem, *, user: User, to_user_id: uuid.UUID, view: str) -> WorkItem:
    _require_open(item)
    if not can(user.role, Permission.MANAGE_ACTIONS):
        raise PermissionError("Your role cannot route cases (manage_actions).")
    if item.assigned_to is not None and item.assigned_to != user.id:
        raise ValueError("This case is with someone else; only they can send it on.")
    view = (view or "").strip()
    if not view:
        raise ValueError("Routing a case needs your view: what you found and what you recommend.")
    if len(view) > MAX_TEXT:
        raise ValueError(f"Your view is at most {MAX_TEXT} characters.")
    to = db.get(User, to_user_id)
    if to is None or not to.is_active:
        raise ValueError("No such person.")
    if to.id == user.id:
        raise ValueError("A case is routed to someone else.")
    if not may_receive(to, item):
        raise ValueError(f"{to.name} cannot decide this case; it needs {item.required_permission}.")
    previous = item.assigned_to
    item.assigned_to = to.id
    if item.prepared_by_id is None:
        item.prepared_by_id = str(user.id)
    item.requires_second_person = True
    ledger.record(db, actor_type="user", actor_id=user.id, action=ROUTED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "assigned_to": to.id,
                                              "previous_assigned_to": previous, "view": view})
    db.flush()
    return item


def return_work_item(db: Session, item: WorkItem, *, user: User, reason: str) -> WorkItem:
    _require_open(item)
    if item.assigned_to != user.id:
        raise PermissionError("Only the person a case is with can return it.")
    route = latest_route(db, item)
    if route is None or str((route.payload or {}).get("assigned_to")) != str(user.id):
        raise ValueError("This case was not routed to you, so there is no one to return it to.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Returning a case needs a reason: what is missing, or what you want done.")
    if len(reason) > MAX_TEXT:
        raise ValueError(f"A reason is at most {MAX_TEXT} characters.")
    router = uuid.UUID(route.actor_id)
    if router == user.id:
        raise ValueError("You routed this case yourself; there is no one to return it to.")
    item.assigned_to = router
    ledger.record(db, actor_type="user", actor_id=user.id, action=RETURNED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "returned_to": router,
                                              "reason": reason})
    db.flush()
    return item


def attach_evidence(db: Session, item: WorkItem, *, user: User, document_id: uuid.UUID, note: str = "") -> WorkItem:
    _require_open(item)
    with_them = item.assigned_to == user.id
    unowned = item.assigned_to is None and can(user.role, Permission.MANAGE_ACTIONS)
    if not (with_them or unowned):
        raise PermissionError("Only the person a case is with can add evidence to it.")
    doc = db.get(Document, document_id)
    if doc is None or doc.borrower_id != item.borrower_id:
        raise ValueError("That document is not on this client's file.")
    attached = list((item.evidence or {}).get("attached", []))
    if any(a.get("document_id") == str(doc.id) for a in attached):
        raise ValueError("That document is already attached to this case.")
    entry = {"document_id": str(doc.id), "title": doc.title, "by": str(user.id), "note": (note or "").strip()[:MAX_NOTE]}
    item.evidence = {**(item.evidence or {}), "attached": [*attached, entry]}  # a new dict, so the change is saved
    ledger.record(db, actor_type="user", actor_id=user.id, action=ATTACHED, entity_type="work_item",
                  entity_id=item.id, payload={"borrower_id": item.borrower_id, "document_id": doc.id,
                                              "note": entry["note"]})
    db.flush()
    return item
```

- [ ] **Step 4: Extend the shared rule (`rules.py`)**

Replace `state_words` and add two functions at the end of `backend/app/squad/rules.py`:

```python
def state_words(item: WorkItem, names: dict[str, str], borrower: Borrower | None = None) -> str:
    """Where an open case stands for someone who cannot act on it."""
    if item.assigned_to:
        return f"With {names.get(str(item.assigned_to), 'a colleague')}"
    if item.required_permission == Permission.DECIDE_BREACH.value:
        return "With the credit officer"
    if borrower is not None and borrower.analyst_id:
        return f"With {names.get(str(borrower.analyst_id), 'the client’s analyst')}"
    return "Open"


def awaits_reroute(user: User, item: WorkItem) -> bool:
    """A case returned to the person who routed it: hers to answer and send back, though she may not decide it."""
    if item.status != "open" or item.assigned_to != user.id or not can(user.role, Permission.MANAGE_ACTIONS):
        return False
    return not (holds_permission(user, item) and not second_person_blocked(user, item))


def needs(user: User, item: WorkItem, borrower: Borrower) -> bool:
    """Counted as needing this person: theirs to decide, or theirs to answer and send back."""
    return can_act(user, item, borrower) or awaits_reroute(user, item)
```

- [ ] **Step 5: The case view and Approvals (`cases.py`)**

```python
# backend/app/squad/cases.py
"""One case as a person sees it: the question, the router's view, what happened to it, and what this person may
do next. Every "may" is the engine's rule read for this viewer; nothing here decides who may act."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ledger import LedgerEvent
from app.core.roles import Permission, can
from app.domain import workflow
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.routing import ROUTING_ACTIONS, may_receive
from app.domain.work_items import offered
from app.squad import rules
from app.squad.words import decision_words

CANDIDATES = 10
OFFICER_PERMISSIONS = frozenset({"decide_breach", "approve_terms", "approve_commentary"})
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _history(db: Session, item_ids: list[str], names: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {i: [] for i in item_ids}
    if not item_ids:
        return out
    query = select(LedgerEvent).where(LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id.in_(item_ids),
                                      LedgerEvent.action.in_(ROUTING_ACTIONS)).order_by(LedgerEvent.seq)
    for e in db.execute(query).scalars():
        p = e.payload or {}
        to = p.get("assigned_to") or p.get("returned_to")
        out[e.entity_id].append({
            "kind": e.action.split(".", 1)[1], "seq": e.seq, "at": e.ts.isoformat(),
            "by": names.get(e.actor_id, e.actor_id), "by_id": e.actor_id,
            "to": names.get(str(to)) if to else None, "to_id": str(to) if to else None,
            "text": p.get("view") or p.get("reason") or p.get("note") or "", "document_id": p.get("document_id")})
    return out


def _latest_route(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((h for h in reversed(history) if h["kind"] == "routed"), None)


def build_case(db: Session, item: WorkItem, viewer: User) -> dict[str, Any]:
    borrower = db.get(Borrower, item.borrower_id)
    people = list(db.execute(select(User).order_by(User.name)).scalars())
    names = {str(u.id): u.name for u in people}
    history = _history(db, [str(item.id)], names)[str(item.id)]
    route = _latest_route(history)
    is_open = item.status == "open"
    acts = is_open and rules.can_act(viewer, item, borrower)
    decisions = []
    for d in offered(item.item_type, item.allowed_decisions):
        extra = workflow.DECISION_PERMISSIONS.get((item.item_type, d))
        decisions.append({"id": d, "needs_reason": workflow.needs_reason(item.item_type, d),
                          "permitted": bool(acts and (extra is None or can(viewer.role, Permission(extra))))})
    manages = can(viewer.role, Permission.MANAGE_ACTIONS)
    route_to = [{"id": str(u.id), "name": u.name, "title": u.title} for u in people
                if u.id != viewer.id and may_receive(u, item)]
    may_route = bool(is_open and manages and item.assigned_to in (None, viewer.id) and route_to)
    may_return = bool(is_open and route and item.assigned_to == viewer.id
                      and route["to_id"] == str(viewer.id) and route["by_id"] != str(viewer.id))
    may_attach = bool(is_open and (item.assigned_to == viewer.id or (item.assigned_to is None and manages)))
    attached = list((item.evidence or {}).get("attached", []))
    candidates: list[dict[str, Any]] = []
    if may_attach:
        taken = {a.get("document_id") for a in attached}
        docs = db.execute(select(Document).where(Document.borrower_id == item.borrower_id,
                                                 Document.status != "rejected")
                          .order_by(Document.created_at.desc()).limit(CANDIDATES + len(taken))).scalars()
        candidates = [{"document_id": str(d.id), "title": d.title, "doc_type": d.doc_type, "pages": d.page_count}
                      for d in docs if str(d.id) not in taken][:CANDIDATES]
    return {
        "work_item_id": str(item.id),
        "borrower": {"id": str(borrower.id), "code": borrower.code, "name": borrower.name},
        "item_type": item.item_type, "title": item.title, "question": item.question, "severity": item.severity,
        "status": item.status, "due_date": item.due_date.isoformat() if item.due_date else None,
        "decision": item.decision, "decision_words": decision_words(item.decision) if item.decision else None,
        "decision_reason": item.decision_reason or "",
        "decided_by": names.get(str(item.decided_by)) if item.decided_by else None,
        "requires_second_person": bool(item.requires_second_person),
        "with": names.get(str(item.assigned_to)) if item.assigned_to else None,
        "state_words": rules.state_words(item, names, borrower) if is_open else "",
        "needs_you": bool(is_open and rules.needs(viewer, item, borrower)),
        "view": {"text": route["text"], "by": route["by"], "at": route["at"]} if route else None,
        "history": history, "attached": attached, "candidates": candidates,
        "decisions": decisions, "route_to": route_to,
        "may_route": may_route, "may_return": may_return, "may_attach": may_attach,
    }


def build_approvals(db: Session, user: User) -> list[dict[str, Any]]:
    """Decisions waiting for this person: cases routed to them, and open cases that need an officer's permission
    they hold. Routed cases (with a view) first, then by severity and due date."""
    borrowers = {b.id: b for b in db.execute(select(Borrower)).scalars()}
    names = {str(u.id): u.name for u in db.execute(select(User)).scalars()}
    items = [w for w in db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars()
             if w.borrower_id in borrowers and rules.can_act(user, w, borrowers[w.borrower_id])
             and (w.assigned_to == user.id or w.required_permission in OFFICER_PERMISSIONS)]
    history = _history(db, [str(w.id) for w in items], names)
    rows = []
    for w in items:
        b = borrowers[w.borrower_id]
        h = history[str(w.id)]
        route = _latest_route(h)
        rows.append({"work_item_id": str(w.id), "borrower_id": str(b.id), "borrower_code": b.code,
                     "borrower_name": b.name, "title": w.title, "severity": w.severity,
                     "due_date": w.due_date.isoformat() if w.due_date else None,
                     "view": route["text"] if route else None, "routed_by": route["by"] if route else None,
                     "routed_at": route["at"] if route else None,
                     "returns": sum(1 for e in h if e["kind"] == "returned")})
    rows.sort(key=lambda r: (r["view"] is None, SEVERITY_RANK.get(r["severity"], 9), r["due_date"] or "9999-12-31"))
    return rows
```

- [ ] **Step 6: The thread shows the hand-off (`threads.py`)**

In `backend/app/squad/threads.py`:

```python
RANK = {"document": 0, "held": 0, "report": 1, "case": 2, "ask": 2, "draft": 3, "qa": 4,
        "handoff": 5, "returned": 5, "attached": 5, "decision": 6}


def _sort_key(m: dict[str, Any]) -> tuple[datetime, int, int, str]:
    """Order by the second, then by how a case unfolds, then by ledger sequence (one transaction writes many
    events in the same second: lesson latest-means-a-sequence-not-a-timestamp)."""
    try:
        ts = datetime.fromisoformat(m["ts"]).replace(microsecond=0)
    except (KeyError, TypeError, ValueError):
        ts = EPOCH
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts, RANK[m["type"]], int(m.get("seq") or 0), m["id"]
```

In `build_thread`, the `ask` message gains two keys and the `case` message passes the borrower to `state_words` and uses `rules.needs`:

```python
            messages.append({"id": f"ask:{i.id}", "type": "ask", "ts": _iso(i.created_at), "work_item_id": str(i.id),
                             "title": i.title, "question": i.question, "options": options, "status": i.status,
                             "choice": question_choice(i.evidence, i.decision),
                             "chosen_by": names.get(str(i.decided_by)) if i.decided_by else None,
                             "needs_you": viewer is not None and rules.needs(viewer, i, borrower),
                             "state_words": rules.state_words(i, names, borrower) if i.status == "open" else ""})
```

```python
                             "needs_you": viewer is not None and rules.needs(viewer, i, borrower),
                             "state_words": rules.state_words(i, names, borrower) if i.status == "open" else ""})
```

Replace the decision and hand-off loops with:

```python
    for e in _events(db, "work_item.decided", item_ids):
        if e.entity_id in question_ids:
            continue
        p = e.payload or {}
        messages.append({"id": f"decision:{e.seq}", "type": "decision", "seq": e.seq, "ts": _iso(e.ts),
                         "work_item_id": e.entity_id, "decision": p.get("decision"),
                         "decision_words": decision_words(p.get("decision")), "reason": p.get("reason", ""),
                         "by": names.get(e.actor_id, e.actor_id), "by_id": e.actor_id})
    for e in [*_events(db, "work_item.assigned", item_ids), *_events(db, "work_item.routed", item_ids)]:
        p = e.payload or {}
        to = p.get("assigned_to")
        messages.append({"id": f"handoff:{e.seq}", "type": "handoff", "seq": e.seq, "ts": _iso(e.ts),
                         "work_item_id": e.entity_id, "assigned_to": names.get(str(to)) if to else None,
                         "assigned_to_id": to, "by": names.get(e.actor_id, e.actor_id), "view": p.get("view")})
    for e in _events(db, "work_item.returned", item_ids):
        p = e.payload or {}
        to = p.get("returned_to")
        messages.append({"id": f"returned:{e.seq}", "type": "returned", "seq": e.seq, "ts": _iso(e.ts),
                         "work_item_id": e.entity_id, "reason": p.get("reason", ""),
                         "by": names.get(e.actor_id, e.actor_id), "to": names.get(str(to)) if to else None})
    titles = {str(d.id): d.title for d in docs}
    for e in _events(db, "work_item.evidence_attached", item_ids):
        p = e.payload or {}
        messages.append({"id": f"attached:{e.seq}", "type": "attached", "seq": e.seq, "ts": _iso(e.ts),
                         "work_item_id": e.entity_id, "document_id": p.get("document_id"),
                         "title": titles.get(str(p.get("document_id")), "A document"), "note": p.get("note", ""),
                         "by": names.get(e.actor_id, e.actor_id)})
```

- [ ] **Step 7: The briefing counts a returned case for the person it came back to (`briefing.py`)**

In `build_briefing`, inside `if w.status == "open":`, add a branch right after the `rules.can_act` branch:

```python
            elif rules.awaits_reroute(user, w):
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": "returned to you",
                              "needs_you": True, "_due": w.due_date})
```

- [ ] **Step 8: The endpoints (`routes_squad.py`)**

Add to `backend/app/api/routes_squad.py` (imports: `from app.domain import routing`, `from app.squad.cases import build_approvals, build_case`):

```python
def _open_item(db: Session, item_id: uuid.UUID) -> WorkItem:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Case not found.")
    return item


def _engine(db: Session, fn, *args, **kwargs) -> None:
    try:
        fn(db, *args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SecondPersonRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()


@router.get("/cases/{work_item_id}")
def get_case(work_item_id: uuid.UUID, db: Session = Depends(get_db),
             user: User = Depends(require(Permission.VIEW))) -> dict:
    return build_case(db, _open_item(db, work_item_id), user)


@router.get("/me/approvals")
def my_approvals(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return build_approvals(db, user)


class RouteIn(BaseModel):
    to: uuid.UUID
    view: str = Field(max_length=4000)


class ReturnIn(BaseModel):
    reason: str = Field(max_length=4000)


class AttachIn(BaseModel):
    document_id: uuid.UUID
    note: str = Field(default="", max_length=500)


@router.post("/work-items/{item_id}/route")
def route_case(item_id: uuid.UUID, body: RouteIn, db: Session = Depends(get_db),
               user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.route_work_item, item, user=user, to_user_id=body.to, view=body.view)
    return build_case(db, item, user)


@router.post("/work-items/{item_id}/return")
def return_case(item_id: uuid.UUID, body: ReturnIn, db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.return_work_item, item, user=user, reason=body.reason)
    return build_case(db, item, user)


@router.post("/work-items/{item_id}/attach")
def attach_to_case(item_id: uuid.UUID, body: AttachIn, db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.attach_evidence, item, user=user, document_id=body.document_id, note=body.note)
    return build_case(db, item, user)
```

- [ ] **Step 9: Run the backend tests**

Run: `uv run pytest backend/tests/squad -q && uv run ruff check backend/app/domain/routing.py backend/app/squad backend/app/api/routes_squad.py backend/tests/squad`
Expected: PASS (the 4a squad tests stay green: `test_threads.py` asserts the old order for documents, cases and decisions, which the new key keeps).

- [ ] **Step 10: Write the failing front-end tests**

```tsx
// frontend/src/squad/__tests__/case.test.tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import type { CaseView } from '../api/types';
import { CasePanel, refusal } from '../case/CasePanel';

const state = vi.hoisted(() => ({ view: undefined as unknown, decide: vi.fn(), route: vi.fn(), ret: vi.fn(), attach: vi.fn(), say: vi.fn(), open: vi.fn(), error: null as unknown }));
const write = (fn: (i: unknown) => void) => ({ mutateAsync: async (i: unknown) => { fn(i); if (state.error) throw state.error; }, isPending: false, error: state.error, reset: () => {} });
vi.mock('../api/hooks', () => ({
  useCase: () => ({ data: state.view, isPending: false, error: null, refetch: vi.fn() }),
  useDecideCase: () => write(state.decide),
  useRouteCase: () => write(state.route),
  useReturnCase: () => write(state.ret),
  useAttachEvidence: () => write(state.attach),
}));
vi.mock('@/api/hooks', () => ({ useWorkItem: () => ({ data: undefined }) }));
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ say: state.say }) }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/screens/work/KeyFigures', () => ({ KeyFigures: () => null }));
vi.mock('@/screens/work/HeldFigures', () => ({ HeldFigures: () => <p>held figures</p> }));

const base: CaseView = {
  work_item_id: 'w1', borrower: { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.' }, item_type: 'covenant.breach',
  title: 'Cash below minimum', question: 'How should the bank respond?', severity: 'high', status: 'open', due_date: null,
  decision: null, decision_words: null, decision_reason: '', decided_by: null, requires_second_person: false, with: null,
  state_words: 'With the credit officer', needs_you: false, view: null, history: [], attached: [], candidates: [],
  decisions: [{ id: 'reservation_of_rights', needs_reason: true, permitted: false }, { id: 'not_a_breach', needs_reason: true, permitted: false }],
  route_to: [{ id: 'u2', name: 'Helen Strand', title: 'Senior Credit Officer' }], may_route: true, may_return: false, may_attach: true,
};

beforeEach(() => {
  state.view = base;
  state.error = null;
  [state.decide, state.route, state.ret, state.attach, state.say].forEach((f) => f.mockClear());
});

describe('CasePanel', () => {
  it('lets the analyst route with her view, and only once the view is written', async () => {
    render(<CasePanel workItemId="w1" />);
    const send = screen.getByRole('button', { name: 'Send to Helen Strand' });
    expect(send).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/your view/i), 'Cash fell under the floor.');
    await userEvent.click(send);
    expect(state.route).toHaveBeenCalledWith({ to: 'u2', view: 'Cash fell under the floor.' });
    expect(state.say).toHaveBeenCalledWith('Sent to Helen Strand with your view · recorded');
    expect(screen.queryByRole('button', { name: /record decision/i })).not.toBeInTheDocument();
  });

  it('shows the officer the view, a reason box the server says is required, and Return', async () => {
    state.view = { ...base, needs_you: true, may_route: false, may_return: true, may_attach: true, view: { text: 'Recommend reserving rights.', by: 'Priya Raman', at: '2026-11-21T09:00:00Z' },
      decisions: base.decisions.map((d) => ({ ...d, permitted: true })) };
    render(<CasePanel workItemId="w1" />);
    expect(screen.getByText('Recommend reserving rights.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /reserve rights/i }));
    const record = screen.getByRole('button', { name: 'Record decision' });
    expect(record).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Reason (required)'), 'Pending the close.');
    await userEvent.click(record);
    expect(state.decide).toHaveBeenCalledWith({ decision: 'reservation_of_rights', reason: 'Pending the close.' });
    await userEvent.type(screen.getByLabelText(/what is missing/i), 'Attach the signed term sheet.');
    await userEvent.click(screen.getByRole('button', { name: 'Return to Priya Raman' }));
    expect(state.ret).toHaveBeenCalledWith({ reason: 'Attach the signed term sheet.' });
  });

  it('shows a second-person refusal in the server’s words, never pre-empted', async () => {
    state.view = { ...base, decisions: [{ id: 'not_a_breach', needs_reason: false, permitted: true }], may_route: false };
    state.error = new ApiError(409, 'This approval must come from a different person than the preparer.');
    render(<CasePanel workItemId="w1" />);
    await userEvent.click(screen.getByRole('radio', { name: /not a breach/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Record decision' }));
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText('Not recorded: a second person must decide this')).toBeInTheDocument();
    expect(within(alert).getByText(/different person than the preparer/)).toBeInTheDocument();
  });

  it('offers an administrator nothing to do', () => {
    state.view = { ...base, may_route: false, may_return: false, may_attach: false, candidates: [] };
    render(<CasePanel workItemId="w1" />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
    expect(screen.getByText(/With the credit officer/)).toBeInTheDocument();
  });

  it('attaches a document the analyst picks; it never attaches one by itself', async () => {
    state.view = { ...base, candidates: [{ document_id: 'd9', title: 'Signed term sheet', doc_type: 'term_sheet', pages: 2 }] };
    render(<CasePanel workItemId="w1" />);
    expect(state.attach).not.toHaveBeenCalled();
    await userEvent.click(screen.getByText(/on file you can attach/));
    await userEvent.click(screen.getByRole('button', { name: 'Attach Signed term sheet' }));
    expect(state.attach).toHaveBeenCalledWith({ document_id: 'd9' });
  });

  it('names each refusal by what it means', () => {
    expect(refusal(new ApiError(403, 'no')).title).toBe('Not recorded: your role cannot do this');
    expect(refusal(new ApiError(422, 'needs a reason')).text).toBe('needs a reason');
  });
});
```

`ApiError(status, detail)` is the constructor in `frontend/src/api/client.ts`.

```tsx
// frontend/src/squad/__tests__/approvals.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Approvals } from '../approvals/Approvals';

const rows = [{ work_item_id: 'w1', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', title: 'Cash below minimum', severity: 'high', due_date: null, view: 'Recommend reserving rights.', routed_by: 'Priya Raman', routed_at: '2026-11-21T09:00:00Z', returns: 0 }];
vi.mock('../api/hooks', () => ({ useApprovals: () => ({ data: rows, isPending: false, error: null, refetch: vi.fn() }) }));
vi.mock('../case/CasePanel', () => ({ CasePanel: ({ workItemId }: { workItemId: string }) => <p>case {workItemId}</p> }));

function mount(path: string) {
  const root = createRootRoute();
  const route = createRoute({ getParentRoute: () => root, path: '/approvals', component: Approvals, validateSearch: (s: Record<string, unknown>) => ({ case: typeof s.case === 'string' ? s.case : undefined }) });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([route, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

describe('Approvals', () => {
  it('counts what waits, shows the analyst’s view, and opens the case beside the list', async () => {
    mount('/approvals?case=w1');
    expect(await screen.findByText('1 decision waits for you')).toBeInTheDocument();
    expect(screen.getByText(/Recommend reserving rights/)).toBeInTheDocument();
    expect(screen.getByText('case w1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open in quillfeather labs, inc\.’s thread/i })).toHaveAttribute('href', '/clients/QFL?case=w1');
  });
});
```

In `frontend/src/squad/__tests__/thread.test.tsx`: delete the `vi.mock('@/drawer/context', …)` line and `openItem` from `state`; add `vi.mock('../case/CasePanel', () => ({ CasePanel: ({ workItemId }: { workItemId: string }) => <p>case panel {workItemId}</p> }));` and replace the test "offers Decide only on a case the viewer can act on, and opens that item in the drawer" with:

```tsx
  it('opens the case inline on the thread a person can act on, through the address', async () => {
    state.thread = thread([{ ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Mine', question: 'q', severity: 'critical', status: 'open', allowed_decisions: ['breach'], needs_you: true, state_words: '' }]);
    mount();
    const mine = (await screen.findByText('Mine')).closest('[data-work-item]') as HTMLElement;
    expect(within(mine).getByRole('link', { name: 'Open the case Mine' })).toHaveAttribute('href', '/clients/QFL?case=w1');
    mount('?case=w1');
    expect(await screen.findByText('case panel w1')).toBeInTheDocument();
  });

  it('says a returned case is back with the person it came back to', async () => {
    state.thread = thread([
      { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Back', question: 'q', severity: 'high', status: 'open', allowed_decisions: [], needs_you: true, state_words: 'With Priya Raman' },
      { ...base, id: 'handoff:1', type: 'handoff', work_item_id: 'w1', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman', view: 'Recommend reserving rights.' },
      { ...base, id: 'returned:2', type: 'returned', work_item_id: 'w1', reason: 'Attach the term sheet.', by: 'Helen Strand', to: 'Priya Raman' },
    ]);
    mount();
    const card = (await screen.findByText('Back')).closest('[data-work-item]') as HTMLElement;
    expect(within(card).getByText('Returned to you')).toBeInTheDocument();
    expect(screen.getByText(/Helen Strand returned this to Priya Raman/)).toBeInTheDocument();
    expect(screen.getByText('Attach the term sheet.')).toBeInTheDocument();
    expect(screen.getByText('Recommend reserving rights.')).toBeInTheDocument();
  });
```

In `frontend/src/squad/__tests__/cockpitSurface.test.tsx`, extend the first `describe`:

```tsx
  it.each(['/approvals'])('%s is a Squad screen', (path) => expect(surfaceOf(path)).toBe('squad'));
```

- [ ] **Step 11: Run them to see them fail**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/case.test.tsx src/squad/__tests__/approvals.test.tsx src/squad/__tests__/thread.test.tsx src/squad/__tests__/cockpitSurface.test.tsx`
Expected: FAIL (`Cannot find module '../case/CasePanel'`, `'../approvals/Approvals'`; the thread test fails on the missing link).

- [ ] **Step 12: Types, hooks and refresh keys**

Append to `frontend/src/squad/api/types.ts`:

```ts
export interface CaseHistoryEntry { kind: 'routed' | 'returned' | 'evidence_attached'; seq: number; at: string; by: string; by_id: string; to: string | null; to_id: string | null; text: string; document_id: string | null }
export interface CaseDecisionOption { id: string; needs_reason: boolean; permitted: boolean }
export interface CaseView {
  work_item_id: string;
  borrower: { id: string; code: string; name: string };
  item_type: string;
  title: string;
  question: string;
  severity: string;
  status: string;
  due_date: string | null;
  decision: string | null;
  decision_words: string | null;
  decision_reason: string;
  decided_by: string | null;
  requires_second_person: boolean;
  with: string | null;
  state_words: string;
  needs_you: boolean;
  view: { text: string; by: string; at: string } | null;
  history: CaseHistoryEntry[];
  attached: Array<{ document_id: string; title: string; by: string; note: string }>;
  candidates: Array<{ document_id: string; title: string; doc_type: string | null; pages: number }>;
  decisions: CaseDecisionOption[];
  route_to: Array<{ id: string; name: string; title: string }>;
  may_route: boolean;
  may_return: boolean;
  may_attach: boolean;
}
export interface ApprovalRow {
  work_item_id: string;
  borrower_id: string;
  borrower_code: string;
  borrower_name: string;
  title: string;
  severity: string;
  due_date: string | null;
  view: string | null;
  routed_by: string | null;
  routed_at: string | null;
  returns: number;
}
```

In the `ThreadMessage` union in the same file (every test fixture of an `ask` message then needs `needs_you` and `state_words`; `pnpm typecheck` lists them): give `ask` the fields `needs_you: boolean; state_words: string`; give `handoff` the field `view?: string | null`; add two members:

```ts
    | { type: 'returned'; work_item_id: string; reason: string; by: string; to: string | null }
    | { type: 'attached'; work_item_id: string; document_id: string; title: string; note: string; by: string }
```

Append to `frontend/src/squad/api/hooks.ts` (import `ApprovalRow, CaseView` from `./types`):

```ts
export const useCase = (id?: string) =>
  useQuery({ queryKey: ['case', id], queryFn: () => get<CaseView>(`/cases/${id}`), enabled: Boolean(id) });
export const useApprovals = () => useQuery({ queryKey: ['approvals'], queryFn: () => get<ApprovalRow[]>('/me/approvals') });
const CASE_KEYS = ['case', 'approvals', 'trail', 'work-item', 'borrowers'];
export const useDecideCase = (id: string) =>
  useWrite<{ decision: string; reason: string }, unknown>(() => `/work-items/${id}/decide`, (i) => i, CASE_KEYS);
export const useRouteCase = (id: string) =>
  useWrite<{ to: string; view: string }, CaseView>(() => `/work-items/${id}/route`, (i) => i, CASE_KEYS);
export const useReturnCase = (id: string) =>
  useWrite<{ reason: string }, CaseView>(() => `/work-items/${id}/return`, (i) => i, CASE_KEYS);
export const useAttachEvidence = (id: string) =>
  useWrite<{ document_id: string; note?: string }, CaseView>(() => `/work-items/${id}/attach`, (i) => i, CASE_KEYS);
```

In `frontend/src/squad/api/polling.ts`: `const REFRESH = [['briefing'], ['thread'], ['trail'], ['borrowers'], ['case'], ['approvals']] as const;`

- [ ] **Step 13: The case panel**

```tsx
// frontend/src/squad/case/CasePanel.tsx
import { useId, useState } from 'react';
import { ApiError, errorMessage } from '@/api/client';
import { useWorkItem } from '@/api/hooks';
import { decisionLabel } from '@/domain/labels';
import { HeldFigures } from '@/screens/work/HeldFigures';
import { KeyFigures } from '@/screens/work/KeyFigures';
import { useSource } from '@/source/context';
import { useAttachEvidence, useCase, useDecideCase, useReturnCase, useRouteCase } from '../api/hooks';
import type { CaseView } from '../api/types';
import { usePresence } from '../presence/Presence';
import { Time } from '../thread/Time';

const HELD = new Set(['spread.value_unverified', 'spread.does_not_foot']);

/** The server's refusal in its own words, titled by what it means. A second-person refusal is shown, never pre-empted. */
export function refusal(error: unknown): { title: string; text: string } {
  const text = errorMessage(error);
  if (error instanceof ApiError && error.status === 409) return { title: 'Not recorded: a second person must decide this', text };
  if (error instanceof ApiError && error.status === 403) return { title: 'Not recorded: your role cannot do this', text };
  return { title: 'Not recorded', text };
}

function Refused({ error }: { error: unknown }) {
  if (!error) return null;
  const r = refusal(error);
  return (
    <div role="alert" className="sq-refusal">
      <b>{r.title}</b>
      <p>The server said: “{r.text}”</p>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <div className="sq-field">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function DecideForm({ c }: { c: CaseView }) {
  const decide = useDecideCase(c.work_item_id);
  const { say } = usePresence();
  const [choice, setChoice] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState<unknown>(null);
  const picked = c.decisions.find((d) => d.id === choice);
  const ready = Boolean(picked) && (!picked?.needs_reason || reason.trim().length > 0);
  async function submit() {
    setError(null);
    try {
      await decide.mutateAsync({ decision: choice, reason: reason.trim() });
      say(`${decisionLabel(choice)} · recorded`);
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Record a decision" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <fieldset className="sq-options">
        <legend>Your decision</legend>
        {c.decisions.filter((d) => d.permitted).map((d) => (
          <label key={d.id} className="sq-option">
            <input type="radio" name={`decision-${c.work_item_id}`} value={d.id} checked={choice === d.id} onChange={() => setChoice(d.id)} />
            <span>{decisionLabel(d.id)}</span>
          </label>
        ))}
      </fieldset>
      <Field label={picked?.needs_reason ? 'Reason (required)' : 'Reason'} value={reason} onChange={setReason} />
      <Refused error={error} />
      <button type="submit" className="sq-btn sq-btn-primary" disabled={!ready || decide.isPending}>Record decision</button>
      {c.requires_second_person ? <p className="sq-faint">Two people: whoever prepared or routed this case cannot decide it.</p> : null}
    </form>
  );
}

function RouteForm({ c }: { c: CaseView }) {
  const route = useRouteCase(c.work_item_id);
  const { say } = usePresence();
  const [to, setTo] = useState(c.route_to[0]?.id ?? '');
  const [view, setView] = useState('');
  const [error, setError] = useState<unknown>(null);
  const person = c.route_to.find((p) => p.id === to);
  async function submit() {
    setError(null);
    try {
      await route.mutateAsync({ to, view: view.trim() });
      say(`Sent to ${person?.name ?? 'them'} with your view · recorded`);
      setView('');
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Send for a decision" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      {c.route_to.length > 1 ? (
        <label className="sq-field">
          Send to
          <select className="sq-input" value={to} onChange={(e) => setTo(e.target.value)}>
            {c.route_to.map((p) => <option key={p.id} value={p.id}>{p.name}, {p.title}</option>)}
          </select>
        </label>
      ) : null}
      <Field label="Your view (required): what you found and what you recommend" value={view} onChange={setView} />
      <Refused error={error} />
      <button type="submit" className="sq-btn" disabled={!view.trim() || !person || route.isPending}>Send to {person?.name ?? 'a person who may decide'}</button>
    </form>
  );
}

function ReturnForm({ c }: { c: CaseView }) {
  const ret = useReturnCase(c.work_item_id);
  const { say } = usePresence();
  const [reason, setReason] = useState('');
  const [error, setError] = useState<unknown>(null);
  const who = c.view?.by ?? 'the person who sent it';
  async function submit() {
    setError(null);
    try {
      await ret.mutateAsync({ reason: reason.trim() });
      say(`Returned to ${who} · recorded`);
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Return the case" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <Field label="What is missing, or what you want done (required)" value={reason} onChange={setReason} />
      <Refused error={error} />
      <button type="submit" className="sq-btn" disabled={!reason.trim() || ret.isPending}>Return to {who}</button>
    </form>
  );
}

function Evidence({ c }: { c: CaseView }) {
  const source = useSource();
  const attach = useAttachEvidence(c.work_item_id);
  const { say } = usePresence();
  const [error, setError] = useState<unknown>(null);
  const open = (documentId: string, title: string) => source.open({ type: 'document', documentId, page: 1, title, borrowerCode: c.borrower.code });
  return (
    <>
      {c.attached.length > 0 ? (
        <ul className="sq-plainlist" aria-label="Attached to this case">
          {c.attached.map((a) => (
            <li key={a.document_id}>
              <button type="button" className="sq-link" aria-label={`Open ${a.title}`} onClick={() => open(a.document_id, a.title)}>{a.title}</button>
              {a.note ? <span className="sq-faint"> · {a.note}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {c.may_attach && c.status === 'open' && c.candidates.length > 0 ? (
        <details className="sq-candidates">
          <summary>Squad found {c.candidates.length === 1 ? '1 document' : `${c.candidates.length} documents`} on file you can attach</summary>
          <ul className="sq-plainlist">
            {c.candidates.map((d) => (
              <li key={d.document_id}>
                <button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => open(d.document_id, d.title)}>{d.title}</button>{' '}
                <button type="button" className="sq-btn" aria-label={`Attach ${d.title}`} disabled={attach.isPending}
                  onClick={() => void attach.mutateAsync({ document_id: d.document_id }).then(() => say(`${d.title} attached · recorded`), setError)}>Attach</button>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <Refused error={error} />
    </>
  );
}

function History({ c }: { c: CaseView }) {
  if (c.history.length === 0) return null;
  const words = { routed: 'sent this to', returned: 'returned this to', evidence_attached: 'attached a document' } as const;
  return (
    <ol className="sq-plainlist sq-faint" aria-label="What happened to this case">
      {c.history.map((h) => (
        <li key={h.seq}>{h.by} {words[h.kind]}{h.kind === 'evidence_attached' ? '' : ` ${h.to ?? ''}`} · <Time ts={h.at} /></li>
      ))}
    </ol>
  );
}

/** One case, in place in the thread or beside the Approvals list: the question, the router's view, the evidence, and only the actions the server allows this person. */
export function CasePanel({ workItemId }: { workItemId: string }) {
  const q = useCase(workItemId);
  const detail = useWorkItem(workItemId);
  if (q.isPending) return <p role="status" className="sq-muted">Opening the case.</p>;
  if (q.error || !q.data)
    return (
      <div role="alert">
        <p>The case could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void q.refetch()}>Try again</button>
      </div>
    );
  const c = q.data;
  const decides = c.status === 'open' && c.decisions.some((d) => d.permitted);
  return (
    <section className="sq-case" aria-label={`Case: ${c.title}`} data-case={c.work_item_id}>
      {c.view ? (
        <figure className="sq-view">
          <figcaption className="sq-faint">{c.view.by}’s view · <Time ts={c.view.at} /></figcaption>
          <blockquote className="sq-quote">{c.view.text}</blockquote>
        </figure>
      ) : null}
      <History c={c} />
      {detail.data ? <KeyFigures item={detail.data} /> : null}
      {detail.data && HELD.has(c.item_type) ? <HeldFigures item={detail.data} code={c.borrower.code} headingLevel="h4" /> : null}
      <Evidence c={c} />
      {c.status !== 'open' ? (
        <p><b>{c.decided_by ?? 'A person'}: {c.decision_words}</b>{c.decision_reason ? ` · “${c.decision_reason}”` : ''}</p>
      ) : (
        <>
          {decides ? <DecideForm c={c} /> : null}
          {c.may_return ? <ReturnForm c={c} /> : null}
          {c.may_route ? <RouteForm c={c} /> : null}
          {!decides && !c.may_route && !c.may_return ? <p className="sq-muted">{c.state_words}. This case is not yours to decide.</p> : null}
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 14: Approvals screen, route, nav and commands**

```tsx
// frontend/src/squad/approvals/Approvals.tsx
import { Link, useSearch } from '@tanstack/react-router';
import { useApprovals } from '../api/hooks';
import { CasePanel } from '../case/CasePanel';
import { threadHref } from '../links';

const waits = (n: number) => (n === 1 ? '1 decision waits for you' : `${n} decisions wait for you`);

/** The credit officer's decisions: each with the case, its evidence and the analyst's view; the case opens beside the list. */
export function Approvals() {
  const { case: selected } = useSearch({ strict: false }) as { case?: string };
  const approvals = useApprovals();
  if (approvals.isPending) return <p role="status" className="sq-muted">Gathering the decisions that wait for you.</p>;
  if (approvals.error || !approvals.data)
    return (
      <div role="alert">
        <p>The decisions could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void approvals.refetch()}>Try again</button>
      </div>
    );
  const rows = approvals.data;
  const current = rows.find((r) => r.work_item_id === selected);
  return (
    <div className="sq-approvals">
      <h1 className="sq-h1">Approvals</h1>
      <h2 className="sq-lede">{rows.length ? waits(rows.length) : 'Nothing waits for your decision.'}</h2>
      <div className="sq-split">
        <ul className="sq-list" aria-label="Decisions waiting">
          {rows.map((r) => (
            <li key={r.work_item_id}>
              <Link to="/approvals" search={{ case: r.work_item_id }} className="sq-row" aria-current={r.work_item_id === selected ? 'true' : undefined}>
                <span className={`sq-dotmark sq-sev-${r.severity}`} aria-hidden />
                <span className="sq-grow">
                  <b>{r.borrower_name}</b>
                  <span className="sq-muted"> · {r.title}</span>
                  {r.view ? <span className="sq-faint sq-block">{r.routed_by}: {r.view}</span> : null}
                </span>
                {r.returns > 0 ? <span className="sq-faint">returned {r.returns === 1 ? 'once' : `${r.returns} times`}</span> : null}
              </Link>
            </li>
          ))}
        </ul>
        <div>
          {selected ? (
            <>
              <CasePanel workItemId={selected} />
              {current ? (
                <Link {...threadHref(current.borrower_code, selected)} className="sq-link">Open in {current.borrower_name}’s thread</Link>
              ) : null}
            </>
          ) : rows.length ? (
            <p className="sq-muted">Choose a decision to see its case, the evidence and the analyst’s view.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
```

`frontend/src/squad/shell/surface.ts`:

```ts
/** Conversation: home and threads (narrow, presence line). Squad: Squad's own wide screens (presence line). Cockpit: a legacy screen kept until Task 5. */
export type Surface = 'conversation' | 'squad' | 'cockpit';

const SQUAD = ['/approvals'];

export function surfaceOf(pathname: string): Surface {
  if (pathname === '/' || pathname === '/clients' || (pathname.startsWith('/clients/') && !pathname.includes('/file'))) return 'conversation';
  if (SQUAD.some((p) => pathname === p || pathname.startsWith(`${p}/`)) || /^\/clients\/[^/]+\/file/.test(pathname)) return 'squad';
  return 'cockpit';
}
```

In `SquadShell.tsx`: render `<PresenceLine />` when `surface !== 'cockpit'`; compute `const showApprovals = can('decide_breach') || can('approve_terms');` from `useAuth()`; pass `showApprovals` to `SquadNav` and `approvals: showApprovals` to `buildCommands`.

In `SquadNav.tsx`, add the prop `showApprovals: boolean` and, after the My Portfolio link:

```tsx
      {showApprovals ? (
        <Link to="/approvals" className="sq-navlink" aria-current={pathname.startsWith('/approvals') ? 'page' : undefined} title="Approvals">
          <Stamp size={18} aria-hidden />
          <span className="sq-navlabel">Approvals</span>
        </Link>
      ) : null}
```

(`Stamp` from `lucide-react`.) In `commands.ts`, add `approvals: boolean` to `CommandInput` and, after the portfolio command: `if (approvals) commands.push({ id: 'go-approvals', group: 'Go to', label: 'Approvals', hint: 'Decisions waiting for you', run: () => go('/approvals') });`. Update the existing `shell.test.tsx` calls of `buildCommands` and `SquadNav` to pass `approvals: false` / `showApprovals={false}`.

In `frontend/src/router.tsx` add, and list it in `routeTree` after `clientRoute`:

```tsx
export const approvalsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/approvals',
  component: lazyRouteComponent(() => import('@/squad/approvals/Approvals'), 'Approvals'),
  validateSearch: (search: Record<string, unknown>): { case?: string } => clean({ case: str(search.case) }),
});
```

Append to `frontend/src/squad/squad.css`:

```css
.sq-main[data-surface='squad'] { max-width: 1280px; }
.sq-split { display: grid; grid-template-columns: minmax(280px, 2fr) minmax(0, 3fr); gap: 20px; align-items: start; }
.sq-case { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--sq-line); }
.sq-caseform { display: flex; flex-direction: column; gap: 8px; }
.sq-field { display: flex; flex-direction: column; gap: 4px; }
.sq-field textarea { padding: 8px 10px; border-radius: 10px; border: 1px solid var(--sq-line-strong); background: var(--sq-surface); color: var(--sq-ink); font: inherit; resize: vertical; }
.sq-refusal { border: 1px solid var(--sq-line-strong); border-radius: 10px; padding: 8px 12px; color: var(--sq-ink); }
.sq-plainlist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.sq-view { margin: 0; }
.sq-block { display: block; white-space: normal; }
@media (max-width: 1100px) { .sq-split { grid-template-columns: 1fr; } }
```

- [ ] **Step 15: The thread opens the case inline and reads hand-offs in words**

In `frontend/src/squad/thread/messages.tsx`: remove the `useWorkspaceDrawer` import and `drawer`; import `CasePanel` from `'../case/CasePanel'` and `threadHref` from `'../links'`. Replace `caseState` and the `case`, `handoff` branches, and add two branches:

```tsx
export function caseState(message: Extract<ThreadMessage, { type: 'case' }>, all: ThreadMessage[]): { text: string; needsYou: boolean } {
  const mine = all.filter((m) => 'work_item_id' in m && m.work_item_id === message.work_item_id);
  const decision = mine.find((m): m is Extract<ThreadMessage, { type: 'decision' }> => m.type === 'decision');
  if (decision) return { text: `${decision.decision_words ?? words(decision.decision)} by ${decision.by}`, needsYou: false };
  if (message.status !== 'open') return { text: words(message.status).replace(/^./, (c) => c.toUpperCase()), needsYou: false };
  const last = [...mine].reverse().find((m) => m.type === 'handoff' || m.type === 'returned');
  if (message.needs_you) return { text: last?.type === 'returned' ? 'Returned to you' : 'Needs your call', needsYou: true };
  if (last?.type === 'returned') return { text: `Returned to ${last.to ?? 'the analyst'}`, needsYou: false };
  if (last?.type === 'handoff') return { text: `With ${last.assigned_to ?? 'no one in particular'}`, needsYou: false };
  return { text: message.state_words || 'Open', needsYou: false };
}
```

```tsx
    case 'case': {
      const state = caseState(message, thread);
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
          <header className="sq-msghead"><b>{message.title}</b> <span className="sq-tag">{SEVERITY[message.severity] ?? words(message.severity)}</span> <span className={state.needsYou ? 'sq-tag sq-tag-needs' : 'sq-tag'}>{state.text}</span> <Time ts={message.ts} /></header>
          <p>{message.question}</p>
          <div className="sq-actions">
            {focused ? null : (
              <Link {...threadHref(borrowerCode, message.work_item_id)} className={state.needsYou ? 'sq-btn sq-btn-primary' : 'sq-btn'} aria-label={`Open the case ${message.title}`}>
                {state.needsYou ? 'Open the case' : 'See the case'}
              </Link>
            )}
            <Link to={clientFile(borrowerCode)} className="sq-link" aria-label={`Open ${message.title} in the client file`}>Open in client file</Link>
          </div>
          {focused ? <CasePanel workItemId={message.work_item_id} /> : null}
          <Trail workItemId={message.work_item_id} />
        </article>
      );
    }
```

```tsx
    case 'handoff':
      return (
        <div className="sq-msg" data-work-item={message.work_item_id}>
          <p className="sq-faint">{message.by} {message.view ? 'sent this to' : 'handed this to'} {message.assigned_to ?? 'no one in particular'}{message.view ? ' with this view:' : '.'} <Time ts={message.ts} /></p>
          {message.view ? <blockquote className="sq-quote">{message.view}</blockquote> : null}
        </div>
      );
    case 'returned':
      return (
        <div className="sq-msg" data-work-item={message.work_item_id}>
          <p className="sq-faint">{message.by} returned this to {message.to ?? 'the analyst'}: <Time ts={message.ts} /></p>
          <blockquote className="sq-quote">{message.reason}</blockquote>
        </div>
      );
    case 'attached':
      return (
        <p className="sq-msg sq-faint" data-work-item={message.work_item_id}>
          {message.by} attached{' '}
          <button type="button" className="sq-link" aria-label={`Open ${message.title}`} onClick={() => source.open({ type: 'document', documentId: message.document_id, page: 1, title: message.title, borrowerCode })}>{message.title}</button>
          {message.note ? ` · ${message.note}` : ''} <Time ts={message.ts} />
        </p>
      );
```

In `frontend/src/squad/thread/AskMessage.tsx`, replace `const mayAnswer = can('decide_work_item');` with `const mayAnswer = message.status === 'open' && message.needs_you;` and, where the options render for someone who may not answer, show `<p className="sq-muted">{message.state_words}</p>` above the disabled fieldset when `message.status === 'open' && !message.needs_you`. Remove `can` from the `useAuth()` destructuring if it is no longer used. Add one test to `src/squad/__tests__/questions.test.tsx`:

```tsx
  it('disables the options for a viewer the server says is not the one to answer, and says whose it is', async () => {
    render(<AskMessage message={{ ...ask, needs_you: false, state_words: 'With Priya Raman' }} focused={false} />);
    expect(screen.getByText('With Priya Raman')).toBeInTheDocument();
    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled();
  });
```

(`ask` is the fixture already defined in that test file; give it `needs_you: true, state_words: ''` so the existing tests keep answering.)

- [ ] **Step 16: Run the front-end checks**

Run: `cd frontend && pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 17: The hand-off journey**

Append to `frontend/e2e/squad.mjs`, before the runner at the bottom:

```js
journey('hand-off: the analyst routes a breach with her view, the officer returns it, it comes back, and the officer decides', async ({ browser }) => {
  const analystCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const a = await analystCtx.newPage();
  await signIn(a, ANALYST);
  const breaches = await api(a, '/work-items?item_type=covenant.breach');
  const open = breaches.find((w) => !w.assigned_to);
  assert(open, 'the seeded book should hold an open, unassigned covenant breach');
  const borrower = await api(a, `/borrowers/${open.borrower_id}`);
  await a.goto(`${BASE}/clients/${borrower.code}?case=${open.id}`);
  const card = a.locator(`[data-work-item="${open.id}"][data-focused="true"]`);
  await card.getByLabel(/your view/i).fill('Cash under the floor two months running; recommend reserving rights.');
  await card.getByRole('button', { name: /^Send to / }).click();
  await a.getByText(/with your view · recorded/).waitFor();
  assert((await card.getByRole('button', { name: 'Record decision' }).count()) === 0, 'the analyst was offered a decision she routed');

  const officerCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const o = await officerCtx.newPage();
  await signIn(o, OFFICER);
  await o.goto(`${BASE}/approvals?case=${open.id}`);
  await o.getByText('Cash under the floor two months running; recommend reserving rights.').first().waitFor();
  await o.getByLabel(/what is missing/i).fill('Attach the signed term sheet for the new round.');
  await o.getByRole('button', { name: 'Return to Priya Raman' }).click();
  await o.getByText(/Returned to Priya Raman · recorded/).waitFor();

  await a.goto(`${BASE}/`);
  const back = (await record(a)).needs.find((i) => i.work_item_id === open.id);
  assert(back && back.state === 'returned to you', 'the returned case does not need the analyst');
  await a.goto(`${BASE}/clients/${borrower.code}?case=${open.id}`);
  await a.getByText('Attach the signed term sheet for the new round.').first().waitFor();
  const found = card.getByText(/on file you can attach$/);
  if (await found.count()) {
    await found.click();
    await card.getByRole('button', { name: /^Attach / }).first().click();
  }
  await card.getByLabel(/your view/i).fill('Term sheet attached; my view stands.');
  await card.getByRole('button', { name: /^Send to / }).click();

  await o.goto(`${BASE}/approvals?case=${open.id}`);
  const first = o.getByRole('radio').first();
  await first.check();
  await o.getByLabel(/^Reason/).fill('Reserving rights until the round closes.');
  await o.getByRole('button', { name: 'Record decision' }).click();
  await o.getByText(/· recorded$/).waitFor();
  const done = await api(o, `/cases/${open.id}`);
  assert(done.status === 'decided' && done.decided_by === 'Helen Strand', 'the officer’s decision was not recorded');
  await analystCtx.close();
  await officerCtx.close();
});
```

Run (stack up on a freshly seeded innovation book plus `uv run python -m app.squad_demo`): `cd frontend && pnpm e2e:squad`
Expected: every journey prints `PASS`, including the new one.

- [ ] **Step 18: Commit**

```bash
uv run pytest backend/tests/squad -q && (cd frontend && pnpm vitest run src/squad && pnpm typecheck && pnpm lint) && \
git add backend/app/domain/routing.py backend/app/squad backend/app/api/routes_squad.py backend/tests/squad \
  frontend/src/squad frontend/src/router.tsx frontend/e2e/squad.mjs && \
git commit -m "feat(p4b): route a case with the analyst's view, Approvals for the officer, return and re-route in the same thread

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

---
### Task 2: The client file (redesigned detail views), and threads that open at what is new

**Files:**
- Modify: `backend/app/squad/words.py`, `backend/app/squad/threads.py`, `backend/app/squad/briefing.py`, `backend/app/api/routes_squad.py`
- Create: `backend/app/squad/client_file.py`
- Test: `backend/tests/squad/test_thread_opening.py`, `backend/tests/squad/test_client_file.py`
- Create: `frontend/src/squad/clientfile/ClientFile.tsx`, `frontend/src/squad/clientfile/views.tsx`, `frontend/src/squad/clientfile/Measure.tsx`, `frontend/src/squad/redirects.ts`, `frontend/src/squad/__tests__/clientFile.test.tsx`, `frontend/src/squad/__tests__/redirects.test.tsx`
- Modify: `frontend/src/squad/links.ts`, `frontend/src/squad/api/types.ts`, `hooks.ts`, `frontend/src/squad/thread/ClientThread.tsx`, `messages.tsx`, `frontend/src/source/SourceDrawer.tsx` (`ViewerLink`), `frontend/src/api/schema.ts` (`CovenantTestRow.note`), `frontend/src/router.tsx`, `frontend/src/squad/squad.css`, `frontend/src/squad/__tests__/shell.test.tsx`, `thread.test.tsx`, `cockpitSurface.test.tsx`

**Interfaces:**
- Consumes: Task 1's `Surface 'squad'`, `CasePanel`; 4a `threadHref`, `useThread`; existing hooks `useBorrowerByCode`, `useBorrowerOverview`, `useSpread`, `useFactsById`, `useBorrowerCovenants`, `useDocuments`, `useBorrowerTerms`, `useBorrowingBase`, `useSignals`, `useTimeline`, `useReviewSheets`, `useReviewSheet`, `useActions`; components `FactFigure`, `SourcedFigure`, `Absent` (`@/source/figures`), `RunStage`, `UploadDocument`, `Commentary` (still in `src/screens/` until Task 5), `describeEvent` (`@/screens/Governance` until Task 4); `metrics_service.runway_not_meaningful(db, borrower, period_end)`; `routes_ui._Labels`, `routes_ui._summary`.
- Produces (backend): `app.squad.words.document_type_words(doc_type: str | None) -> str`; `app.squad.client_file.measure_series(db, borrower, limit: int = 6) -> {"kind": "rml" | "headroom", "label": str, "points": [{"period_end": iso, "fact": FactSummary | None, "note": str | None}]}`; `GET /api/v1/borrowers/{id}/measure`. Thread: `document` messages gain `doc_type_words`; new message `arrivals` `{id: "arrivals:YYYY-MM", ts, title, period_end, documents: [document message, …]}`; the thread gains `opening_id: str | None`.
- Produces (front end): `ClientFileView = 'overview' | 'spreads' | 'covenants' | 'documents' | 'funding' | 'loans' | 'reviews' | 'history'`; `clientFile(code, view?) -> '/clients/<code>/file[/<view>]'`; routes `/clients/$code/file` and `/clients/$code/file/$view` (search `document?`, `page?`); `oldAddress(pathname: string, search: Record<string, unknown>) -> string | null` in `src/squad/redirects.ts` (unit-tested here, wired into the router in Task 5); `TrendBars({ points, label })` and `MeasureNow({ series })` in `clientfile/Measure.tsx`; hooks `useMeasure(borrowerId)`, `useFundingEvents(borrowerId)`; types `MeasurePoint`, `MeasureSeries`, `FundingEventRow`.

- [ ] **Step 1: Write the failing backend tests**

```python
# backend/tests/squad/test_thread_opening.py
from datetime import date, timedelta

from app.domain.documents import Document
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing
from app.squad.threads import build_thread
from app.squad.words import document_type_words

OCT, SEP = date(2026, 10, 31), date(2026, 9, 30)


def _doc(db, borrower, title, doc_type, period):
    d = Document(borrower_id=borrower.id, title=title, file_name="d.pdf", storage_path="x", sha256="c" * 64,
                 page_count=1, doc_type=doc_type, period_end=period, status="indexed")
    db.add(d)
    db.flush()
    return d


def _october(db, borrower):
    for title, kind in (("MRR report, October 2026", "mrr_report"), ("Account statement, October 2026", "bank_statement"),
                        ("Management financial statements, October 2026", "monthly_financials")):
        _doc(db, borrower, title, kind, OCT)


def test_documents_for_one_period_arrive_as_one_message(db, world):
    _october(db, world["borrower"])
    _doc(db, world["borrower"], "Venture Loan and Security Agreement", "credit_agreement", None)
    msgs = build_thread(db, world["borrower"].id)["messages"]
    arrivals = [m for m in msgs if m["type"] == "arrivals"]
    assert len(arrivals) == 1 and arrivals[0]["title"] == "3 documents arrived for October 2026"
    assert sorted(d["doc_type_words"] for d in arrivals[0]["documents"]) == [
        "Bank account statement", "MRR report", "Monthly financial statements"]
    assert [m["type"] for m in msgs].count("document") == 1  # the agreement has no period and stands alone


def test_the_thread_opens_at_the_first_open_case_not_the_oldest_document(db, world):
    _doc(db, world["borrower"], "MRR report, September 2026", "mrr_report", SEP)
    _october(db, world["borrower"])
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="test.opening", title="A line is new",
                      question="How should the new line be mapped?", allowed_decisions=["mapped"])
    assert build_thread(db, world["borrower"].id)["opening_id"] == f"case:{item.id}"


def test_with_nothing_open_it_opens_at_the_newest_arrivals(db, world):
    for title in ("MRR report, September 2026", "Account statement, September 2026"):
        _doc(db, world["borrower"], title, "mrr_report", SEP)
    _october(db, world["borrower"])
    assert build_thread(db, world["borrower"].id)["opening_id"] == "arrivals:2026-10"


def test_an_empty_thread_opens_nowhere(db, world):
    assert build_thread(db, world["borrower"].id)["opening_id"] is None


def test_document_types_read_in_plain_words():
    assert document_type_words("mrr_report") == "MRR report"
    assert document_type_words("bank_statement") == "Bank account statement"
    assert document_type_words("bank_statements") == "Bank account statement"
    assert document_type_words(None) == "Not yet classified"
    assert document_type_words("new_kind") == "New kind"


def test_an_overdue_mrr_report_reads_mrr_in_the_briefing(db, world):
    from decimal import Decimal

    from app.core import clock
    from app.domain.credit import Facility
    from app.domain.terms import ReportingObligation
    f = Facility(borrower_id=world["borrower"].id, code="QFL-TL", name="Term loan", facility_type="term_loan",
                 commitment=Decimal("1000000"))
    db.add(f)
    db.flush()
    today = clock.today(db)
    db.add(ReportingObligation(borrower_id=world["borrower"].id, facility_id=f.id, requirement_id="mrr",
                               document_type="mrr_report", period_end=date(2026, 10, 31),
                               due_date=today - timedelta(days=4), status="overdue"))
    db.flush()
    titles = [i["title"] for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "overdue_report"]
    assert titles == ["MRR report for October 2026 is overdue"]
```

```python
# backend/tests/squad/test_client_file.py
from datetime import date
from decimal import Decimal

from app.domain.facts_service import add_fact
from app.domain.workflow import open_cycle
from app.squad import client_file
from app.squad.client_file import measure_series

from .conftest import sign_in

ENDS = [date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31)]


def _periods(db, borrower):
    for end in ENDS:
        open_cycle(db, borrower_id=borrower.id, period_end=end, months=1, cycle_type="monthly")


def test_runway_points_carry_stored_facts_and_never_a_zero(db, world, monkeypatch):
    b = world["borrower"]  # vc-1
    _periods(db, b)
    fact = add_fact(db, borrower_id=b.id, key="metric.rml", period_end=ENDS[0], months=0, value=Decimal("14.2"),
                    kind="calculated", unit="count", status="verified")
    monkeypatch.setattr(client_file, "runway_not_meaningful", lambda db, borrower, period_end: period_end == ENDS[1])
    series = measure_series(db, b)
    assert series["kind"] == "rml" and series["label"] == "Runway (months)"
    assert [p["period_end"] for p in series["points"]] == [e.isoformat() for e in ENDS]
    assert series["points"][0]["fact"]["id"] == str(fact.id) and series["points"][0]["note"] is None
    assert series["points"][1]["fact"] is None and series["points"][1]["note"] == "Not meaningful: cash-flow positive"
    assert series["points"][2]["fact"] is None and series["points"][2]["note"] == "Not measured"


def test_a_proposed_runway_is_not_shown_as_measured(db, world, monkeypatch):
    b = world["borrower"]
    _periods(db, b)
    add_fact(db, borrower_id=b.id, key="metric.rml", period_end=ENDS[2], months=0, value=Decimal("9.0"),
             kind="calculated", unit="count", status="proposed")
    monkeypatch.setattr(client_file, "runway_not_meaningful", lambda *a: False)
    assert measure_series(db, b)["points"][2]["fact"] is None


def test_headroom_picks_the_tightest_stored_headroom_per_period(db, world):
    b = world["other"]
    b.template_id = "ci-1"
    _periods(db, b)
    loose = add_fact(db, borrower_id=b.id, key="cov.leverage.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("0.31"), kind="calculated", unit="pct", status="verified")
    tight = add_fact(db, borrower_id=b.id, key="cov.fccr.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("0.04"), kind="calculated", unit="pct", status="verified")
    series = measure_series(db, b)
    assert series["kind"] == "headroom" and series["points"][2]["fact"]["id"] == str(tight.id) != str(loose.id)
    assert series["points"][0]["note"] == "Not measured"


def test_measure_endpoint(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/borrowers/{world['other'].id}/measure").json()["points"] == []
    assert client.get("/api/v1/borrowers/00000000-0000-0000-0000-000000000000/measure").status_code == 404
```

`world["other"]` is a C&I client: `borrowers.template_id` defaults to `ci-1` (`backend/app/domain/credit.py`). It is a server default, so the headroom test sets `world["other"].template_id = "ci-1"` explicitly on its first line to have the value in the session before the first read.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest backend/tests/squad/test_thread_opening.py backend/tests/squad/test_client_file.py -q`
Expected: FAIL (`ImportError: cannot import name 'document_type_words'`, `No module named 'app.squad.client_file'`).

- [ ] **Step 3: Document types in plain words (`words.py`)**

```python
_DOC_TYPES = {
    "mrr_report": "MRR report", "bank_statement": "Bank account statement", "bank_statements": "Bank account statement",
    "monthly_financials": "Monthly financial statements", "credit_agreement": "Credit agreement",
    "compliance_certificate": "Compliance certificate", "borrowing_base_certificate": "Borrowing base certificate",
    "receivables_aging": "Receivables aging", "annual_statements": "Annual financial statements",
    "interim_statements": "Interim financial statements", "quarterly_statements": "Quarterly financial statements",
    "tax_return": "Tax return", "term_sheet": "Term sheet", "investor_update": "Investor update",
    "amendment": "Amendment", "waiver": "Waiver", "other": "Other document",
}


def document_type_words(doc_type: str | None) -> str:
    """"MRR report", "Bank account statement": a document type as people say it. The document's own printed title
    ("Account statement, August 2026") is shown beside it unchanged."""
    if not doc_type:
        return "Not yet classified"
    return _DOC_TYPES.get(doc_type, doc_type.replace("_", " ").capitalize())
```

- [ ] **Step 4: Arrivals and the opening position (`threads.py`)**

Import `date` and `document_type_words`. In the document loop, the `document` message gains `"doc_type_words": document_type_words(d.doc_type)`. Add `"arrivals": 0` to `RANK`. Add:

```python
def _group_arrivals(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Documents for one period become one message ("3 documents arrived for October 2026"). A lone document, a held
    one, or one with no period stays on its own. The group sits where its last document arrived."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for m in messages:
        if m["type"] == "document" and m.get("period_end"):
            groups.setdefault(m["period_end"][:7], []).append(m)
    grouped = {k: v for k, v in groups.items() if len(v) > 1}
    out = [m for m in messages if not (m["type"] == "document" and (m.get("period_end") or "")[:7] in grouped)]
    for key, docs in grouped.items():
        label = date.fromisoformat(docs[0]["period_end"]).strftime("%B %Y")
        out.append({"id": f"arrivals:{key}", "type": "arrivals", "ts": max(d["ts"] for d in docs),
                    "title": f"{len(docs)} documents arrived for {label}", "period_end": docs[0]["period_end"],
                    "documents": sorted(docs, key=lambda d: d["title"])})
    return out


def _opening(messages: list[dict[str, Any]]) -> str | None:
    """Where a person starts reading: the first thing still open (a case or ask, an unsent draft); else the newest
    arrivals or document; else the last message."""
    for m in messages:
        if (m["type"] in ("case", "ask") and m.get("status") == "open") or (m["type"] == "draft" and m.get("status") == "draft"):
            return m["id"]
    for m in reversed(messages):
        if m["type"] in ("arrivals", "document", "held"):
            return m["id"]
    return messages[-1]["id"] if messages else None
```

At the end of `build_thread`, before sorting: `messages = _group_arrivals(messages)`; after sorting, return `"opening_id": _opening(messages)` alongside `head_seq`.

In `briefing.py`, the overdue title becomes `f"{document_type_words(ob.document_type)} for {ob.period_end:%B %Y} is overdue"` (import from `app.squad.words`).

- [ ] **Step 5: The measure series (`client_file.py`) and its endpoint**

```python
# backend/app/squad/client_file.py
"""The one measure each client is watched by, period by period: runway in months for a venture client (`vc-1`), the
tightest covenant headroom for a C&I client. Every point is a stored fact or says why there is none; nothing is
calculated here and an unmeasured point is never a zero."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes_ui import _Labels, _summary
from app.domain.credit import Borrower
from app.domain.facts import USABLE_STATUSES, Fact
from app.domain.metrics_service import runway_not_meaningful
from app.domain.monitoring import Cycle

NOT_MEASURED = "Not measured"
NOT_MEANINGFUL = "Not meaningful: cash-flow positive"


def _periods(db: Session, borrower: Borrower, limit: int) -> list:
    ends = sorted(set(db.execute(select(Cycle.period_end).where(Cycle.borrower_id == borrower.id)).scalars()))
    return ends[-limit:]


def measure_series(db: Session, borrower: Borrower, limit: int = 6) -> dict[str, Any]:
    labels = _Labels(db)
    periods = _periods(db, borrower, limit)
    venture = borrower.template_id == "vc-1"
    pattern = "metric.rml" if venture else "cov.%.headroom_pct"
    latest: dict[tuple[str, Any], Fact] = {}
    for fact in db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key.like(pattern),
                                              Fact.status.in_(USABLE_STATUSES), Fact.period_end.in_(periods or [None]))
                           .order_by(Fact.seq)).scalars():
        latest[(fact.key, fact.period_end)] = fact  # by sequence: the last stored fact for a key and period wins
    points = []
    for end in periods:
        candidates = [f for (_, p), f in latest.items() if p == end]
        fact = min(candidates, key=lambda f: f.value) if candidates else None  # chosen, not computed
        note = None
        if fact is None:
            note = NOT_MEANINGFUL if venture and runway_not_meaningful(db, borrower, end) else NOT_MEASURED
        points.append({"period_end": end.isoformat(), "fact": _summary(fact, labels) if fact else None, "note": note})
    return {"kind": "rml" if venture else "headroom",
            "label": "Runway (months)" if venture else "Tightest covenant headroom", "points": points}
```

Add to `routes_squad.py` (import `measure_series`):

```python
@router.get("/borrowers/{borrower_id}/measure")
def borrower_measure(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                     _: User = Depends(require(Permission.VIEW))) -> dict:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise HTTPException(404, "Client not found.")
    return measure_series(db, borrower)
```

- [ ] **Step 6: Run the backend tests**

Run: `uv run pytest backend/tests/squad -q && uv run ruff check backend/app/squad backend/tests/squad`
Expected: PASS.

- [ ] **Step 7: Write the failing front-end tests**

```tsx
// frontend/src/squad/__tests__/redirects.test.tsx
import { describe, expect, it } from 'vitest';
import { clientFile } from '../links';
import { oldAddress } from '../redirects';

describe('old addresses', () => {
  it.each([
    ['/borrowers/QFL', '/clients/QFL/file'],
    ['/borrowers/QFL/covenants', '/clients/QFL/file/covenants'],
    ['/borrowers/QFL/spreads', '/clients/QFL/file/spreads'],
    ['/borrowers/QFL/timeline', '/clients/QFL/file/history'],
    ['/borrowers/QFL/borrowing-base', '/clients/QFL/file/loans'],
    ['/borrowers/QFL/signals', '/clients/QFL/file'],
    ['/borrowers/QFL/packages', '/clients/QFL/file'],
    ['/borrowers', '/portfolio'],
  ])('%s goes to %s', (from, to) => expect(oldAddress(from, {})).toBe(to));

  it('keeps the document and page of a document link', () => {
    expect(oldAddress('/borrowers/QFL/documents/d1', { page: 3 })).toBe('/clients/QFL/file/documents?document=d1&page=3');
  });

  it('leaves every Squad address alone', () => {
    for (const path of ['/', '/clients/QFL', '/clients/QFL/file/spreads', '/approvals']) expect(oldAddress(path, {})).toBeNull();
  });

  it('builds client file addresses in one place', () => {
    expect(clientFile('QFL')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'overview')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'covenants')).toBe('/clients/QFL/file/covenants');
  });
});
```

```tsx
// frontend/src/squad/__tests__/clientFile.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MeasurePoint } from '../api/types';
import { ClientFile } from '../clientfile/ClientFile';
import { MeasureNow, TrendBars } from '../clientfile/Measure';

const state = vi.hoisted(() => ({ open: vi.fn() }));
vi.mock('@/api/hooks', () => ({
  useBorrowerByCode: (code: string) => ({ borrower: code === 'QFL' ? { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' } : undefined, notFound: code !== 'QFL', error: null }),
  useDocuments: () => ({ data: [{ id: 'd1', title: 'MRR report, October 2026', doc_type: 'mrr_report', page_count: 1, period_end: '2026-10-31', received_date: '2026-11-12', status: 'indexed' }], isPending: false, error: null }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/source/figures', () => ({ FactFigure: ({ fact }: { fact: { value: string } }) => <span>fact {fact.value}</span>, Absent: ({ reason }: { reason?: string }) => <span>{reason ?? 'Not measured'}</span>, SourcedFigure: () => null }));
vi.mock('../clientfile/views', async () => {
  const actual = await vi.importActual<typeof import('../clientfile/views')>('../clientfile/views');
  return { ...actual, Overview: () => <p>overview</p> };
});

function mount(path: string) {
  const root = createRootRoute();
  const file = createRoute({ getParentRoute: () => root, path: '/clients/$code/file', component: ClientFile });
  const view = createRoute({ getParentRoute: () => root, path: '/clients/$code/file/$view', component: ClientFile, validateSearch: (s: Record<string, unknown>) => ({ document: typeof s.document === 'string' ? s.document : undefined, page: typeof s.page === 'number' ? s.page : undefined }) });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([file, view, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

beforeEach(() => state.open.mockClear());

describe('ClientFile', () => {
  it('names the client, offers every view and the way back to the thread', async () => {
    mount('/clients/QFL/file');
    expect(await screen.findByRole('heading', { level: 1, name: 'Quillfeather Labs, Inc.' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Client file' });
    expect(within(nav).getByRole('link', { name: 'Covenants' })).toHaveAttribute('href', '/clients/QFL/file/covenants');
    expect(within(nav).getByRole('link', { name: 'Overview' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Back to the thread' })).toHaveAttribute('href', '/clients/QFL');
  });

  it('says so for an unknown view or client', async () => {
    mount('/clients/QFL/file/nonsense');
    expect(await screen.findByText('There is no such part of the client file.')).toBeInTheDocument();
    mount('/clients/NOPE/file');
    expect(await screen.findByText('There is no client with that code.')).toBeInTheDocument();
  });

  it('lists documents in plain words and opens the one an old link named, beside the file', async () => {
    mount('/clients/QFL/file/documents?document=d1&page=1');
    expect(await screen.findByText('MRR report')).toBeInTheDocument();
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 1 }));
  });
});

describe('Measure', () => {
  const points: MeasurePoint[] = [
    { period_end: '2026-08-31', fact: { id: 'f1', key: 'metric.rml', label: 'Runway', value: '14.2', unit: 'count', kind: 'calculated', status: 'verified', period_end: '2026-08-31', months: 0, borrower_id: 'b1', document_id: null, page: null, calc_run_id: 'c1' }, note: null },
    { period_end: '2026-09-30', fact: null, note: 'Not meaningful: cash-flow positive' },
  ];

  it('draws no bar for an unmeasured period and no number of its own', () => {
    const { container } = render(<TrendBars points={points} label="Runway (months)" />);
    const bars = container.querySelectorAll('.sq-bar');
    expect(bars).toHaveLength(2);
    expect(bars[1]).toHaveClass('sq-bar-none');
    expect((bars[1] as HTMLElement).style.height).toBe('');
    expect(container.textContent).toBe('');
  });

  it('shows the stored note, never a zero, when the latest point has no figure', () => {
    render(<MeasureNow series={{ kind: 'rml', label: 'Runway (months)', points }} />);
    expect(screen.getByText('Not meaningful: cash-flow positive')).toBeInTheDocument();
    expect(screen.queryByText(/^0/)).not.toBeInTheDocument();
  });
});
```

Update the existing tests: in `shell.test.tsx` the `clientFile('QFL', 'covenants')` expectation becomes `'/clients/QFL/file/covenants'`; in `thread.test.tsx` the "Open in client file" `href` becomes `'/clients/QFL/file'`, and add:

```tsx
  it('opens at what is new and groups arrivals for one period', async () => {
    const scrolled: string[] = [];
    Element.prototype.scrollIntoView = function (this: Element) { scrolled.push(this.getAttribute('data-message-id') ?? ''); };
    state.thread = { ...thread([
      { ...base, id: 'arrivals:2026-10', type: 'arrivals', title: '2 documents arrived for October 2026', period_end: '2026-10-31', documents: [
        { ...base, id: 'doc:1', type: 'document', document_id: 'd1', title: 'MRR report, October 2026', doc_type: 'mrr_report', doc_type_words: 'MRR report', pages: 1, period_end: '2026-10-31' },
        { ...base, id: 'doc:2', type: 'document', document_id: 'd2', title: 'Account statement, October 2026', doc_type: 'bank_statement', doc_type_words: 'Bank account statement', pages: 1, period_end: '2026-10-31' },
      ] },
      { ...base, id: 'case:9', type: 'case', work_item_id: 'w9', item_type: 'x', title: 'New line', question: 'q', severity: 'medium', status: 'open', allowed_decisions: [], needs_you: true, state_words: '' },
    ]), opening_id: 'case:9' };
    mount();
    expect(await screen.findByText('2 documents arrived for October 2026')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open MRR report, October 2026' })).toBeInTheDocument();
    expect(scrolled).toEqual(['case:9']);
  });
```

In `cockpitSurface.test.tsx`, add `'/clients/QFL/file'` and `'/clients/QFL/file/covenants'` to the Squad list (the `/borrowers…` paths stay cockpit screens until Task 5).

- [ ] **Step 8: Run them to see them fail**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/redirects.test.tsx src/squad/__tests__/clientFile.test.tsx src/squad/__tests__/thread.test.tsx src/squad/__tests__/shell.test.tsx`
Expected: FAIL (`Cannot find module '../redirects'`, `'../clientfile/ClientFile'`).

- [ ] **Step 9: Addresses, redirects, types and hooks**

```ts
// frontend/src/squad/links.ts
/** Where the client file and a thread live. One place, so every link moves together. */
export type ClientFileView = 'overview' | 'spreads' | 'covenants' | 'documents' | 'funding' | 'loans' | 'reviews' | 'history';

export function clientFile(code: string, view?: ClientFileView): string {
  return view && view !== 'overview' ? `/clients/${code}/file/${view}` : `/clients/${code}/file`;
}

export function threadHref(code: string, caseId?: string) {
  return { to: '/clients/$code' as const, params: { code }, search: caseId ? { case: caseId } : {} };
}
```

```ts
// frontend/src/squad/redirects.ts
import { clientFile, type ClientFileView } from './links';

const OLD_VIEWS: Record<string, ClientFileView> = {
  '': 'overview', loans: 'loans', documents: 'documents', spreads: 'spreads', covenants: 'covenants',
  'borrowing-base': 'loans', signals: 'overview', reviews: 'reviews', packages: 'overview', timeline: 'history',
};

/** Where an address from the retired cockpit now lives, or null for an address that is not an old one. */
export function oldAddress(pathname: string, search: Record<string, unknown>): string | null {
  if (pathname === '/borrowers' || pathname === '/borrowers/') return '/portfolio';
  const doc = /^\/borrowers\/([^/]+)\/documents\/([^/]+)\/?$/.exec(pathname);
  if (doc) {
    const page = typeof search.page === 'number' || typeof search.page === 'string' ? `&page=${search.page}` : '';
    return `${clientFile(doc[1], 'documents')}?document=${encodeURIComponent(doc[2])}${page}`;
  }
  const match = /^\/borrowers\/([^/]+)(?:\/([^/]+))?\/?$/.exec(pathname);
  if (!match) return null;
  return clientFile(match[1], OLD_VIEWS[match[2] ?? ''] ?? 'overview');
}
```

Append to `frontend/src/squad/api/types.ts` (import `FactSummary` from `@/api/schema`):

```ts
export interface MeasurePoint { period_end: string; fact: FactSummary | null; note: string | null }
export interface MeasureSeries { kind: 'rml' | 'headroom'; label: string; points: MeasurePoint[] }
export interface FundingEventRow { id: string; kind: string; amount: string; expected_close: string; status: string; evidence_document_ids: string[] }
```

In the `ThreadMessage` union, give `document` the field `doc_type_words: string`, add `| { type: 'arrivals'; title: string; period_end: string; documents: Array<Extract<ThreadMessage, { type: 'document' }>> }` (write the document shape out inline if TypeScript rejects the self-reference), and give `Thread` the field `opening_id: string | null` (the `thread()` helper in `thread.test.tsx` returns `opening_id: null`).

Append to `frontend/src/squad/api/hooks.ts`:

```ts
export const useMeasure = (borrowerId?: string) =>
  useQuery({ queryKey: ['measure', borrowerId], queryFn: () => get<MeasureSeries>(`/borrowers/${borrowerId}/measure`), enabled: Boolean(borrowerId) });
export const useFundingEvents = (borrowerId?: string) =>
  useQuery({ queryKey: ['funding', borrowerId], queryFn: () => get<FundingEventRow[]>(`/borrowers/${borrowerId}/funding-events`), enabled: Boolean(borrowerId) });
```

In `frontend/src/api/schema.ts`, `CovenantTestRow` gains `note?: string | null;` (the stored column, e.g. `not_meaningful_cash_flow_positive`).

- [ ] **Step 10: The measure components**

```tsx
// frontend/src/squad/clientfile/Measure.tsx
import { Absent, FactFigure } from '@/source/figures';
import type { MeasurePoint, MeasureSeries } from '../api/types';

/** Plot positions only: each bar's height comes from its stored value; the bars carry no number of their own.
 * A period with no stored figure draws an outline, never a bar at zero. */
export function TrendBars({ points, label }: { points: MeasurePoint[]; label: string }) {
  const values = points.map((p) => (p.fact ? Number(p.fact.value) : null)); // parsed for the plot position only
  const max = Math.max(0, ...values.filter((v): v is number => v !== null));
  return (
    <span className="sq-bars" role="img" aria-label={`${label}, last ${points.length} ${points.length === 1 ? 'period' : 'periods'}`}>
      {points.map((p, i) => {
        const v = values[i];
        const drawn = v !== null && max > 0;
        return <span key={p.period_end} className={drawn ? 'sq-bar' : 'sq-bar sq-bar-none'} style={drawn ? { height: `${Math.max(8, Math.round((Math.max(v, 0) / max) * 100))}%` } : undefined} />;
      })}
    </span>
  );
}

/** The latest point: its stored figure with its source, or the stored reason there is none. */
export function MeasureNow({ series }: { series: MeasureSeries }) {
  const last = series.points.at(-1);
  if (!last) return <Absent reason="No period has been tested yet" />;
  return last.fact ? <FactFigure fact={last.fact} /> : <span className="sq-muted">{last.note ?? 'Not measured'}</span>;
}
```

- [ ] **Step 11: The client file shell and its views**

```tsx
// frontend/src/squad/clientfile/ClientFile.tsx
import { Link, useParams } from '@tanstack/react-router';
import { useBorrowerByCode } from '@/api/hooks';
import { clientFile, threadHref, type ClientFileView } from '../links';
import { Covenants, Documents, Funding, History, Loans, Overview, Reviews, Spreads } from './views';

const VIEWS: Array<[ClientFileView, string]> = [
  ['overview', 'Overview'], ['spreads', 'Spreads'], ['covenants', 'Covenants'], ['documents', 'Documents'],
  ['funding', 'Funding'], ['loans', 'Loans and terms'], ['reviews', 'Reviews'], ['history', 'History'],
];
const BODY = { overview: Overview, spreads: Spreads, covenants: Covenants, documents: Documents, funding: Funding, loans: Loans, reviews: Reviews, history: History };

/** The client file: the detail behind a thread. Every figure opens its source in the evidence drawer, which pushes the file aside. */
export function ClientFile() {
  const { code, view = 'overview' } = useParams({ strict: false }) as { code: string; view?: string };
  const { borrower, notFound } = useBorrowerByCode(code);
  if (notFound)
    return (
      <div role="alert" className="sq-card">
        <p>There is no client with that code.</p>
        <Link to="/" className="sq-link">Back to Squad</Link>
      </div>
    );
  if (!borrower) return <p role="status" className="sq-muted">Opening the client file.</p>;
  const current = VIEWS.find(([id]) => id === view)?.[0];
  const Body = current ? BODY[current] : null;
  return (
    <div className="sq-file" data-ready="">
      <header className="sq-threadhead">
        <div>
          <h1 className="sq-h1">{borrower.name}</h1>
          <p className="sq-faint">Client file · <span className="sq-mono">{borrower.code}</span></p>
        </div>
        <Link {...threadHref(borrower.code)} className="sq-link">Back to the thread</Link>
      </header>
      <nav aria-label="Client file" className="sq-tabs">
        {VIEWS.map(([id, label]) => (
          <Link key={id} to={clientFile(borrower.code, id)} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>
        ))}
      </nav>
      {Body ? <Body borrower={borrower} /> : (
        <p role="alert">There is no such part of the client file. <Link to={clientFile(borrower.code)} className="sq-link">Open the overview</Link></p>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/squad/clientfile/views.tsx
import { useSearch } from '@tanstack/react-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  useActions, useBorrowerCovenants, useBorrowerOverview, useBorrowerTerms, useBorrowingBase, useDocuments, useFactsById,
  useReviewSheet, useReviewSheets, useSignals, useSpread, useTimeline,
} from '@/api/hooks';
import type { BorrowerRow, FactSummary } from '@/api/schema';
import { formatDate } from '@/design';
import { OUTCOME, signalLabel } from '@/domain/labels';
import { RunStage } from '@/screens/borrower/RunStage';
import { UploadDocument } from '@/screens/borrower/UploadDocument';
import { describeEvent } from '@/screens/Governance';
import { Commentary } from '@/screens/review/Commentary';
import { useSource } from '@/source/context';
import { Absent, FactFigure, SourcedFigure } from '@/source/figures';
import { useFundingEvents, useMeasure } from '../api/hooks';
import { Time } from '../thread/Time';
import { MeasureNow, TrendBars } from './Measure';

type Props = { borrower: BorrowerRow };
const DOC_WORDS: Record<string, string> = {
  mrr_report: 'MRR report', bank_statement: 'Bank account statement', monthly_financials: 'Monthly financial statements',
  credit_agreement: 'Credit agreement', compliance_certificate: 'Compliance certificate', term_sheet: 'Term sheet',
  investor_update: 'Investor update', borrowing_base_certificate: 'Borrowing base certificate', receivables_aging: 'Receivables aging',
  annual_statements: 'Annual financial statements', interim_statements: 'Interim financial statements', amendment: 'Amendment', waiver: 'Waiver',
};
/** The same words the server uses (`app/squad/words.py::document_type_words`); kept in step by the client file test. */
export const docWords = (t: string | null) => (t ? (DOC_WORDS[t] ?? t.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())) : 'Not yet classified');

function Loading({ what }: { what: string }) {
  return <p role="status" className="sq-muted">Reading {what}.</p>;
}
function Failed({ what }: { what: string }) {
  return <p role="alert">{what} could not be loaded. Try again in a moment.</p>;
}

export function Overview({ borrower }: Props) {
  const overview = useBorrowerOverview(borrower.id);
  const measure = useMeasure(borrower.id);
  const signals = useSignals({ borrower_id: borrower.id });
  if (overview.isPending) return <Loading what="the overview" />;
  if (overview.error || !overview.data) return <Failed what="The overview" />;
  const { exposure, cycle } = overview.data;
  return (
    <div className="sq-filegrid">
      <section className="sq-card" aria-label="Exposure">
        <h2 className="sq-h2">Exposure</h2>
        <dl className="sq-defs">
          {Object.entries(exposure).map(([key, fact]) => (
            <div key={key}><dt>{fact?.label ?? key}</dt><dd>{fact ? <FactFigure fact={fact} /> : <Absent />}</dd></div>
          ))}
        </dl>
      </section>
      <section className="sq-card" aria-label={measure.data?.label ?? 'Measure'}>
        <h2 className="sq-h2">{measure.data?.label ?? 'Measure'}</h2>
        {measure.data ? (
          <>
            <MeasureNow series={measure.data} />
            <TrendBars points={measure.data.points} label={measure.data.label} />
          </>
        ) : <Loading what="the measure" />}
      </section>
      <section className="sq-card" aria-label="This cycle">
        <h2 className="sq-h2">This cycle</h2>
        {cycle ? (
          <>
            <p>Period ended {formatDate(cycle.period_end)} · {cycle.status === 'closed' ? 'closed' : `at ${cycle.stage.replace(/_/g, ' ')}`}</p>
            {cycle.status !== 'closed' ? <RunStage cycle={cycle} /> : null}
          </>
        ) : <p className="sq-muted">No cycle has been opened for this client yet.</p>}
      </section>
      <section className="sq-card" aria-label="Signals">
        <h2 className="sq-h2">Signals</h2>
        {(signals.data ?? []).length === 0 ? <p className="sq-muted">No open signal.</p> : (
          <ul className="sq-plainlist">
            {(signals.data ?? []).map((s) => <li key={s.id}><span className={`sq-dotmark sq-sev-${s.severity}`} aria-hidden /> {signalLabel(s.rule_id)} · <span className="sq-faint">{formatDate(s.period_end)}</span></li>)}
          </ul>
        )}
      </section>
    </div>
  );
}

export function Spreads({ borrower }: Props) {
  const spread = useSpread(borrower.id);
  const periods = useMemo(() => (spread.data?.periods ?? []).slice(-6), [spread.data]);
  const ids = useMemo(() => (spread.data?.lines ?? []).flatMap((l) => periods.map((p) => l.cells[p.period_end]?.fact_id)), [spread.data, periods]);
  const facts = useFactsById(ids);
  if (spread.isPending) return <Loading what="the spread" />;
  if (spread.error || !spread.data) return <Failed what="The spread" />;
  const lines = spread.data.lines.filter((l) => periods.some((p) => l.cells[p.period_end]));
  if (lines.length === 0) return <p className="sq-muted">Nothing has been spread for this client yet.</p>;
  return (
    <div className="sq-tablewrap">
      <table className="sq-table" aria-label="Spread">
        <thead><tr><th scope="col">Line</th>{periods.map((p) => <th key={p.period_end} scope="col" className="sq-num">{formatDate(p.period_end)}{p.months ? ` · ${p.months} mo` : ''}</th>)}</tr></thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.key}>
              <th scope="row">{l.label}</th>
              {periods.map((p) => {
                const cell = l.cells[p.period_end];
                const fact: FactSummary | undefined = cell ? facts.data?.[cell.fact_id] : undefined;
                return <td key={p.period_end} className="sq-num">{cell ? (fact ? <FactFigure fact={fact} align="column" /> : <span className="sq-faint">Reading</span>) : <Absent align="column" />}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const NOTE_WORDS: Record<string, string> = { not_meaningful_cash_flow_positive: 'Not meaningful: cash-flow positive' };

export function Covenants({ borrower }: Props) {
  const covenants = useBorrowerCovenants(borrower.id);
  if (covenants.isPending) return <Loading what="the covenants" />;
  if (covenants.error || !covenants.data) return <Failed what="The covenants" />;
  const { tests, facts } = covenants.data;
  const latest = tests.length ? tests[0].period_end : null;
  const current = tests.filter((t) => t.period_end === latest);
  if (current.length === 0) return <p className="sq-muted">No covenant has been tested for this client yet.</p>;
  return (
    <div className="sq-tablewrap">
      <p className="sq-faint">Tested for the period ended {formatDate(latest as string)}</p>
      <table className="sq-table" aria-label="Covenants">
        <thead><tr><th scope="col">Covenant</th><th scope="col" className="sq-num">Value</th><th scope="col" className="sq-num">Limit</th><th scope="col" className="sq-num">Headroom</th><th scope="col">Outcome</th></tr></thead>
        <tbody>
          {current.map((t) => {
            const note = t.note ? (NOTE_WORDS[t.note] ?? t.note.replace(/_/g, ' ')) : null;
            return (
              <tr key={t.id}>
                <th scope="row">{t.covenant_name}{t.terms_version ? <span className="sq-faint"> · terms v{t.terms_version.version}</span> : null}</th>
                <td className="sq-num">{t.value_fact_id && facts[t.value_fact_id] ? <FactFigure fact={facts[t.value_fact_id]} align="column" /> : <Absent align="column" reason={note ?? 'Not measured'} />}</td>
                <td className="sq-num">{t.threshold_fact_id && facts[t.threshold_fact_id] ? <FactFigure fact={facts[t.threshold_fact_id]} align="column" /> : <Absent align="column" />}</td>
                <td className="sq-num">{t.headroom_fact_id && facts[t.headroom_fact_id] ? <FactFigure fact={facts[t.headroom_fact_id]} align="column" /> : <Absent align="column" />}</td>
                <td>{['breach', 'breach_reported_compliant'].includes(t.outcome) ? <span className="sq-tag sq-tag-breach">{OUTCOME[t.outcome].label}</span> : OUTCOME[t.outcome]?.label ?? t.outcome}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Documents({ borrower }: Props) {
  const documents = useDocuments(borrower.id);
  const source = useSource();
  const search = useSearch({ strict: false }) as { document?: string; page?: number };
  const opened = useRef<string | undefined>(undefined);
  const [uploading, setUploading] = useState(false);
  const rows = documents.data ?? [];
  useEffect(() => {
    const doc = rows.find((d) => d.id === search.document);
    if (!doc || opened.current === doc.id) return;
    opened.current = doc.id;
    source.open({ type: 'document', documentId: doc.id, page: search.page ?? 1, title: doc.title, borrowerCode: borrower.code });
  }, [rows, search.document, search.page, source, borrower.code]);
  if (documents.isPending) return <Loading what="the documents" />;
  if (documents.error) return <Failed what="The documents" />;
  return (
    <div>
      <button type="button" className="sq-btn" onClick={() => setUploading((u) => !u)} aria-expanded={uploading}>File a document</button>
      {uploading ? <UploadDocument borrowerId={borrower.id} code={borrower.code} onClose={() => setUploading(false)} /> : null}
      {rows.length === 0 ? <p className="sq-muted">No document is on file for this client.</p> : (
        <table className="sq-table" aria-label="Documents">
          <thead><tr><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Period</th><th scope="col">Received</th></tr></thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <th scope="row"><button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => source.open({ type: 'document', documentId: d.id, page: 1, title: d.title, borrowerCode: borrower.code })}>{d.title}</button>{d.status === 'rejected' ? <span className="sq-faint"> · set aside</span> : null}</th>
                <td>{docWords(d.doc_type)}</td>
                <td>{d.period_end ? formatDate(d.period_end) : <span className="sq-faint">None</span>}</td>
                <td>{d.received_date ? formatDate(d.received_date) : <span className="sq-faint">Not recorded</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const FUNDING_KIND: Record<string, string> = { equity_round: 'Equity round', extension: 'Extension', milestone_tranche: 'Milestone tranche', venture_debt: 'Venture debt' };

export function Funding({ borrower }: Props) {
  const events = useFundingEvents(borrower.id);
  if (events.isPending) return <Loading what="the funding events" />;
  if (events.error || !events.data) return <Failed what="The funding events" />;
  if (events.data.length === 0) return <p className="sq-muted">No funding event is recorded for this client.</p>;
  return (
    <table className="sq-table" aria-label="Funding events">
      <thead><tr><th scope="col">Event</th><th scope="col" className="sq-num">Amount</th><th scope="col">Expected close</th><th scope="col">Status</th></tr></thead>
      <tbody>
        {events.data.map((e) => (
          <tr key={e.id}>
            <th scope="row">{FUNDING_KIND[e.kind] ?? e.kind}</th>
            <td className="sq-num">
              <SourcedFigure value={e.amount} unit="usd" kind="manual" label={`${FUNDING_KIND[e.kind] ?? e.kind} amount`} align="column"
                source={{ type: 'record', kind: 'manual', title: 'Funding event', value: e.amount, rows: [['Kind', FUNDING_KIND[e.kind] ?? e.kind], ['Expected close', formatDate(e.expected_close)], ['Status', e.status]], note: 'Recorded by a person on the funding event; not read from a document.' }} />
            </td>
            <td>{formatDate(e.expected_close)}</td>
            <td>{e.status === 'slipped' ? <span className="sq-tag sq-tag-attention">Slipped</span> : e.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Loans({ borrower }: Props) {
  const terms = useBorrowerTerms(borrower.id);
  const base = useBorrowingBase(borrower.id);
  if (terms.isPending) return <Loading what="the loans" />;
  if (terms.error || !terms.data) return <Failed what="The loans" />;
  return (
    <div className="sq-filegrid">
      {terms.data.map((loan) => (
        <section key={loan.id} className="sq-card" aria-label={loan.name}>
          <h2 className="sq-h2">{loan.name}</h2>
          <p>
            Commitment{' '}
            <SourcedFigure value={loan.commitment} unit="usd" kind="system" label={`${loan.name} commitment`}
              source={{ type: 'record', kind: 'system', title: loan.name, value: loan.commitment, rows: [['Loan', loan.code], ['Type', loan.facility_type.replace('_', ' ')]], note: 'From the loan record.' }} />
          </p>
          <ul className="sq-plainlist">
            {loan.terms_versions.map((v) => (
              <li key={v.id}>Terms v{v.version} · {v.in_force ? 'in force' : v.status}{v.approved_by_name ? ` · approved by ${v.approved_by_name}` : ''} · {v.covenants.map((c) => c.name).join(', ')}</li>
            ))}
          </ul>
        </section>
      ))}
      {(base.data ?? []).slice(0, 1).map((r) => (
        <section key={r.id} className="sq-card" aria-label="Borrowing base">
          <h2 className="sq-h2">Borrowing base · {formatDate(r.period_end)}</h2>
          <p>Availability {r.availability_fact ? <FactFigure fact={r.availability_fact} /> : <Absent />}</p>
          <p className="sq-muted">{r.outcome.replace(/_/g, ' ')}</p>
        </section>
      ))}
    </div>
  );
}

export function Reviews({ borrower }: Props) {
  const sheets = useReviewSheets({ borrower_id: borrower.id });
  const actions = useActions({ status: 'all', borrower_id: borrower.id });
  const [open, setOpen] = useState<string | null>(null);
  const sheet = useReviewSheet(open);
  if (sheets.isPending) return <Loading what="the reviews" />;
  if (sheets.error || !sheets.data) return <Failed what="The reviews" />;
  return (
    <div>
      {sheets.data.length === 0 ? <p className="sq-muted">No review sheet has been prepared. One is built when the cycle reaches review preparation.</p> : (
        <ul className="sq-plainlist" aria-label="Review sheets">
          {sheets.data.map((s) => (
            <li key={s.id}><button type="button" className="sq-link" aria-expanded={open === s.id} onClick={() => setOpen(open === s.id ? null : s.id)}>Review for the period ended {formatDate(s.period_end)}</button> · <span className="sq-faint">{s.status === 'draft' ? 'draft, not yet approved' : s.status}</span></li>
          ))}
        </ul>
      )}
      {open && sheet.data ? <Commentary sheet={sheet.data} /> : null}
      <h2 className="sq-h2">Actions</h2>
      {(actions.data ?? []).length === 0 ? <p className="sq-muted">No action has been raised for this client.</p> : (
        <ul className="sq-plainlist">{(actions.data ?? []).map((a) => <li key={a.id}>{a.title} · <span className="sq-faint">{a.owner_name ?? 'No owner'}{a.due_date ? ` · due ${formatDate(a.due_date)}` : ''}</span></li>)}</ul>
      )}
    </div>
  );
}

export function History({ borrower }: Props) {
  const timeline = useTimeline(borrower.id);
  if (timeline.isPending) return <Loading what="the history" />;
  if (timeline.error || !timeline.data) return <Failed what="The history" />;
  if (timeline.data.length === 0) return <p className="sq-muted">Nothing has been recorded for this client yet.</p>;
  return (
    <ol className="sq-plainlist" aria-label="History">
      {timeline.data.map((e) => (
        <li key={e.seq}><Time ts={e.ts} /> · <b>{e.actor_name ?? e.actor_type}</b> · {e.action.replace(/[._]/g, ' ')}{describeEvent(e) ? ` · ${describeEvent(e)}` : ''}</li>
      ))}
    </ol>
  );
}
```

Add to the client file test file one consistency check so the two word lists cannot drift:

```tsx
import { docWords } from '../clientfile/views';
it('reads document types in the server’s words', () => {
  expect(docWords('mrr_report')).toBe('MRR report');
  expect(docWords('bank_statement')).toBe('Bank account statement');
  expect(docWords(null)).toBe('Not yet classified');
});
```

- [ ] **Step 12: Routes, redirects, the source drawer link, the thread**

In `frontend/src/router.tsx`, add the two client file routes and list them in `routeTree` after `clientRoute`:

```tsx
export const clientFileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code/file',
  component: lazyRouteComponent(() => import('@/squad/clientfile/ClientFile'), 'ClientFile'),
});
export const clientFileViewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/clients/$code/file/$view',
  component: lazyRouteComponent(() => import('@/squad/clientfile/ClientFile'), 'ClientFile'),
  validateSearch: (search: Record<string, unknown>): { document?: string; page?: number } => clean({ document: str(search.document), page: int(search.page) }),
});
```

Leave the cockpit routes (`/borrowers…`, `/command-centre`, `/agent-activity`, `/governance`, `/calendar`, `/review-room`, `/design`) registered: the cockpit screens are typed against their ids (`useSearch({ from: '/borrowers/$code/covenants' })` and others) and would stop compiling. Nothing in Squad links to them any more after this task; Task 5 deletes the screens and swaps those routes for redirects through `oldAddress` in the same commit.

In `frontend/src/source/SourceDrawer.tsx`, `ViewerLink` points into the client file:

```tsx
    <Link
      to="/clients/$code/file/$view"
      params={{ code, view: 'documents' }}
      search={{ document: documentId, page: page ?? 1 }}
      onClick={onNavigate}
      className="link inline-flex items-center gap-0.5 text-body font-medium"
    >
      Open in the client file
      <ArrowUpRight size={12} aria-hidden />
    </Link>
```

(Update `SourceDrawer.test.tsx` if it asserts the old link text or address.) In `frontend/src/squad/thread/messages.tsx`, the `document` branch shows `message.doc_type_words`, and a new branch renders arrivals:

```tsx
    case 'arrivals':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>{message.title}</b> <Time ts={message.ts} /></header>
          <ul className="sq-plainlist">
            {message.documents.map((d) => (
              <li key={d.document_id}>
                <button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => source.open({ type: 'document', documentId: d.document_id, page: 1, title: d.title, borrowerCode })}>{d.title}</button>
                <span className="sq-faint"> · {d.doc_type_words} · {d.pages} {d.pages === 1 ? 'page' : 'pages'}</span>
              </li>
            ))}
          </ul>
        </article>
      );
```

In `frontend/src/squad/thread/ClientThread.tsx`, wrap each message in `<div key={m.id} data-message-id={m.id}>…</div>`, and after the existing focus effect add the opening effect (once per client; `?case=` wins):

```tsx
  const opened = useRef<string | undefined>(undefined);
  useEffect(() => {
    const data = thread.data;
    if (focusId || !data?.opening_id || opened.current === data.borrower.id) return;
    const el = document.querySelector(`[data-message-id="${CSS.escape(data.opening_id)}"]`);
    if (!el) return;
    opened.current = data.borrower.id;
    el.scrollIntoView?.({ block: 'start' });
  }, [focusId, thread.data]);
```

(If jsdom lacks `CSS.escape`, use the id unescaped: message ids contain only letters, digits, `:` and `-`, and wrap the selector value in double quotes as above.)

Append to `squad.css`:

```css
.sq-tabs { display: flex; flex-wrap: wrap; gap: 4px; margin: 12px 0 16px; border-bottom: 1px solid var(--sq-line); }
.sq-tab { padding: 6px 10px; color: var(--sq-ink2); text-decoration: none; border-bottom: 2px solid transparent; }
.sq-tab[aria-current='page'] { color: var(--sq-ink); border-bottom-color: var(--sq-ink); font-weight: 600; }
.sq-filegrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.sq-tablewrap { overflow-x: auto; }
.sq-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.sq-table th, .sq-table td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--sq-line); vertical-align: baseline; }
.sq-table .sq-num { text-align: right; }
.sq-defs { display: grid; gap: 6px; margin: 0; }
.sq-defs div { display: flex; justify-content: space-between; gap: 12px; }
.sq-mono { font-family: 'JetBrains Mono Variable', monospace; font-size: 12px; }
.sq-bars { display: inline-flex; align-items: flex-end; gap: 3px; height: 28px; vertical-align: middle; }
.sq-bar { width: 8px; background: var(--sq-ink3); border-radius: 2px; }
.sq-bar-none { height: 100%; background: transparent; border: 1px dashed var(--sq-line-strong); }
.sq-tag-breach { border-color: var(--sq-bad); color: var(--sq-ink); font-weight: 600; }
.sq-tag-attention { border-color: var(--sq-warn); color: var(--sq-ink); }
```

(`--sq-ink3`, `--sq-bad` and `--sq-warn` are existing look tokens in `looks.ts`; red for a breach, amber for needs-attention, as the colour rules say.)

- [ ] **Step 13: Run the front-end checks**

Run: `cd frontend && pnpm vitest run src/squad src/source && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 14: Commit**

```bash
uv run pytest backend/tests/squad -q && (cd frontend && pnpm vitest run src/squad src/source && pnpm typecheck && pnpm lint) && \
git add backend/app/squad backend/app/api/routes_squad.py backend/tests/squad frontend/src && \
git commit -m "feat(p4b): redesigned client file with every figure sourced; threads open at what is new and group arrivals; old addresses redirect

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

---
### Task 3: My Portfolio, track records and remembered habits, a calmer briefing, a readable nav

**Files:**
- Create: `backend/app/squad/portfolio.py`, `backend/tests/squad/test_portfolio.py`
- Modify: `backend/app/squad/briefing.py`, `backend/app/squad/threads.py`, `backend/app/api/routes_squad.py`, `backend/tests/squad/test_briefing.py`
- Create: `frontend/src/squad/portfolio/Portfolio.tsx`, `frontend/src/squad/__tests__/portfolio.test.tsx`
- Modify: `frontend/src/squad/home/SquadHome.tsx`, `frontend/src/squad/shell/SquadNav.tsx`, `frontend/src/squad/shell/surface.ts`, `frontend/src/squad/thread/AskMessage.tsx`, `frontend/src/squad/clientfile/views.tsx` (Overview), `frontend/src/squad/api/types.ts`, `hooks.ts`, `polling.ts`, `frontend/src/router.tsx`, `frontend/src/squad/squad.css`, `frontend/src/squad/__tests__/home.test.tsx`, `shell.test.tsx`, `cockpitSurface.test.tsx`, `frontend/e2e/squad.mjs`

**Interfaces:**
- Consumes: Task 2's `measure_series(db, borrower, limit)`, `TrendBars`, `MeasureNow`, `MeasureSeries`; 4a's `track_record(db, borrower_id)` and `GET /borrowers/{id}/track-record` (`TrackRecordRow[]`); `Lesson` (`app.domain.agents`); `SIGNAL_LABELS` (`app.publishing.content`).
- Produces (backend): `app.squad.portfolio.build_portfolio(db, user) -> {"as_of": iso, "sections": [{"template_id": "vc-1" | "ci-1", "title": str, "measure_label": str, "rows": [PortfolioRow]}]}` where `PortfolioRow = {"borrower_id", "code", "name", "analyst": str | None, "mine": bool, "open": int, "measure": MeasureSeries}`, rows sorted by the latest stored figure, lowest first, unmeasured last (sorted in Python on Decimals; the browser never sorts by value); `lessons_for(db, borrower_id) -> [{"id", "topic", "tag", "text", "by", "at", "work_item_id"}]`; `GET /api/v1/me/portfolio`; `GET /api/v1/borrowers/{id}/lessons`; `ask` messages gain `habits: [{"text", "by", "at"}]`. Briefing: `kind == "signal"` rows are one per client, `needs_you` always false, `state == "watching"`, title `"Signal: <label>"` for one and `"Signals: <a>, <b>"` for several.
- Produces (front end): route `/portfolio` (Squad's `Portfolio`), hooks `usePortfolio()` (key `['my-portfolio']`), `useTrackRecord(borrowerId)`, `useLessons(borrowerId)`; types `PortfolioRow`, `PortfolioSection`, `Habit`; `SquadNav` collapsed shows one "Open cases" button instead of one circle per client.

- [ ] **Step 1: Write the failing backend tests**

```python
# backend/tests/squad/test_portfolio.py
from datetime import date
from decimal import Decimal

from app.domain.facts_service import add_fact
from app.domain.lessons import record_lesson
from app.domain.work_items import raise_item
from app.domain.workflow import open_cycle
from app.squad import client_file
from app.squad.portfolio import build_portfolio, lessons_for
from app.squad.questions import raise_question
from app.squad.threads import build_thread

from .conftest import sign_in

END = date(2026, 10, 31)


def _venture(db, code, name, runway):
    from app.domain.credit import Borrower
    b = Borrower(code=code, name=name, template_id="vc-1")
    db.add(b)
    db.flush()
    open_cycle(db, borrower_id=b.id, period_end=END, months=1, cycle_type="monthly")
    if runway is not None:
        add_fact(db, borrower_id=b.id, key="metric.rml", period_end=END, months=0, value=Decimal(runway),
                 kind="calculated", unit="count", status="verified")
    return b


def test_venture_clients_are_ordered_by_runway_lowest_first_unmeasured_last(db, world, monkeypatch):
    monkeypatch.setattr(client_file, "runway_not_meaningful", lambda *a: False)
    world["borrower"].template_id = "vc-1"
    long_ = _venture(db, "LNG", "Longwater Robotics, Inc.", "22.5")
    short = _venture(db, "SHT", "Shortfield Bio, Inc.", "7.1")
    none_ = _venture(db, "NON", "Nonesuch Analytics, Inc.", None)
    short.analyst_id = world["analyst"].id
    raise_item(db, borrower_id=short.id, item_type="test.portfolio", title="t", question="Is this fine?",
               allowed_decisions=["yes"])
    out = build_portfolio(db, world["analyst"])
    venture = next(s for s in out["sections"] if s["template_id"] == "vc-1")
    codes = [r["code"] for r in venture["rows"]]
    assert codes.index("SHT") < codes.index("LNG") < codes.index("NON")
    row = next(r for r in venture["rows"] if r["code"] == "SHT")
    assert row["mine"] is True and row["open"] == 1 and row["analyst"] == "Priya Raman"
    assert next(r for r in venture["rows"] if r["code"] == "NON")["measure"]["points"][-1]["fact"] is None
    assert none_.id and long_.id


def test_lessons_are_listed_with_who_wrote_them_and_show_on_a_later_ask(db, world):
    record_lesson(db, borrower_id=world["borrower"].id, topic="line_mapping", text="Recurring revenue here is ARR.",
                  written_by=world["analyst"].id, tag="map_to_arr")
    rows = lessons_for(db, world["borrower"].id)
    assert rows[0]["text"] == "Recurring revenue here is ARR." and rows[0]["by"] == "Priya Raman"
    raise_question(db, borrower_id=world["borrower"].id, title="Map a line", question="ARR or MRR?",
                   topic="line_mapping", options=[{"id": "map_to_arr", "label": "ARR", "evidence": "Annual."},
                                                  {"id": "map_to_mrr", "label": "MRR", "evidence": "Monthly."}])
    ask = next(m for m in build_thread(db, world["borrower"].id, world["analyst"])["messages"] if m["type"] == "ask")
    assert [h["text"] for h in ask["habits"]] == ["Recurring revenue here is ARR."]


def test_portfolio_and_lessons_endpoints(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    out = client.get("/api/v1/me/portfolio").json()
    assert {s["template_id"] for s in out["sections"]} <= {"vc-1", "ci-1"}
    assert client.get(f"/api/v1/borrowers/{world['borrower'].id}/lessons").json() == []
```

In `backend/tests/squad/test_briefing.py`, change three tests to the new signal rule (a deliberate rule change, named in the commit):

```python
    signals = [i for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "signal"]
    assert len(signals) == 1 and signals[0]["severity"] == "high" and signals[0]["needs_you"] is False
    assert signals[0]["title"].startswith("Signals: Covenant cushion below the policy floor, ")
    assert signals[0]["title"].count(", ") == 2
```

(in `test_one_signal_per_borrower_the_most_severe`, renamed `test_one_signal_row_per_client_naming_every_signal_most_severe_first`), and in `test_overdue_reports_and_signals_count_only_for_the_clients_analyst` (renamed `test_overdue_reports_count_for_the_clients_analyst_and_signals_never_count`) the first assertion becomes `assert priya["needs_you"] == 1`. `test_a_different_signal_for_the_same_client_is_still_listed` keeps `["Signal: burn rising"]`.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest backend/tests/squad/test_portfolio.py backend/tests/squad/test_briefing.py -q`
Expected: FAIL (`No module named 'app.squad.portfolio'`; the briefing tests fail on `needs_you` and the title).

- [ ] **Step 3: The portfolio read model**

```python
# backend/app/squad/portfolio.py
"""My Portfolio: every client by the one measure it is watched by, lowest first, and the habits people taught Squad.
Values are compared here, as Decimals, so the browser never orders by a parsed figure."""
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.domain.agents import Lesson
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.squad.client_file import measure_series

SECTIONS = (("vc-1", "Innovation clients", "Runway (months)"), ("ci-1", "Commercial and industrial clients",
                                                                  "Tightest covenant headroom"))


def _latest_value(row: dict[str, Any]) -> tuple[int, Decimal]:
    points = row["measure"]["points"]
    fact = points[-1]["fact"] if points else None
    return (0, Decimal(fact["value"])) if fact else (1, Decimal(0))  # unmeasured last; the 0 only breaks no tie


def build_portfolio(db: Session, user: User) -> dict[str, Any]:
    names = {u.id: u.name for u in db.execute(select(User)).scalars()}
    open_items = dict(db.execute(select(WorkItem.borrower_id, func.count()).where(WorkItem.status == "open")
                                 .group_by(WorkItem.borrower_id)).all())
    rows: dict[str, list[dict[str, Any]]] = {t: [] for t, _, _ in SECTIONS}
    for b in db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        rows.setdefault(b.template_id, []).append({
            "borrower_id": str(b.id), "code": b.code, "name": b.name, "analyst": names.get(b.analyst_id),
            "mine": b.analyst_id == user.id, "open": open_items.get(b.id, 0), "measure": measure_series(db, b)})
    sections = []
    for template_id, title, label in SECTIONS:
        if rows.get(template_id):
            sections.append({"template_id": template_id, "title": title, "measure_label": label,
                             "rows": sorted(rows[template_id], key=lambda r: (*_latest_value(r), r["name"]))})
    return {"as_of": clock.today(db).isoformat(), "sections": sections}


def lessons_for(db: Session, borrower_id: uuid.UUID, topic: str | None = None) -> list[dict[str, Any]]:
    names = {u.id: u.name for u in db.execute(select(User)).scalars()}
    query = select(Lesson).where(Lesson.borrower_id == borrower_id).order_by(Lesson.created_at.desc())
    if topic is not None:
        query = query.where(Lesson.topic == topic)
    return [{"id": str(x.id), "topic": x.topic, "tag": x.tag, "text": x.text, "by": names.get(x.written_by, "A person"),
             "at": x.created_at.isoformat(), "work_item_id": str(x.work_item_id) if x.work_item_id else None}
            for x in db.execute(query).scalars()]
```

Endpoints in `routes_squad.py` (import `build_portfolio`, `lessons_for`):

```python
@router.get("/me/portfolio")
def my_portfolio(db: Session = Depends(get_db), user: User = Depends(require(Permission.VIEW))) -> dict:
    return build_portfolio(db, user)


@router.get("/borrowers/{borrower_id}/lessons")
def borrower_lessons(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                     _: User = Depends(require(Permission.VIEW))) -> list[dict]:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return lessons_for(db, borrower_id)
```

In `threads.py`, the `ask` message gains (import `lessons_for` inside the function to avoid an import cycle):

```python
                             "habits": [{"text": h["text"], "by": h["by"], "at": h["at"]}
                                        for h in lessons_for(db, borrower_id, (i.evidence or {}).get("topic"))
                                        if h["work_item_id"] != str(i.id)],
```

- [ ] **Step 4: Signals are listed, one row per client, never counted (`briefing.py`)**

Replace the block from `seen_signals: set = set()` to the end of its loop with:

```python
    # Signals are listed, not counted: a signal that needs a decision has a work item, and that item counts.
    signals = [s for s in db.execute(select(Signal).where(Signal.status == "open")).scalars()
               if (s.borrower_id, s.rule_id) not in raised and s.borrower_id in borrowers]
    signals.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), -x.created_at.timestamp()))
    by_client: dict[Any, list[Signal]] = {}
    for s in signals:
        by_client.setdefault(s.borrower_id, []).append(s)
    for bid, rows in by_client.items():
        labels = list(dict.fromkeys(SIGNAL_LABELS.get(s.rule_id, s.rule_id.replace("_", " ")) for s in rows))
        title = f"Signal: {labels[0]}" if len(labels) == 1 else f"Signals: {', '.join(labels)}"
        items.append({**ref(bid), "key": f"signal:{bid}", "kind": "signal", "title": title, "state": "watching",
                      "severity": rows[0].severity, "needs_you": False, "work_item_id": None, "_due": None})
```

Remove `mine(...)` from the signal rows only; overdue reports keep `"needs_you": mine(ob.borrower_id)`.

- [ ] **Step 5: Run the backend tests**

Run: `uv run pytest backend/tests/squad -q && uv run ruff check backend/app/squad backend/tests/squad`
Expected: PASS.

- [ ] **Step 6: Write the failing front-end tests**

```tsx
// frontend/src/squad/__tests__/portfolio.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { PortfolioRow } from '../api/types';
import { Portfolio } from '../portfolio/Portfolio';

const row = (code: string, name: string, mine: boolean, value: string | null, note: string | null = null): PortfolioRow => ({
  borrower_id: code, code, name, analyst: mine ? 'Priya Raman' : 'Tomas Keller', mine, open: mine ? 2 : 0,
  measure: { kind: 'rml', label: 'Runway (months)', points: [{ period_end: '2026-10-31', note, fact: value ? { id: `f-${code}`, key: 'metric.rml', label: 'Runway', value, unit: 'count', kind: 'calculated', status: 'verified', period_end: '2026-10-31', months: 0, borrower_id: code, document_id: null, page: null, calc_run_id: 'c' } : null }] },
});
const data = { as_of: '2026-11-21', sections: [{ template_id: 'vc-1', title: 'Innovation clients', measure_label: 'Runway (months)', rows: [row('SHT', 'Shortfield Bio, Inc.', true, '7.1'), row('LNG', 'Longwater Robotics, Inc.', false, '22.5'), row('NON', 'Nonesuch Analytics, Inc.', false, null, 'Not meaningful: cash-flow positive')] }] };
vi.mock('../api/hooks', () => ({ usePortfolio: () => ({ data, isPending: false, error: null, refetch: vi.fn() }) }));
vi.mock('@/source/figures', () => ({ FactFigure: ({ fact }: { fact: { value: string } }) => <span>{fact.value} months</span>, Absent: () => <span>Not measured</span> }));

function mount() {
  const root = createRootRoute();
  const page = createRoute({ getParentRoute: () => root, path: '/portfolio', component: Portfolio });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([page, thread]), history: createMemoryHistory({ initialEntries: ['/portfolio'] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

describe('Portfolio', () => {
  it('lists clients in the server’s order, each row opening the client’s thread', async () => {
    mount();
    const table = await screen.findByRole('table', { name: 'Innovation clients' });
    const links = within(table).getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['Shortfield Bio, Inc.', 'Longwater Robotics, Inc.', 'Nonesuch Analytics, Inc.']);
    expect(links[0]).toHaveAttribute('href', '/clients/SHT');
  });

  it('shows the stored note for an unmeasured client, never a zero', async () => {
    mount();
    expect(await screen.findByText('Not meaningful: cash-flow positive')).toBeInTheDocument();
    expect(screen.queryByText(/^0 months/)).not.toBeInTheDocument();
  });

  it('narrows to the analyst’s own clients and back', async () => {
    mount();
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Only my clients' }));
    expect(screen.getAllByRole('link').map((l) => l.textContent)).toEqual(['Shortfield Bio, Inc.']);
    await userEvent.click(screen.getByRole('checkbox', { name: 'Only my clients' }));
    expect(screen.getAllByRole('link')).toHaveLength(3);
  });
});
```

In `home.test.tsx`, add:

```tsx
  it('lists signals under Watching, grouped by client, and never counts them', async () => {
    mount(briefing([
      item({ key: 'a', needs_you: true }),
      item({ key: 's1', kind: 'signal', needs_you: false, state: 'watching', title: 'Signals: runway falling, burn rising', work_item_id: null }),
      item({ key: 'f1', kind: 'funding', needs_you: false, state: 'expected', title: 'Expected equity round closes 30 November', work_item_id: null }),
      item({ key: 's2', kind: 'signal', needs_you: false, state: 'watching', title: 'Signal: revenue below plan', work_item_id: null, borrower_id: 'b2', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.' }),
    ]));
    expect(await screen.findByText('1 needs you')).toBeInTheDocument();
    const watching = screen.getByRole('region', { name: 'Watching' });
    const groups = within(watching).getAllByRole('group');
    expect(groups.map((g) => within(g).getAllByText(/Inc\./)[0].textContent)).toEqual(['Quillfeather Labs, Inc.', 'Zephyr Zinc Works, Inc.']);
    expect(within(groups[0]).getByText(/runway falling, burn rising/)).toBeInTheDocument();
  });
```

In `shell.test.tsx`: in "names every link when collapsed" remove `/quillfeather/i` from the list, and add:

```tsx
  it('shows one Open cases button when collapsed, not a circle per client, and expands to the names', async () => {
    const toggle = vi.fn();
    mountNav({ collapsed: true, onToggle: toggle });
    expect(await screen.findByRole('link', { name: /squad/i })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: /open cases/i })).not.toBeInTheDocument();
    expect(document.querySelectorAll('.sq-initial')).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'Open cases: 1 client' }));
    expect(toggle).toHaveBeenCalled();
  });
```

In `cockpitSurface.test.tsx`, move `'/portfolio'` from the cockpit list to the Squad list; in `mountAt`, the route list becomes `['/', '/calendar', '/portfolio']`; the test "gives a legacy cockpit route the full width and no presence line" mounts `/calendar` (still a cockpit screen until Task 5); add a test that `/portfolio` mounts with `data-surface="squad"` and a presence line.

- [ ] **Step 7: Run them to see them fail**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/portfolio.test.tsx src/squad/__tests__/home.test.tsx src/squad/__tests__/shell.test.tsx src/squad/__tests__/cockpitSurface.test.tsx`
Expected: FAIL (`Cannot find module '../portfolio/Portfolio'`; the home and nav tests fail on the missing region and button).

- [ ] **Step 8: Types, hooks, refresh**

Append to `types.ts`:

```ts
export interface PortfolioRow { borrower_id: string; code: string; name: string; analyst: string | null; mine: boolean; open: number; measure: MeasureSeries }
export interface PortfolioSection { template_id: 'vc-1' | 'ci-1'; title: string; measure_label: string; rows: PortfolioRow[] }
export interface Habit { text: string; by: string; at: string }
export interface LessonRow extends Habit { id: string; topic: string; tag: string | null; work_item_id: string | null }
```

Give the `ask` member of `ThreadMessage` the field `habits: Habit[]` (ask fixtures in the tests gain `habits: []`). Append to `hooks.ts`:

```ts
export const usePortfolio = () => useQuery({ queryKey: ['my-portfolio'], queryFn: () => get<{ as_of: string; sections: PortfolioSection[] }>('/me/portfolio') });
export const useTrackRecord = (borrowerId?: string) =>
  useQuery({ queryKey: ['track-record', borrowerId], queryFn: () => get<TrackRecordRow[]>(`/borrowers/${borrowerId}/track-record`), enabled: Boolean(borrowerId) });
export const useLessons = (borrowerId?: string) =>
  useQuery({ queryKey: ['lessons', borrowerId], queryFn: () => get<LessonRow[]>(`/borrowers/${borrowerId}/lessons`), enabled: Boolean(borrowerId) });
```

Add `['my-portfolio']` and `['lessons']` to `REFRESH` in `polling.ts`.

- [ ] **Step 9: The portfolio screen and route**

```tsx
// frontend/src/squad/portfolio/Portfolio.tsx
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { usePortfolio } from '../api/hooks';
import { MeasureNow, TrendBars } from '../clientfile/Measure';
import { threadHref } from '../links';

/** Every client by the measure it is watched by, lowest first as the server orders it; a row opens the client's thread. */
export function Portfolio() {
  const portfolio = usePortfolio();
  const [mineOnly, setMineOnly] = useState(false);
  if (portfolio.isPending) return <p role="status" className="sq-muted">Reading the portfolio.</p>;
  if (portfolio.error || !portfolio.data)
    return (
      <div role="alert">
        <p>The portfolio could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void portfolio.refetch()}>Try again</button>
      </div>
    );
  const { sections } = portfolio.data;
  return (
    <div className="sq-portfolio" data-ready="">
      <h1 className="sq-h1">My Portfolio</h1>
      <label className="sq-check"><input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} /> Only my clients</label>
      {sections.map((s) => {
        const rows = s.rows.filter((r) => !mineOnly || r.mine);
        return (
          <section key={s.template_id} aria-label={s.title}>
            <h2 className="sq-h2">{s.title}</h2>
            {rows.length === 0 ? <p className="sq-muted">None of these clients is yours.</p> : (
              <table className="sq-table" aria-label={s.title}>
                <thead><tr><th scope="col">Client</th><th scope="col">Analyst</th><th scope="col" className="sq-num">Open</th><th scope="col" className="sq-num">{s.measure_label}</th><th scope="col">Trend</th></tr></thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.borrower_id}>
                      <th scope="row"><Link {...threadHref(r.code)} className="sq-link">{r.name}</Link></th>
                      <td>{r.analyst ?? <span className="sq-faint">No analyst</span>}</td>
                      <td className="sq-num">{r.open}</td>
                      <td className="sq-num"><MeasureNow series={r.measure} /></td>
                      <td><TrendBars points={r.measure.points} label={`${r.name}: ${s.measure_label}`} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        );
      })}
    </div>
  );
}
```

In `router.tsx`, `portfolioRoute` loads `@/squad/portfolio/Portfolio` (export `Portfolio`). In `surface.ts`, add `'/portfolio'` to `SQUAD`. Append `.sq-check { display: inline-flex; gap: 6px; align-items: center; margin: 4px 0 8px; }` to `squad.css`.

- [ ] **Step 10: A calmer briefing**

Replace the body of `SquadHome` after the error guard with:

```tsx
  const { items, overnight } = briefing.data;
  const needs = items.filter((i) => i.needs_you);
  const decided = items.filter((i) => !i.needs_you && i.kind === 'decided');
  const watching = items.filter((i) => !i.needs_you && i.kind !== 'decided');
  const clients = [...new Map(watching.map((i) => [i.borrower_id, i.borrower_name])).entries()];
  return (
    <div className="sq-home">
      <h1 className="sq-h1">Hello, {user?.name.split(' ')[0] ?? 'there'}.</h1>
      <h2 className="sq-lede">{needs.length ? word(needs.length) : 'Nothing needs you.'}</h2>
      {needs.length > 0 ? (
        <ul className="sq-list" aria-label="Needs you">
          {needs.map((i) => <Row key={i.key} item={i} />)}
        </ul>
      ) : null}
      {clients.length > 0 ? (
        <section aria-label="Watching">
          <h2 className="sq-h2">Watching</h2>
          {clients.map(([id, name]) => {
            const rows = watching.filter((i) => i.borrower_id === id);
            return (
              <details key={id} className="sq-group" role="group" aria-label={name}>
                <summary><b>{name}</b> <span className="sq-faint">· {rows.length === 1 ? rows[0].title : `${rows.length} things to watch`}</span></summary>
                <ul className="sq-list">{rows.map((i) => <Row key={i.key} item={i} />)}</ul>
              </details>
            );
          })}
        </section>
      ) : null}
      {decided.length > 0 ? (
        <details className="sq-group">
          <summary className="sq-h2">Recently decided</summary>
          <ul className="sq-list" aria-label="Recently decided">{decided.map((i) => <Row key={i.key} item={i} />)}</ul>
        </details>
      ) : null}
      {overnight.length > 0 ? (
        <details className="sq-group">
          <summary className="sq-h2">What Squad did overnight ({overnight.length})</summary>
          <ul className="sq-list" aria-label="Overnight">
            {overnight.map((o) => (
              <li key={`${o.agent_name}|${o.finished_at}|${o.borrower_id}`} className="sq-card sq-squad">
                <p className="sq-faint"><b>{o.agent_name.charAt(0).toUpperCase() + o.agent_name.slice(1)} agent</b> · {o.borrower_name}</p>
                <AgentBody text={o.text} />
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
```

The test's group name assertion reads the `<b>` text; keep the client name as the first text in the summary. Existing home tests that look for the list "Also on the record" move to "Watching" (update their queries to `getByRole('region', { name: 'Watching' })`); tests on the overnight list open the `details` first (`await userEvent.click(screen.getByText(/What Squad did overnight/))`). Append `.sq-group { margin-top: 8px; } .sq-group > summary { cursor: pointer; padding: 6px 2px; }` to `squad.css`.

- [ ] **Step 11: A nav that reads (`SquadNav.tsx`)**

Replace the Open cases block with:

```tsx
      {openClients.length > 0 && collapsed ? (
        <button type="button" className="sq-navlink sq-navbtn" onClick={onToggle} title="Open cases"
          aria-label={`Open cases: ${openClients.length} ${openClients.length === 1 ? 'client' : 'clients'}`}>
          <FolderOpen size={18} aria-hidden />
          <span className="sq-count">{openClients.length}</span>
        </button>
      ) : null}
      {openClients.length > 0 && !collapsed ? (
        <nav aria-label="Open cases" className="sq-cases">
          <p className="sq-navhead sq-navlabel">Open cases</p>
          {openClients.map((c) => (
            <Link key={c.borrower_id} to="/clients/$code" params={{ code: c.code }} className="sq-navlink" title={c.name}
              aria-current={pathname === `/clients/${c.code}` ? 'page' : undefined}>
              <span className="sq-navlabel sq-grow">{c.name}</span>
              <span className="sq-count sq-navlabel">{c.open}</span>
            </Link>
          ))}
        </nav>
      ) : null}
```

(`FolderOpen` from `lucide-react`.) The Oversight links lose their letter circles the same way: use `Activity` and `Landmark` icons from `lucide-react` in place of `<span className="sq-initial">A</span>` and `G`. Append `.sq-navbtn { background: none; border: 0; font: inherit; cursor: pointer; width: 100%; }` to `squad.css`.

- [ ] **Step 12: Track record and habits where they are used**

In `clientfile/views.tsx` `Overview`, add two sections after Signals (import `useLessons`, `useTrackRecord` from `../api/hooks`):

```tsx
      <section className="sq-card" aria-label="Track record">
        <h2 className="sq-h2">Track record</h2>
        {(track.data ?? []).length === 0 ? <p className="sq-muted">No figure has been read for this client yet.</p> : (
          <table className="sq-table">
            <thead><tr><th scope="col">Task</th><th scope="col" className="sq-num">Checked</th><th scope="col" className="sq-num">Right</th><th scope="col" className="sq-num">Corrected</th><th scope="col">Last correction</th></tr></thead>
            <tbody>
              {(track.data ?? []).map((t) => (
                <tr key={`${t.agent_name}|${t.task}`}>
                  <th scope="row">{t.agent_name.charAt(0).toUpperCase() + t.agent_name.slice(1)} agent · {t.task.replace(/_/g, ' ')}</th>
                  <td className="sq-num">{t.checked}</td><td className="sq-num">{t.right}</td><td className="sq-num">{t.corrected}</td>
                  <td>{t.last_correction_at ? <Time ts={t.last_correction_at} /> : <span className="sq-faint">None</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="sq-card" aria-label="What Squad remembers">
        <h2 className="sq-h2">What Squad remembers</h2>
        {(lessons.data ?? []).length === 0 ? <p className="sq-muted">Nothing has been taught for this client yet.</p> : (
          <ul className="sq-plainlist">{(lessons.data ?? []).map((l) => <li key={l.id}>{l.text} <span className="sq-faint">· {l.by}, <Time ts={l.at} /></span></li>)}</ul>
        )}
      </section>
```

with `const track = useTrackRecord(borrower.id); const lessons = useLessons(borrower.id);` at the top of `Overview`. The counts are the server's (`track_record`), never computed in the browser.

In `AskMessage.tsx`, above the options:

```tsx
      {message.habits.length > 0 ? (
        <div className="sq-habits" aria-label="What Squad remembers">
          {message.habits.map((h) => <p key={h.at} className="sq-faint">Squad remembers: {h.text} ({h.by})</p>)}
        </div>
      ) : null}
```

Give the `ask` fixture in `questions.test.tsx` `habits: []` and add one test that a habit renders as "Squad remembers: …".

- [ ] **Step 13: Journeys for the portfolio**

In `frontend/e2e/squad.mjs`, replace the journey `'portfolio: the nav row opens My Portfolio and a row opens that client'` with:

```js
journey('portfolio: every client appears once, by measure, and each row opens its own thread', async ({ page }) => {
  await signIn(page, ANALYST);
  await page.getByRole('link', { name: /my portfolio/i }).click();
  await page.waitForURL(`${BASE}/portfolio`);
  const data = await api(page, '/me/portfolio');
  const all = data.sections.flatMap((s) => s.rows);
  const borrowers = await api(page, '/borrowers');
  assert(all.length === borrowers.length && new Set(all.map((r) => r.code)).size === all.length, 'a client is missing or listed twice');
  for (const r of all.slice(0, 3)) {
    await page.goto(`${BASE}/portfolio`);
    await page.getByRole('link', { name: r.name, exact: true }).click();
    await page.waitForURL(new RegExp(`/clients/${r.code}$`));
    await page.getByRole('heading', { level: 1, name: r.name }).waitFor();
  }
});
```

and replace the journey `'legacy cockpit route: /portfolio in Night is full width…'` with the same checks on the Squad screen: `.sq-main[data-surface="squad"]`, width at most 1280, the presence line present, the axe run clean, no horizontal scroll.

- [ ] **Step 14: Run the front-end checks**

Run: `cd frontend && pnpm vitest run src/squad && pnpm typecheck && pnpm lint`
Expected: PASS.

- [ ] **Step 15: Commit**

```bash
uv run pytest backend/tests/squad -q && (cd frontend && pnpm vitest run src/squad && pnpm typecheck && pnpm lint) && \
git add backend/app/squad backend/app/api/routes_squad.py backend/tests/squad frontend/src frontend/e2e/squad.mjs && \
git commit -m "feat(p4b): My Portfolio by runway or headroom, track records and habits where used; signals listed not counted; nav without letter circles

The briefing rule changes on purpose: open signals are listed under Watching, one row per client, and no longer
counted as needing the analyst (a signal that needs a decision has a work item, which counts).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

---

### Task 4: Oversight in Squad's looks (agent activity, ledger, governance, evaluations, the clock)

**Files:**
- Create: `frontend/src/squad/oversight/Oversight.tsx`, `frontend/src/squad/oversight/describeEvent.ts`, `frontend/src/squad/__tests__/oversight.test.tsx`
- Modify: `frontend/src/screens/Governance.tsx` (re-export `describeEvent`), `frontend/src/__tests__/workspace.test.tsx` (import path), `frontend/src/squad/clientfile/views.tsx` (import path), `frontend/src/squad/api/hooks.ts`, `frontend/src/squad/shell/SquadNav.tsx`, `commands.ts`, `surface.ts`, `frontend/src/router.tsx`, `frontend/src/squad/__tests__/shell.test.tsx`, `cockpitSurface.test.tsx`

**Interfaces:**
- Consumes: existing endpoints and hooks only (no backend change): `useAgentRuns()` (`GET /agent-runs`), `useLedger(filter)` (`GET /ledger`), `useLedgerVerification(run)` (`GET /ledger/verify`), `useRolesAndPermissions()`, `usePolicyRegister()`, `useClock(signedIn)`, `useSetClock()`; `GET /evals/latest`; `OVERSIGHT_ROLES` (`admin`, `credit_review`, `credit_admin`).
- Produces: route `/oversight` and `/oversight/$tab` with `tab ∈ 'activity' | 'ledger' | 'governance' | 'evaluations' | 'clock'` (`clock` only where `can('advance_clock')`); `describeEvent(event: LedgerEvent) -> string` in `src/squad/oversight/describeEvent.ts`; hook `useEvalLatest()`; `oldAddress` maps `/agent-activity`, `/governance`, `/command-centre` (wired into the router in Task 5).

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/squad/__tests__/oversight.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '@/auth/context';
import { oldAddress } from '../redirects';
import { Oversight } from '../oversight/Oversight';

vi.mock('@/api/hooks', () => ({
  useAgentRuns: () => ({ data: [{ id: 'r1', agent_name: 'covenant', task: 'investigate', borrower_name: 'Quillfeather Labs, Inc.', borrower_code: 'QFL', status: 'abstained', created_at: '2026-11-21T08:00:00Z', duration_ms: 1200, steps_count: 12, input_tokens: 100, output_tokens: 20 }], isPending: false, error: null }),
  useLedger: () => ({ data: [{ seq: 7, id: 'e7', ts: '2026-11-21T08:00:00Z', actor_type: 'user', actor_id: 'u1', actor_name: 'Priya Raman', action: 'work_item.routed', entity_type: 'work_item', entity_id: 'w1', payload: { view: 'Recommend reserving rights.' }, hash: 'h', note: null }], isPending: false, error: null }),
  useLedgerVerification: () => ({ data: undefined, isFetching: false }),
  useRolesAndPermissions: () => ({ data: { roles: [{ id: 'credit_officer', label: 'Credit officer', people: 1 }], permissions: [{ id: 'decide_breach', label: 'Decide the response to a breach', group: 'Exceptions', second_person: false }], grants: { credit_officer: ['decide_breach'] }, second_person: { rule: 'Two people.', applies_to: [] } }, isPending: false, error: null }),
  usePolicyRegister: () => ({ data: { sections: [], signal_rules: { version: '1', rules: [] }, agents: [] }, isPending: false, error: null }),
  useClock: () => ({ data: { today: '2026-11-21' } }),
  useSetClock: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}));
vi.mock('../api/hooks', () => ({ useEvalLatest: () => ({ data: { mode: 'standin', standin: true, notice: 'Stand-in run: not model performance.', gate_passed: true, created_at: '2026-11-21T07:00:00Z', results: { metrics: {} } }, isPending: false, error: null }) }));

function mount(path: string, role = 'credit_review', permissions: string[] = ['view', 'record_qa_finding']) {
  const root = createRootRoute();
  const base = createRoute({ getParentRoute: () => root, path: '/oversight', component: Oversight });
  const tab = createRoute({ getParentRoute: () => root, path: '/oversight/$tab', component: Oversight });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([base, tab, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  const user = { id: 'u9', email: 'r@x', name: 'Ruth Calloway', title: '', role, permissions };
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={{ user, status: 'signed-in', can: (p: string) => permissions.includes(p), signIn: async () => user, signOut: async () => {}, retry: () => {} }}>
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('Oversight', () => {
  it('lists agent runs with their outcome and a link to the client', async () => {
    mount('/oversight/activity');
    const table = await screen.findByRole('table', { name: 'Agent activity' });
    expect(within(table).getByText('Abstained')).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Quillfeather Labs, Inc.' })).toHaveAttribute('href', '/clients/QFL');
  });

  it('describes ledger events in words, including a routed view', async () => {
    mount('/oversight/ledger');
    expect(await screen.findByText(/Recommend reserving rights/)).toBeInTheDocument();
  });

  it('labels a stand-in evaluation as such', async () => {
    mount('/oversight/evaluations');
    expect(await screen.findByText('Stand-in run: not model performance.')).toBeInTheDocument();
  });

  it('offers the clock only to a role that may move it, and never a credit decision', async () => {
    mount('/oversight', 'credit_review');
    expect(await screen.findByRole('navigation', { name: 'Oversight' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Clock' })).not.toBeInTheDocument();
    mount('/oversight', 'admin', ['view', 'change_policy', 'manage_users', 'advance_clock']);
    expect(await screen.findAllByRole('link', { name: 'Clock' })).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: /record decision|send to|return to|attach/i })).not.toBeInTheDocument();
  });

  it('moves the old oversight addresses', () => {
    expect(oldAddress('/agent-activity', {})).toBe('/oversight/activity');
    expect(oldAddress('/governance', {})).toBe('/oversight/governance');
    expect(oldAddress('/command-centre', {})).toBe('/');
  });
});
```

In `cockpitSurface.test.tsx`, add `'/oversight'` and `'/oversight/ledger'` to the Squad list. In `shell.test.tsx`, "lists oversight only for the roles that have it" now finds one link named `Oversight` with `href="/oversight"`; "names every link when collapsed" checks `/oversight/i` in place of `/agent activity/i` and `/governance/i`, and the `mountNav` routes add `'/oversight'`.

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/oversight.test.tsx src/squad/__tests__/shell.test.tsx src/squad/__tests__/cockpitSurface.test.tsx`
Expected: FAIL (`Cannot find module '../oversight/Oversight'`).

- [ ] **Step 3: Move `describeEvent`**

Create `frontend/src/squad/oversight/describeEvent.ts` with the body of `describeEvent` cut from `frontend/src/screens/Governance.tsx` (lines 58–88) and the `UUID` constant (line 32, used only by `describeEvent`; move it, so lint does not flag an unused constant), with its imports (`decisionLabel`, `docTypeLabel`, `humanize`, `roleLabel`, `signalLabel`, `stageLabel`, `STAGE_STATUS_LABEL` from `@/domain/labels`; `formatDate` from `@/design`; `LedgerEvent` from `@/api/schema`). Add one line inside it, before the `parts.length === 0` fallback, so routed and returned events read in words:

```ts
  if (text('view')) parts.push(`“${text('view')}”`);
```

Remove any import that lint then reports unused in `Governance.tsx`. In `Governance.tsx`, replace the cut code with `export { describeEvent } from '@/squad/oversight/describeEvent';` so the cockpit screen still builds until Task 5 deletes it. Point `src/__tests__/workspace.test.tsx` and `src/squad/clientfile/views.tsx` at `@/squad/oversight/describeEvent`.

- [ ] **Step 4: The hook, redirects and the Oversight screen**

Append to `squad/api/hooks.ts`:

```ts
export interface EvalLatest { mode: string | null; standin: boolean; notice: string | null; gate_passed: boolean | null; created_at: string | null; results: { metrics?: Record<string, unknown> } }
export const useEvalLatest = () => useQuery({ queryKey: ['evals-latest'], queryFn: () => get<EvalLatest>('/evals/latest'), retry: false });
```

In `src/squad/redirects.ts`, before the `/borrowers` checks:

```ts
  const moved: Record<string, string> = { '/agent-activity': '/oversight/activity', '/governance': '/oversight/governance', '/command-centre': '/' };
  if (moved[pathname]) return moved[pathname];
```

```tsx
// frontend/src/squad/oversight/Oversight.tsx
import { Link, useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAgentRuns, useClock, useLedger, useLedgerVerification, usePolicyRegister, useRolesAndPermissions, useSetClock } from '@/api/hooks';
import { useAuth } from '@/auth/context';
import { useEvalLatest } from '../api/hooks';
import { threadHref } from '../links';
import { Time } from '../thread/Time';
import { describeEvent } from './describeEvent';

type Tab = 'activity' | 'ledger' | 'governance' | 'evaluations' | 'clock';
const TABS: Array<[Tab, string]> = [['activity', 'Agent activity'], ['ledger', 'Ledger'], ['governance', 'Governance'], ['evaluations', 'Evaluations'], ['clock', 'Clock']];
const STATUS: Record<string, string> = { running: 'Running', completed: 'Completed', abstained: 'Abstained', failed: 'Failed', refused: 'Refused' };

function Activity() {
  const runs = useAgentRuns();
  if (runs.isPending) return <p role="status" className="sq-muted">Reading agent activity.</p>;
  if (runs.error || !runs.data) return <p role="alert">Agent activity could not be loaded.</p>;
  return (
    <table className="sq-table" aria-label="Agent activity">
      <thead><tr><th scope="col">When</th><th scope="col">Agent</th><th scope="col">Client</th><th scope="col">Outcome</th><th scope="col" className="sq-num">Tool calls</th><th scope="col" className="sq-num">Tokens in / out</th></tr></thead>
      <tbody>
        {runs.data.map((r) => (
          <tr key={r.id}>
            <td><Time ts={r.created_at} /></td>
            <td>{r.agent_name} · <span className="sq-faint">{r.task.replace(/_/g, ' ')}</span></td>
            <td>{r.borrower_code && r.borrower_name ? <Link {...threadHref(r.borrower_code)} className="sq-link">{r.borrower_name}</Link> : <span className="sq-faint">No client</span>}</td>
            <td>{STATUS[r.status] ?? r.status}</td>
            <td className="sq-num">{r.steps_count}</td>
            <td className="sq-num">{r.input_tokens} / {r.output_tokens}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Ledger() {
  const [verify, setVerify] = useState(false);
  const events = useLedger({ limit: 100 });
  const verification = useLedgerVerification(verify);
  return (
    <div>
      <button type="button" className="sq-btn" onClick={() => setVerify(true)} disabled={verification.isFetching}>Verify the chain</button>
      {verification.data ? <p role="status">{verification.data.ok ? `The chain verifies: ${verification.data.events_checked} events checked.` : `The chain does not verify: ${verification.data.problem}`}</p> : null}
      {events.isPending ? <p role="status" className="sq-muted">Reading the ledger.</p> : (
        <ol className="sq-plainlist" aria-label="Ledger">
          {(events.data ?? []).map((e) => (
            <li key={e.seq}><span className="sq-mono">#{e.seq}</span> · <Time ts={e.ts} /> · <b>{e.actor_name ?? e.actor_type}</b> · {e.action.replace(/[._]/g, ' ')}{describeEvent(e) ? ` · ${describeEvent(e)}` : ''}</li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Governance() {
  const roles = useRolesAndPermissions();
  const policy = usePolicyRegister();
  if (roles.isPending || policy.isPending) return <p role="status" className="sq-muted">Reading the rules.</p>;
  if (!roles.data || !policy.data) return <p role="alert">The rules could not be loaded.</p>;
  const { roles: list, permissions, grants, second_person } = roles.data;
  return (
    <div>
      <table className="sq-table" aria-label="Who may do what">
        <thead><tr><th scope="col">Permission</th>{list.map((r) => <th key={r.id} scope="col">{r.label}</th>)}</tr></thead>
        <tbody>
          {permissions.map((p) => (
            <tr key={p.id}>
              <th scope="row">{p.label}{p.second_person ? <span className="sq-faint"> · second person</span> : null}</th>
              {list.map((r) => <td key={r.id}>{grants[r.id]?.includes(p.id) ? 'Yes' : <span className="sq-faint">No</span>}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <p>{second_person.rule}</p>
      {policy.data.sections.map((s) => (
        <section key={s.id} aria-label={s.title}>
          <h2 className="sq-h2">{s.title}</h2>
          <ul className="sq-plainlist">{s.rules.map((r) => <li key={r.id}><b>{r.rule}</b>: {r.setting} · <span className="sq-faint">{r.effect}</span></li>)}</ul>
        </section>
      ))}
    </div>
  );
}

function Evaluations() {
  const latest = useEvalLatest();
  if (latest.isPending) return <p role="status" className="sq-muted">Reading the latest evaluation.</p>;
  if (latest.error || !latest.data) return <p className="sq-muted">No evaluation has been run in this database yet.</p>;
  const e = latest.data;
  return (
    <div>
      {e.notice ? <p className="sq-card">{e.notice}</p> : null}
      <p>Mode: {e.mode ?? 'unknown'} · gate {e.gate_passed === null ? 'not recorded' : e.gate_passed ? 'passed' : 'failed'}{e.created_at ? <> · <Time ts={e.created_at} /></> : null}</p>
      <table className="sq-table" aria-label="Evaluation measures">
        <tbody>
          {Object.entries(e.results.metrics ?? {}).map(([k, v]) => (
            <tr key={k}><th scope="row">{k.replace(/_/g, ' ')}</th><td className="sq-num">{v === null || v === undefined ? <span className="sq-faint">Not measured</span> : String(v)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Clock() {
  const clock = useClock(true);
  const set = useSetClock();
  const [day, setDay] = useState('');
  return (
    <form aria-label="The demonstration clock" onSubmit={(ev) => { ev.preventDefault(); if (day) set.mutate(day); }}>
      <p>The working date is {clock.data?.today ?? 'not known'}.</p>
      <label className="sq-field">Set the working date<input className="sq-input" type="date" value={day} onChange={(ev) => setDay(ev.target.value)} /></label>
      <button type="submit" className="sq-btn" disabled={!day || set.isPending}>Set the date</button>
      {set.error ? <p role="alert">The server said: “{errorMessage(set.error)}”</p> : null}
    </form>
  );
}

/** Oversight for administrators and reviewers: what agents did, the ledger, the rules, the evaluation. No credit decision is offered here. */
export function Oversight() {
  const { tab = 'activity' } = useParams({ strict: false }) as { tab?: string };
  const { can } = useAuth();
  const tabs = TABS.filter(([id]) => id !== 'clock' || can('advance_clock'));
  const current = tabs.find(([id]) => id === tab)?.[0];
  const body = { activity: <Activity />, ledger: <Ledger />, governance: <Governance />, evaluations: <Evaluations />, clock: <Clock /> };
  return (
    <div className="sq-oversight" data-ready="">
      <h1 className="sq-h1">Oversight</h1>
      <nav aria-label="Oversight" className="sq-tabs">
        {tabs.map(([id, label]) => <Link key={id} to={id === 'activity' ? '/oversight' : `/oversight/${id}`} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>)}
      </nav>
      {current ? body[current] : <p role="alert">There is no such part of Oversight.</p>}
    </div>
  );
}
```

`useSetClock().mutate` takes the date string (`src/api/hooks.ts`). The tool-call column shows `steps_count`, the stored count the step cap is measured against (`AgentRunRow` in `src/api/schema.ts`).

- [ ] **Step 5: Routes, nav and commands**

In `router.tsx`, add the two Oversight routes (the cockpit `/agent-activity` and `/governance` routes stay until Task 5 swaps them for redirects):

```tsx
const oversightRoute = createRoute({ getParentRoute: () => rootRoute, path: '/oversight', component: lazyRouteComponent(() => import('@/squad/oversight/Oversight'), 'Oversight') });
const oversightTabRoute = createRoute({ getParentRoute: () => rootRoute, path: '/oversight/$tab', component: lazyRouteComponent(() => import('@/squad/oversight/Oversight'), 'Oversight') });
```

In `SquadNav.tsx`, the Oversight block becomes one link:

```tsx
      {OVERSIGHT_ROLES.includes(role) ? (
        <Link to="/oversight" className="sq-navlink" title="Oversight" aria-current={pathname.startsWith('/oversight') ? 'page' : undefined}>
          <Landmark size={18} aria-hidden />
          <span className="sq-navlabel">Oversight</span>
        </Link>
      ) : null}
```

In `commands.ts`, the two oversight commands become `{ id: 'go-oversight', group: 'Oversight', label: 'Oversight', hint: 'Agent activity, ledger, governance, evaluations', run: () => go('/oversight') }` and `{ id: 'go-ledger', group: 'Oversight', label: 'The ledger', run: () => go('/oversight/ledger') }`. In `surface.ts`, add `'/oversight'` to `SQUAD`.

- [ ] **Step 6: Run the checks**

Run: `cd frontend && pnpm vitest run && pnpm typecheck && pnpm lint`
Expected: PASS (the whole vitest suite, since `workspace.test.tsx` and the cockpit `Governance` screen changed import paths).

- [ ] **Step 7: Commit**

```bash
(cd frontend && pnpm vitest run && pnpm typecheck && pnpm lint) && git add frontend/src && \
git commit -m "feat(p4b): Oversight in Squad's looks: agent activity, ledger with verification, governance, evaluations, the clock

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

---
### Task 5: Retire the cockpit

**Files:**
- Move (`git mv`): `frontend/src/screens/work/HeldFigures.tsx` → `frontend/src/squad/case/HeldFigures.tsx`; `frontend/src/screens/work/KeyFigures.tsx` → `frontend/src/squad/case/KeyFigures.tsx`; `frontend/src/screens/borrower/RunStage.tsx`, `RunStage.test.tsx`, `UploadDocument.tsx`, `UploadDocument.test.tsx` → `frontend/src/squad/clientfile/`; `frontend/src/screens/review/Commentary.tsx`, `CommentaryEditor.tsx`, `commentary.test.tsx` → `frontend/src/squad/clientfile/review/`
- Delete (`git rm`): `frontend/src/shell/` (all), `frontend/src/drawer/` (all), `frontend/src/fixtures/` (all; only `DesignPage` used them), `frontend/src/screens/AgentActivity.tsx`, `AgentActivity.test.tsx`, `Calendar.tsx`, `Calendar.test.ts`, `CommandCentre.tsx`, `CommandCentre.test.ts`, `DesignPage.tsx`, `Governance.tsx`, `Governance.test.tsx`, `Portfolio.tsx`, `Portfolio.test.tsx`, `ReviewRoom.tsx`, `frontend/src/screens/borrower/` (what remains after the moves), `frontend/src/screens/work/` (what remains: `WorkItemPanel.tsx`, `decision.test.tsx`), `frontend/e2e/run.mjs`, `frontend/e2e/repair.mjs`, `frontend/e2e/seed_repair.py`
- Keep: `frontend/src/screens/SignIn.tsx` and `frontend/src/screens/parts.tsx` (shared by `SignIn`, the moved parts and `repair/`)
- Create: `frontend/src/squad/__tests__/retired.test.ts`
- Rename: `frontend/src/squad/__tests__/cockpitSurface.test.tsx` → `surface.test.tsx`
- Modify: `frontend/src/router.tsx`, `frontend/src/squad/shell/SquadShell.tsx`, `surface.ts`, `frontend/src/squad/redirects.ts`, `frontend/src/squad/case/CasePanel.tsx`, `frontend/src/squad/clientfile/views.tsx`, `frontend/src/repair/repair.test.tsx`, `frontend/src/squad/squad.css`, `frontend/src/squad/__tests__/shell.test.tsx`, `thread.test.tsx`, `case.test.tsx`, `frontend/src/squad/home/SquadHome.tsx`, `frontend/src/squad/thread/ClientThread.tsx` (`data-ready`), `frontend/package.json`, `frontend/scripts/serve.mjs`, `frontend/e2e/squad.mjs`, `README.md`, `docs/HANDOFF.md`, `frontend/DESIGN.md`

**Interfaces:**
- Consumes: Tasks 1–4 (every Squad screen and redirect exists before anything is deleted).
- Produces: `Surface = 'conversation' | 'squad'` (no `'cockpit'`); `oldAddress` also moves `/calendar`, `/review-room` and `/design` to `/`; new paths `@/squad/case/HeldFigures`, `@/squad/case/KeyFigures`, `@/squad/clientfile/RunStage`, `@/squad/clientfile/UploadDocument`, `@/squad/clientfile/review/Commentary`. The legacy-token bridge in `looks.ts` stays: `src/design/` components and the moved parts still read those names (checked in Step 6).

**Owner question 1 decides one branch here:** if the owner has said to keep packages, the review room or the calendar in v2, do not delete `Packages.tsx`, `PackageSchedules.tsx` (and its test), `ReviewRoom.tsx` or `Calendar.tsx` in Step 4; stop after Step 3 and report, because each needs its own Squad screen (a separate task the owner must see first). With no answer, delete them: v1 keeps them (git 2292b38) and the APIs stay.

- [ ] **Step 1: Write the failing guard test**

```ts
// frontend/src/squad/__tests__/retired.test.ts
import { describe, expect, it } from 'vitest';

const sources = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
const RETIRED = /from '@\/(shell|drawer|fixtures)\/|from '@\/screens\/(?!SignIn'|parts')/;

describe('the cockpit is retired', () => {
  it('no source file imports the cockpit shell, drawer, fixtures or a cockpit screen', () => {
    const offenders = Object.entries(sources).filter(([path, text]) => !path.endsWith('retired.test.ts') && RETIRED.test(text)).map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
```

In `frontend/src/squad/__tests__/surface.test.tsx` (renamed from `cockpitSurface.test.tsx`): the `surfaceOf` cases become `['/', '/clients/QFL']` → `'conversation'` and `['/approvals', '/portfolio', '/clients/QFL/file', '/oversight', '/anything-else']` → `'squad'`; drop the `WorkspaceDrawerProvider` wrapper from `mountAt`; delete the test that mounts `/calendar` as a cockpit screen; the CSS test becomes `expect(css).toMatch(/\.sq-main\[data-surface='squad'\]\s*\{[^}]*max-width:\s*1280px/)` and `expect(css).not.toMatch(/data-surface='cockpit'/)`. Keep the "legacy cockpit tokens stay legible in every look" tests (the bridge stays). In `shell.test.tsx`, delete the `describe('SquadShell and the legacy drawer', …)` block and the `WorkspaceDrawerProvider` import. In `redirects.test.tsx`, add `['/calendar', '/'], ['/review-room', '/'], ['/design', '/']` to the table.

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/retired.test.ts src/squad/__tests__/surface.test.tsx src/squad/__tests__/redirects.test.tsx`
Expected: FAIL: `retired.test.ts` lists `src/router.tsx`, `src/squad/shell/SquadShell.tsx`, `src/squad/case/CasePanel.tsx`, `src/squad/clientfile/views.tsx`, `src/repair/repair.test.tsx` and others; the surface and redirect tests fail on `'cockpit'` and `/calendar`.

- [ ] **Step 3: Move what Squad still uses, and point its imports at the new places**

```bash
cd frontend
git mv src/screens/work/HeldFigures.tsx src/squad/case/HeldFigures.tsx
git mv src/screens/work/KeyFigures.tsx src/squad/case/KeyFigures.tsx
git mv src/screens/borrower/RunStage.tsx src/squad/clientfile/RunStage.tsx
git mv src/screens/borrower/RunStage.test.tsx src/squad/clientfile/RunStage.test.tsx
git mv src/screens/borrower/UploadDocument.tsx src/squad/clientfile/UploadDocument.tsx
git mv src/screens/borrower/UploadDocument.test.tsx src/squad/clientfile/UploadDocument.test.tsx
mkdir -p src/squad/clientfile/review
git mv src/screens/review/Commentary.tsx src/squad/clientfile/review/Commentary.tsx
git mv src/screens/review/CommentaryEditor.tsx src/squad/clientfile/review/CommentaryEditor.tsx
git mv src/screens/review/commentary.test.tsx src/squad/clientfile/review/commentary.test.tsx
sed -i "s#from '\.\./parts'#from '@/screens/parts'#" src/squad/clientfile/RunStage.tsx src/squad/clientfile/UploadDocument.tsx src/squad/clientfile/review/Commentary.tsx
sed -i "s#@/screens/work/HeldFigures#@/squad/case/HeldFigures#; s#@/screens/work/KeyFigures#@/squad/case/KeyFigures#" src/squad/case/CasePanel.tsx src/squad/__tests__/case.test.tsx src/repair/repair.test.tsx
sed -i "s#@/screens/borrower/RunStage#@/squad/clientfile/RunStage#; s#@/screens/borrower/UploadDocument#@/squad/clientfile/UploadDocument#; s#@/screens/review/Commentary#@/squad/clientfile/review/Commentary#" src/squad/clientfile/views.tsx
```

Then fix the two links inside the moved files: in `RunStage.tsx`, `<Link to="/agent-activity" …>` becomes `<Link to="/oversight" …>`; in `UploadDocument.tsx`, the "open the filed document" link becomes `<Link to="/clients/$code/file/$view" params={{ code, view: 'documents' }} search={{ document: filed.id, page: 1 }} …>`. If a moved test mocks a path by its old location (`vi.mock('../parts', …)` or `vi.mock('./BorrowerLayout', …)`), point it at `@/screens/parts` or remove the mock the component no longer needs.

Run: `pnpm typecheck`
Expected: errors only in files Step 4 deletes (cockpit screens importing the moved files) and in `router.tsx`.

- [ ] **Step 4: Delete the cockpit**

```bash
cd frontend
git rm -r -q src/shell src/drawer src/fixtures src/screens/work src/screens/borrower
git rm -q src/screens/AgentActivity.tsx src/screens/AgentActivity.test.tsx src/screens/Calendar.tsx src/screens/Calendar.test.ts \
  src/screens/CommandCentre.tsx src/screens/CommandCentre.test.ts src/screens/DesignPage.tsx src/screens/Governance.tsx \
  src/screens/Governance.test.tsx src/screens/Portfolio.tsx src/screens/Portfolio.test.tsx src/screens/ReviewRoom.tsx \
  e2e/run.mjs e2e/repair.mjs e2e/seed_repair.py
ls src/screens   # expect: SignIn.tsx parts.tsx
```

(`src/screens/review/` is already empty after Step 3's moves, so it is not in the command.)

- [ ] **Step 5: Router, shell, surface, redirects**

In `frontend/src/router.tsx`: remove the imports of `CommandCentre`, `WorkspaceDrawerProvider`, `CopilotConversationProvider`; `Root` renders `<SourceProvider><SquadShell /></SourceProvider>`. Delete `commandCentreRoute`, `borrowersRoute`, `borrowerRoute` and every child of it (`summaryRoute` … `timelineRoute`, `documentRoute`, `spreadsRoute`, `covenantsRoute`, `borrowingBaseRoute`), `calendarRoute`, `reviewRoomRoute`, `agentActivityRoute`, `governanceRoute`, `designRoute`, and register redirect routes in their place (import `redirect` from `@tanstack/react-router` and `oldAddress` from `@/squad/redirects`):

```tsx
const toNew = ({ location }: { location: { pathname: string; search: Record<string, unknown> } }) => {
  const href = oldAddress(location.pathname, location.search);
  if (href) throw redirect({ href, replace: true });
};
const old = (path: string) => createRoute({ getParentRoute: () => rootRoute, path, beforeLoad: toNew, component: () => null });
const oldRoutes = [
  '/borrowers', '/borrowers/$code', '/borrowers/$code/$view', '/borrowers/$code/documents/$documentId',
  '/command-centre', '/agent-activity', '/governance', '/calendar', '/review-room', '/design',
].map(old);
```

and add `...oldRoutes` to `routeTree`. (If TanStack's typed `createRoute` refuses a `path` typed as `string`, write the ten `createRoute` calls out one by one with literal paths.) `Notice` stays imported from `@/screens/parts`.

In `frontend/src/squad/redirects.ts`, extend the `moved` map: `'/calendar': '/', '/review-room': '/', '/design': '/'`.

In `frontend/src/squad/shell/SquadShell.tsx`: remove `defaultCopilotScope`, `useWorkspaceDrawer`, `WorkspaceDrawer`, the Ctrl J effect and `<WorkspaceDrawer />`; the `PresenceLine` renders on every surface.

```ts
// frontend/src/squad/shell/surface.ts
/** Conversation: home and threads (a narrow column). Squad: every other screen (wider). Both carry the presence line. */
export type Surface = 'conversation' | 'squad';

export function surfaceOf(pathname: string): Surface {
  return pathname === '/' || pathname === '/clients' || (pathname.startsWith('/clients/') && !/^\/clients\/[^/]+\/file/.test(pathname))
    ? 'conversation'
    : 'squad';
}
```

In `squad.css`, delete the `.sq-main[data-surface='cockpit']` rule and its comment. Add `data-ready=""` to the root `div` of `SquadHome` and the `section` of `ClientThread` once their data has loaded (the screenshot and a11y scripts wait for it).

In `frontend/package.json` scripts: delete `"e2e"` and `"e2e:repair"`; keep `"e2e:squad"`, `"screenshots"`, `"a11y"`.

- [ ] **Step 6: Check the legacy-token bridge is still read, and say so**

Run: `cd frontend && grep -rlE "text-ink|bg-surface|border-hairline|text-cobalt|bg-canvas" src/design src/squad src/repair src/source | head`
Expected: several files (the `src/design/` components, `HeldFigures`, `KeyFigures`, `repair/`, `SourceDrawer`). The bridge stays; Step 9 records why in `frontend/DESIGN.md`. If the command prints nothing, delete `legacyTokens`, `LEGACY_TOKENS` and their use in `looks.ts` and the "legacy cockpit tokens" tests in `surface.test.tsx` instead.

- [ ] **Step 7: Scripts and journeys on Squad's screens**

In `frontend/scripts/serve.mjs`: `signIn` waits for `` `${BASE}/` `` and `.sq-main` (replace `waitForURL('**/command-centre**')` and the `[data-ready]` wait); `BREACH` becomes `'kestrel-bay-packaging'` on the legacy book or `'corvane-analytics'` on the innovation book (set `const BREACH = process.env.SHOT_CLIENT ?? 'corvane-analytics';`); replace `PAGES` with:

```js
export const PAGES = [
  { name: 'sign-in', path: '/sign-in', signedOut: true },
  { name: 'home', path: '/' },
  { name: 'thread', path: `/clients/${BREACH}` },
  { name: 'client-file', path: `/clients/${BREACH}/file` },
  { name: 'spreads', path: `/clients/${BREACH}/file/spreads` },
  { name: 'covenants', path: `/clients/${BREACH}/file/covenants` },
  { name: 'documents', path: `/clients/${BREACH}/file/documents` },
  { name: 'funding', path: `/clients/${BREACH}/file/funding` },
  { name: 'history', path: `/clients/${BREACH}/file/history` },
  { name: 'portfolio', path: '/portfolio' },
  { name: 'oversight', path: '/oversight' },
];
```

and delete `openSource`/`waitForPage` if nothing uses them any more. In `frontend/e2e/squad.mjs`, delete the 'legacy cockpit route' journey if Task 3 did not already replace it, and add:

```js
journey('old addresses: every retired cockpit address lands on the Squad place that replaced it', async ({ page }) => {
  await signIn(page, ANALYST);
  const [first] = await api(page, '/borrowers');
  const docs = await api(page, `/borrowers/${first.id}/documents`);
  const cases = [
    [`/borrowers/${first.code}/covenants`, `/clients/${first.code}/file/covenants`],
    [`/borrowers/${first.code}`, `/clients/${first.code}/file`],
    ['/borrowers', '/portfolio'],
    ['/command-centre', '/'],
    ['/governance', '/oversight/governance'],
    ['/agent-activity', '/oversight/activity'],
  ];
  if (docs.length) cases.push([`/borrowers/${first.code}/documents/${docs[0].id}?page=1`, `/clients/${first.code}/file/documents`]);
  for (const [from, to] of cases) {
    await page.goto(`${BASE}${from}`);
    await page.waitForURL((url) => url.pathname === to, { timeout: 10000 });
    assert((await page.getByRole('alert').count()) === 0, `${from} landed on an error`);
  }
});

journey('repair: a held reading opens in its case with the held figures and the person’s decision', async ({ page }) => {
  await signIn(page, ANALYST);
  const held = [...(await api(page, '/work-items?item_type=spread.value_unverified')), ...(await api(page, '/work-items?item_type=spread.does_not_foot'))];
  assert(held.length > 0, 'the seeded innovation book should hold one spread for a person (Stripple)');
  const borrower = await api(page, `/borrowers/${held[0].borrower_id}`);
  await page.goto(`${BASE}/clients/${borrower.code}?case=${held[0].id}`);
  const card = page.locator(`[data-work-item="${held[0].id}"][data-focused="true"]`);
  await card.locator('[data-held-figures]').waitFor();
  await card.getByRole('button', { name: 'Record decision' }).waitFor();
});
```

(The repair journey does not change the record: the held figures stay held for the next run.)

- [ ] **Step 8: Run everything the front end has**

Run: `cd frontend && pnpm vitest run && pnpm typecheck && pnpm lint && pnpm build`
Expected: PASS; `retired.test.ts` passes; the build has no chunk for a deleted screen.

Then, with the stack up on a freshly seeded innovation book plus `uv run python -m app.squad_demo`: `pnpm e2e:squad`
Expected: every journey prints `PASS`.

- [ ] **Step 9: Documents**

- `README.md`, "Check it": the front-end line becomes `(cd frontend && pnpm typecheck && pnpm lint && pnpm test && pnpm build && pnpm e2e:squad)`, with the sentence "The Squad journeys need the seeded stack and `uv run python -m app.squad_demo`; they record a hand-off and a decision, so run them on a fresh seed." The "Workspace" row of "Where things are" becomes `Credit Squad: frontend/src/squad/ (design rules in frontend/DESIGN.md; spec docs/specs/2026-11-20-squad-experience-design.md)`.
- `frontend/DESIGN.md`: replace the "Shell" section with a "Shell (Credit Squad)" section: collapsible left nav (Squad with its needs-you count, My Portfolio, Approvals for roles that decide breaches or approve terms, Open cases by name when expanded and as one button when collapsed, Oversight for administrators and reviewers, the person, the look and sign-out); the presence line under the mark carries every confirmation; the evidence drawer pushes content; Ctrl K palette; no Ctrl J (the Copilot is the composer in each thread). In "The product on real data", delete the rows for `WorkItemPanel`, `screens/AgentActivity`, `screens/Governance`, `borrower/PackageSchedules`; rename `work/HeldFigures` to `squad/case/HeldFigures`, `review/Commentary` to `squad/clientfile/review/Commentary`, `borrower/UploadDocument` to `squad/clientfile/UploadDocument`; add rows for `squad/case/CasePanel` ("one case: the router's view, the evidence, and only the actions the server allows; a refusal is named and quoted, a second-person refusal is never pre-empted"), `squad/clientfile` ("every figure is a stored fact or a record field with its glyph; unmeasured is 'Not measured' or the stored note, never zero") and `squad/clientfile/Measure` ("plot positions only; an unmeasured period is an outline"). Add one sentence under Colour tokens: "`src/squad/looks.ts` bridges these names to each look, because `src/design/` components and the case and repair parts still read them." Replace the "Checks" block with `pnpm typecheck && pnpm lint && pnpm test && pnpm build`, `pnpm e2e:squad`, `node scripts/screenshots.mjs`, `node scripts/a11y.mjs`, and keep the final checklist paragraph unchanged.
- `docs/HANDOFF.md`: in the phase table, row 4 reads "4a done and merged (20 Nov). 4b: `docs/plans/2026-11-21-phase-4b-squad-approvals-and-client-file.md`, tasks 1–5 done; cockpit retired (v1 at git 2292b38)". Under "Known gaps carried to later phases", add the three carry items listed at the top of this plan (spreadsheet reading, Kestrel Bay wrong-abstain, Pellham wording) with "needs a billable re-record to show any fix; owner to approve".

- [ ] **Step 10: Commit**

```bash
(cd frontend && pnpm vitest run && pnpm typecheck && pnpm lint && pnpm build) && \
git add -A frontend README.md docs/HANDOFF.md && \
git commit -m "chore(p4b): retire the cockpit: shell, drawer, command centre and borrower screens deleted; held figures, upload, run-stage and commentary move into Squad; old addresses redirect

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

(`git add -A frontend` stages the deletions and moves; check `git status` first that nothing outside the listed files is staged, in particular no `.env` and no `frontend/e2e/failures/`.)

---

### Task 6: Every client, both roles, every look and width; the gates; merge-ready

**Files:**
- Modify: `frontend/e2e/squad.mjs`, `docs/HANDOFF.md`
- Create: `docs/product/screens/v2-4b-*.png` (screenshots of the manual pass), `docs/product/v2-4b-walkthrough.md` (what the manual pass found)

**Interfaces:**
- Consumes: everything above; `GET /api/v1/borrowers`, `/me/briefing`, `/me/approvals`, `/me/portfolio`, `/threads/{id}`, `/cases/{id}`.
- Produces: data-driven journeys over every client in the seeded book; the final verification record.

- [ ] **Step 1: The data-driven journeys**

Append to `frontend/e2e/squad.mjs`, before the runner:

```js
const VIEWS = ['', '/spreads', '/covenants', '/documents', '/funding', '/loans', '/reviews', '/history'];

async function noScroll(page, where) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `horizontal page scroll on ${where}`);
}

async function noTypedZeroForUnmeasured(page, where) {
  // An unmeasured figure must read "Not measured" or its stored note, never as a bare zero beside a bar.
  const zeros = await page.locator('.sq-bar-none').evaluateAll((bars) => bars.filter((b) => (b.closest('td')?.previousElementSibling?.textContent ?? '').trim() === '0').length);
  assert(zeros === 0, `an unmeasured point shows 0 on ${where}`);
}

for (const [who, email] of [['analyst', ANALYST], ['officer', OFFICER]]) {
  journey(`every client, ${who}: thread, case focus, client file views and portfolio row all land on the same client`, async ({ page }) => {
    await signIn(page, email);
    const borrowers = await api(page, '/borrowers');
    assert(borrowers.length >= 20, `expected the whole seeded book, found ${borrowers.length} clients`);
    for (const b of borrowers) {
      await page.goto(`${BASE}/clients/${b.code}`);
      await page.getByRole('heading', { level: 1, name: b.name }).waitFor();
      assert((await page.getByRole('alert').count()) === 0, `${b.name}: the thread shows an error`);
      const thread = await api(page, `/threads/${b.id}`);
      const text = await page.locator('.sq-messages').innerText().catch(() => '');
      for (const other of borrowers) {
        if (other.id !== b.id && other.name.length > 12 && text.includes(other.name)) throw new Error(`${b.name}'s thread names ${other.name}`);
      }
      const open = thread.messages.filter((m) => (m.type === 'case' || m.type === 'ask') && m.status === 'open');
      for (const m of open.slice(0, 2)) {
        await page.goto(`${BASE}/clients/${b.code}?case=${m.work_item_id}`);
        await page.locator(`[data-work-item="${m.work_item_id}"][data-focused="true"]`).waitFor();
        const view = await api(page, `/cases/${m.work_item_id}`);
        const decide = await page.getByRole('button', { name: 'Record decision' }).count();
        assert((decide > 0) === view.decisions.some((d) => d.permitted), `${b.name}: the decision form disagrees with the server for ${m.title}`);
      }
      for (const v of VIEWS) {
        await page.goto(`${BASE}/clients/${b.code}/file${v}`);
        await page.getByRole('heading', { level: 1, name: b.name }).waitFor();
        assert((await page.getByRole('alert').count()) === 0, `${b.name}: client file${v || ' overview'} shows an error`);
        await noTypedZeroForUnmeasured(page, `${b.code}/file${v}`);
      }
    }
    await page.goto(`${BASE}/portfolio`);
    for (const b of borrowers) assert((await page.getByRole('link', { name: b.name, exact: true }).count()) === 1, `${b.name} is not on My Portfolio exactly once`);
  });
}

journey('every look, every Squad screen: contrast and names hold', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  await signIn(page, ANALYST);
  const [b] = await api(page, '/borrowers');
  const screens = ['/', `/clients/${b.code}`, `/clients/${b.code}/file`, `/clients/${b.code}/file/covenants`, '/portfolio'];
  for (const look of LOOKS) {
    await page.goto(`${BASE}/`);
    await page.getByRole('button', { name: /^look:/i }).click();
    await page.getByRole('menuitemradio', { name: look }).click();
    for (const path of screens) {
      await page.goto(`${BASE}${path}`);
      await page.locator('.sq-main').waitFor();
      await page.addScriptTag({ content: axeSource });
      const result = await page.evaluate(() => window.axe.run(document.body, { runOnly: ['color-contrast', 'label', 'button-name', 'link-name'] }));
      const bad = result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
      assert(bad.length === 0, `${look} ${path}: ${bad.join(', ')}`);
    }
  }
  await context.close();
});

journey('every width from 1000 to 1920, and phone and tablet, on every Squad screen: no horizontal scroll', async ({ browser }) => {
  for (const email of [ANALYST, OFFICER]) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    await signIn(page, email);
    const [b] = await api(page, '/borrowers');
    const screens = ['/', `/clients/${b.code}`, `/clients/${b.code}/file`, `/clients/${b.code}/file/spreads`, `/clients/${b.code}/file/covenants`, '/portfolio', email === OFFICER ? '/approvals' : '/'];
    for (const width of [390, 820, ...WIDTHS]) {
      await page.setViewportSize({ width, height: 900 });
      for (const path of screens) {
        await page.goto(`${BASE}${path}`);
        await page.locator('.sq-main').waitFor();
        await noScroll(page, `${path} at ${width}px`);
      }
    }
    await context.close();
  }
});
```

The first-look bugs 2 and 3 (duplicate rows, raw amounts in titles) stay fixed:

```js
for (const [who, email] of [['analyst', ANALYST], ['officer', OFFICER]]) {
  journey(`the ${who}'s briefing lists each thing once and prints no raw amount in a title`, async ({ page }) => {
    await signIn(page, email);
    const { b } = await record(page);
    const keys = b.items.map((i) => i.key);
    assert(new Set(keys).size === keys.length, 'a briefing row is listed twice');
    const raw = b.items.filter((i) => /\d{1,3}(,\d{3})+\.\d{2}\b/.test(i.title));
    assert(raw.length === 0, `raw amounts in titles: ${raw.map((i) => i.title).join('; ')}`);
  });
}
```

The admin view is covered once:

```js
journey('the administrator sees Oversight and no credit decision anywhere', async ({ page }) => {
  await signIn(page, 'admin@bankofstoic.example');
  await page.goto(`${BASE}/oversight`);
  await page.getByRole('navigation', { name: 'Oversight' }).waitFor();
  const items = (await api(page, '/work-items')).slice(0, 3);
  for (const w of items) {
    const b = await api(page, `/borrowers/${w.borrower_id}`);
    await page.goto(`${BASE}/clients/${b.code}?case=${w.id}`);
    await page.locator(`[data-work-item="${w.id}"][data-focused="true"]`).waitFor();
    assert((await page.getByRole('button', { name: /record decision|^send to|^return to|^attach/i }).count()) === 0, 'an administrator was offered a credit action');
  }
});
```

- [ ] **Step 2: Run the journeys on a fresh seed**

```bash
service postgresql start
# fresh database for the journeys (they write); see docs/HANDOFF.md "Running it" for the stack
PYTHONPATH=backend uv run python -m app.seed_book            # innovation book, about 3 minutes
PYTHONPATH=backend uv run python -m app.squad_demo
# API on 8000 and `pnpm dev` on 5173 in the background, then:
cd frontend && pnpm e2e:squad
```

Expected: every journey prints `PASS`. Any failure is a defect in the task that owns the code: fix it there with a unit test, and rerun. Playwright here launches Chromium directly and records no trace; if any Playwright CLI is used to debug, pass `--trace off`.

- [ ] **Step 3: The gates, one process at a time**

```bash
uv run ruff check .
uv run pytest -q                                                     # the whole suite, about 70 minutes; nothing else running
uv run python -m evals.run --mode standin --book both               # the stand-in gate on both books
uv run python -m evals.run --mode recorded --book innovation        # the recorded replay; no model is called
(cd frontend && pnpm typecheck && pnpm lint && pnpm test && pnpm build)
```

Expected: all green; the stand-in gate passes on both books with the numbers in `docs/HANDOFF.md` (legacy 2,677 of 2,677; innovation 1,621 of 1,621, covenants 94.9%); the replay gate passes with the known wrong-abstain 1 (Kestrel Bay, not gated). If `evals.run` asks for `--confirm-billable` or any key, stop: the command is wrong; never pass that flag in this plan. A change in any eval number is a finding to report, not something to adjust.

- [ ] **Step 4: The manual pass on the owner's screen sizes**

Run `node scripts/screenshots.mjs --no-build` against the seeded stack, and walk, as Priya then as Helen, at 1440 and at 390 px: home, Stripple's thread (opens at its open case, arrivals grouped, "MRR report" in words), the hand-off loop on one breach, Corvane's client file (covenants, runway with its trend), My Portfolio, Approvals, Oversight as the administrator. Copy six screenshots to `docs/product/screens/v2-4b-*.png` and write `docs/product/v2-4b-walkthrough.md` in the shape of `v2-first-look-findings.md`: each first-look finding with "fixed, seen" or "still open", and anything new. Do not fix new findings in this task unless they are defects against this plan's tests; list them.

- [ ] **Step 5: HANDOFF and commit**

In `docs/HANDOFF.md`, row 4 of the phase table records 4b done with the counts from Steps 2–3 as the tool output gave them (journeys passed, vitest count, pytest count, eval numbers) and "merge-ready on `slice-1/monitoring-cycle`; Phase 5 hosts it". Say plainly what was not verified.

```bash
git add frontend/e2e/squad.mjs docs/HANDOFF.md docs/product/v2-4b-walkthrough.md docs/product/screens/v2-4b-*.png && \
git commit -m "test(p4b): every client in both roles, every look and width; gates green; walkthrough recorded

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LdgDGWNkubuJiXXErhFMLq"
```

---

## Owner questions

1. **Packages, the review room and the calendar.** The Squad spec's structure (section 3) has no place for them, so Task 5 deletes them with the cockpit; v1 keeps them (git 2292b38) and their APIs stay. Keep any of them in v2? If yes, each needs its own Squad screen, as a separate task.
2. **Agents reading figures from spreadsheets.** Out of 4b (a new reading capability, not experience). Which phase should own it?
3. **Kestrel Bay's covenant investigation (wrong-abstain) and Pellham's re-recorded wording.** Both are agent behaviour; neither can be shown fixed without a new record pass, which is billable. Approve a small targeted re-record after a fix, in a later phase? An estimate will come with the request (for scale only: the 21 November re-record of three agents over the whole book measured 2.56 US dollars).
4. **Signals no longer counted in "needs you"** (finding 5, Task 3). A signal that needs a decision already raises a work item, which counts. Confirm.
5. **"Bank account statement"** is the plain-words name for `bank_statement` beside the document's own printed title ("Account statement, August 2026"). Confirm or name the wording you want.

## Rulings where the spec was silent (each can be overruled)

- A return is not a decision; it keeps the case open and sends it back to the person who routed it.
- Routing makes the router the preparer when none is set, so the engine's two-person rule applies to her; an earlier preparer (for example terms prepared by someone else) is kept.
- "Squad gathers what was asked" lists the client's documents not yet attached; a person attaches.
- The thread opens at the first open case, ask or unsent draft; else at the newest arrivals.
- Documents for one period are grouped when there are two or more.
- My Portfolio orders by the latest stored figure, lowest first, unmeasured last; the analyst can narrow to her clients.
- Oversight has five tabs; the clock tab shows only for a role that may move it.

## Self-review

**Spec coverage.**
- §3 Structure: Squad home (4a, calmer in Task 3), client threads (4a; opening position and arrivals Task 2), My Portfolio (Task 3), Approvals (Task 1), Client file (Task 2), Evidence drawer (4a; client file figures open it), Oversight (Task 4). Nav: Squad with count, My Portfolio, Open cases by name, Approvals, Oversight, avatar (Tasks 1, 3, 4). Palette stays (4a; commands updated Tasks 1, 4).
- §5 Briefing: state in words per case including "returned to you" and "with Helen Strand" (Task 1); signals listed by client (Task 3).
- §6 Threads: hand-off with the view, return with the reason, attached evidence, decision, in order by sequence (Task 1); "a case started in a client's thread stays there through the officer's decision and back" (Task 1 journey).
- §10 Approvals and hand-offs: required view, required reason by the engine's rule, approve-or-reserve via the item's decisions, return, gather, re-route, decide again; two people by the engine (Task 1).
- §11 Track records and remembered habits where used (Task 3).
- §12 Backend additions: all 4a items exist; 4b adds `/cases/{id}`, `/me/approvals`, route, return, attach, `/borrowers/{id}/measure`, `/me/portfolio`, `/borrowers/{id}/lessons`.
- §13 Visual rules: ink primary buttons, ember only for needs-you, red/amber only for breach/attention tags, paper evidence (drawer unchanged), confirmations in the presence line (every write in Task 1), drawer pushes (4a), contrast in every look (Task 6), widths 1000–1920 plus 390 and 820 (Task 6; lesson look-at-it-on-the-owners-screen).
- §14 Testing: unit tests per endpoint (Tasks 1–3), component tests (Tasks 1–5), journeys for every entry point of every client in both roles (Task 6), contrast scan in all looks (Task 6), the eval gate (Task 6).
- §15 decisions: product name unchanged; client file redesigned (Task 2); default looks unchanged.
- Findings: every one placed (table at the top); bugs 1–3 were already fixed and are re-checked by Task 6's journeys.

**Placeholder scan.** No "TBD" or "add tests for the above". Two steps name a check the executor runs before writing (Task 5 Step 6 decides whether the legacy-token bridge stays, with both outcomes spelled out; Task 5's owner-question branch with both outcomes spelled out). Mechanical moves are given as commands.

**Type and name consistency.** `CaseView` fields match `build_case` keys (`may_route`, `may_return`, `may_attach`, `decisions[].permitted`, `decisions[].needs_reason`, `view.{text,by,at}`, `history[].kind ∈ routed|returned|evidence_attached`). `ApprovalRow` matches `build_approvals`. Thread message types `returned`, `attached`, `arrivals` and the fields `view`, `doc_type_words`, `habits`, `needs_you`, `state_words`, `opening_id` match between `threads.py` and `types.ts`. `MeasureSeries`/`MeasurePoint` match `measure_series`. `clientFile(code, view)` and `ClientFileView` are the same in `links.ts`, `redirects.ts`, `ClientFile.tsx` and the tests. Hook names (`useCase`, `useApprovals`, `useDecideCase`, `useRouteCase`, `useReturnCase`, `useAttachEvidence`, `useMeasure`, `useFundingEvents`, `usePortfolio`, `useTrackRecord`, `useLessons`, `useEvalLatest`) are defined once and used with those names. The squad `usePortfolio` (key `['my-portfolio']`) is a different hook from the deleted cockpit `usePortfolio` in `@/api/hooks` (key `['portfolio']`); `Portfolio.tsx` imports it from `../api/hooks`.

**Review Focus coverage.** 1: `test_routing.py` (loop order, return counts for the analyst only, 409 through the API), `case.test.tsx`, the hand-off journey. 2: `test_thread_opening.py`, the thread test "opens at what is new". 3: `test_client_file.py`, `clientFile.test.tsx` (`TrendBars`, `MeasureNow`), `portfolio.test.tsx`, Task 6's `noTypedZeroForUnmeasured`. 4: `redirects.test.tsx`, `oversight.test.tsx`, Task 5's "old addresses" journey. 5: `test_the_case_view_says_what_each_person_may_do`, `test_route_api_refuses_an_administrator`, `case.test.tsx` ("offers an administrator nothing to do"), `oversight.test.tsx`, Task 6's administrator journey.

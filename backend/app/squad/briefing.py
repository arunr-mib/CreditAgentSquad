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

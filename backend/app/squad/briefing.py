"""What Squad tells the signed-in person on opening: what needs them, ordered by consequence,
and what agents finished overnight. Every count is taken from the list that is returned."""
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.roles import Permission, can
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.funding import FundingEvent
from app.domain.monitoring import Signal, WorkItem
from app.domain.org import User
from app.domain.terms import ReportingObligation
from app.publishing.content import SIGNAL_LABELS
from app.squad import rules
from app.squad.threads import REPORT_TEXT_KEYS
from app.squad.words import decision_words, question_choice

BREACH_TYPES = frozenset({"covenant.breach", "covenant.reported_breach_unconfirmed", "bb.over_advance"})
KIND_RANK = {"breach": 0, "overdue_report": 1, "signal": 2, "question": 3, "review": 4, "funding": 5, "decided": 6}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
RECENT = timedelta(days=2)
FUNDING_WINDOW_DAYS = 14
OVERNIGHT_LIMIT = 8


def _decided_state(w: WorkItem, who: str) -> str:
    choice = question_choice(w.evidence, w.decision) if w.item_type == "question" else None
    return f"{choice} \u2014 chosen by {who}" if choice else f"{decision_words(w.decision)} by {who}"


def _days(n: int) -> str:
    return f"{n} day overdue" if n == 1 else f"{n} days overdue"


def build_briefing(db: Session, user: User) -> dict[str, Any]:
    today = clock.today(db)
    borrowers = {b.id: b for b in db.execute(select(Borrower)).scalars()}
    names = {u.id: u.name for u in db.execute(select(User)).scalars()}
    can_decide = can(user.role, Permission.DECIDE_WORK_ITEM)

    def mine(borrower_id) -> bool:
        """Overdue reports and signals are the client's analyst's to work; others see them listed."""
        return can_decide and rules.is_clients_analyst(user, borrowers[borrower_id])

    def ref(borrower_id) -> dict[str, Any]:
        b = borrowers[borrower_id]
        return {"borrower_id": str(b.id), "borrower_code": b.code, "borrower_name": b.name}

    items: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    open_or_recent = or_(WorkItem.status == "open",
                         and_(WorkItem.status == "decided", WorkItem.decided_at >= now - RECENT))
    for w in db.execute(select(WorkItem).where(open_or_recent)).scalars():
        if w.borrower_id not in borrowers:
            continue
        kind = "question" if w.item_type == "question" else "breach" if w.item_type in BREACH_TYPES else "review"
        base = {**ref(w.borrower_id), "title": w.title, "severity": w.severity, "work_item_id": str(w.id)}
        if w.status == "open":
            prepared_by_me = rules.prepared_by(user, w)
            second_person_blocked = rules.second_person_blocked(user, w)
            if rules.can_act(user, w, borrowers[w.borrower_id]):
                state = "Squad asks" if kind == "question" else "waiting for you"
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": state, "needs_you": True,
                              "_due": w.due_date})
            elif (rules.holds_permission(user, w) and not second_person_blocked and w.assigned_to is None
                  and user.role == "analyst"):  # an analyst's colleague's client: listed, not counted
                owner = names.get(borrowers[w.borrower_id].analyst_id, "a colleague")
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": f"with {owner}",
                              "needs_you": False, "_due": w.due_date})
            elif prepared_by_me and (second_person_blocked or (w.assigned_to and w.assigned_to != user.id)):
                who = names.get(w.assigned_to, "a colleague") if w.assigned_to else "a second person"
                items.append({**base, "key": f"item:{w.id}", "kind": kind, "state": f"with {who}",
                              "needs_you": False, "_due": w.due_date})
        else:
            items.append({**base, "key": f"item:{w.id}", "kind": "decided",
                          "state": _decided_state(w, names.get(w.decided_by, "a colleague")),
                          "needs_you": False, "_due": None})

    for ob in db.execute(select(ReportingObligation).where(ReportingObligation.status == "overdue")).scalars():
        if ob.borrower_id in borrowers:
            days = (today - ob.due_date).days
            items.append({**ref(ob.borrower_id), "key": f"overdue:{ob.id}", "kind": "overdue_report",
                          "title": f"{ob.document_type.replace('_', ' ').capitalize()} for {ob.period_end:%B %Y} is overdue",
                          "state": _days(days), "severity": "medium",
                          "needs_you": mine(ob.borrower_id),
                          "work_item_id": None, "_due": ob.due_date})

    # A signal that has an open work item (raised from it, or attached to a chaser) is listed once, as the item.
    raised: set[tuple[Any, str]] = set()
    for w in db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars():
        evidence = w.evidence or {}
        rules_raised = {evidence.get("rule_id")} | {e.get("rule_id") for e in evidence.get("signals", [])}
        raised |= {(w.borrower_id, r) for r in rules_raised if r}
    seen_signals: set = set()
    signals = [s for s in db.execute(select(Signal).where(Signal.status == "open")).scalars()
               if (s.borrower_id, s.rule_id) not in raised]
    signals.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), -x.created_at.timestamp()))
    for s in signals:
        if s.borrower_id in borrowers and s.borrower_id not in seen_signals:
            seen_signals.add(s.borrower_id)
            label = SIGNAL_LABELS.get(s.rule_id, s.rule_id.replace("_", " "))
            items.append({**ref(s.borrower_id), "key": f"signal:{s.borrower_id}", "kind": "signal",
                          "title": f"Signal: {label}", "state": "new signal", "severity": s.severity,
                          "needs_you": mine(s.borrower_id), "work_item_id": None, "_due": None})

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
    runs = db.execute(select(AgentRun).where(
        AgentRun.status == "completed", AgentRun.agent_name != "copilot", AgentRun.borrower_id.is_not(None),
        AgentRun.finished_at >= since).order_by(AgentRun.finished_at.desc()).limit(OVERNIGHT_LIMIT * 4)).scalars()
    for run in runs:
        out = run.output or {}
        text = next((out[k] for k in REPORT_TEXT_KEYS if isinstance(out.get(k), str) and out[k].strip()), None)
        if text and run.borrower_id in borrowers:
            overnight.append({"agent_name": run.agent_name, "text": text, "finished_at": run.finished_at.isoformat(),
                              **ref(run.borrower_id)})
        if len(overnight) == OVERNIGHT_LIMIT:
            break

    open_clients: dict[str, dict[str, Any]] = {}
    for i in items:
        if i["kind"] != "decided":
            c = open_clients.setdefault(i["borrower_id"], {"borrower_id": i["borrower_id"], "code": i["borrower_code"],
                                                            "name": i["borrower_name"], "open": 0})
            c["open"] += 1
    return {"as_of": today.isoformat(), "needs_you": sum(1 for i in items if i["needs_you"]), "items": items,
            "overnight": overnight, "open_clients": sorted(open_clients.values(), key=lambda c: c["name"])}

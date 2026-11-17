"""The review sheet for one borrower and period: assembled by code from stored facts, with
commentary drafted by the Review Agent and approved by a person."""
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.review import draft_commentary
from app.calc.periods import same_period_prior_year
from app.core import ledger
from app.domain.credit import Borrower, Facility
from app.domain.facts import Fact
from app.domain.metrics_service import store_metrics
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, Signal, WorkItem
from app.domain.org import User
from app.domain.reviews import Commentary, ReviewSheet
from app.domain.work_items import raise_item
from app.guardrails.narrative import FactView, check_narrative, referenced_fact_ids, render

METRIC_LABELS = {
    "revenue_ttm": "Revenue, trailing twelve months", "ebitda": "EBITDA, trailing twelve months",
    "ebitda_margin": "EBITDA margin", "net_income_ttm": "Net income, trailing twelve months",
    "leverage": "Total debt to EBITDA", "interest_coverage": "Interest coverage", "current_ratio": "Current ratio",
    "dso": "Days sales outstanding", "dpo": "Days payables outstanding", "cash": "Cash",
    "total_debt": "Total debt", "revenue_growth_yoy": "Revenue growth, year on year",
}


def _view(fact: Fact) -> FactView:
    return FactView(str(fact.id), fact.value, fact.unit)


def _fact(db: Session, borrower_id: uuid.UUID, key: str, period_end: date) -> Fact | None:
    from app.domain.facts_service import current_fact
    return current_fact(db, borrower_id, key, period_end, 0)


def build_sheet(db: Session, cycle: Cycle) -> tuple[dict[str, Any], dict[str, FactView], dict[str, str]]:
    """The sheet's content, the facts it references and a label for each. Code only."""
    borrower = db.get(Borrower, cycle.borrower_id)
    end, prior = cycle.period_end, same_period_prior_year(cycle.period_end)
    facts: dict[str, FactView] = {}
    labels: dict[str, str] = {}

    def ref(fact: Fact | None, label: str) -> str | None:
        if fact is None:
            return None
        facts[str(fact.id)] = _view(fact)
        labels[str(fact.id)] = label
        return str(fact.id)

    now, then = store_metrics(db, borrower, end), store_metrics(db, borrower, prior)
    metrics = [{"metric": name, "label": METRIC_LABELS[name],
                "current": ref(now.get(name), f"{METRIC_LABELS[name]}, {end:%b %-d, %Y}"),
                "year_earlier": ref(then.get(name), f"{METRIC_LABELS[name]}, {prior:%b %-d, %Y}")}
               for name in METRIC_LABELS if name in now]

    covenants = []
    for test in db.execute(select(CovenantTest).where(
            CovenantTest.cycle_id == cycle.id, CovenantTest.superseded.is_(False), CovenantTest.covenant_id != "*")
            .order_by(CovenantTest.covenant_name)).scalars():
        name = test.covenant_name
        covenants.append({
            "covenant": name, "operator": test.operator, "outcome": test.outcome, "calc_run_id": str(test.calc_run_id),
            "value": ref(db.get(Fact, test.value_fact_id) if test.value_fact_id else None, f"{name}, calculated"),
            "threshold": ref(_fact(db, borrower.id, f"cov.{test.covenant_id}.threshold", end), f"{name}, required"),
            "headroom_pct": ref(_fact(db, borrower.id, f"cov.{test.covenant_id}.headroom_pct", end), f"{name}, cushion"),
            "reported": ref(db.get(Fact, test.reported_fact_id) if test.reported_fact_id else None,
                            f"{name}, reported on the certificate"),
            "certificate_claims_compliance": test.reported_in_compliance})

    signals = [{"signal_id": str(s.id), "rule": s.rule_id, "severity": s.severity,
                "explanation": (s.explanation or {}).get("text")}
               for s in db.execute(select(Signal).where(Signal.cycle_id == cycle.id)
                                   .order_by(Signal.rank.nulls_last(), Signal.severity)).scalars()]
    review = db.execute(select(BorrowingBaseReview).where(BorrowingBaseReview.cycle_id == cycle.id)
                        .order_by(BorrowingBaseReview.period_end.desc())).scalars().first()
    collateral = None
    if review is not None:
        collateral = {"as_of": review.period_end.isoformat(), "outcome": review.outcome,
                      "availability": ref(_fact(db, borrower.id, "bb.availability", review.period_end), "Availability"),
                      "mismatched_lines": [d["line"] for d in review.differences if d.get("status") == "mismatch"]}
    items = [{"type": w.item_type, "severity": w.severity, "title": w.title, "status": w.status, "decision": w.decision}
             for w in db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id)
                                 .order_by(WorkItem.created_at)).scalars()
             if w.item_type != "review.commentary_approval"]
    loans = [{"loan": f.name, "type": f.facility_type, "has_borrowing_base": f.has_borrowing_base}
             for f in db.execute(select(Facility).where(Facility.borrower_id == borrower.id).order_by(Facility.code)).scalars()]
    sheet = {"period_end": end.isoformat(), "risk_rating": borrower.risk_rating, "loans": loans, "metrics": metrics,
             "covenants": covenants, "signals": signals, "collateral": collateral, "work_items": items}
    return sheet, facts, labels


def _store_commentary(db: Session, sheet_row: ReviewSheet, section: str, body: str, *, author: tuple[str, str],
                      agent_run_id: uuid.UUID | None = None) -> Commentary:
    latest = db.execute(select(func.max(Commentary.version)).where(
        Commentary.review_sheet_id == sheet_row.id, Commentary.section == section)).scalar() or 0
    for old in db.execute(select(Commentary).where(
            Commentary.review_sheet_id == sheet_row.id, Commentary.section == section,
            Commentary.status == "draft")).scalars():
        old.status = "superseded"
    row = Commentary(borrower_id=sheet_row.borrower_id, review_sheet_id=sheet_row.id, section=section,
                     version=latest + 1, body=body, fact_ids=referenced_fact_ids(body), author_type=author[0],
                     author_id=author[1], agent_run_id=agent_run_id)
    db.add(row)
    db.flush()
    ledger.record(db, actor_type=author[0], actor_id=author[1], action="commentary.written",
                  entity_type="commentary", entity_id=row.id,
                  payload={"review_sheet_id": sheet_row.id, "section": section, "version": row.version})
    return row


def prepare_review(db: Session, *, cycle: Cycle, llm: LLMClient) -> ReviewSheet:
    """Build the sheet, ask the Review Agent for a draft, and ask a person to approve it."""
    borrower = db.get(Borrower, cycle.borrower_id)
    sheet, facts, labels = build_sheet(db, cycle)
    row = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one_or_none()
    if row is None:
        row = ReviewSheet(borrower_id=borrower.id, cycle_id=cycle.id)
        db.add(row)
    row.content = {**sheet, "fact_labels": labels}
    row.status = "draft"
    db.flush()
    draft = draft_commentary(db, borrower=borrower, cycle=cycle, sheet=sheet, facts=facts, labels=labels, llm=llm)
    for section, body in draft.sections.items():
        _store_commentary(db, row, section, body, author=("agent", "review@1"), agent_run_id=draft.run_id)
    raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="review_prep", item_type="review.commentary_approval",
        severity="medium", title=f"{borrower.name}: review sheet is ready for approval",
        question=("The Review Agent drafted commentary for this review. Approve it as written or after your edits?"
                  if draft.sections else
                  "No commentary could be drafted for this review. Write the commentary and approve the sheet?"),
        allowed_decisions=["approve", "return_for_rework"], required_permission="approve_commentary",
        evidence={"review_sheet_id": str(row.id), "sections": sorted(draft.sections)}, guardrail_notes=draft.notes,
        agent_run_id=draft.run_id, actor=("agent", "review"), dedupe_key=f"review.approval:{row.id}")
    ledger.record(db, actor_type="system", actor_id="reviews", action="review_sheet.prepared",
                  entity_type="review_sheet", entity_id=row.id,
                  payload={"cycle_id": cycle.id, "sections_drafted": sorted(draft.sections),
                           "sections_dropped": len(draft.notes)})
    db.flush()
    return row


def facts_for(db: Session, fact_ids: list[str]) -> dict[str, FactView]:
    out = {}
    for fid in fact_ids:
        fact = db.get(Fact, uuid.UUID(fid))
        if fact is not None:
            out[fid.lower()] = _view(fact)
    return out


def write_section(db: Session, sheet_row: ReviewSheet, *, section: str, body: str, user: User) -> tuple[Commentary, list[str]]:
    """A person writes or edits a section. Typed figures are the person's own responsibility, so
    they are reported back as warnings, not refused; a reference to an unknown fact is refused."""
    if sheet_row.status == "released":
        raise ValueError("a released review sheet cannot be edited")
    facts = facts_for(db, referenced_fact_ids(body))
    notes = check_narrative(body, facts)
    typed = ("figure_untraceable", "number_in_words")  # the person's own quantities: warned, not refused
    broken = [n.detail for n in notes if n.check not in typed]
    if broken:
        raise ValueError("; ".join(broken))
    row = _store_commentary(db, sheet_row, section, body, author=("user", str(user.id)))
    return row, [f"{n.subject}: {n.detail}" if n.subject else n.detail for n in notes]


def current_commentary(db: Session, sheet_row: ReviewSheet) -> list[Commentary]:
    rows = db.execute(select(Commentary).where(
        Commentary.review_sheet_id == sheet_row.id, Commentary.status.in_(("draft", "approved")))
        .order_by(Commentary.section, Commentary.version.desc())).scalars()
    latest: dict[str, Commentary] = {}
    for c in rows:
        latest.setdefault(c.section, c)
    return list(latest.values())


def rendered(db: Session, commentary: Commentary) -> str:
    return render(commentary.body, facts_for(db, commentary.fact_ids))


def on_decision(db: Session, item: WorkItem, user: User, decision: str, reason: str) -> None:
    """Approval marks the current commentary approved and the sheet reviewed."""
    reference = item.evidence.get("review_sheet_id")
    sheet_row = db.get(ReviewSheet, uuid.UUID(reference)) if reference else None
    if sheet_row is None:
        raise ValueError("the review sheet no longer exists")
    if decision != "approve":
        if not reason.strip():
            raise ValueError("returning a review for rework needs a reason")
        return
    sections = current_commentary(db, sheet_row)
    if not sections:
        raise ValueError("there is no commentary to approve; write at least a summary first")
    for c in sections:
        c.status = "approved"
        c.approved_by = user.id
        c.approved_at = datetime.now(UTC)
    sheet_row.status = "reviewed"
    sheet_row.approved_by = user.id
    sheet_row.approved_at = datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=user.id, action="review_sheet.approved",
                  entity_type="review_sheet", entity_id=sheet_row.id,
                  payload={"sections": [c.section for c in sections], "reason": reason})
    db.flush()

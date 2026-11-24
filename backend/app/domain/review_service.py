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
from app.core.roles import SecondPersonRequired, require_second_person
from app.domain.credit import Borrower, Facility
from app.domain.facts import USABLE_STATUSES, Fact
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


# Which check withheld a drafted section, in the words the approver reads.
_WITHHELD_BY = {"narrative": "number check", "policy": "policy check"}


def withheld_sections(notes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Each section the agent drafted that a check withheld, with the check and the reason, in
    section order. An older note without `section` is read from its `detail` ("section: why")."""
    out = []
    for note in notes:
        if note.get("action") != "section_dropped":
            continue
        section, _, reason = (note.get("detail") or "").partition(": ")
        withheld_by = ("fact reference check" if note.get("check") == "no_facts"
                       else _WITHHELD_BY.get(note.get("layer", ""), "check"))
        out.append({"section": note.get("section") or section, "withheld_by": withheld_by,
                    "check": note.get("check", ""), "reason": note.get("reason") or reason})
    return sorted(out, key=lambda w: w["section"])


def _approval_wording(name: str, drafted: bool, withheld: list[dict[str, str]]) -> tuple[str, str]:
    """The approval item's title and question. Withheld sections are named in both, so the
    approver knows the sheet is missing them before opening it."""
    title = f"{name}: review sheet is ready for approval"
    if not withheld:
        return title, ("The Review Agent drafted commentary for this review. Approve it as written or after your "
                       "edits?" if drafted else
                       "No commentary could be drafted for this review. Write the commentary and approve the sheet?")
    many = len(withheld) != 1
    by = " and the ".join(sorted({w["withheld_by"] for w in withheld}))
    title = f"{title}, {len(withheld)} section{'s' if many else ''} withheld by the {by}"
    names = [w["section"] for w in withheld]
    listed = names[0] if not many else ", ".join(names[:-1]) + " and " + names[-1]
    lead = ("The Review Agent drafted commentary for this review, but" if drafted
            else "No section of the Review Agent's draft passed its checks:")
    question = (f"{lead} the {listed} section{'s were' if many else ' was'} withheld and "
                f"{'are' if many else 'is'} not on the sheet. Write the withheld section{'s' if many else ''}, "
                f"or approve the sheet without {'them' if many else 'it'}?")
    return title[:240], question


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
        if section in draft.code_sections:  # written by code: no model text, so not shown as agent-written
            _store_commentary(db, row, section, body, author=("system", "review"))
        else:
            _store_commentary(db, row, section, body, author=("agent", "review@1"), agent_run_id=draft.run_id)
    withheld = withheld_sections(draft.notes)
    row.content = {**row.content, "withheld_sections": withheld}
    title, question = _approval_wording(borrower.name, bool(draft.sections), withheld)
    raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="review_prep", item_type="review.commentary_approval",
        severity="medium", title=title, question=question,
        allowed_decisions=["approve", "return_for_rework"], required_permission="approve_commentary",
        evidence={"review_sheet_id": str(row.id), "sections": sorted(draft.sections),
                  "withheld_sections": withheld},
        guardrail_notes=draft.notes,
        agent_run_id=draft.run_id, actor=("agent", "review"), dedupe_key=f"review.approval:{row.id}")
    ledger.record(db, actor_type="system", actor_id="reviews", action="review_sheet.prepared",
                  entity_type="review_sheet", entity_id=row.id,
                  payload={"cycle_id": cycle.id, "sections_drafted": sorted(draft.sections),
                           "sections_dropped": len(draft.notes),
                           "sections_withheld": [w["section"] for w in withheld]})
    db.flush()
    return row


def facts_for(db: Session, fact_ids: list[str], borrower_id: uuid.UUID | None = None) -> dict[str, FactView]:
    """The facts behind references. With `borrower_id`, a fact of any other borrower is left out,
    so a reference to it reads as a fact that is not in scope."""
    out = {}
    for fid in fact_ids:
        fact = db.get(Fact, uuid.UUID(fid))
        if fact is not None and (borrower_id is None or fact.borrower_id == borrower_id):
            out[fid.lower()] = _view(fact)
    return out


# What `check_narrative` finds in text a person wrote falls into two groups. A quantity typed or
# spelt out is the person's to stand behind, so the text is saved, but it cannot be approved
# unless the figure is one of the borrower's stored facts. Everything else, including a check
# this code has not seen before, is a broken reference and the text is not saved.
TYPED_QUANTITY_CHECKS = frozenset({"figure_untraceable", "number_in_words"})
BLOCKS_APPROVAL = "this blocks approval until it is replaced by a fact reference or removed"


def _stored_values(db: Session, borrower_id: uuid.UUID) -> tuple[list[Any], list[Any]]:
    """Every figure in use for the borrower, and the ratios among them."""
    rows = db.execute(select(Fact.value, Fact.unit).where(
        Fact.borrower_id == borrower_id, Fact.status.in_(USABLE_STATUSES))).all()
    return [value for value, _ in rows], [value for value, unit in rows if unit == "ratio"]


def commentary_findings(db: Session, borrower_id: uuid.UUID, body: str) -> tuple[list[str], list[str], list[str]]:
    """Check text a person wrote. Returns (broken references, typed quantities, and the typed
    quantities that match no stored fact of this borrower and so block approval)."""
    facts = facts_for(db, referenced_fact_ids(body), borrower_id)
    notes = check_narrative(body, facts)
    broken = [_say(n) for n in notes if n.check not in TYPED_QUANTITY_CHECKS]
    typed = [_say(n) for n in notes if n.check in TYPED_QUANTITY_CHECKS]
    values, ratios = _stored_values(db, borrower_id)
    # a quantity spelt out in words cannot be matched to a fact, so it stays in this list
    unmatched = [_say(n) for n in check_narrative(body, facts, allowed_figures=values, known_ratios=ratios)
                 if n.check in TYPED_QUANTITY_CHECKS]
    return broken, typed, unmatched


def _say(note: Any) -> str:
    """A finding in words. The guardrail's note may name the offending text in `subject`, apart
    from the explanation in `detail`; an older note carries it inside `detail`."""
    subject = getattr(note, "subject", None)
    return f"{subject}: {note.detail}" if subject else note.detail


def write_section(db: Session, sheet_row: ReviewSheet, *, section: str, body: str, user: User) -> tuple[Commentary, list[str]]:
    """A person writes or edits a section. A reference to a fact that is unknown, or belongs to
    another borrower, is refused. A typed figure is the person's own responsibility: it is
    reported back as a warning, and one that matches no stored fact of this borrower blocks
    approval until it is replaced by a fact reference or removed."""
    if sheet_row.status == "released":
        raise ValueError("a released review sheet cannot be edited")
    broken, typed, unmatched = commentary_findings(db, sheet_row.borrower_id, body)
    if broken:
        raise ValueError("; ".join(broken))
    row = _store_commentary(db, sheet_row, section, body, author=("user", str(user.id)))
    blocking = set(unmatched)
    return row, [f"{detail}; {BLOCKS_APPROVAL}" if detail in blocking else detail for detail in typed]


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


def approval_refusal(db: Session, item: WorkItem, user_id, decision: str) -> Exception | None:
    """The four-eyes rule of `on_decision`, asked without recording anything: whoever last edited a section cannot approve."""
    if decision != "approve":
        return None
    reference = item.evidence.get("review_sheet_id")
    try:
        sheet_row = db.get(ReviewSheet, uuid.UUID(str(reference))) if reference else None
    except ValueError:  # evidence is written by code; a malformed id is read as no sheet, never a 500
        sheet_row = None
    if sheet_row is None:
        return None
    for c in current_commentary(db, sheet_row):
        if c.author_type == "user":
            try:
                require_second_person(c.author_id, user_id, _LAST_EDITOR.format(section=c.section))
            except SecondPersonRequired as exc:
                return exc
    return None


_LAST_EDITOR = "You last edited the {section} section, so a different person must approve this review."


def on_decision(db: Session, item: WorkItem, user: User, decision: str, reason: str) -> None:
    """Approval marks the current commentary approved and the sheet reviewed."""
    reference = item.evidence.get("review_sheet_id")
    try:
        sheet_row = db.get(ReviewSheet, uuid.UUID(str(reference))) if reference else None
    except ValueError:  # evidence is written by code; a malformed id is read as no sheet, never a 500
        sheet_row = None
    if sheet_row is None:
        raise ValueError("the review sheet no longer exists")
    if decision != "approve":
        if not reason.strip():
            raise ValueError("returning a review for rework needs a reason")
        return
    sections = current_commentary(db, sheet_row)
    if not sections:
        raise ValueError("there is no commentary to approve; write at least a summary first")
    written = [c for c in sections if c.author_type == "user"]
    for c in written:
        # four eyes: whoever last edited a section prepared it, and cannot be the one who approves it
        require_second_person(c.author_id, user.id, _LAST_EDITOR.format(section=c.section))
    problems = []
    for c in written:
        broken, _, unmatched = commentary_findings(db, sheet_row.borrower_id, c.body)
        problems += [f"{c.section}: {detail}" for detail in broken + unmatched]
    if problems:
        raise ValueError("commentary written by a person has a figure that matches no stored fact for this "
                         "borrower; replace it with a fact reference or remove it. " + "; ".join(problems))
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

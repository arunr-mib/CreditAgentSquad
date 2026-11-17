"""Load the synthetic loan book into the database and replay its history through the real
services, so every seeded covenant test, borrowing base review and signal is produced by the
same code that runs live. Seeded facts are marked `seeded`: loaded from ground truth, not extracted.

Run: PYTHONPATH=backend python -m app.seed_book [--current seeded|live|none]
  seeded  the current period is also loaded from ground truth (a full demo without model calls)
  live    current-period documents arrive unclassified and the agents process them
  none    history only
"""
import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.intake import chase_missing
from app.calc import template
from app.calc.terms import Terms
from app.core import clock, ledger
from app.core.roles import Role
from app.core.security import hash_password
from app.domain import calendar, workflow
from app.domain.collateral_service import review_borrowing_base, store_line_availability
from app.domain.covenant_service import run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import add_fact
from app.domain.monitoring import STAGES, Cycle
from app.domain.org import User
from app.domain.signals_service import run_signals
from app.domain.terms import TermsVersion
from app.domain.terms_service import check_provenance, raise_unapproved_amendments
from app.domain.work_items import raise_item

SYNTHETIC_ROOT = Path(__file__).resolve().parents[2] / "synthetic" / "out"
SEED_ACTOR = ("system", "seed")
DOC_TYPES = {"annual_financial_statements": "annual_statements",
             "interim_financial_statements": "interim_statements"}
# borrowing base lines: the book's names -> the calculation's names
BB_LINES = {
    "gross_ar": "ar_total", "ineligible_excluded": "ar_ineligible_excluded",
    "ineligible_over_age": "ar_ineligible_age", "ineligible_cross_aging": "ar_ineligible_cross_aging",
    "ineligible_contra": "ar_ineligible_contra", "ineligible_concentration": "ar_ineligible_concentration",
    "total_ineligible_ar": "ar_ineligible_total", "eligible_ar": "ar_eligible",
    "gross_inventory": "inventory_total", "ineligible_inventory": "inventory_ineligible",
    "eligible_inventory": "inventory_eligible", "lesser_of_base_and_commitment": "borrowing_limit",
}
AR_BUCKETS = {"0_30": "current", "31_60": "days_31_60", "61_90": "days_61_90", "over_90": "over_90"}
# Problems that stop a live cycle before covenant testing. In seeded mode the current period's
# figures are therefore not loaded for these borrowers, and a stand-in item is raised.
HALTING = ("intake.missing_document", "spread.image_only", "spread.does_not_foot")
SEEDED_ITEMS = {
    "spread.image_only": ("The current statements are a scanned image and cannot be read. Request a text PDF, or key the figures by hand?",
                          ["request_new_document", "key_by_hand"], True),
    "spread.does_not_foot": ("The current statements do not foot: a section appears to be missing. Which figure is wrong, or is a page missing?",
                             ["values_corrected", "accept_as_reported", "request_new_document"], True),
    "spread.restatement": ("The comparative column differs from what was confirmed last year. Has the borrower restated, and should the prior spread be updated?",
                           ["restated_update_prior", "keep_prior", "ask_borrower"], False),
}


def halted(truth: dict[str, Any]) -> bool:
    return any(x["type"] in HALTING for x in truth["expected"]["exceptions"])


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def doc_type(name: str) -> str:
    return DOC_TYPES.get(name, name)


def normalise_terms(terms: dict[str, Any]) -> dict[str, Any]:
    """The book's document type names -> the product's."""
    out = json.loads(json.dumps(terms))
    for req in out.get("reporting_requirements", []):
        req["document_type"] = doc_type(req["document_type"])
    return out


def ar_rows(aging: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in aging:
        out = {"customer": row["customer"], "days_1_30": "0", "contra": str(row.get("contra", "0"))}
        for theirs, ours in AR_BUCKETS.items():
            out[ours] = str(row["buckets"][theirs])
        if row.get("category") and row["category"] != "trade":
            out["flags"] = [row["category"]]
        rows.append(out)
    return rows


def bb_certificate(lines: dict[str, Any]) -> dict[str, Decimal]:
    return {BB_LINES.get(name, name): _d(value) for name, value in lines.items()}


@dataclass
class SeedReport:
    borrowers: int = 0
    documents: int = 0
    facts: int = 0
    cycles: int = 0
    covenant_tests: int = 0
    borrowing_base_reviews: int = 0
    signals: int = 0
    work_items: int = 0
    provenance_warnings: dict[str, list[str]] = field(default_factory=dict)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z]+", ".", name.lower()).strip(".")


def ensure_user(db: Session, name: str, role: Role, title: str, password_hash: str) -> User:
    user = db.execute(select(User).where(User.name == name)).scalar_one_or_none()
    if user is None:
        user = User(email=f"{_slug(name)}@bankofstoic.example", name=name, title=title, role=role.value,
                    password_hash=password_hash)
        db.add(user)
        db.flush()
        ledger.record(db, actor_type="system", actor_id="seed", action="user.created", entity_type="user",
                      entity_id=user.id, payload={"email": user.email, "role": role.value})
    return user


def _seed_facts(db: Session, borrower: Borrower, period: dict[str, Any]) -> int:
    end, months, count = _day(period["period_end"]), period["months"], 0
    for key, value in period["values"].items():
        line = template.LINE_BY_KEY.get(key)
        if line is None:
            continue
        add_fact(db, borrower_id=borrower.id, key=key, period_end=end, months=months if line.flow else 0,
                 value=_d(value), kind="seeded", note="loaded from synthetic ground truth, not extracted",
                 actor=SEED_ACTOR)
        count += 1
    return count


def _seed_certificate(db: Session, borrower: Borrower, certificate: dict[str, Any]) -> int:
    end, count = _day(certificate["period_end"]), 0
    for covenant_id, entry in certificate["reported"].items():
        for name, value, unit in (("value", entry.get("value"), entry.get("unit", "ratio")),
                                  ("threshold", entry.get("threshold"), entry.get("unit", "ratio"))):
            if value is not None:
                add_fact(db, borrower_id=borrower.id, key=f"cert.{covenant_id}.{name}", period_end=end, months=0,
                         value=_d(value), unit=unit, kind="seeded", actor=SEED_ACTOR)
                count += 1
        if entry.get("in_compliance") is not None:
            add_fact(db, borrower_id=borrower.id, key=f"cert.{covenant_id}.in_compliance", period_end=end,
                     months=0, value=Decimal(1 if entry["in_compliance"] else 0), unit="count", kind="seeded",
                     actor=SEED_ACTOR)
            count += 1
    return count


def _settle(db: Session, cycle: Cycle, *, close: bool) -> None:
    """Set a seeded cycle's stages. History is closed; a seeded current period rests on the first
    stage that still has an open blocking item, or on review preparation when nothing is open."""
    resting = None
    for st in workflow.stages(db, cycle):
        if close:
            st.status = "done"
            continue
        if resting is not None:
            st.status = "pending"
        elif workflow.open_blocking_items(db, cycle, st.stage) > 0:
            st.status, resting = "needs_person", st.stage
        elif STAGES.index(st.stage) >= STAGES.index("review_prep"):
            st.status, resting = "pending", st.stage
        else:
            st.status = "done"
    if close:
        cycle.status, cycle.stage, cycle.closed_at = "closed", "closed", datetime.now(UTC)
    else:
        cycle.stage = resting or "review_prep"
    db.flush()


def seed_borrower(db: Session, truth: dict[str, Any], *, docs_root: Path, current: str, password_hash: str,
                  report: SeedReport) -> Borrower:
    info = truth["borrower"]
    as_of, current_period = _day(truth["as_of"]), _day(truth["current_period"])
    rm = ensure_user(db, info["relationship_manager"], Role.PORTFOLIO_MANAGER, "Relationship Manager", password_hash)
    analyst = ensure_user(db, info["analyst"], Role.ANALYST, "Credit Analyst", password_hash)
    borrower = Borrower(
        code=info["id"], name=info["name"], industry=info["industry"],
        fiscal_year_end_month=info["fiscal_year_end_month"], risk_rating=info["risk_rating"],
        relationship_manager_id=rm.id, analyst_id=analyst.id,
        profile={k: info[k] for k in ("legal_form", "city", "state", "chief_financial_officer", "auditor",
                                      "statement_scale") if k in info})
    db.add(borrower)
    db.flush()
    report.borrowers += 1

    facilities: dict[str, Facility] = {}
    for f in truth["facilities"]:
        facility = Facility(
            borrower_id=borrower.id, code=f["id"], name=f["name"], facility_type=f["type"],
            commitment=_d(f["commitment"]), has_borrowing_base=bool(f.get("borrowing_base")),
            origination_date=_day(f.get("closing_date")), maturity_date=_day(f.get("maturity_date")),
            profile={k: f[k] for k in ("interest_rate", "original_amount") if k in f})
        db.add(facility)
        facilities[f["id"]] = facility
    db.flush()

    # documents: history is filed by the seed; current-period documents depend on the mode
    documents: dict[str, Document] = {}
    for d in truth["documents"]:
        period_end = _day(d.get("period_end"))
        is_current = period_end == current_period
        if is_current and current == "none":
            continue
        path = docs_root / d["path"]
        if not path.exists():
            continue
        filed = not (is_current and current == "live")
        doc = ingest_pdf(
            db, borrower_id=borrower.id, data=path.read_bytes(), file_name=path.name, title=d["title"],
            doc_type=doc_type(d["type"]) if filed else None, doc_type_source="system", period_end=period_end if filed else None,
            received_date=_day(d.get("received_date")),
            effective_date=_day(d.get("document_date")) if filed and period_end is None else None,
            source="seed", actor=SEED_ACTOR)
        doc.meta = {**doc.meta, "external_id": d["id"]}
        documents[d["id"]] = doc
        report.documents += 1
    db.flush()

    # terms, exactly as the book states them: an approved version governs, a proposed one does not
    for tv in truth["terms_versions"]:
        facility = facilities[tv["facility_id"]]
        terms = normalise_terms(tv["terms"])
        Terms.model_validate(terms)
        approved = tv["status"] in ("approved", "superseded")
        approver = ensure_user(db, tv["approved_by"], Role.CREDIT_OFFICER, "Credit Officer", password_hash) \
            if approved and tv.get("approved_by") else None
        row = TermsVersion(
            facility_id=facility.id, version=tv["version"], status=tv["status"],
            effective_from=_day(tv["effective_from"]), effective_to=_day(tv.get("effective_to")), terms=terms,
            source_document_ids=list(tv.get("source_documents") or []), prepared_by_type="seed",
            prepared_by_id=tv.get("prepared_by") or "seed", approved_by=approver.id if approver else None,
            approved_at=datetime.combine(_day(tv["approved_at"]), datetime.min.time(), UTC)
            if approved and tv.get("approved_at") else None)
        db.add(row)
        db.flush()
        row.warnings = check_provenance(db, borrower.id, Terms.model_validate(terms))
        if row.warnings:
            report.provenance_warnings[f"{info['id']} v{tv['version']}"] = row.warnings
        calendar.generate_obligations(db, facility, row, start=date(2025, 1, 1), through=as_of)
    for doc in documents.values():
        calendar.match_document(db, doc)
    calendar.refresh_statuses(db, as_of)

    # facts
    load_current = current == "seeded" and not halted(truth)
    for period in truth.get("comparative_periods", []) + truth["periods"]:
        if _day(period["period_end"]) == current_period and not load_current:
            continue
        report.facts += _seed_facts(db, borrower, period)
    for row in truth["system_of_record"]:
        when = _day(row["date"])
        for key, value in (("sys.revolver_outstanding", row.get("revolver_outstanding")),
                           ("sys.commitment", row.get("commitment")),
                           ("sys.past_due_days", row.get("past_due_days")),
                           ("sys.term_loan_outstanding", row.get("term_loan_outstanding"))):
            if value is None:
                continue
            add_fact(db, borrower_id=borrower.id, key=key, period_end=when, months=0, value=_d(value),
                     unit="days" if key.endswith("days") else "usd", kind="system", connector="core_loan_accounting",
                     record_ref=info["id"], as_of=datetime.combine(when, datetime.min.time(), UTC), actor=SEED_ACTOR)
            report.facts += 1
    for certificate in truth["certificates"]:
        if _day(certificate["period_end"]) == current_period and not load_current:
            continue
        report.facts += _seed_certificate(db, borrower, certificate)

    # replay: one cycle per quarter, run through the same services that run live
    tested = sorted({_day(t["period_end"]) for t in truth["expected"]["covenant_tests"]})
    terms_facilities = [facilities[tv["facility_id"]] for tv in truth["terms_versions"]]
    bb_by_period = {_day(b["period_end"]): b for b in truth["borrowing_base"]}
    for end in tested:
        is_current = end == current_period
        if is_current and current != "seeded":
            continue
        months = ((end.month - borrower.fiscal_year_end_month) % 12) or 12
        cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=end, months=months, origin="seeded",
                                    actor=SEED_ACTOR)
        report.cycles += 1
        stops_here = is_current and not load_current
        for facility in facilities.values():
            store_line_availability(db, borrower=borrower, facility=facility, period_end=end, actor=SEED_ACTOR)
        if is_current:
            chase_missing(db, borrower=borrower, cycle=cycle, today=as_of)
            for expected in truth["expected"]["exceptions"]:
                if expected["type"] in SEEDED_ITEMS:
                    question, decisions, blocks = SEEDED_ITEMS[expected["type"]]
                    raise_item(
                        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="spreading",
                        item_type=expected["type"], severity="high" if blocks else "medium",
                        title=f"{borrower.name}: {expected['summary']}", question=question,
                        allowed_decisions=decisions, required_permission="confirm_spread", blocks_stage=blocks,
                        evidence={"seeded": True, "note": "Stand-in for the item the Spreading Agent raises on a live run.",
                                  "subject": expected.get("subject")},
                        actor=SEED_ACTOR, dedupe_key=f"{expected['type']}:{cycle.id}")
        for facility in ({} if stops_here else {f.id: f for f in terms_facilities}).values():
            report.covenant_tests += len(run_covenant_tests(
                db, borrower=borrower, facility=facility, period_end=end, cycle=cycle, origin="seeded",
                raise_items=is_current, actor=SEED_ACTOR))
            if is_current:
                raise_unapproved_amendments(db, facility, cycle_id=cycle.id, actor=SEED_ACTOR)
        for bb_end, bb in sorted(bb_by_period.items()):
            # month-end certificates belong to the quarter they fall in
            if not (end.year == bb_end.year and (bb_end.month - 1) // 3 == (end.month - 1) // 3):
                continue
            if stops_here and bb_end == end:
                continue
            facility = next(f for f in facilities.values() if f.has_borrowing_base)
            review_borrowing_base(
                db, borrower=borrower, facility=facility, period_end=bb_end, ar_rows=ar_rows(bb["ar_aging"]),
                inventory_rows=bb["inventory"], certificate=bb_certificate(bb["certificate"]),
                outstanding=_d(bb["outstanding"]), letters_of_credit=_d(bb["letters_of_credit"]), cycle=cycle,
                origin="seeded", raise_items=is_current and bb_end == end,
                source={"document": bb.get("document_id")}, actor=SEED_ACTOR)
            report.borrowing_base_reviews += 1
        report.signals += len(run_signals(db, borrower=borrower, period_end=end, as_of=as_of if is_current else end,
                                          cycle=cycle, origin="seeded", raise_items=is_current))
        _settle(db, cycle, close=not is_current)

    if current == "live":
        workflow.open_cycle(db, borrower_id=borrower.id, period_end=current_period, months=9, actor=SEED_ACTOR)
        report.cycles += 1
    return borrower


def seed_book(db: Session, *, root: Path = SYNTHETIC_ROOT, current: str = "seeded", only: list[str] | None = None,
              password: str = "squad-demo") -> SeedReport:
    from app.domain.monitoring import WorkItem

    report = SeedReport()
    password_hash = hash_password(password)
    files = sorted((root / "truth").glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no truth files under {root}/truth; run: python -m synthetic.generate")
    as_of = None
    for path in files:
        truth = json.loads(path.read_text())
        if only and truth["borrower"]["id"] not in only:
            continue
        if db.execute(select(Borrower.id).where(Borrower.code == truth["borrower"]["id"])).first():
            continue
        as_of = _day(truth["as_of"])
        seed_borrower(db, truth, docs_root=root, current=current, password_hash=password_hash, report=report)
    if as_of is not None:
        clock.set_today(db, as_of, actor=SEED_ACTOR)
    report.work_items = len(db.execute(select(WorkItem.id)).all())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--current", choices=("seeded", "live", "none"), default="seeded")
    parser.add_argument("--only", nargs="*", help="borrower ids to load")
    args = parser.parse_args()
    from app.core.db import get_engine
    from app.domain import hooks  # noqa: F401
    from app.seed_users import seed_users

    with Session(get_engine()) as db:
        seed_users(db)
        report = seed_book(db, current=args.current, only=args.only)
        db.commit()
    print(json.dumps(report.__dict__, indent=1, default=str))


if __name__ == "__main__":
    main()

"""Propose, check and approve covenant terms.

Terms govern a test only after a second person approves them. Approval never rewrites an
earlier version: the old version is closed the day before the new one takes effect.
"""
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.calc.terms import Citation, Terms
from app.core import clock, ledger
from app.core.roles import Permission, can, require_second_person
from app.domain import calendar
from app.domain.credit import Facility
from app.domain.documents import Document, DocumentPage
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.terms import TermsVersion
from app.domain.work_items import raise_item
from app.guardrails.quotes import number_in_quote, quote_on_page


class TermsRefused(Exception):
    """The terms cannot be proposed or approved as they stand. The message says what to repair."""


def resolve_document(db: Session, borrower_id: uuid.UUID, reference: str) -> Document | None:
    """A citation names a document by its id, or by the external id it arrived with."""
    try:
        doc = db.get(Document, uuid.UUID(reference))
        if doc is not None and doc.borrower_id == borrower_id:
            return doc
    except ValueError:
        pass
    return db.execute(select(Document).where(
        Document.borrower_id == borrower_id, Document.meta["external_id"].astext == reference)).scalar_one_or_none()


def _check_citation(db, borrower_id, citation: Citation | None, field: str, numbers: list[Decimal],
                    ratios: list[Decimal], warnings: list[str]) -> None:
    if citation is None or not citation.quote or citation.page is None:
        warnings.append(f"citation_missing:{field}")
        return
    doc = resolve_document(db, borrower_id, citation.document_id)
    if doc is None:
        warnings.append(f"document_not_on_file:{field}")
        return
    page = db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc.id, DocumentPage.page_number == citation.page)).scalar_one_or_none()
    if page is None or not quote_on_page(page.text, citation.quote):
        warnings.append(f"quote_not_on_page:{field}")
        return
    for number in numbers:
        if not number_in_quote(number, citation.quote, known_ratios=ratios):
            warnings.append(f"number_not_in_quote:{field}")
            return


_FLOOR = re.compile(r"\b(?:less\s+than|below|minimum|at\s+least|fall\s+below)\b", re.I)
_CEILING = re.compile(r"\b(?:exceed|exceeds|greater\s+than|more\s+than|maximum|above|in\s+excess\s+of)\b", re.I)
_GENERIC = {"ratio", "total", "minimum", "maximum", "the", "of", "and", "to", "consolidated", "covenant", "test"}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _distinctive(name: str) -> set[str]:
    """The words of a covenant's name that tell it from another ("fixed charge coverage",
    "leverage", "tangible net worth")."""
    return _tokens(name) - _GENERIC


def _clause_around(db, borrower_id, citation: Citation) -> str:
    """The sentence on the page that contains the quote, found by code: from the end of the
    sentence before it to the end of its own. A quote may be a fragment; what it is a fragment of
    is read from the page, not taken from the reader."""
    doc = resolve_document(db, borrower_id, citation.document_id)
    page = None if doc is None or citation.page is None else db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc.id, DocumentPage.page_number == citation.page)).scalar_one_or_none()
    if page is None:
        return ""
    text, quote = " ".join(page.text.split()), " ".join(citation.quote.split())
    at = text.lower().find(quote.lower())
    if at == -1:
        return ""
    stops = [m.end() for m in re.finditer(r"(?<!\bNo)(?<!\bU\.S)\.\s+(?=[A-Z])", text)]
    start = max((stop for stop in stops if stop <= at), default=0)
    end = min((stop for stop in stops if stop >= at + len(quote)), default=len(text))
    return text[start:end]


def check_provenance(db: Session, borrower_id: uuid.UUID, terms: Terms) -> list[str]:
    """Every number in the terms must appear in its quoted clause, on the cited page of a
    document on file. Returns warning codes; an empty list means the checks ran clean."""
    warnings: list[str] = []
    for covenant in terms.covenants:
        numbers = [covenant.test.threshold] + [s.value for s in covenant.test.steps]
        ratios = numbers if covenant.test.unit == "ratio" else []
        citations = covenant.citations or [None]
        # the threshold must be stated in at least one of the covenant's cited clauses
        found: list[str] = []
        for citation in citations:
            local: list[str] = []
            _check_citation(db, borrower_id, citation, f"covenants.{covenant.id}", [], ratios, local)
            if local:
                found.extend(local)
        stated = [n for n in numbers if any(
            c is not None and c.quote and number_in_quote(n, c.quote, known_ratios=ratios) for c in citations)]
        if found:
            warnings.extend(sorted(set(found)))
        elif len(stated) != len(numbers):
            warnings.append(f"number_not_in_quote:covenants.{covenant.id}.threshold")
        # the clause that states the threshold must be about this covenant: a number lifted from
        # another covenant's clause is on the page too
        distinctive = _distinctive(covenant.name)
        clauses = [_clause_around(db, borrower_id, c) for c in citations if c is not None and c.quote]
        clauses = [c for c in clauses if c]
        if distinctive and clauses and not any(distinctive <= _tokens(c) for c in clauses):
            warnings.append(f"covenant_not_named_in_clause:covenants.{covenant.id}")
        # a floor must be worded as a floor and a ceiling as a ceiling
        floor = covenant.test.operator in (">=", ">")
        says_floor = any(_FLOOR.search(c) for c in clauses)
        says_ceiling = any(_CEILING.search(c) for c in clauses)
        if clauses and ((floor and says_ceiling and not says_floor) or (not floor and says_floor and not says_ceiling)):
            warnings.append(f"direction_contradicts_clause:covenants.{covenant.id}")
    for name, definition in terms.definitions.items():
        for addback in definition.addbacks:
            cap_numbers = [addback.cap.value] if addback.cap is not None else []
            _check_citation(db, borrower_id, addback.citation, f"definitions.{name}.addbacks.{addback.name}",
                            cap_numbers, [], warnings)
    for req in terms.reporting_requirements:
        _check_citation(db, borrower_id, req.citation, f"reporting_requirements.{req.id}",
                        [Decimal(req.due_days_after_period_end)], [], warnings)
    if terms.borrowing_base is not None:
        bb = terms.borrowing_base
        clauses = [c for c in [bb.citation, *bb.citations] if c is not None]
        if not clauses:
            warnings.append("citation_missing:borrowing_base")
        for clause in clauses:
            _check_citation(db, borrower_id, clause, "borrowing_base", [], [], warnings)
        # each number of the block must be stated in at least one of its cited clauses
        numbers = {"commitment": bb.commitment}
        for component in bb.components:
            numbers[f"{component.collateral}.advance_rate"] = component.advance_rate
            if component.sublimit is not None:
                numbers[f"{component.collateral}.sublimit"] = component.sublimit
        for reserve in bb.reserves:
            numbers[f"reserves.{reserve.name}"] = reserve.amount
        for name, number in numbers.items():
            if not any(c.quote and number_in_quote(number, c.quote) for c in clauses):
                warnings.append(f"number_not_in_quote:borrowing_base.{name}")
    return warnings


def propose_terms(
    db: Session, *, facility: Facility, terms: dict[str, Any], effective_from: date,
    source_document_ids: list[str], prepared_by: tuple[str, str], agent_run_id: uuid.UUID | None = None,
    cycle_id: uuid.UUID | None = None,
) -> tuple[TermsVersion, WorkItem]:
    """Store a proposed version, check its citations, and ask a second person to approve it."""
    try:
        parsed = Terms.model_validate(terms)
    except ValidationError as exc:
        raise TermsRefused(f"the terms are not well formed: {exc.errors()[0]['msg']} at "
                           f"{'.'.join(str(p) for p in exc.errors()[0]['loc'])}") from exc
    latest = db.execute(select(func.max(TermsVersion.version)).where(
        TermsVersion.facility_id == facility.id)).scalar() or 0
    warnings = check_provenance(db, facility.borrower_id, parsed)
    version = TermsVersion(
        facility_id=facility.id, version=latest + 1, status="proposed", effective_from=effective_from,
        terms=terms, source_document_ids=source_document_ids, warnings=warnings,
        prepared_by_type=prepared_by[0], prepared_by_id=prepared_by[1], agent_run_id=agent_run_id)
    db.add(version)
    db.flush()
    ledger.record(db, actor_type="agent" if prepared_by[0] == "agent" else prepared_by[0], actor_id=prepared_by[1],
                  action="terms.proposed", entity_type="terms_version", entity_id=version.id,
                  payload={"facility_id": facility.id, "version": version.version,
                           "effective_from": effective_from, "warnings": warnings})
    item = raise_item(
        db, borrower_id=facility.borrower_id, facility_id=facility.id, cycle_id=cycle_id,
        stage="covenant_testing" if cycle_id else None, item_type="terms.approval_needed",
        severity="high" if warnings else "medium",
        title=f"{facility.name}: terms version {version.version} needs approval",
        question=("These terms have citation warnings. Approve them as they stand, or reject them for correction?"
                  if warnings else "Do these terms match the agreement and its amendments?"),
        allowed_decisions=["approve", "reject"], required_permission=Permission.APPROVE_TERMS.value,
        requires_second_person=True, prepared_by_id=prepared_by[1], agent_run_id=agent_run_id,
        evidence={"terms_version_id": str(version.id), "warnings": warnings,
                  "source_document_ids": source_document_ids},
        actor=("agent" if prepared_by[0] == "agent" else "system", prepared_by[1]),
        dedupe_key=f"terms.approval:{version.id}")
    return version, item


def approve_terms(db: Session, version: TermsVersion, approver: User, *, reason: str = "") -> TermsVersion:
    if version.status != "proposed":
        raise TermsRefused(f"version {version.version} is {version.status}, not proposed")
    if not can(approver.role, Permission.APPROVE_TERMS):
        raise PermissionError("your role cannot approve terms")
    require_second_person(version.prepared_by_id, approver.id)
    if version.warnings and not reason.strip():
        raise TermsRefused("these terms have citation warnings; approving them needs a written reason")
    try:
        Terms.model_validate(version.terms)
    except ValidationError as exc:
        raise TermsRefused("the stored terms are no longer well formed") from exc

    previous = db.execute(select(TermsVersion).where(
        TermsVersion.facility_id == version.facility_id, TermsVersion.status == "approved",
        TermsVersion.effective_to.is_(None))).scalar_one_or_none()
    if previous is not None:
        if version.effective_from <= previous.effective_from:
            raise TermsRefused("the new version must take effect after the version it replaces")
        previous.status = "superseded"
        previous.effective_to = version.effective_from - timedelta(days=1)
        ledger.record(db, actor_type="user", actor_id=approver.id, action="terms.superseded",
                      entity_type="terms_version", entity_id=previous.id,
                      payload={"effective_to": previous.effective_to, "by_version": version.version})
        db.flush()  # the old version is closed before the new one opens
    version.status = "approved"
    version.approved_by = approver.id
    version.approved_at = datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=approver.id, action="terms.approved",
                  entity_type="terms_version", entity_id=version.id,
                  payload={"version": version.version, "effective_from": version.effective_from,
                           "warnings_accepted": version.warnings or [], "reason": reason})
    db.flush()
    facility = db.get(Facility, version.facility_id)
    today = clock.today(db)
    calendar.generate_obligations(db, facility, version, start=date(today.year - 1, 1, 1),
                                  through=today + timedelta(days=120))
    return version


def reject_terms(db: Session, version: TermsVersion, user: User, *, reason: str) -> TermsVersion:
    if version.status != "proposed":
        raise TermsRefused(f"version {version.version} is {version.status}, not proposed")
    if not reason.strip():
        raise TermsRefused("rejecting terms needs a reason")
    version.status = "rejected"
    ledger.record(db, actor_type="user", actor_id=user.id, action="terms.rejected", entity_type="terms_version",
                  entity_id=version.id, payload={"version": version.version, "reason": reason})
    db.flush()
    return version


def on_decision(db: Session, item: WorkItem, user: User, decision: str, reason: str) -> None:
    """Called when a person decides a terms approval item."""
    reference = item.evidence.get("terms_version_id")
    version = db.get(TermsVersion, uuid.UUID(reference)) if reference else None
    if version is None:
        raise TermsRefused("the terms version no longer exists")
    if decision == "approve":
        approve_terms(db, version, user, reason=reason)
    else:
        reject_terms(db, version, user, reason=reason)


def unapproved_amendments(db: Session, facility: Facility) -> list[Document]:
    """Amendments on file for the borrower that no approved or superseded terms version names
    as a source. Such an amendment may change a test, so a person must decide what to do."""
    named: set[str] = set()
    for version in db.execute(select(TermsVersion).where(
            TermsVersion.facility_id == facility.id,
            TermsVersion.status.in_(("approved", "superseded")))).scalars():
        named.update(str(ref) for ref in version.source_document_ids or [])
    amendments = db.execute(select(Document).where(
        Document.borrower_id == facility.borrower_id, Document.doc_type == "amendment")
        .order_by(Document.effective_date.nulls_last(), Document.created_at)).scalars()
    return [d for d in amendments if str(d.id) not in named and d.meta.get("external_id") not in named]


def raise_unapproved_amendments(db: Session, facility: Facility, *, cycle_id: uuid.UUID | None = None,
                                actor: tuple[str, str] = ("system", "terms")) -> list[WorkItem]:
    items = []
    for doc in unapproved_amendments(db, facility):
        items.append(raise_item(
            db, borrower_id=facility.borrower_id, facility_id=facility.id, cycle_id=cycle_id,
            stage="covenant_testing" if cycle_id else None, item_type="terms.unapproved_amendment",
            severity="high", title=f"{doc.title} is on file but not in the approved terms",
            question="A signed amendment is on file but is not reflected in the approved terms. Should the terms be updated before covenants are tested?",
            allowed_decisions=["terms_update_requested", "amendment_not_applicable"],
            required_permission=Permission.PREPARE_TERMS.value,
            evidence={"document_id": str(doc.id), "effective_date": doc.effective_date.isoformat() if doc.effective_date else None},
            actor=actor, dedupe_key=f"terms.unapproved_amendment:{doc.id}"))
    return items

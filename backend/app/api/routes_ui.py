"""Read-only views the workspace screens need: the portfolio summary, facts in bulk, the source of
a fact (page, calculation, clause, history), terms versions, borrowing base reviews, covenant
tests with their fact ids, and a borrower timeline built from the ledger. Nothing here writes."""
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.serialize import plain, row
from app.calc import template
from app.core import clock
from app.core.db import get_db
from app.core.ledger import LedgerEvent
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.facts import CalcRun, Fact
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, Signal, WorkItem
from app.domain.org import User
from app.domain.reviews import Action, ReviewSheet
from app.domain.terms import ReportingObligation, TermsVersion

router = APIRouter(tags=["ui"])

STATEMENT_TYPES = ("annual_statements", "interim_statements")
SYSTEM_LABELS = {
    "sys.revolver_outstanding": "Line of credit, outstanding",
    "sys.commitment": "Line of credit, commitment",
    "sys.term_loan_outstanding": "Term loan, outstanding",
    "sys.past_due_days": "Days past due",
    "bb.availability": "Availability",
}
NAMED = {"ebitda": "EBITDA", "total_debt": "Total debt", "senior_debt": "Senior debt", "tnw": "Tangible net worth"}
BB_LINES = (
    ("ar_total", "Accounts receivable, total", 0), ("ar_ineligible_excluded", "Less: excluded accounts", 1),
    ("ar_ineligible_age", "Less: past the age limit", 1), ("ar_ineligible_cross_aging", "Less: cross-aging", 1),
    ("ar_ineligible_contra", "Less: contra accounts", 1), ("ar_ineligible_concentration", "Less: over the concentration limit", 1),
    ("ar_ineligible_total", "Total ineligible receivables", 0), ("ar_eligible", "Eligible receivables", 0),
    ("ar_availability", "Receivables availability", 0), ("inventory_total", "Inventory, total", 0),
    ("inventory_ineligible", "Less: ineligible inventory", 1), ("inventory_eligible", "Eligible inventory", 0),
    ("inventory_availability_before_sublimit", "Inventory availability before the sublimit", 1),
    ("inventory_availability", "Inventory availability", 0), ("reserves", "Less: reserves", 0),
    ("borrowing_base", "Borrowing base", 0), ("commitment", "Commitment", 0),
    ("borrowing_limit", "Lesser of borrowing base and commitment", 0), ("outstanding", "Less: outstanding", 0),
    ("letters_of_credit", "Less: letters of credit", 0), ("availability", "Availability", 0),
    ("over_advance", "Over-advance", 0),
)


def _borrower_or_404(db: Session, borrower_id: uuid.UUID) -> Borrower:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise HTTPException(404, "Borrower not found.")
    return borrower


def _pretty(name: str) -> str:
    text = name.replace("_", " ").replace(".", " ").strip()
    return NAMED.get(name, text[:1].upper() + text[1:])


class _Labels:
    """Plain-word labels for fact keys. Covenant names are read once per borrower."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._covenants: dict[uuid.UUID, dict[str, str]] = {}

    def covenant_name(self, borrower_id: uuid.UUID, covenant_id: str) -> str:
        if borrower_id not in self._covenants:
            rows = self.db.execute(select(CovenantTest.covenant_id, CovenantTest.covenant_name)
                                   .where(CovenantTest.borrower_id == borrower_id).distinct()).all()
            self._covenants[borrower_id] = dict(rows)
        return self._covenants[borrower_id].get(covenant_id) or _pretty(covenant_id)

    def label(self, fact: Fact) -> str:
        key = fact.key
        if key in SYSTEM_LABELS:
            return SYSTEM_LABELS[key]
        stated = key.startswith(template.STATED_PREFIX)
        line = template.LINE_BY_KEY.get(key[len(template.STATED_PREFIX):] if stated else key)
        if line is not None:
            return f"{line.label}, as stated" if stated else line.label
        parts = key.split(".")
        if parts[0] in ("cov", "cert") and len(parts) >= 3:
            name = self.covenant_name(fact.borrower_id, ".".join(parts[1:-1]))
            suffix = {
                ("cov", "value"): "", ("cov", "threshold"): ", threshold in force", ("cov", "headroom_pct"): ", headroom",
                ("cert", "value"): ", reported on the certificate", ("cert", "threshold"): ", requirement on the certificate",
                ("cert", "in_compliance"): ", compliance as certified",
            }.get((parts[0], parts[-1]), f", {_pretty(parts[-1]).lower()}")
            return name + suffix
        if parts[0] == "metric":
            return _pretty(".".join(parts[1:]))
        return _pretty(key)


def _summary(fact: Fact, labels: _Labels) -> dict[str, Any]:
    return {"id": str(fact.id), "key": fact.key, "label": labels.label(fact), "value": plain(fact.value),
            "unit": fact.unit, "kind": fact.kind, "status": fact.status, "period_end": fact.period_end.isoformat(),
            "months": fact.months, "borrower_id": str(fact.borrower_id), "document_id": plain(fact.document_id),
            "page": fact.page, "calc_run_id": plain(fact.calc_run_id)}


def _facts_by_id(db: Session, ids: list[str], labels: _Labels) -> dict[str, dict[str, Any]]:
    wanted = []
    for raw in ids:
        try:
            wanted.append(uuid.UUID(raw))
        except (ValueError, TypeError):
            continue
    if not wanted:
        return {}
    facts = db.execute(select(Fact).where(Fact.id.in_(wanted))).scalars()
    return {str(f.id): _summary(f, labels) for f in facts}


@router.get("/ui/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """Names and roles, so the workspace can show who acted instead of an identifier."""
    return [row(u, only=("id", "name", "title", "role")) for u in db.execute(select(User).order_by(User.name)).scalars()]


@router.get("/ui/facts")
def facts_in_bulk(ids: str = Query(default="", description="comma-separated fact ids"),
                  db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, dict]:
    """Many facts at once, each with a plain-word label. Unknown ids are left out."""
    wanted = [part for part in ids.split(",") if part.strip()][:400]
    return _facts_by_id(db, wanted, _Labels(db))


# ── where a figure is printed ────────────────────────────────────────────

def _squash(text: str) -> str:
    return re.sub(r"[\s$]", "", text).replace("−", "-").replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"')


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", text.lower()) if len(t) > 2}


def _group(number: Decimal) -> str:
    text = format(number.normalize(), "f") if number == number.to_integral() else format(number, "f").rstrip("0").rstrip(".")
    whole, _, frac = text.partition(".")
    return f"{int(whole):,}" + (f".{frac}" if frac else "")


def _printed_forms(fact: Fact, scale: int) -> list[str]:
    value = abs(fact.value)
    if fact.unit == "ratio":
        two = format(value.quantize(Decimal("0.01")), "f")
        return [f"{two}x", two]
    if fact.unit == "usd":
        if value == 0:
            return []
        shown = _group(value / Decimal(scale))
        return [shown, f"({shown})"]
    if fact.unit == "days":
        return [_group(value)]
    return []


def _find_runs(words: list[Any], printed: str, limit: int = 400) -> list[tuple[int, int]]:
    """Every run of whole words whose text, with spaces removed, equals `printed`."""
    target = _squash(printed)
    if not target:
        return []
    squashed = [_squash(str(w[4])) for w in words]
    found = []
    for i in range(len(words)):
        if not squashed[i] or not target.startswith(squashed[i]):
            continue
        acc = ""
        for j in range(i, min(i + limit, len(words))):
            acc += squashed[j]
            if acc == target:
                found.append((i, j))
                break
            if not target.startswith(acc):
                break
    return found


def _line_boxes(words: list[Any], first: int, last: int) -> list[list[float]]:
    """One box per printed line for a run of words, so a long quote is outlined line by line."""
    boxes: list[list[float]] = []
    for w in words[first:last + 1]:
        x0, y0, x1, y1 = (float(v) for v in w[:4])
        if boxes and abs(boxes[-1][1] - y0) < 3:
            boxes[-1] = [min(boxes[-1][0], x0), min(boxes[-1][1], y0), max(boxes[-1][2], x1), max(boxes[-1][3], y1)]
        else:
            boxes.append([x0, y0, x1, y1])
    return [[round(v, 2) for v in box] for box in boxes]


def _row_label(words: list[Any], index: int) -> str:
    x0, y0, _, y1 = (float(v) for v in words[index][:4])
    mid = (y0 + y1) / 2
    left = [w for w in words if float(w[2]) <= x0 and float(w[1]) - 2 <= mid <= float(w[3]) + 2]
    return " ".join(str(w[4]) for w in sorted(left, key=lambda w: float(w[0])))


def _statement_hint(key: str) -> tuple[str, ...]:
    base = key[len(template.STATED_PREFIX):] if key.startswith(template.STATED_PREFIX) else key
    return {"is": ("income", "operations"), "bs": ("balance sheet",), "cf": ("cash flows",),
            "sup": ("supplemental",)}.get(base.split(".", 1)[0], ())


def _candidate_documents(db: Session, fact: Fact) -> list[tuple[Document, bool]]:
    """Documents where this fact should be printed, each with whether the figure sits in the
    comparative (prior-period) column."""
    prefix = fact.key.split(".", 1)[0]
    if prefix == "cert":
        types: tuple[str, ...] = ("compliance_certificate",)
    elif prefix in ("is", "bs", "cf", "sup", "stated"):
        types = STATEMENT_TYPES
    else:
        return []
    docs = list(db.execute(select(Document).where(
        Document.borrower_id == fact.borrower_id, Document.doc_type.in_(types),
        Document.status == "indexed").order_by(Document.received_date.desc().nulls_last())).scalars())
    exact = [(d, False) for d in docs if d.period_end == fact.period_end]
    if fact.months == 12:
        exact.sort(key=lambda pair: pair[0].doc_type != "annual_statements")
    try:
        later = fact.period_end.replace(year=fact.period_end.year + 1)
    except ValueError:
        later = fact.period_end + timedelta(days=365)
    comparative = [(d, True) for d in docs if d.period_end == later] if prefix != "cert" else []
    return exact + comparative


def locate_fact(db: Session, fact: Fact, labels: _Labels) -> dict[str, Any] | None:
    """Find where a figure is printed when the fact carries no page of its own (facts loaded from
    the synthetic book). Code searches the period's document for the figure as printed and picks
    the occurrence whose row label matches best. The result is marked `located`, never `cited`."""
    borrower = db.get(Borrower, fact.borrower_id)
    scale = int((borrower.profile or {}).get("statement_scale") or 1) if fact.key.split(".", 1)[0] != "cert" else 1
    forms = _printed_forms(fact, scale)
    if not forms:
        return None
    want = _tokens(labels.label(fact).split(",")[0] if fact.key.startswith("cert.") else labels.label(fact))
    hints = _statement_hint(fact.key)
    for doc, comparative in _candidate_documents(db, fact):
        best: tuple[float, dict[str, Any]] | None = None
        pages = db.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id)
                           .order_by(DocumentPage.page_number)).scalars()
        for page in pages:
            if not page.has_text:
                continue
            head = page.text[:400].lower()
            on_statement = 1.0 if any(h in head for h in hints) else 0.0
            for printed in forms:
                for first, last in _find_runs(page.words, printed, limit=4):
                    row_text = _row_label(page.words, first)
                    got = _tokens(row_text)
                    similarity = len(want & got) / len(want) if want else 0.0
                    x0 = float(page.words[first][0])
                    score = similarity * 10 + on_statement * 3 + (x0 if comparative else -x0) / 10000
                    if best is None or score > best[0]:
                        best = (score, {
                            "document_id": str(doc.id), "document_title": doc.title, "doc_type": doc.doc_type,
                            "page": page.page_number, "page_count": doc.page_count, "width": page.width,
                            "height": page.height, "boxes": _line_boxes(page.words, first, last), "quote": printed,
                            "label_text": row_text or None, "method": "located", "comparative_column": comparative,
                            "scale": scale, "label_match": round(similarity, 2)})
        if best is not None:
            return best[1]
    return None


def _cited_page(db: Session, fact: Fact) -> dict[str, Any] | None:
    if fact.document_id is None or fact.page is None:
        return None
    doc = db.get(Document, fact.document_id)
    page = db.execute(select(DocumentPage).where(
        DocumentPage.document_id == fact.document_id, DocumentPage.page_number == fact.page)).scalar_one_or_none()
    if doc is None:
        return None
    return {"document_id": str(doc.id), "document_title": doc.title, "doc_type": doc.doc_type, "page": fact.page,
            "page_count": doc.page_count, "width": page.width if page else None, "height": page.height if page else None,
            "boxes": [fact.bbox] if fact.bbox else [], "quote": fact.quote, "label_text": fact.label_text,
            "method": "cited", "comparative_column": False, "scale": fact.scale_as_reported, "label_match": None}


def _document_by_reference(db: Session, borrower_id: uuid.UUID, reference: str) -> Document | None:
    """Terms cite documents by their identifier in the system of record, or by row id."""
    try:
        doc = db.get(Document, uuid.UUID(reference))
        if doc is not None:
            return doc
    except (ValueError, TypeError):
        pass
    for doc in db.execute(select(Document).where(Document.borrower_id == borrower_id)).scalars():
        if (doc.meta or {}).get("external_id") == reference:
            return doc
    return None


def _clause(db: Session, borrower_id: uuid.UUID, citation: dict[str, Any] | None) -> dict[str, Any] | None:
    """A terms citation resolved to a document page, with the quote outlined when it is found."""
    if not citation or not citation.get("document_id"):
        return None
    doc = _document_by_reference(db, borrower_id, str(citation["document_id"]))
    out = {"document_id": str(doc.id) if doc else None, "document_title": doc.title if doc else str(citation["document_id"]),
           "doc_type": doc.doc_type if doc else None, "page": citation.get("page"), "section": citation.get("section"),
           "field": citation.get("field"), "quote": citation.get("quote"), "boxes": [], "page_count": doc.page_count if doc else None,
           "method": "cited"}
    if doc is not None and citation.get("page") and citation.get("quote"):
        page = db.execute(select(DocumentPage).where(
            DocumentPage.document_id == doc.id, DocumentPage.page_number == citation["page"])).scalar_one_or_none()
        if page is not None:
            out["width"], out["height"] = page.width, page.height
            runs = _find_runs(page.words, str(citation["quote"]))
            if runs:
                out["boxes"] = _line_boxes(page.words, *runs[0])
    return out


# ── calculations in plain words ──────────────────────────────────────────

_BASIS = {"ttm": "trailing twelve months", "point": "at the period end", "ytd": "year to date", "quarter": "quarter"}


def _line_name(key: str) -> str:
    line = template.line_info(key)
    return line.label if line else SYSTEM_LABELS.get(key, _pretty(key))


def expression_text(node: Any, top: bool = True) -> str:
    """A stored expression tree as a formula a person can read."""
    if not isinstance(node, dict):
        return str(node)
    op = node.get("op")
    if op == "line":
        return _line_name(str(node.get("key", "")))
    if op == "named":
        return NAMED.get(str(node.get("name")), _pretty(str(node.get("name", ""))))
    if op in ("const", "value"):
        return str(node.get("value"))
    if op == "div":
        return f"{expression_text(node.get('num'), False)} ÷ {expression_text(node.get('den'), False)}"
    args = [expression_text(arg, False) for arg in node.get("args", [])]
    joined = {"add": " + ", "sub": " − ", "mul": " × "}.get(str(op))
    if joined and args:
        text = joined.join(args)
        return text if top else f"({text})"
    return f"{_pretty(str(op))}({', '.join(args)})" if args else _pretty(str(op))


def calculation_out(db: Session, calc: CalcRun, labels: _Labels) -> dict[str, Any]:
    """A calculation with its inputs joined to their facts and its steps named in plain words."""
    inputs = [i for i in (calc.inputs or []) if isinstance(i, dict)]
    facts = _facts_by_id(db, [str(i["fact_id"]) for i in inputs if i.get("fact_id")], labels)
    trace = calc.trace if isinstance(calc.trace, dict) else {}
    by_key: dict[str, list[dict[str, Any]]] = {}
    shaped_inputs = []
    for i in inputs:
        key = str(i.get("key") or i.get("name") or "")
        item = {"key": key, "name": _line_name(key) if key else "Input", "sign": i.get("sign", 1),
                "value": plain(i.get("value")), "fact_id": i.get("fact_id"), "period_end": i.get("period_end"),
                "months": i.get("months")}
        shaped_inputs.append(item)
        by_key.setdefault(key, []).append(item)
    steps = []
    raw_steps = [s for s in trace.get("steps", []) if isinstance(s, dict)]
    for index, step in enumerate(raw_steps):
        op, label = str(step.get("op")), step.get("label")
        key, _, basis = str(label or "").partition(":")
        if op == "line":
            name, components = _line_name(key), by_key.get(key, [])
        elif op in ("named", "addback"):
            name, components = NAMED.get(str(label), _pretty(str(label or op))), []
        else:
            name, components = {"add": "Sum", "sub": "Difference", "div": "Ratio", "mul": "Product",
                                "min": "Lesser of", "max": "Greater of"}.get(op, _pretty(op)), []
        steps.append({"n": index + 1, "op": op, "name": name, "key": key if op == "line" else None,
                      "basis": _BASIS.get(basis, basis or None), "value": plain(step.get("value")),
                      "period_end": step.get("period_end"), "inputs": components,
                      "unit": "ratio" if op == "div" else "usd", "final": index == len(raw_steps) - 1})
    version = db.get(TermsVersion, calc.terms_version_id) if calc.terms_version_id else None
    return {
        "id": str(calc.id), "formula_key": calc.formula_key, "formula_version": calc.formula_version,
        "engine_version": calc.engine_version, "period_end": calc.period_end.isoformat(), "error": calc.error,
        "created_at": plain(calc.created_at), "created_by_type": calc.created_by_type, "created_by_id": calc.created_by_id,
        "terms_version": {"id": str(version.id), "version": version.version, "status": version.status,
                          "effective_from": version.effective_from.isoformat()} if version else None,
        "expression": expression_text(trace["expression"]) if trace.get("expression") else None,
        "inputs": shaped_inputs, "steps": steps, "addbacks": plain(trace.get("addbacks") or []),
        "outputs": plain(calc.outputs if isinstance(calc.outputs, dict) else {}), "facts": facts,
    }


@router.get("/ui/calculations/{calc_id}")
def get_calculation(calc_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    calc = db.get(CalcRun, calc_id)
    if calc is None:
        raise HTTPException(404, "Calculation not found.")
    labels = _Labels(db)
    out = calculation_out(db, calc, labels)
    produced = db.execute(select(Fact).where(Fact.calc_run_id == calc.id).order_by(Fact.key)).scalars()
    out["produced"] = [_summary(f, labels) for f in produced]
    return out


def _threshold_citation(version: TermsVersion | None, covenant_id: str) -> dict[str, Any] | None:
    if version is None:
        return None
    for covenant in (version.terms or {}).get("covenants", []):
        if covenant.get("id") == covenant_id:
            citations = covenant.get("citations") or []
            for citation in citations:
                if str(citation.get("field", "")).startswith("test"):
                    return citation
            return citations[0] if citations else None
    return None


@router.get("/ui/facts/{fact_id}/source")
def fact_source(fact_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """Everything behind one figure: the page it is printed on (cited by the fact, or located by
    code when the fact carries no page), the calculation with its inputs, the clause that sets a
    threshold, the system record or the person, and the fact's history in both directions."""
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(404, "Fact not found.")
    labels = _Labels(db)
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    out: dict[str, Any] = {
        "fact": {**_summary(fact, labels), "quote": fact.quote, "label_text": fact.label_text,
                 "scale_as_reported": fact.scale_as_reported, "connector": fact.connector, "record_ref": fact.record_ref,
                 "as_of": plain(fact.as_of), "entered_by": users.get(fact.entered_by), "reason": fact.reason,
                 "note": fact.note, "confirmed_by": users.get(fact.confirmed_by), "confirmed_at": plain(fact.confirmed_at),
                 "created_at": plain(fact.created_at), "agent_run_id": plain(fact.agent_run_id),
                 "facility_id": plain(fact.facility_id)},
        "page": None, "calculation": None, "clause": None,
    }
    borrower = db.get(Borrower, fact.borrower_id)
    out["borrower"] = {"id": str(borrower.id), "name": borrower.name, "code": borrower.code}
    out["page"] = _cited_page(db, fact)
    if out["page"] is None and fact.kind in ("seeded", "manual"):
        out["page"] = locate_fact(db, fact, labels)
    if fact.calc_run_id:
        calc = db.get(CalcRun, fact.calc_run_id)
        if calc is not None:
            out["calculation"] = calculation_out(db, calc, labels)
            parts = fact.key.split(".")
            if parts[0] == "cov" and parts[-1] == "threshold" and calc.terms_version_id:
                version = db.get(TermsVersion, calc.terms_version_id)
                out["clause"] = _clause(db, fact.borrower_id, _threshold_citation(version, ".".join(parts[1:-1])))
    earlier, cursor, seen = [], fact, {fact.id}
    while cursor.supersedes_fact_id and cursor.supersedes_fact_id not in seen:
        cursor = db.get(Fact, cursor.supersedes_fact_id)
        if cursor is None:
            break
        seen.add(cursor.id)
        earlier.append(cursor)
    later, cursor = [], fact
    while True:
        nxt = db.execute(select(Fact).where(Fact.supersedes_fact_id == cursor.id)
                         .order_by(Fact.created_at).limit(1)).scalar_one_or_none()
        if nxt is None or nxt.id in seen:
            break
        seen.add(nxt.id)
        later.append(nxt)
        cursor = nxt

    def entry(f: Fact, relation: str) -> dict[str, Any]:
        return {**row(f, only=("id", "value", "unit", "kind", "status", "created_at", "reason")), "relation": relation,
                "entered_by": users.get(f.entered_by)}

    out["history"] = ([entry(f, "later") for f in reversed(later)] + [entry(fact, "this")]
                      + [entry(f, "earlier") for f in earlier])
    return out


# ── portfolio ────────────────────────────────────────────────────────────

def _latest_system_facts(db: Session, borrower_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, dict[str, Fact]]:
    """The newest fact per borrower for each system-of-record balance."""
    query = select(Fact).where(Fact.key.in_(tuple(SYSTEM_LABELS)), Fact.status.in_(("verified", "confirmed")))
    if borrower_ids is not None:
        query = query.where(Fact.borrower_id.in_(borrower_ids))
    latest: dict[uuid.UUID, dict[str, Fact]] = {}
    for fact in db.execute(query.order_by(Fact.period_end, Fact.created_at)).scalars():
        latest.setdefault(fact.borrower_id, {})[fact.key] = fact
    return latest


def _latest_cycles(db: Session) -> dict[uuid.UUID, Cycle]:
    latest: dict[uuid.UUID, Cycle] = {}
    for cycle in db.execute(select(Cycle).order_by(Cycle.period_end)).scalars():
        latest[cycle.borrower_id] = cycle
    return latest


def _counted(rows: Any, name: str) -> list[dict[str, Any]]:
    return [{name: key, "count": count} for key, count in sorted(rows, key=lambda pair: (-pair[1], str(pair[0])))]


@router.get("/ui/portfolio")
def portfolio_summary(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """Counts and totals for the command centre and the portfolio page. Totals are summed here
    with decimals; the per-borrower balances carry the ids of the facts they come from."""
    as_of = clock.today(db)
    labels = _Labels(db)
    borrowers = list(db.execute(select(Borrower)).scalars())
    cycles = _latest_cycles(db)
    stage_counts: dict[str, int] = {}
    for cycle in cycles.values():
        stage_counts[cycle.stage] = stage_counts.get(cycle.stage, 0) + 1
    outcome_counts: dict[str, int] = {}
    tests = 0
    for test in db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))).scalars():
        cycle = cycles.get(test.borrower_id)
        if cycle is not None and test.period_end == cycle.period_end:
            outcome_counts[test.outcome] = outcome_counts.get(test.outcome, 0) + 1
            tests += 1
    system = _latest_system_facts(db)
    commitment_total = db.execute(select(func.coalesce(func.sum(Facility.commitment), 0))).scalar() or Decimal(0)
    loans = db.execute(select(func.count()).select_from(Facility)).scalar() or 0
    totals = {key: Decimal(0) for key in ("sys.revolver_outstanding", "sys.term_loan_outstanding")}
    exposure = {}
    for borrower in borrowers:
        facts = system.get(borrower.id, {})
        for key in totals:
            if key in facts:
                totals[key] += facts[key].value
        exposure[str(borrower.id)] = {key.split(".", 1)[1]: _summary(fact, labels) for key, fact in facts.items()}
    week = as_of + timedelta(days=7)
    obligations = list(db.execute(select(ReportingObligation)).scalars())
    periods = sorted({c.period_end for c in cycles.values()})
    return {
        "as_of": as_of.isoformat(),
        "borrowers": len(borrowers),
        "loans": loans,
        "period_end": periods[-1].isoformat() if periods else None,
        "exposure": {"commitment": plain(commitment_total), "revolver_outstanding": plain(totals["sys.revolver_outstanding"]),
                     "term_loan_outstanding": plain(totals["sys.term_loan_outstanding"]),
                     "outstanding": plain(totals["sys.revolver_outstanding"] + totals["sys.term_loan_outstanding"])},
        "borrower_exposure": exposure,
        "cycles": {"open": sum(1 for c in cycles.values() if c.status == "open"),
                   "by_stage": _counted(stage_counts.items(), "stage")},
        "covenants": {"tests": tests, "by_outcome": _counted(outcome_counts.items(), "outcome")},
        "work_items": {
            "open": db.execute(select(func.count()).select_from(WorkItem).where(WorkItem.status == "open")).scalar() or 0,
            "by_type": _counted(db.execute(select(WorkItem.item_type, func.count()).where(WorkItem.status == "open")
                                           .group_by(WorkItem.item_type)).all(), "item_type"),
            "by_severity": _counted(db.execute(select(WorkItem.severity, func.count()).where(WorkItem.status == "open")
                                               .group_by(WorkItem.severity)).all(), "severity"),
        },
        "signals": {
            "open": db.execute(select(func.count()).select_from(Signal).where(Signal.status == "open")).scalar() or 0,
            "by_severity": _counted(db.execute(select(Signal.severity, func.count()).where(Signal.status == "open")
                                               .group_by(Signal.severity)).all(), "severity"),
        },
        "obligations": {
            "overdue": sum(1 for o in obligations if o.status == "overdue"),
            "due_within_7_days": sum(1 for o in obligations if o.status == "due" and as_of <= o.due_date <= week),
            "received_in_last_30_days": sum(1 for o in obligations if o.status == "received" and o.received_date
                                            and as_of - timedelta(days=30) <= o.received_date <= as_of),
        },
    }


# ── borrower views ───────────────────────────────────────────────────────

@router.get("/ui/borrowers/{borrower_id}/overview")
def borrower_overview(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """What the borrower header and summary need in one call: balances as facts, the current
    cycle with its stages, and counts of what is open."""
    borrower = _borrower_or_404(db, borrower_id)
    labels = _Labels(db)
    facts = _latest_system_facts(db, [borrower.id]).get(borrower.id, {})
    cycle = _latest_cycles(db).get(borrower.id)
    cycle_out = None
    if cycle is not None:
        from app.domain import workflow

        open_by_stage = dict(db.execute(select(WorkItem.stage, func.count()).where(
            WorkItem.cycle_id == cycle.id, WorkItem.status == "open").group_by(WorkItem.stage)).all())
        cycle_out = {**row(cycle), "stages": [{**row(s), "open_work_items": open_by_stage.get(s.stage, 0)}
                                              for s in workflow.stages(db, cycle)]}
    metrics = {}
    if cycle is not None:
        for fact in db.execute(select(Fact).where(
                Fact.borrower_id == borrower.id, Fact.key.like("metric.%"), Fact.period_end == cycle.period_end,
                Fact.status.in_(("verified", "confirmed"))).order_by(Fact.created_at)).scalars():
            metrics[fact.key.split(".", 1)[1]] = _summary(fact, labels)
    return {
        "exposure": {key.split(".", 1)[1]: _summary(fact, labels) for key, fact in facts.items()},
        "cycle": cycle_out,
        "metrics": metrics,
        "open_work_items": db.execute(select(func.count()).select_from(WorkItem).where(
            WorkItem.borrower_id == borrower.id, WorkItem.status == "open")).scalar() or 0,
        "open_signals": db.execute(select(func.count()).select_from(Signal).where(
            Signal.borrower_id == borrower.id, Signal.status == "open")).scalar() or 0,
        "documents": db.execute(select(func.count()).select_from(Document).where(
            Document.borrower_id == borrower.id)).scalar() or 0,
    }


@router.get("/ui/borrowers/{borrower_id}/covenants")
def borrower_covenants(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """Covenant tests with the ids of every fact shown beside them (value, threshold, headroom,
    certificate), the clause that sets each threshold, and the work item raised on each test."""
    borrower = _borrower_or_404(db, borrower_id)
    labels = _Labels(db)
    tests = list(db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower.id, CovenantTest.superseded.is_(False))
        .order_by(CovenantTest.period_end.desc(), CovenantTest.covenant_name)).scalars())
    companions: dict[tuple[str, date], Fact] = {}
    for fact in db.execute(select(Fact).where(
            Fact.borrower_id == borrower.id, Fact.key.like("cov.%"), Fact.status.in_(("verified", "confirmed")))
            .order_by(Fact.created_at)).scalars():
        companions[(fact.key, fact.period_end)] = fact
    items_by_test: dict[str, WorkItem] = {}
    for item in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)
                           .order_by(WorkItem.created_at)).scalars():
        reference = (item.evidence or {}).get("covenant_test_id")
        if reference:
            items_by_test[str(reference)] = item
    versions = {v.id: v for v in db.execute(select(TermsVersion).join(Facility, Facility.id == TermsVersion.facility_id)
                                            .where(Facility.borrower_id == borrower.id)).scalars()}
    facilities = {f.id: f for f in db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars()}
    fact_ids: set[str] = set()
    out = []
    for test in tests:
        threshold = companions.get((f"cov.{test.covenant_id}.threshold", test.period_end))
        headroom = companions.get((f"cov.{test.covenant_id}.headroom_pct", test.period_end))
        version = versions.get(test.terms_version_id)
        citation = _threshold_citation(version, test.covenant_id)
        item = items_by_test.get(str(test.id))
        facility = facilities.get(test.facility_id)
        entry = {
            **row(test),
            "threshold_fact_id": str(threshold.id) if threshold else None,
            "headroom_fact_id": str(headroom.id) if headroom else None,
            "loan_name": facility.name if facility else None,
            "terms_version": {"id": str(version.id), "version": version.version, "status": version.status} if version else None,
            "citation": {"section": citation.get("section"), "page": citation.get("page"), "quote": citation.get("quote"),
                         "document_id": (lambda d: str(d.id) if d else None)(
                             _document_by_reference(db, borrower.id, str(citation.get("document_id"))))} if citation else None,
            "work_item": row(item, only=("id", "item_type", "status", "severity", "decision", "title")) if item else None,
        }
        for key in ("value_fact_id", "reported_fact_id", "threshold_fact_id", "headroom_fact_id"):
            if entry.get(key):
                fact_ids.add(str(entry[key]))
        out.append(entry)
    return {"tests": out, "facts": _facts_by_id(db, sorted(fact_ids), labels)}


@router.get("/ui/borrowers/{borrower_id}/terms")
def borrower_terms(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """Each loan with every version of its terms, newest first, and which one governs today."""
    borrower = _borrower_or_404(db, borrower_id)
    as_of = clock.today(db)
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    documents = {(d.meta or {}).get("external_id"): d for d in db.execute(
        select(Document).where(Document.borrower_id == borrower.id)).scalars()}
    by_id = {str(d.id): d for d in documents.values()}

    def resolve(reference: Any) -> dict[str, Any]:
        doc = documents.get(reference) or by_id.get(str(reference))
        return {"reference": str(reference), "id": str(doc.id) if doc else None, "title": doc.title if doc else str(reference),
                "doc_type": doc.doc_type if doc else None}

    def citation_out(citation: dict[str, Any] | None) -> dict[str, Any] | None:
        if not citation:
            return None
        doc = documents.get(citation.get("document_id")) or by_id.get(str(citation.get("document_id")))
        return {"section": citation.get("section"), "page": citation.get("page"), "quote": citation.get("quote"),
                "field": citation.get("field"), "document_id": str(doc.id) if doc else None,
                "document_title": doc.title if doc else None}

    out = []
    facilities = db.execute(select(Facility).where(Facility.borrower_id == borrower.id).order_by(Facility.code)).scalars()
    for facility in facilities:
        versions = list(db.execute(select(TermsVersion).where(TermsVersion.facility_id == facility.id)
                                   .order_by(TermsVersion.version.desc())).scalars())
        shaped = []
        for v in versions:
            terms = v.terms or {}
            in_force = (v.status == "approved" and v.effective_from <= as_of
                        and (v.effective_to is None or v.effective_to >= as_of))
            shaped.append({
                **row(v, exclude=("terms",)), "in_force": in_force, "approved_by_name": users.get(v.approved_by),
                "source_documents": [resolve(r) for r in v.source_document_ids or []],
                "covenants": [{
                    "id": c.get("id"), "name": c.get("name"), "archetype": c.get("archetype"),
                    "operator": (c.get("test") or {}).get("operator"), "threshold": plain((c.get("test") or {}).get("threshold")),
                    "unit": (c.get("test") or {}).get("unit"), "steps": plain((c.get("test") or {}).get("steps") or []),
                    "measurement": c.get("measurement"),
                    "citations": [citation_out(x) for x in c.get("citations") or []],
                } for c in terms.get("covenants", [])],
                "addbacks": plain(((terms.get("definitions") or {}).get("ebitda") or {}).get("addbacks") or []),
                "reporting_requirements": [{
                    "id": r.get("id"), "document_type": r.get("document_type"), "frequency": r.get("frequency"),
                    "due_days": r.get("due_days"), "quality": r.get("quality"), "citation": citation_out(r.get("citation")),
                } for r in terms.get("reporting_requirements", [])],
                "has_borrowing_base": terms.get("borrowing_base") is not None,
            })
        out.append({**row(facility), "terms_versions": shaped})
    return out


@router.get("/ui/borrowers/{borrower_id}/borrowing-base")
def borrower_borrowing_base(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                            _: User = Depends(current_user)) -> list[dict]:
    """Borrowing base reviews, newest first: each line as recalculated beside the certificate."""
    borrower = _borrower_or_404(db, borrower_id)
    labels = _Labels(db)
    facilities = {f.id: f for f in db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars()}
    reviews = list(db.execute(select(BorrowingBaseReview).where(BorrowingBaseReview.borrower_id == borrower.id)
                              .order_by(BorrowingBaseReview.period_end.desc(), BorrowingBaseReview.created_at.desc())).scalars())
    documents = {(d.meta or {}).get("external_id"): d for d in db.execute(select(Document).where(
        Document.borrower_id == borrower.id, Document.doc_type == "borrowing_base_certificate")).scalars()}
    items: dict[str, WorkItem] = {}
    for item in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalars():
        reference = (item.evidence or {}).get("borrowing_base_review_id")
        if reference:
            items[str(reference)] = item
    out = []
    for review in reviews:
        computed, certificate = review.computed or {}, review.certificate or {}
        differences = {d.get("line"): d for d in review.differences or [] if isinstance(d, dict)}
        lines = []
        for key, label, depth in BB_LINES:
            if key not in computed and key not in certificate:
                continue
            diff = differences.get(key, {})
            lines.append({"line": key, "label": label, "depth": depth, "computed": plain(computed.get(key)),
                          "certificate": plain(certificate.get(key)), "difference": plain(diff.get("difference")),
                          "status": diff.get("status")})
        calc = db.get(CalcRun, review.calc_run_id) if review.calc_run_id else None
        source = ((calc.inputs or {}).get("source") or {}) if calc is not None and isinstance(calc.inputs, dict) else {}
        doc = documents.get(source.get("document"))
        if doc is None:
            doc = next((d for d in documents.values() if d.period_end == review.period_end), None)
        availability = db.execute(select(Fact).where(
            Fact.borrower_id == borrower.id, Fact.key == "bb.availability", Fact.period_end == review.period_end,
            Fact.calc_run_id == review.calc_run_id)).scalars().first() if review.calc_run_id else None
        item = items.get(str(review.id))
        facility = facilities.get(review.facility_id)
        out.append({
            **row(review, exclude=("computed", "certificate", "differences")), "lines": lines,
            "loan_name": facility.name if facility else None,
            "certificate_document": {"id": str(doc.id), "title": doc.title, "page_count": doc.page_count} if doc else None,
            "availability_fact": _summary(availability, labels) if availability else None,
            "work_item": row(item, only=("id", "item_type", "status", "severity", "decision", "title")) if item else None,
            "customers": plain((calc.trace or {}).get("customers") or []) if calc is not None and isinstance(calc.trace, dict) else [],
        })
    return out


# routine events that would bury the decisions; shown only when asked for
_QUIET_ACTIONS = ("obligation.received", "obligation.overdue", "cycle.stage_changed")


@router.get("/ui/borrowers/{borrower_id}/timeline")
def borrower_timeline(borrower_id: uuid.UUID, limit: int = 300, include_routine: bool = False,
                      db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """Ledger events about this borrower, newest first. The ledger stores an entity per event, so
    the borrower's cycles, documents, loans, tests, signals, items and reviews are gathered first."""
    borrower = _borrower_or_404(db, borrower_id)
    ids: set[str] = {str(borrower.id)}
    for model in (Cycle, Document, Facility, WorkItem, Signal, CovenantTest, BorrowingBaseReview, ReviewSheet, Action,
                  ReportingObligation):
        ids.update(str(i) for (i,) in db.execute(select(model.id).where(model.borrower_id == borrower.id)).all())
    facility_ids = [f for (f,) in db.execute(select(Facility.id).where(Facility.borrower_id == borrower.id)).all()]
    if facility_ids:
        ids.update(str(i) for (i,) in db.execute(
            select(TermsVersion.id).where(TermsVersion.facility_id.in_(facility_ids))).all())
    query = select(LedgerEvent).where(LedgerEvent.entity_id.in_(ids)).order_by(LedgerEvent.seq.desc()).limit(min(limit, 1000))
    if not include_routine:
        query = query.where(LedgerEvent.action.notin_(_QUIET_ACTIONS))
    users = {str(u.id): u.name for u in db.execute(select(User)).scalars()}
    titles = {str(d.id): d.title for d in db.execute(select(Document).where(Document.borrower_id == borrower.id)).scalars()}
    return [{**row(e, exclude=("prev_hash",)), "actor_name": users.get(e.actor_id),
             "document_title": titles.get(e.entity_id) if e.entity_type == "document" else None}
            for e in db.execute(query).scalars()]

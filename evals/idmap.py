"""Describes the ids a model is shown, by value, so a recorded answer that cites them can be replayed.

Fact, document and calculation ids are random per run. At record time the harness saves a descriptor of
every id in the request beside the response; at replay `RecordedClient` finds the id with the same
descriptor in the replay's request and rewrites the recorded id to it (see `app.agents.llm.remap_ids`).
A descriptor is built from what the id stands for, never from the id: a fact by its key, period, months,
value, kind and source (document hash and page); a document by its hash; a calculation by its formula,
period, terms version and result. This module is eval-side: the product never imports it.
"""
from typing import Any

from sqlalchemy.orm import Session


class Resolver:
    """Callable `uuid string -> descriptor | None`, reading the database session of the run in progress."""

    def __init__(self) -> None:
        self.db: Session | None = None

    def __call__(self, ref: str) -> dict[str, Any] | None:
        if self.db is None:
            return None
        return describe(self.db, ref)


RESOLVER = Resolver()


def _number(value: Any) -> str:
    from decimal import Decimal, InvalidOperation

    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    return format(d.normalize(), "f")


def _is_number(value: Any) -> bool:
    from decimal import Decimal, InvalidOperation

    if not isinstance(value, str):
        return False
    try:
        Decimal(value)
    except InvalidOperation:
        return False
    return True


def describe(db: Session, ref: str) -> dict[str, Any] | None:
    import uuid

    from app.domain.documents import Document
    from app.domain.facts import CalcRun, Fact
    from app.domain.terms import TermsVersion

    try:
        key = uuid.UUID(ref)
    except ValueError:
        return None
    fact = db.get(Fact, key)
    if fact is not None:
        document = db.get(Document, fact.document_id) if fact.document_id else None
        return {"type": "fact", "key": fact.key, "period_end": fact.period_end.isoformat(), "months": fact.months,
                "value": _number(fact.value), "kind": fact.kind,
                "document": document.sha256 if document is not None else None, "page": fact.page}
    document = db.get(Document, key)
    if document is not None:
        return {"type": "document", "sha256": document.sha256}
    calc = db.get(CalcRun, key)
    if calc is not None:
        terms = db.get(TermsVersion, calc.terms_version_id) if calc.terms_version_id else None
        outputs = {k: v if isinstance(v, bool) else _number(v) for k, v in (calc.outputs or {}).items()
                   if isinstance(v, bool | int | float) or _is_number(v)}
        return {"type": "calc", "formula_key": calc.formula_key, "period_end": calc.period_end.isoformat(),
                "terms_version": terms.version if terms is not None else None, "outputs": outputs}
    return None

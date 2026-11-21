"""Plain-word labels for fact keys and the summary shape every figure travels in. Shared by the read views
(`routes_ui`) and Squad's read models, so no one imports a private name of a route module."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serialize import plain
from app.calc import template
from app.domain.facts import Fact
from app.domain.monitoring import CovenantTest

SYSTEM_LABELS = {
    "sys.revolver_outstanding": "Line of credit, outstanding",
    "sys.commitment": "Line of credit, commitment",
    "sys.term_loan_outstanding": "Term loan, outstanding",
    "sys.past_due_days": "Days past due",
    "bb.availability": "Availability",
}
NAMED = {"ebitda": "EBITDA", "total_debt": "Total debt", "senior_debt": "Senior debt", "tnw": "Tangible net worth"}
def _pretty(name: str) -> str:
    text = name.replace("_", " ").replace(".", " ").strip()
    return NAMED.get(name, text[:1].upper() + text[1:])


class FactLabels:
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
        line = template.ALL_LINE_BY_KEY.get(key[len(template.STATED_PREFIX):] if stated else key)
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


def fact_summary(fact: Fact, labels: FactLabels) -> dict[str, Any]:
    return {"id": str(fact.id), "key": fact.key, "label": labels.label(fact), "value": plain(fact.value),
            "unit": fact.unit, "kind": fact.kind, "status": fact.status, "period_end": fact.period_end.isoformat(),
            "months": fact.months, "borrower_id": str(fact.borrower_id), "document_id": plain(fact.document_id),
            "page": fact.page, "calc_run_id": plain(fact.calc_run_id)}

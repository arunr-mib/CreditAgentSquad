"""Connect decisions on work items to the services that carry them out. Imported once at startup."""
from app.domain import terms_service, workflow

workflow.DECISION_HOOKS["terms.approval_needed"] = terms_service.on_decision

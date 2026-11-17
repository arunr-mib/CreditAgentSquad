"""Connect decisions on work items to the services that carry them out. Imported once at startup."""
from app.domain import review_service, stages, terms_service, workflow  # noqa: F401  (stages registers handlers)

workflow.DECISION_HOOKS["terms.approval_needed"] = terms_service.on_decision
workflow.DECISION_HOOKS["review.commentary_approval"] = review_service.on_decision

"""The work trail under a case ("How I got here"): which specialist did what, and which checks it passed."""
from typing import Any

from sqlalchemy.orm import Session

from app.domain.agents import AgentRun
from app.domain.facts import CalcRun
from app.domain.monitoring import CovenantTest, WorkItem

ROLE_LINES = {
    "intake": "files incoming documents",
    "spreading": "reads figures from documents",
    "covenant": "tests covenants against the loan terms",
    "terms": "reads the loan agreement",
    "code": "calculation, no AI",
}


def _who(agent_name: str) -> str:
    return f"{agent_name.capitalize()} agent"


def case_trail(db: Session, item: WorkItem) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    run = db.get(AgentRun, item.agent_run_id) if item.agent_run_id else None
    if run is not None:
        steps.append({"n": len(steps) + 1, "who": _who(run.agent_name),
                      "role_line": ROLE_LINES.get(run.agent_name, "works for Squad"),
                      "text": f"Ran {run.task.replace('_', ' ')}.", "check": run.status, "run_id": str(run.id)})
        checks += [{"layer": n.get("layer"), "check": n.get("check"), "action": n.get("action"), "detail": n.get("detail")}
                   for n in (run.guardrail_notes or []) if isinstance(n, dict)]
    checks += [{"layer": n.get("layer"), "check": n.get("check"), "action": n.get("action"), "detail": n.get("detail")}
               for n in (item.guardrail_notes or []) if isinstance(n, dict)]
    calc = None
    calc_id = (item.evidence or {}).get("calc_run_id")
    if not calc_id and (item.evidence or {}).get("covenant_test_id"):
        test = db.get(CovenantTest, item.evidence["covenant_test_id"])
        calc_id = str(test.calc_run_id) if test and test.calc_run_id else None
    calc_row = db.get(CalcRun, calc_id) if calc_id else None
    if calc_row is not None:
        calc = {"id": str(calc_row.id), "formula_key": calc_row.formula_key, "inputs": calc_row.inputs,
                "outputs": calc_row.outputs}
        steps.append({"n": len(steps) + 1, "who": "Code", "role_line": ROLE_LINES["code"],
                      "text": f"Applied {calc_row.formula_key} to {len(calc_row.inputs)} stored figures.",
                      "check": "exact arithmetic", "run_id": None})
    return {"work_item_id": str(item.id), "steps": steps, "calculation": calc, "checks": checks}

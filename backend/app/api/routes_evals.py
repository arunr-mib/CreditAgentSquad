"""Evaluation results for the governance screen: the latest scorecard and the history of runs.

Results are written by `python -m evals.run`. The scorecard is read from the `eval_runs` table,
or, when no run has been stored in this database, from `evals/results/latest.json`. A stand-in
run is always labelled as such: it proves the pipeline and the grader, not model performance.
"""
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.db import get_db
from app.domain.governance import EvalRun
from app.domain.org import User

router = APIRouter(tags=["evals"])
RESULTS_FILE = Path(__file__).resolve().parents[3] / "evals" / "results" / "latest.json"
STANDIN_NOTICE = ("Stand-in run: a perfect reader built from the synthetic book's ground truth answered in place "
                  "of the model. It proves the pipeline, the workflow and the grader. It is not model performance.")


def _envelope(results: dict[str, Any], *, source: str, run: EvalRun | None = None) -> dict[str, Any]:
    meta = results.get("meta", {})
    mode = run.mode if run is not None else meta.get("mode")
    standin = mode == "standin"
    return {
        "source": source,  # database | file
        "id": str(run.id) if run is not None else None,
        "created_at": run.created_at.isoformat() if run is not None and run.created_at else meta.get("generated_at"),
        "suite": run.suite if run is not None else meta.get("suite"),
        "mode": mode,
        "standin": standin,
        "notice": STANDIN_NOTICE if standin else None,
        "commit": (run.commit if run is not None else meta.get("commit")) or None,
        "gate_passed": run.gate_passed if run is not None else (results.get("gate") or {}).get("passed"),
        "results": results,
    }


def _summary(run: EvalRun) -> dict[str, Any]:
    out = _envelope(run.results or {}, source="database", run=run)
    results = out.pop("results")
    out["metrics"] = results.get("metrics")  # unmeasured metrics stay null
    out["failure_counts"] = results.get("failure_counts")
    out["borrowers"] = (results.get("meta") or {}).get("borrowers")
    return out


@router.get("/evals/latest")
def latest_eval(suite: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """The most recent scorecard, in full."""
    query = select(EvalRun).order_by(EvalRun.created_at.desc(), EvalRun.id.desc()).limit(1)
    if suite:
        query = query.where(EvalRun.suite == suite)
    run = db.execute(query).scalar_one_or_none()
    if run is not None:
        return _envelope(run.results or {}, source="database", run=run)
    if RESULTS_FILE.exists():
        results = json.loads(RESULTS_FILE.read_text())
        if not suite or (results.get("meta") or {}).get("suite") == suite:
            return _envelope(results, source="file")
    raise HTTPException(404, "No evaluation has been run yet. Run: uv run python -m evals.run --mode standin")


@router.get("/evals/runs")
def list_eval_runs(limit: int = 20, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    """Recent runs, newest first, with headline numbers only."""
    runs = db.execute(select(EvalRun).order_by(EvalRun.created_at.desc(), EvalRun.id.desc())
                      .limit(max(1, min(limit, 100)))).scalars()
    return [_summary(run) for run in runs]


@router.get("/evals/runs/{run_id}")
def get_eval_run(run_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    try:
        key = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(404, "Evaluation run not found.") from exc
    run = db.get(EvalRun, key)
    if run is None:
        raise HTTPException(404, "Evaluation run not found.")
    return _envelope(run.results or {}, source="database", run=run)

"""Runway for a cash-flow-positive client has no figure: no stored metric.rml, a plain-words result."""
import json
from decimal import Decimal

import pytest
from app.agents import copilot_tools as ct
from app.agents.tools import Scope, ToolContext
from app.domain import metrics_service
from app.domain.agents import AgentRun
from app.domain.facts import Fact
from sqlalchemy import select

pytestmark = pytest.mark.slow


def _desk(db, borrower):
    run = AgentRun(agent_name="copilot", agent_version="test", model="none", task="tools")
    db.add(run)
    db.flush()
    return ToolContext(db=db, scope=Scope(borrower_id=borrower.id), run=run, state={}), ct.copilot_gateway()


def test_ferrogate_runway_is_not_stored_and_the_copilot_says_why(innovation_cycle):
    db, borrower, cycle = innovation_cycle("ferrogate-cloud", through="covenant_testing")
    assert metrics_service.store_metric(db, borrower, "rml", cycle.period_end) is None
    ctx, gateway = _desk(db, borrower)
    out = gateway.call(ctx, "metrics", {"names": ["rml"], "period_end": cycle.period_end.isoformat()},
                       allowed=ct.TOOL_NAMES)
    assert not out.refused
    entry = out.content["metrics"][0]
    assert entry["fact"] is None and "not meaningful" in entry["note"].lower()
    json.dumps(out.content, default=str)
    stored = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == "metric.rml")).scalars().all()
    assert not [f for f in stored if f.value is not None and Decimal(f.value) < 0]
    assert stored == []


def test_a_burning_client_still_gets_its_runway_figure(innovation_cycle):
    db, borrower, cycle = innovation_cycle("datamarrow", through="covenant_testing")
    fact = metrics_service.store_metric(db, borrower, "rml", cycle.period_end)
    assert fact is not None and fact.value > 0


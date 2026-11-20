"""The innovation book, seeded through the real services, against the generator's own expected values.

The generator computes those with separate arithmetic, so agreement here means two independent implementations reach
the same covenant tests, signals, exceptions and funding events. A disagreement is a finding to investigate, never a
value to patch. The legacy 21-borrower book keeps its own test (`test_seed_book.py`)."""
import json
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.core import ledger
from app.core.config import get_settings
from app.domain import hooks  # noqa: F401
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.funding import FundingEvent
from app.domain.monitoring import CovenantTest, Cycle, Signal, WorkItem
from app.domain.terms import TermsVersion
from app.seed_book import BOOKS, SYNTHETIC_ROOT, _day, halted, seed_book
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.slow
KEPT = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")
# raised by a reconciliation that the calculation layer does not do (Phase 3), so seeding cannot raise it
PENDING = {"cash.statement_mismatch"}


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("innovation") / "out"
    subprocess.run([sys.executable, "-m", "synthetic.books.innovation.generate", "--out", str(out), "--oracle",
                    str(out.parent / "oracle.csv")], cwd=REPO, check=True, capture_output=True)
    return out


@pytest.fixture(scope="module")
def seeded(engine, book, tmp_path_factory):
    import os

    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    report = seed_book(db, root=book, current="seeded")
    truths = {json.loads(p.read_text())["borrower"]["id"]: json.loads(p.read_text())
              for p in sorted((book / "truth").glob("*.json"))}
    yield db, truths, report
    db.close()
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


def borrower(db, code) -> Borrower:
    return db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()


def test_the_default_book_is_innovation_and_the_legacy_book_is_still_selectable():
    assert SYNTHETIC_ROOT == BOOKS["innovation"] and BOOKS["legacy"].name == "out"
    assert BOOKS["innovation"].parts[-3:] == ("books", "innovation", "out")


def test_twenty_borrowers_load_with_their_templates_and_clean_terms(seeded):
    db, truths, report = seeded
    assert report.borrowers == len(truths) == 20 and report.provenance_warnings == {}
    assert all(v.warnings == [] for v in db.execute(select(TermsVersion)).scalars())
    templates = {c: borrower(db, c).template_id for c in truths}
    assert sorted(set(templates.values())) == ["ci-1", "vc-1"]
    assert sorted(c for c, t in templates.items() if t == "ci-1") == sorted(KEPT)


def test_covenant_tests_match_the_generator_exactly(seeded):
    db, truths, _ = seeded
    problems, checked = [], 0
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        ours = {(t.period_end, t.covenant_id): t for t in db.execute(select(CovenantTest).where(
            CovenantTest.borrower_id == b.id, CovenantTest.superseded.is_(False))).scalars()}
        expected_keys = set()
        for e in truth["expected"]["covenant_tests"]:
            key = (_day(e["period_end"]), e["covenant_id"])
            if halted(truth) and key[0] == current:
                assert e["outcome"] == "cannot_test" and key not in ours  # the live cycle stops before testing
                continue
            expected_keys.add(key)
            checked += 1
            t = ours.get(key)
            if t is None:
                problems.append(f"missing {code} {key}")
                continue
            value = None if e.get("value") is None else D(e["value"])
            if (t.value, t.passed, t.outcome) != (value, e.get("pass"), e["outcome"]) or t.threshold != D(e["threshold"]):
                problems.append(f"{code} {key}: ours {t.value} {t.threshold} {t.passed} {t.outcome}; "
                                f"book {e.get('value')} {e['threshold']} {e.get('pass')} {e['outcome']}")
        problems.extend(f"unexpected {code} {k}" for k in sorted(set(ours) - expected_keys))
    assert problems == [] and checked > 720


def test_current_period_signals_match_the_generator(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        rows = list(db.execute(select(Signal).where(Signal.borrower_id == b.id, Signal.period_end == current)).scalars())
        ours = sorted((s.rule_id, s.severity, s.basis.get("covenant_id") or "") for s in rows)
        book_signals = sorted((s["rule"], s["severity"], (s.get("detail") or {}).get("covenant_id") or "")
                              for s in truth["expected"]["signals"] if _day(s["period_end"]) == current)
        if ours != book_signals:
            problems.append(f"{code}: ours {ours}; book {book_signals}")
    assert problems == []


def test_the_plan_for_revenue_below_plan_comes_from_the_approved_terms(seeded):
    db, _, _ = seeded
    corvane = borrower(db, "corvane-analytics")
    fired = db.execute(select(Signal).where(Signal.borrower_id == corvane.id, Signal.rule_id == "revenue_below_plan",
                                            Signal.period_end == _day("2026-10-31"))).scalars().all()
    assert len(fired) == 1 and fired[0].severity == "medium"
    clean = borrower(db, "mosswell-robotics")
    assert not db.execute(select(Signal).where(Signal.borrower_id == clean.id, Signal.rule_id == "revenue_below_plan",
                                               Signal.period_end == _day("2026-10-31"))).first()


def test_each_scenario_raises_exactly_its_exceptions_and_clean_clients_raise_none(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        ours = sorted({w.item_type for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == b.id)).scalars()})
        expected = sorted({x["type"] for x in truth["expected"]["exceptions"]} - PENDING)
        if ours != expected:
            problems.append(f"{code} ({truth['scenario']['code']}): ours {ours}; book {expected}")
    assert problems == []
    assert sorted(c for c, t in truths.items() if t["scenario"]["code"] == "clean") == [
        "harrowgate-precision", "mosswell-robotics", "orbitline-systems", "pellucid-sensors", "quillon-ai",
        "tessaract-labs", "veridia-payments"]  # harrowgate is the kept clean C&I borrower


def test_funding_events_are_seeded_and_only_nimbusfields_has_slipped(seeded):
    db, truths, report = seeded
    rows = {}
    for event in db.execute(select(FundingEvent)).scalars():
        rows.setdefault(db.get(Borrower, event.borrower_id).code, []).append(event)
    assert sorted(rows) == ["dataflake", "halcyon-grid", "kelvra-bio", "nimbusfield-security"] and report.funding_events == 4
    assert {c: [e.status for e in es] for c, es in rows.items()} == {
        "dataflake": ["signed"], "halcyon-grid": ["expected"], "kelvra-bio": ["expected"],
        "nimbusfield-security": ["slipped"]}
    assert rows["dataflake"][0].amount == D("8000000") and rows["dataflake"][0].expected_close == _day("2026-12-12")
    assert all(e.evidence_document_ids for es in rows.values() for e in es)
    nimbus = borrower(db, "nimbusfield-security")
    assert len(db.execute(select(WorkItem).where(WorkItem.borrower_id == nimbus.id,
                                                 WorkItem.item_type == "funding_slipped")).scalars().all()) == 1


def test_the_stray_mrr_export_is_held_unclassified_and_the_workbook_is_not_filed(seeded):
    db, _, report = seeded
    stripple = borrower(db, "stripple-tech")
    docs = list(db.execute(select(Document).where(Document.borrower_id == stripple.id)).scalars())
    held = [d for d in docs if d.meta.get("external_id") == "stripple-tech.mrr-export"]
    assert len(held) == 1 and held[0].doc_type is None and held[0].period_end is None
    assert not [d for d in docs if d.file_name.endswith(".xlsx")] and report.skipped_documents == 1


def test_venture_clients_run_monthly_cycles_and_the_kept_four_stay_quarterly(seeded):
    db, truths, _ = seeded
    for code in truths:
        types = {c.cycle_type for c in db.execute(select(Cycle).where(Cycle.borrower_id == borrower(db, code).id)).scalars()}
        assert types == ({"quarterly"} if code in KEPT else {"monthly"}), code
    dataflake = borrower(db, "dataflake")
    ends = sorted(c.period_end for c in db.execute(select(Cycle).where(Cycle.borrower_id == dataflake.id)).scalars())
    assert (ends[0], ends[-1], len(ends)) == (_day("2025-08-31"), _day("2026-10-31"), 15)


def test_the_ledger_chain_verifies_after_seeding_the_whole_book(seeded):
    db, _, _ = seeded
    ok, count, problem = ledger.verify_chain(db)
    assert ok and problem is None and count > 5000

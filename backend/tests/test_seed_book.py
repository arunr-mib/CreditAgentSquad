"""The whole synthetic book, seeded through the real services, against the generator's own
expected values. The generator computes those with separate arithmetic, so agreement here means
two independent implementations reach the same covenant tests, borrowing bases, signals and
exceptions. A disagreement is a finding to investigate, never a value to patch."""
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
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, Signal, WorkItem
from app.domain.terms import TermsVersion
from app.seed_book import BB_LINES, _day, halted, seed_book
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
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


def test_every_citation_in_the_book_is_on_its_page(seeded):
    db, truths, report = seeded
    assert report.borrowers == len(truths) == 21 and report.documents == 360
    assert report.provenance_warnings == {}
    assert all(v.warnings == [] for v in db.execute(select(TermsVersion)).scalars())


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
                # the live cycle stops before covenant testing; no test is run for this period
                assert e["outcome"] == "cannot_test" and key not in ours
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
    assert problems == [] and checked > 350


def test_borrowing_base_reviews_match_the_generator_exactly(seeded):
    db, truths, _ = seeded
    problems, checked = [], 0
    for code, truth in truths.items():
        b = borrower(db, code)
        ours = {r.period_end: r for r in db.execute(select(BorrowingBaseReview).where(
            BorrowingBaseReview.borrower_id == b.id)).scalars()}
        for e in truth["expected"]["borrowing_base"]:
            checked += 1
            r = ours.get(_day(e["period_end"]))
            if r is None:
                problems.append(f"missing {code} {e['period_end']}")
                continue
            for name, value in e["calculated"].items():
                line = BB_LINES.get(name, name)
                if r.computed.get(line) is None or D(r.computed[line]) != D(value):
                    problems.append(f"{code} {e['period_end']} {line}: ours {r.computed.get(line)}; book {value}")
            if (r.outcome == "over_advance") != e["over_advance"]:
                problems.append(f"{code} {e['period_end']} over-advance: ours {r.outcome}; book {e['over_advance']}")
            if (r.outcome in ("mismatch",)) == e["certificate_matches"] and r.outcome != "over_advance":
                problems.append(f"{code} {e['period_end']} certificate: ours {r.outcome}; book matches={e['certificate_matches']}")
    assert problems == [] and checked == 24


def test_signals_match_the_generator(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        # lists, not sets: a duplicate signal is a difference
        rows = list(db.execute(select(Signal).where(Signal.borrower_id == b.id, Signal.period_end == current)).scalars())
        ours = sorted((s.rule_id, s.severity, s.basis.get("covenant_id") or "") for s in rows)
        book_signals = sorted((s["rule"], s["severity"], (s.get("detail") or {}).get("covenant_id") or "")
                              for s in truth["expected"]["signals"] if _day(s["period_end"]) == current)
        for s in rows:
            linked = s.basis.get("metric_fact_ids") or s.basis.get("system_fact_ids") or s.rule_id == "reporting_late"
            headroom = s.basis.get("metric") == "headroom_pct"
            if not linked and not headroom:
                problems.append(f"{code}: {s.rule_id} has no stored fact behind its figures")
        if ours != book_signals:
            problems.append(f"{code}: ours {ours}; book {book_signals}")
    assert problems == []


def test_each_scenario_raises_exactly_its_exceptions_and_clean_borrowers_raise_none(seeded):
    db, truths, _ = seeded
    problems = []
    for code, truth in truths.items():
        b = borrower(db, code)
        ours = sorted({w.item_type for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == b.id)).scalars()})
        expected = sorted({x["type"] for x in truth["expected"]["exceptions"]})
        if ours != expected:
            problems.append(f"{code} ({truth['scenario']['code']}): ours {ours}; book {expected}")
    assert problems == []
    clean = [c for c, t in truths.items() if t["scenario"]["code"] == "clean"]
    assert len(clean) == 8


def test_history_is_closed_and_the_current_cycle_rests_where_a_person_is_needed(seeded):
    db, truths, _ = seeded
    for code, truth in truths.items():
        b = borrower(db, code)
        current = _day(truth["current_period"])
        cycles = list(db.execute(select(Cycle).where(Cycle.borrower_id == b.id).order_by(Cycle.period_end)).scalars())
        assert all(c.status == "closed" and c.origin == "seeded" for c in cycles if c.period_end < current)
        now = next(c for c in cycles if c.period_end == current)
        blocking = db.execute(select(WorkItem).where(
            WorkItem.cycle_id == now.id, WorkItem.status == "open", WorkItem.blocks_stage.is_(True))).scalars().all()
        if blocking:
            assert now.stage in {w.stage for w in blocking}, (code, now.stage)
        else:
            assert now.stage == "review_prep", (code, now.stage)


def test_the_ledger_chain_verifies_after_seeding_the_whole_book(seeded):
    db, _, _ = seeded
    ok, count, problem = ledger.verify_chain(db)
    assert ok and problem is None and count > 10000

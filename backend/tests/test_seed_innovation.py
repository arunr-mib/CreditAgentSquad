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
from app.core.ledger import LedgerEvent
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
# Raised by the live cycle's cash reconciliation (Task 6, app/domain/cash_reconciliation.py), which seeding
# does not run: the seeder stores the certificate's figures without reading bank statements. The live path is
# pinned by the stand-in suite (evals/tests/test_standin_suite.py), which asserts Brackmere raises it.
SEED_DOES_NOT_RAISE = {"cash.statement_mismatch"}


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
    meridew = borrower(db, "meridew-analytics")
    fired = db.execute(select(Signal).where(Signal.borrower_id == meridew.id, Signal.rule_id == "revenue_below_plan",
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
        expected = sorted({x["type"] for x in truth["expected"]["exceptions"]} - SEED_DOES_NOT_RAISE)
        if ours != expected:
            problems.append(f"{code} ({truth['scenario']['code']}): ours {ours}; book {expected}")
    assert problems == []
    assert sorted(c for c, t in truths.items() if t["scenario"]["code"] == "clean") == [
        "harrowgate-precision", "mosswell-robotics", "orbitline-systems", "pellucid-sensors", "tarnavi-ai",
        "vantrell-labs", "veridia-payments"]  # harrowgate is the kept clean C&I borrower


def test_funding_events_are_seeded_and_only_nimbusfields_has_slipped(seeded):
    db, truths, report = seeded
    rows = {}
    for event in db.execute(select(FundingEvent)).scalars():
        rows.setdefault(db.get(Borrower, event.borrower_id).code, []).append(event)
    assert sorted(rows) == ["datamarrow", "kelvra-bio", "nimbusfield-security", "tavernel-grid"] and report.funding_events == 4
    assert {c: [e.status for e in es] for c, es in rows.items()} == {
        "datamarrow": ["signed"], "tavernel-grid": ["expected"], "kelvra-bio": ["expected"],
        "nimbusfield-security": ["slipped"]}
    assert rows["datamarrow"][0].amount == D("8000000") and rows["datamarrow"][0].expected_close == _day("2026-12-12")
    assert all(e.evidence_document_ids for es in rows.values() for e in es)
    nimbus = borrower(db, "nimbusfield-security")
    assert len(db.execute(select(WorkItem).where(WorkItem.borrower_id == nimbus.id,
                                                 WorkItem.item_type == "funding_slipped")).scalars().all()) == 1


def test_the_stray_mrr_export_is_held_unclassified_and_the_workbook_is_what_arrives(seeded):
    db, _, report = seeded
    cindrel = borrower(db, "cindrel-tech")
    docs = list(db.execute(select(Document).where(Document.borrower_id == cindrel.id)).scalars())
    held = [d for d in docs if d.meta.get("external_id") == "cindrel-tech.mrr-export"]
    assert len(held) == 1 and held[0].doc_type is None and held[0].period_end is None
    assert held[0].file_name == "mrr_export.xlsx" and held[0].meta["format"] == "xlsx"
    assert not [d for d in docs if d.file_name.endswith(".pdf") and d.file_name.startswith("mrr_export")]
    assert report.skipped_documents == 1  # the PDF print of the workbook


def test_venture_clients_run_monthly_cycles_and_the_kept_four_stay_quarterly(seeded):
    db, truths, _ = seeded
    for code in truths:
        types = {c.cycle_type for c in db.execute(select(Cycle).where(Cycle.borrower_id == borrower(db, code).id)).scalars()}
        assert types == ({"quarterly"} if code in KEPT else {"monthly"}), code
    datamarrow = borrower(db, "datamarrow")
    ends = sorted(c.period_end for c in db.execute(select(Cycle).where(Cycle.borrower_id == datamarrow.id)).scalars())
    assert (ends[0], ends[-1], len(ends)) == (_day("2025-08-31"), _day("2026-10-31"), 15)


def test_the_ledger_chain_verifies_after_seeding_the_whole_book(seeded):
    db, _, _ = seeded
    ok, count, problem = ledger.verify_chain(db)
    assert ok and problem is None and count > 5000


def test_stand_in_items_are_marked_as_seeded_and_never_block(seeded):
    db, _, _ = seeded
    cindrel = borrower(db, "cindrel-tech")
    items = list(db.execute(select(WorkItem).where(
        WorkItem.borrower_id == cindrel.id,
        WorkItem.item_type.in_(("intake.unclassified", "spread.value_unverified")))).scalars())
    assert sorted(i.item_type for i in items) == ["intake.unclassified", "spread.value_unverified"]
    for item in items:
        assert item.evidence["seeded"] is True and item.blocks_stage is False
        raised = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.raised",
                                                      LedgerEvent.entity_id == str(item.id))).scalar_one()
        assert (raised.actor_type, raised.actor_id) == ("system", "seed")
    # why the held file is held is said on the case, in words: the answer key's own summary names years, and a
    # stand-in's text is shown unsourced
    from app.squad.words import figure_free

    held = next(i for i in items if i.item_type == "intake.unclassified")
    assert held.evidence["note"] == ("The file names no company, and its rows are dated a year earlier than this package. "
                                    "Open it to see the rows. Stand-in for the item the Intake Agent raises on a live run.")
    assert figure_free(held.evidence["note"])
    other = next(i for i in items if i.item_type == "spread.value_unverified")
    assert other.evidence["note"] == "Stand-in for the item the Spreading Agent raises on a live run."


def test_funding_evidence_belongs_to_the_borrower_and_each_event_is_recorded_once(seeded):
    db, _, report = seeded
    events = list(db.execute(select(FundingEvent)).scalars())
    assert events and report.funding_evidence_skipped == 0
    for event in events:
        for doc_id in event.evidence_document_ids:
            assert db.get(Document, doc_id).borrower_id == event.borrower_id
        recorded = db.execute(select(LedgerEvent).where(LedgerEvent.action == "funding_event.recorded",
                                                        LedgerEvent.entity_id == str(event.id))).scalars().all()
        assert len(recorded) == 1


def test_ferrogate_terms_are_v1_superseded_then_v2_approved(seeded):
    db, _, _ = seeded
    ferro = borrower(db, "ferrogate-cloud")
    from app.domain.credit import Facility
    rows = list(db.execute(select(TermsVersion).join(Facility, Facility.id == TermsVersion.facility_id).where(
        Facility.borrower_id == ferro.id).order_by(TermsVersion.version)).scalars())
    assert [(r.version, r.status) for r in rows] == [(1, "superseded"), (2, "approved")]
    assert rows[0].effective_to == _day("2026-05-30") and rows[1].effective_from == _day("2026-05-31")



def test_no_ledger_summary_work_item_title_or_question_carries_an_unsourced_figure(seeded):
    """Final review I3: every event of the seeded book reads without a figure (the guardrail's own detector), and so
    does every work item's title and question, which home, Approvals and the thread show without a source."""
    from app.guardrails.narrative import check_narrative
    from app.squad.words import describe_event

    db, _, _ = seeded
    bad = []
    for e in db.execute(select(LedgerEvent).order_by(LedgerEvent.seq)).scalars():
        # a file's own name ("afs-2024.pdf") is an identifier, not a figure
        summary = describe_event(e.action, {k: v for k, v in (e.payload or {}).items() if k != "file_name"})
        if check_narrative(summary, {}):
            bad.append((e.action, summary))
    for w in db.execute(select(WorkItem)).scalars():
        for text in (w.title, w.question):
            if check_narrative(text or "", {}):
                bad.append((w.item_type, text))
    assert bad == []


def test_a_calculation_names_the_cash_it_leaves_out_so_a_certificate_gap_can_be_seen(seeded):
    """Datamarrow's certificate counts 1.5 million of pledged cash as unrestricted. The covenant uses cash in
    operating accounts only, so the calculation's source must show the pledged line beside it, as a stored fact."""
    from app.api.routes_ui import _Labels, calculation_out
    from app.domain.facts import CalcRun

    db, _, _ = seeded
    datamarrow = borrower(db, "datamarrow")
    test = db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == datamarrow.id, CovenantTest.covenant_id == "min_unrestricted_cash",
        CovenantTest.period_end == _day("2026-10-31"))).scalar_one()
    out = calculation_out(db, db.get(CalcRun, test.calc_run_id), _Labels(db))
    assert [i["key"] for i in out["inputs"]] == ["bs.cash_unrestricted"]
    [left] = out["left_out"]
    assert (left["key"], left["part_of"]) == ("bs.cash_restricted", "Total cash")
    fact = out["facts"][left["fact_id"]]
    assert D(fact["value"]) == D("1500000") and fact["label"] == "Cash pledged or restricted"
    # a calculation that touches no part of a total leaves nothing out
    plan = db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == datamarrow.id, CovenantTest.covenant_id == "revenue_vs_plan",
        CovenantTest.period_end == _day("2026-10-31"))).scalar_one()
    assert calculation_out(db, db.get(CalcRun, plan.calc_run_id), _Labels(db))["left_out"] == []

"""Run the live monitoring cycle over the synthetic book and grade what comes out.

    uv run python -m evals.run --mode standin [--only id ...] [--decide]

Modes:
  standin   (default) a perfect reader built from the book's ground truth stands in for the
            model. Proves the pipeline, the workflow and the grader. NOT model performance.
  recorded  replays saved model responses from the recordings directory. No model is called.
  live      calls the model (billable). Refuses to start unless every oracle row for the
            borrowers in scope is signed by the owner, or --allow-unsigned is given.
  record    as live, and saves each response for later replay.

Each borrower is loaded in live mode inside a database transaction that is rolled back, so the
database is left as it was found. Only the EvalRun row (the scorecard) is committed.
"""
import argparse
import json
import os
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from evals.book import BOOKS, DEFAULT_BOOK, REPO, Book, Borrower, load_book, oracle_for, unsigned_oracle_rows

# The evaluation measures the automatic path: what the product does with a reading when no
# person looks at it. A deployment defaults to "assisted", where a person confirms every reading.
os.environ.setdefault("EXTRACTION_AUTONOMY", "automatic")

RESULTS_DIR = REPO / "evals" / "results"
RECORDINGS_DIR = REPO / "evals" / "recordings"
MODES = ("standin", "recorded", "live", "record")
BILLABLE = ("live", "record")
SUITE = "monitoring-cycle"
STANDIN_LABEL = ("STAND-IN: a perfect reader built from the book's ground truth answered in place of the model. "
                 "This proves the pipeline, the workflow and the grader. It is not model performance.")
COST_WARNING = (
    "WARNING: this mode calls the model and is billable. A full pass makes up to five model calls per "
    "borrower (intake, spreading, certificate, borrowing base, review), each carrying a PDF. Estimate, "
    "labelled as an estimate and not measured: about 20 US dollars per pass of 21 borrowers (range 10 "
    "to 35), and 2 to 5 dollars for a three-borrower trial. Run it only with the owner's go-ahead.")

# A scripted, sensible decision for each kind of exception, so a cycle can continue past the
# point where a person is needed. Items that are not listed are left open on purpose: the cycle
# is waiting for the borrower (a new document) or for a person to key or confirm figures, and no
# scripted decision can supply those. `terms.unapproved_amendment` is left open too: the sensible
# decision (`terms_update_requested`) starts the Terms Agent, which the stand-in does not answer,
# so that cycle rests on the item its scenario expects.
DECISIONS: dict[str, tuple[str, str]] = {
    "covenant.reported_mismatch": ("escalate_to_committee", "The calculated covenant fails while the certificate claims compliance; escalated for a decision on the bank's response."),
    "covenant.breach": ("escalate_to_committee", "The covenant fails its test for the period; escalated for a decision on the bank's response."),
    "bb.over_advance": ("paydown_required", "Borrowings exceed the recalculated borrowing base; paydown required under the agreement."),
    "bb.certificate_mismatch": ("bank_figures_stand", "The certificate differs from the recalculation; the bank's figures stand and the borrower is told."),
    "cash.statement_mismatch": ("reviewed", "Bank statements and the certificate differ on unrestricted cash; reviewed with the analyst and carried into the review."),
    "intake.unclassified": ("not_needed", "A spreadsheet export is not this period's financial package and carries no figure the bank may rely on; set aside so the cycle continues with the documents that are."),
    "signal.high": ("acknowledged", "High-severity signal acknowledged; carried into the review."),
    "spread.restatement": ("ask_borrower", "The comparative column differs from the confirmed spread; the borrower is asked to confirm the restatement."),
    "review.commentary_approval": ("approve", "Stand-in commentary approved so the scripted cycle can run to its close."),
}

def _is_sheet_item(db, item) -> bool:
    """The unclassified document behind this item is a spreadsheet."""
    from app.domain.documents import Document
    ref = (item.evidence or {}).get("document_id")
    doc = db.get(Document, uuid.UUID(ref)) if ref else None
    return doc is not None and (doc.meta or {}).get("format") in ("xlsx", "csv")


ROLE_ORDER = ("analyst", "portfolio_manager", "credit_officer", "credit_admin")


class RunRefused(Exception):
    """The run was not started (unsigned oracle rows, no recordings, a database already in use)."""


# ---- plain data ---------------------------------------------------------------------------


def plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [plain(v) for v in value]
    return value


# ---- database -------------------------------------------------------------------------------


def default_database_url() -> str:
    from app.core.config import get_settings

    return os.environ.get("EVAL_DATABASE_URL") or get_settings().test_database_url


def ensure_schema(engine: Engine) -> None:
    """Create the product's tables in an empty database. An existing schema is left alone."""
    from app import models
    from app.core.ledger import install_guards

    if inspect(engine).has_table("borrowers"):
        return
    with engine.begin() as conn:
        models.Base.metadata.create_all(conn)
        install_guards(conn)


# ---- one borrower -----------------------------------------------------------------------------


def _decider(db: Session, permission: str, cache: dict[str, Any]):
    """A user whose role grants the permission, created on first use."""
    from app.core.roles import Permission, can
    from app.domain.org import User

    role = next((r for r in ROLE_ORDER if can(r, Permission(permission))), "admin")
    if role not in cache:
        user = User(email=f"eval.{role}@bankofstoic.example", name=f"Evaluation {role.replace('_', ' ')}",
                    role=role, password_hash="not-a-login")
        db.add(user)
        db.flush()
        cache[role] = user
    return cache[role]


def _snapshot(db: Session, cycle) -> tuple:
    from app.domain import workflow
    from app.domain.monitoring import WorkItem

    open_items = len(db.execute(select(WorkItem.id).where(WorkItem.cycle_id == cycle.id,
                                                           WorkItem.status == "open")).all())
    return (cycle.status, cycle.stage, tuple((s.stage, s.status) for s in workflow.stages(db, cycle)), open_items)


def _settle(db: Session, cycle, rounds: int = 12) -> None:
    """Advance the cycle and drain the job queue until nothing moves."""
    from app.domain import workflow

    before = None
    for _ in range(rounds):
        workflow.tick(db)
        workflow.drain(db)
        db.flush()
        now = _snapshot(db, cycle)
        if now == before:
            return
        before = now


class LoadedBorrower:
    """One borrower loaded in live mode inside a transaction that is never committed. The cycle
    can be run any number of times from the same loaded state (each run is rolled back), which
    is what the mutation checks use; closing rolls the load back too."""

    def __init__(self, engine: Engine, book: Book, borrower: Borrower):
        from app.domain import hooks  # noqa: F401  (registers stage handlers and decision hooks)
        from app.domain.credit import Borrower as BorrowerRow
        from app.seed_book import seed_book

        self.book, self.borrower = book, borrower
        started = time.monotonic()
        self.conn = engine.connect()
        self.outer = self.conn.begin()
        try:
            db = Session(bind=self.conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
            if db.execute(select(BorrowerRow.id).where(BorrowerRow.code == borrower.code)).first():
                raise RunRefused(
                    f"{borrower.code} is already loaded in this database; the evaluation needs a database without "
                    "the book in it (the test database, not the demo database)")
            seed_book(db, root=book.root, current="live", only=[borrower.code])
            db.commit()  # into the outer transaction only
            db.close()
        except BaseException:
            self.close()
            raise
        self.seed_seconds = round(time.monotonic() - started, 2)

    def __enter__(self) -> "LoadedBorrower":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self.outer.is_active:
            self.outer.rollback()
        self.conn.close()

    def run(self, llm_factory: Callable[[], Any], *, decide: bool = False) -> dict[str, Any]:
        """Run the current cycle and return a recording of what the product did."""
        from app.domain import stages

        started = time.monotonic()
        borrower = self.borrower
        recording: dict[str, Any] = {"borrower": borrower.code, "scenario": borrower.scenario,
                                     "period_end": borrower.current_period.isoformat(),
                                     "seed_seconds": self.seed_seconds}
        savepoint = self.conn.begin_nested()
        db = Session(bind=self.conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        previous_factory = stages.LLM_FACTORY
        stages.LLM_FACTORY = llm_factory
        try:
            self._cycle(db, recording, decide)
        except Exception as exc:  # noqa: BLE001 - a crash is part of the result, never a silent pass
            recording["error"] = f"{type(exc).__name__}: {exc}"[:1000]
        finally:
            stages.LLM_FACTORY = previous_factory
            db.close()
            if savepoint.is_active:
                savepoint.rollback()
        recording["seconds"] = round(time.monotonic() - started + self.seed_seconds, 2)
        return recording

    def _cycle(self, db: Session, recording: dict[str, Any], decide: bool) -> None:
        from app.core import ledger
        from app.domain import workflow
        from app.domain.agents import AgentRun
        from app.domain.credit import Borrower as BorrowerRow
        from app.domain.documents import Document
        from app.domain.facts import Fact
        from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, Signal, WorkItem
        from app.domain.reviews import Commentary, ReviewSheet
        from app.domain.terms import TermsVersion

        borrower = self.borrower
        row = db.execute(select(BorrowerRow).where(BorrowerRow.code == borrower.code)).scalar_one()
        cycle = db.execute(select(Cycle).where(Cycle.borrower_id == row.id, Cycle.status == "open",
                                               Cycle.period_end == borrower.current_period)).scalar_one()
        seeded_facts = set(db.execute(select(Fact.id).where(Fact.borrower_id == row.id)).scalars())
        # funding_slipped is raised by check_funding_events at seed time; it is the product's own exception and is graded
        seeded_items = set(db.execute(select(WorkItem.id).where(
            WorkItem.borrower_id == row.id, WorkItem.item_type != "funding_slipped")).scalars())

        deciders: dict[str, Any] = {}
        stops: list[dict[str, Any]] = []
        for _ in range(20):
            _settle(db, cycle)
            if cycle.status == "closed":
                break
            waiting = list(db.execute(select(WorkItem).where(
                WorkItem.cycle_id == cycle.id, WorkItem.status == "open").order_by(WorkItem.created_at)).scalars())
            stop = {"stage": cycle.stage,
                    "stage_status": next(s.status for s in workflow.stages(db, cycle) if s.stage == cycle.stage),
                    "open_items": [{"type": w.item_type, "blocks_stage": w.blocks_stage, "stage": w.stage}
                                   for w in waiting], "decisions": []}
            stops.append(stop)
            if not decide:
                break
            moved = False
            for item in waiting:
                scripted = DECISIONS.get(item.item_type)
                if scripted is None or scripted[0] not in item.allowed_decisions:
                    continue
                if item.item_type == "intake.unclassified" and not _is_sheet_item(db, item):
                    continue  # the scripted answer is true of a spreadsheet export only; any other document is left
                user = _decider(db, item.required_permission, deciders)
                entry = {"type": item.item_type, "decision": scripted[0], "by_role": user.role, "error": None}
                try:
                    workflow.decide_work_item(db, item, user_id=user.id, user_role=user.role, decision=scripted[0],
                                              reason=scripted[1])
                    moved = True
                except Exception as exc:  # noqa: BLE001 - a refused decision is recorded, not hidden
                    entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
                stop["decisions"].append(entry)
            if not moved:
                break
        db.flush()

        stage_rows = workflow.stages(db, cycle)
        done = [s.stage for s in stage_rows if s.status in ("done", "skipped")]
        recording["cycle"] = {
            "status": cycle.status, "stage": cycle.stage, "last_stage_done": done[-1] if done else None,
            "stages": [{"stage": s.stage, "status": s.status, "detail": plain(s.detail)} for s in stage_rows]}
        recording["stops"] = stops
        recording["decide"] = decide

        documents = {d.id: d for d in db.execute(select(Document).where(Document.borrower_id == row.id)).scalars()}
        versions = {v.id: v for v in db.execute(select(TermsVersion)).scalars()}
        # the documents of the current period: the ones the live cycle had to file itself
        recording["documents"] = [
            {"file_name": d.file_name, "external_id": d.meta.get("external_id"), "doc_type": d.doc_type,
             "doc_type_source": d.doc_type_source, "period_end": plain(d.period_end), "status": d.status,
             "quality": d.meta.get("quality"), "image_only_pages": d.meta.get("image_only_pages", [])}
            for d in documents.values() if d.doc_type_source != "system"]
        covenant_of = {str(t.id): t.covenant_id for t in db.execute(
            select(CovenantTest).where(CovenantTest.cycle_id == cycle.id)).scalars()}
        recording["work_items"] = [
            {"id": str(w.id), "type": w.item_type, "severity": w.severity, "stage": w.stage, "status": w.status,
             "decision": w.decision, "blocks_stage": w.blocks_stage, "title": w.title, "question": w.question,
             "allowed_decisions": w.allowed_decisions, "required_permission": w.required_permission,
             "evidence": plain(w.evidence), "guardrail_notes": plain(w.guardrail_notes),
             "recommendation": plain(w.recommendation), "covenant_id": covenant_of.get(
                 str((w.evidence or {}).get("covenant_test_id"))), "agent_run_id": plain(w.agent_run_id)}
            for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == row.id)
                                .order_by(WorkItem.created_at, WorkItem.id)).scalars() if w.id not in seeded_items]
        recording["covenant_tests"] = [
            {"covenant_id": t.covenant_id, "period_end": plain(t.period_end), "value": plain(t.value),
             "threshold": plain(t.threshold), "operator": t.operator, "unit": t.unit, "passed": t.passed,
             "outcome": t.outcome, "note": t.note, "reported_value": plain(t.reported_value),
             "reported_in_compliance": t.reported_in_compliance, "error": t.error,
             "terms_version": versions[t.terms_version_id].version if t.terms_version_id in versions else None,
             "terms_status": versions[t.terms_version_id].status if t.terms_version_id in versions else None,
             "value_fact_id": plain(t.value_fact_id), "reported_fact_id": plain(t.reported_fact_id)}
            for t in db.execute(select(CovenantTest).where(
                CovenantTest.cycle_id == cycle.id, CovenantTest.superseded.is_(False))
                .order_by(CovenantTest.covenant_id)).scalars()]
        recording["borrowing_base"] = [
            {"period_end": plain(r.period_end), "outcome": r.outcome, "computed": plain(r.computed),
             "certificate": plain(r.certificate), "differences": plain(r.differences),
             "availability": plain(r.availability), "over_advance": plain(r.over_advance)}
            for r in db.execute(select(BorrowingBaseReview).where(BorrowingBaseReview.cycle_id == cycle.id)).scalars()]
        recording["signals"] = [
            {"rule_id": s.rule_id, "severity": s.severity, "basis": plain(s.basis), "explanation": plain(s.explanation)}
            for s in db.execute(select(Signal).where(Signal.cycle_id == cycle.id).order_by(Signal.rule_id)).scalars()]
        facts = [f for f in db.execute(select(Fact).where(Fact.borrower_id == row.id)
                                       .order_by(Fact.seq)).scalars() if f.id not in seeded_facts]
        recording["facts"] = [
            {"id": str(f.id), "key": f.key, "period_end": plain(f.period_end), "months": f.months,
             "value": plain(f.value), "unit": f.unit, "kind": f.kind, "status": f.status, "page": f.page,
             "quote": f.quote, "label": f.label_text, "scale": f.scale_as_reported,
             "document": documents[f.document_id].file_name if f.document_id in documents else None,
             "agent_run_id": plain(f.agent_run_id), "calc_run_id": plain(f.calc_run_id)}
            for f in facts]
        recording["all_fact_ids"] = sorted(str(i) for i in seeded_facts | {f.id for f in facts})
        recording["agent_runs"] = [
            {"id": str(r.id), "agent": r.agent_name, "version": r.agent_version, "task": r.task, "status": r.status,
             "llm_mode": r.llm_mode, "model": r.model, "served_model": r.served_model, "steps": r.steps_count,
             "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "cache_read_tokens": r.cache_read_tokens,
             "guardrail_notes": plain(r.guardrail_notes), "error": r.error}
            for r in db.execute(select(AgentRun).where(AgentRun.borrower_id == row.id)
                                .order_by(AgentRun.created_at, AgentRun.id)).scalars()]
        sheet = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one_or_none()
        recording["review"] = None if sheet is None else {
            "status": sheet.status,
            "commentary": [{"section": c.section, "version": c.version, "body": c.body, "fact_ids": c.fact_ids,
                            "author_type": c.author_type, "status": c.status}
                           for c in db.execute(select(Commentary).where(Commentary.review_sheet_id == sheet.id)
                                               .order_by(Commentary.section, Commentary.version)).scalars()]}
        ok, events, problem = ledger.verify_chain(db)
        recording["ledger"] = {"ok": ok, "events": events, "problem": problem}


def run_borrower(engine: Engine, book: Book, borrower: Borrower, llm_factory: Callable[[], Any], *,
                 decide: bool = False) -> dict[str, Any]:
    """Load one borrower in live mode, run its current cycle, and return a recording of what the
    product did. Everything is rolled back."""
    started = time.monotonic()
    try:
        with LoadedBorrower(engine, book, borrower) as loaded:
            return loaded.run(llm_factory, decide=decide)
    except RunRefused:
        raise
    except Exception as exc:  # noqa: BLE001 - a load that crashes is part of the result
        return {"borrower": borrower.code, "scenario": borrower.scenario,
                "period_end": borrower.current_period.isoformat(), "error": f"{type(exc).__name__}: {exc}"[:1000],
                "seconds": round(time.monotonic() - started, 2)}


# ---- the suite ------------------------------------------------------------------------------------


def make_client(mode: str, book: Book, *, recordings: Path = RECORDINGS_DIR, tamper=None,
                accept_stale: frozenset[str] = frozenset()):
    """The model client for a mode. Stand-in and recorded never call a model."""
    if mode == "standin":
        from evals.standin import StandInReader

        return StandInReader(book, tamper=tamper)
    from app.agents.llm import RecordedClient, client_for
    from app.core.config import Settings

    if mode == "recorded":
        return RecordedClient(recordings, accept_stale)
    return client_for(Settings(squad_llm_mode=mode, squad_recordings_dir=str(recordings)))


def check_may_start(mode: str, codes: list[str], *, oracle: Path, allow_unsigned: bool = False, confirm_billable: bool = False,
                    recordings: Path = RECORDINGS_DIR, out=None) -> None:
    """Refuse a run that should not start. Raises RunRefused with the reason."""
    out = out or sys.stderr
    if mode not in MODES:
        raise RunRefused(f"unknown mode {mode!r}; choose one of {', '.join(MODES)}")
    if mode == "recorded" and not any(Path(recordings).rglob("*.json")):
        raise RunRefused(f"no recorded model responses under {recordings}; record a live run first "
                         "(--mode record, billable) or use --mode standin")
    if mode in BILLABLE:
        print(COST_WARNING, file=out)
        unsigned = unsigned_oracle_rows(codes, oracle)
        if unsigned and not allow_unsigned:
            borrowers = sorted({r["borrower_id"] for r in unsigned})
            raise RunRefused(
                f"{len(unsigned)} oracle row(s) for {len(borrowers)} borrower(s) in scope are not signed by the owner "
                f"(the book's oracle.csv, owner_signed_off). A {mode} run grades a model against the oracle, so it "
                "refuses unsigned rows. Sign them, or pass --allow-unsigned for a deliberate exception.")
        if unsigned:
            print(f"NOTE: --allow-unsigned: {len(unsigned)} oracle row(s) in scope are not signed by the owner; "
                  "results are graded against unsigned expectations.", file=out)
        if not confirm_billable:
            raise RunRefused(f"a {mode} run is billable; pass --confirm-billable once the owner has agreed")


@contextmanager
def scratch_file_store():
    """Documents loaded during a run are kept in a temporary directory, never in the repository."""
    from app.core.config import get_settings

    previous = os.environ.get("FILE_STORE_DIR")
    with tempfile.TemporaryDirectory(prefix="evals-files-") as files:
        os.environ["FILE_STORE_DIR"] = files
        get_settings.cache_clear()
        try:
            yield files
        finally:
            if previous is None:
                os.environ.pop("FILE_STORE_DIR", None)
            else:
                os.environ["FILE_STORE_DIR"] = previous
            get_settings.cache_clear()


class CapturingClient:
    """Keeps what the model answered, in memory, for the evaluation's results only. The product
    stores a refused note as "removed" and never its text (a refused figure must not reach a
    person); the grader needs that text, because a refused honest sentence is the test case."""

    def __init__(self, inner):
        self.inner = inner
        self.mode = getattr(inner, "mode", "unknown")
        self.outputs: list[dict[str, Any]] = []

    def create(self, request):
        response = self.inner.create(request)
        content = getattr(response, "content", None)
        self.outputs.append({"record_key": getattr(request, "record_key", ""),
                             "content": content if isinstance(content, list) else []})
        return response


def run_pass(engine: Engine, book: Book, client, *, decide: bool, progress: Callable[[str], None] | None = None,
             ) -> dict[str, dict[str, Any]]:
    """One pass over every borrower in the book. Returns recordings by borrower code."""
    recordings = {}
    for borrower in book:
        capture = CapturingClient(client)
        recording = run_borrower(engine, book, borrower, lambda capture=capture: capture, decide=decide)
        recording["model_outputs"] = capture.outputs
        recordings[borrower.code] = recording
        if progress:
            cycle = recording.get("cycle", {})
            progress(f"{borrower.code:28s} {borrower.scenario:22s} {cycle.get('stage', 'error'):18s} "
                     f"{recording['seconds']:6.1f}s {recording.get('error', '')}")
    return recordings


def run_suite(*, mode: str = "standin", book_root: Path | str = DEFAULT_BOOK, only: list[str] | None = None,
              decide: bool = True, passes: int = 1, database_url: str | None = None, engine: Engine | None = None,
              allow_unsigned: bool = False, confirm_billable: bool = False, recordings: Path = RECORDINGS_DIR,
              tamper=None, progress: Callable[[str], None] | None = None, keep_recordings: bool = False,
              accept_stale: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Run and grade the suite. Returns the results document (see evals/README.md)."""
    from evals.grade import build_results

    book = load_book(book_root, only)
    codes = [b.code for b in book]
    oracle = oracle_for(book_root)
    check_may_start(mode, codes, allow_unsigned=allow_unsigned, confirm_billable=confirm_billable,
                    recordings=recordings, oracle=oracle)
    own_engine = engine is None
    engine = engine or create_engine(database_url or default_database_url())
    started = time.monotonic()
    try:
        with scratch_file_store():
            ensure_schema(engine)
            client = make_client(mode, book, recordings=recordings, tamper=tamper, accept_stale=accept_stale)
            all_passes = []
            for n in range(1, passes + 1):
                if progress:
                    progress(f"pass {n} of {passes} ({mode})")
                all_passes.append(run_pass(engine, book, client, decide=decide, progress=progress))
    finally:
        if own_engine:
            engine.dispose()
    results = build_results(book, all_passes, mode=mode, decide=decide,
                            seconds=round(time.monotonic() - started, 1),
                            standin_disagreements=getattr(client, "disagreements", []),
                            unsigned_oracle_rows=len(unsigned_oracle_rows(codes, oracle)), scope=only)
    results["meta"]["accepted_stale"] = sorted(accept_stale)
    results["meta"]["prompt_only_verified"] = getattr(client, "prompt_only_verified", 0)
    if keep_recordings:
        results["recordings"] = all_passes
    return results


def write_results(results: dict[str, Any], out_dir: Path = RESULTS_DIR, stem: str = "latest") -> tuple[Path, Path]:
    from evals.scorecard import render_markdown

    out_dir.mkdir(parents=True, exist_ok=True)
    document = {k: v for k, v in results.items() if k != "recordings"}
    json_path, md_path = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(document, indent=1, sort_keys=False) + "\n")
    md_path.write_text(render_markdown(document))
    return json_path, md_path


def save_eval_run(engine: Engine, results: dict[str, Any]) -> str:
    """Commit the scorecard as an EvalRun row, for the governance screen."""
    from app.domain.governance import EvalRun

    document = {k: v for k, v in results.items() if k != "recordings"}
    with Session(engine) as db:
        row = EvalRun(suite=SUITE, mode=results["meta"]["mode"], commit=results["meta"].get("commit") or "",
                      results=document, gate_passed=results["gate"]["passed"])
        db.add(row)
        db.commit()
        return str(row.id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.run", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=MODES, default="standin")
    parser.add_argument("--only", nargs="*", metavar="ID", help="borrower ids to run (default: the whole book)")
    parser.add_argument("--book", default="innovation",
                        help="legacy, innovation (default), both, or the path of a generated book")
    parser.add_argument("--decide", dest="decide", action="store_true", default=True,
                        help="apply a scripted decision where a person is needed, so the cycle continues (default)")
    parser.add_argument("--no-decide", dest="decide", action="store_false",
                        help="stop at the first work item that needs a person")
    parser.add_argument("--passes", type=int, default=1, help="repeat the suite; the gate checks every pass")
    parser.add_argument("--database-url", help="scratch database (default: EVAL_DATABASE_URL, then TEST_DATABASE_URL)")
    parser.add_argument("--recordings", default=str(RECORDINGS_DIR))
    parser.add_argument("--accept-stale", nargs="*", default=[], metavar="AGENT",
                        help="recorded mode: replay stale recordings of these agents (printed in the scorecard)")
    parser.add_argument("--allow-unsigned", action="store_true",
                        help="live/record only: run although oracle rows in scope are not signed by the owner")
    parser.add_argument("--confirm-billable", action="store_true",
                        help="live/record only: the owner has agreed to the cost")
    parser.add_argument("--out", default=str(RESULTS_DIR), help="where latest.json and latest.md are written")
    parser.add_argument("--no-eval-run", action="store_true", help="do not write an EvalRun row")
    parser.add_argument("--save-recordings", metavar="FILE", help="also write the full per-borrower recordings")
    parser.add_argument("--mutations", action="store_true",
                        help="stand-in only: also run the mutation checks (about one minute) and add them to the scorecard")
    args = parser.parse_args(argv)

    names = ["legacy", "innovation"] if args.book == "both" else [args.book]
    plan = []
    try:  # preflight every book before any is built, run or billed
        for name in names:
            root = BOOKS.get(name, Path(name))
            book = load_book(root, args.only or None)
            check_may_start(args.mode, [b.code for b in book], oracle=oracle_for(root),
                            allow_unsigned=args.allow_unsigned, confirm_billable=args.confirm_billable,
                            recordings=Path(args.recordings))
            plan.append((root, _stem(name, root)))
    except (RunRefused, FileNotFoundError, KeyError) as exc:
        print(f"Not started: {exc}", file=sys.stderr)
        return 2
    return max(_run_one(args, root, stem) for root, stem in plan)


def _stem(name: str, root: Path) -> str:
    """Only the default book writes latest.*; any other book writes latest-<book>.*."""
    if root.resolve() == DEFAULT_BOOK.resolve():
        return "latest"
    label = name if name in BOOKS else (root.parent.name if root.name == "out" else root.name)
    return f"latest-{label}"


def _run_one(args, root: Path, stem: str) -> int:
    url = args.database_url or default_database_url()
    engine = create_engine(url)
    try:
        results = run_suite(
            mode=args.mode, book_root=root, only=args.only or None, decide=args.decide, passes=args.passes,
            engine=engine, allow_unsigned=args.allow_unsigned, confirm_billable=args.confirm_billable,
            recordings=Path(args.recordings), progress=lambda line: print(line, flush=True),
            keep_recordings=bool(args.save_recordings), accept_stale=frozenset(args.accept_stale))
    except (RunRefused, FileNotFoundError, KeyError) as exc:
        print(f"Not started: {exc}", file=sys.stderr)
        return 2
    if args.save_recordings:
        Path(args.save_recordings).write_text(json.dumps(results["recordings"], indent=1))
    if args.mutations and args.mode == "standin":
        from evals.mutations import MUTATIONS, run_mutations

        print("mutation checks (the stand-in's answers are tampered with on purpose)", flush=True)
        with scratch_file_store():
            whole = load_book(root)
            here = [m for m in MUTATIONS if whole.get(m.borrower) is not None]  # each book runs its own borrowers' mutations
            results["mutations"] = run_mutations(
                engine, load_book(root, sorted({m.borrower for m in here})), [m.name for m in here],
                progress=lambda line: print(line, flush=True))
        slipped = [m["name"] for m in results["mutations"] if m["caught_by"] in ("SLIPPED", "NOT APPLIED")]
        if slipped:
            results["gate"]["passed"] = False
            results["gate"]["reasons"].append("mutation(s) caught by neither the product nor the grader: " + ", ".join(slipped))
    if not args.no_eval_run:
        results["meta"]["eval_run_id"] = save_eval_run(engine, results)
    json_path, md_path = write_results(results, Path(args.out), stem)
    engine.dispose()

    from evals.scorecard import render_summary

    print(render_summary(results))
    print(f"\nScorecard: {md_path}\nResults:   {json_path}")
    return 0 if results["gate"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

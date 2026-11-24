"""When a run may start. No test here calls a model, and none may."""
import io
import shutil

import pytest
from app.agents.llm import RecordedClient

from evals import run
from evals.book import BOOKS, DEFAULT_BOOK, load_book, oracle_for, parse_printed, unsigned_oracle_rows
from evals.run import COST_WARNING, RunRefused, check_may_start, make_client

BOOK_BUILT = (DEFAULT_BOOK / "truth").exists()


def _oracle(tmp_path, signed: str):
    """A copy of the oracle with every row signed or unsigned, so these guards do not depend on
    whether the owner has signed the real one."""
    lines = oracle_for(DEFAULT_BOOK).read_text().splitlines()
    body = [line.rsplit(",", 1)[0] + "," + signed for line in lines[1:]]
    path = tmp_path / "oracle.csv"
    path.write_text("\n".join([lines[0], *body]) + "\n")
    return path


@pytest.fixture
def unsigned_oracle(tmp_path):
    return _oracle(tmp_path, "no")


def test_live_and_record_refuse_unsigned_oracle_rows_and_print_the_cost_warning(unsigned_oracle):
    for mode in ("live", "record"):
        out = io.StringIO()
        with pytest.raises(RunRefused, match="not signed by the owner"):
            check_may_start(mode, ["datamarrow"], out=out, oracle=unsigned_oracle)
        assert COST_WARNING in out.getvalue()


def test_allow_unsigned_is_a_stated_exception_and_still_needs_the_owners_go_ahead(unsigned_oracle):
    out = io.StringIO()
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["datamarrow"], allow_unsigned=True, out=out, oracle=unsigned_oracle)
    assert "--allow-unsigned" in out.getvalue() and COST_WARNING in out.getvalue()
    # with both flags the run may start; nothing is called here
    check_may_start("live", ["datamarrow"], allow_unsigned=True, confirm_billable=True, out=io.StringIO(),
                    oracle=unsigned_oracle)


def test_unsigned_rows_are_listed_and_a_borrower_without_rows_counts_as_unsigned(unsigned_oracle):
    rows = unsigned_oracle_rows(["datamarrow"], unsigned_oracle)
    assert len(rows) >= 5 and {r["owner_signed_off"] for r in rows} == {"no"}
    assert unsigned_oracle_rows(["not-a-borrower"], unsigned_oracle)[0]["item"] == "no oracle row"


def test_signed_rows_let_a_billable_run_start_only_with_the_owners_go_ahead(tmp_path):
    signed = _oracle(tmp_path, "yes")
    assert unsigned_oracle_rows(["datamarrow"], signed) == []
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["datamarrow"], out=io.StringIO(), oracle=signed)
    check_may_start("live", ["datamarrow"], confirm_billable=True, out=io.StringIO(), oracle=signed)


def test_recorded_mode_refuses_when_there_are_no_recordings(tmp_path):
    with pytest.raises(RunRefused, match="no recorded model responses"):
        check_may_start("recorded", ["kelvra-bio"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK))
    (tmp_path / "intake").mkdir()
    (tmp_path / "intake" / "x.json").write_text("{}")
    check_may_start("recorded", ["kelvra-bio"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK))


RENAMED = {"datamarrow", "tarnavi-ai", "calvere-health", "tavernel-grid", "vantrell-labs", "meridew-analytics",
           "brackmere-medical", "cindrel-tech"}


def test_the_clients_renamed_on_22_nov_were_re_recorded_and_recorded_mode_skips_no_one():
    assert run.NOT_RECORDED == frozenset()  # re-recorded on 23 Nov with the owner's go-ahead
    recorded = {p.name for agent in run.RECORDINGS_DIR.iterdir() if agent.is_dir() for p in agent.iterdir()}
    # Calvere Health's October package is late, so its cycle never calls the model and it has nothing to record
    assert RENAMED - recorded == {"calvere-health"}
    # the old recordings are kept, not replayed
    archive = run.REPO / "evals" / "recordings-archive" / "renamed-2026-11-22"
    assert len(list(archive.rglob("*.json"))) == 65
    assert run.replayable(["kelvra-bio", "datamarrow", "pellham-grain"]) == (["kelvra-bio", "datamarrow", "pellham-grain"], [])


@pytest.fixture
def renamed_not_recorded(monkeypatch):
    """The skip is still there for the next rename: these tests put the eight back on the list."""
    monkeypatch.setattr(run, "NOT_RECORDED", frozenset(RENAMED))


def test_a_client_on_the_list_is_split_from_the_ones_recorded_mode_replays(renamed_not_recorded):
    assert run.NO_RECORDING == "no recording: renamed 22 Nov, re-record needs owner go-ahead"
    assert run.replayable(["kelvra-bio", "datamarrow", "pellham-grain"]) == (["kelvra-bio", "pellham-grain"], ["datamarrow"])


def test_recorded_mode_refuses_a_scope_of_not_recorded_clients_only(tmp_path, renamed_not_recorded):
    (tmp_path / "intake").mkdir()
    (tmp_path / "intake" / "x.json").write_text("{}")
    with pytest.raises(RunRefused, match="nothing to replay: datamarrow, cindrel-tech: no recording: renamed 22 Nov"):
        check_may_start("recorded", ["datamarrow", "cindrel-tech"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK))
    for mode in ("standin", "live", "record"):  # only replay is affected; a record run may re-record them (billable)
        check_may_start(mode, ["datamarrow"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK),
                        confirm_billable=True, out=io.StringIO())


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
@pytest.mark.parametrize("only", [None, ["kelvra-bio", "datamarrow"]])
def test_a_recorded_run_skips_not_recorded_clients_out_loud_and_runs_the_rest(monkeypatch, renamed_not_recorded, only):
    import evals.grade
    from evals.scorecard import _not_replayed

    ran = []
    monkeypatch.setattr(run, "ensure_schema", lambda engine: None)
    monkeypatch.setattr(run, "make_client", lambda *a, **k: object())
    monkeypatch.setattr(run, "run_pass", lambda engine, book, client, **k: ran.append([b.code for b in book]) or {})
    monkeypatch.setattr(evals.grade, "build_results", lambda book, passes, **k: {"meta": {"scope": k["scope"]}})
    lines = []
    results = run.run_suite(mode="recorded", only=only, engine=object(), progress=lines.append)
    whole = [b.code for b in load_book(DEFAULT_BOOK)]
    expected = [c for c in (only or whole) if c not in RENAMED]
    assert ran == [expected]
    skipped = [c for c in (only or whole) if c in RENAMED]
    assert results["meta"]["not_replayed"] == [{"borrower": c, "reason": run.NO_RECORDING} for c in skipped]
    assert [ln for ln in lines if "SKIPPED" in ln] == [f"{c:28s} SKIPPED: {run.NO_RECORDING}" for c in skipped]
    if only is None:
        assert len(expected) == 12 and len(skipped) == 8
        assert results["meta"]["scope"] == "whole book except 8 not replayed"
    [line] = _not_replayed({**results["meta"], "borrowers": len(expected)})
    assert line.startswith(f"NOT REPLAYED ({len(skipped)}; the gate covers only the {len(expected)} that ran): ")
    assert line.endswith(f" - {run.NO_RECORDING}.") and all(c in line for c in skipped)


def test_stand_in_needs_no_signature_and_no_flag():
    check_may_start("standin", ["datamarrow"], out=io.StringIO(), oracle=oracle_for(DEFAULT_BOOK))
    with pytest.raises(RunRefused, match="unknown mode"):
        check_may_start("cheap", [], oracle=oracle_for(DEFAULT_BOOK))


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_the_other_modes_go_through_client_for_with_one_setting_changed(tmp_path, monkeypatch):
    book = load_book(only=["datamarrow"])
    assert make_client("standin", book).mode == "standin"
    recorded = make_client("recorded", book, recordings=tmp_path, accept_stale=frozenset({"intake"}))
    assert isinstance(recorded, RecordedClient) and recorded.root == tmp_path
    assert recorded.accept_stale == frozenset({"intake"})
    seen = []
    monkeypatch.setattr("app.agents.llm.client_for", lambda settings: seen.append(settings.squad_llm_mode) or "client")
    assert make_client("live", book) == "client" and make_client("record", book) == "client"
    assert seen == ["live", "record"]


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_the_command_line_refuses_a_live_run_without_calling_anything(capsys, monkeypatch):
    monkeypatch.setattr(run, "make_client", lambda *a, **k: pytest.fail("a client was built for a refused run"))
    code = run.main(["--mode", "live", "--only", "datamarrow", "--database-url", "postgresql+psycopg://unused/none"])
    captured = capsys.readouterr()
    assert code == 2 and "Not started" in captured.err and COST_WARNING in captured.err


@pytest.mark.parametrize(("printed", "value"), [
    ("74,118", "74118"), ("(2,520)", "-2520"), ("-", "0"), ("1.51x", "1.51"), ("$ 48,250", "48250"), ("85%", "85")])
def test_printed_figures_are_read_the_way_an_accountant_reads_them(printed, value):
    assert str(parse_printed(printed)) == value


@pytest.mark.parametrize("text", ["Yes", "Not less than 1.05x", "12 months", "1,2,3x4", ""])
def test_text_that_is_not_one_figure_is_not_read_as_one(text):
    assert parse_printed(text) is None


def test_the_oracle_is_required_there_is_no_default_to_borrow():
    with pytest.raises(TypeError):
        check_may_start("live", ["datamarrow"], confirm_billable=True, out=io.StringIO())
    with pytest.raises(TypeError):
        unsigned_oracle_rows(["datamarrow"])


def _nothing_is_built(monkeypatch):
    monkeypatch.setattr(run, "make_client", lambda *a, **k: pytest.fail("a client was built for a refused run"))
    monkeypatch.setattr(run, "create_engine", lambda *a, **k: pytest.fail("an engine was created for a refused run"))


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_both_books_are_refused_together_before_anything_is_built(monkeypatch, capsys):
    _nothing_is_built(monkeypatch)
    assert run.main(["--mode", "live", "--book", "both"]) == 2
    assert "Not started" in capsys.readouterr().err


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_a_book_path_with_an_unsigned_oracle_is_refused_by_its_own_oracle(tmp_path, monkeypatch, capsys):
    _nothing_is_built(monkeypatch)
    root = tmp_path / "book" / "out"
    shutil.copytree(DEFAULT_BOOK, root, ignore=shutil.ignore_patterns("documents"))
    (tmp_path / "book" / "oracle.csv").write_text(_oracle(tmp_path, "no").read_text())
    assert run.main(["--mode", "live", "--book", str(root), "--confirm-billable"]) == 2
    assert "not signed by the owner" in capsys.readouterr().err


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_a_missing_borrower_in_any_book_refuses_the_whole_run(monkeypatch, capsys):
    _nothing_is_built(monkeypatch)
    assert run.main(["--mode", "standin", "--book", "both", "--only", "datamarrow"]) == 2
    assert "not in the book" in capsys.readouterr().err


def test_only_the_default_book_writes_latest(tmp_path):
    assert run._stem("innovation", BOOKS["innovation"]) == "latest"
    assert run._stem("legacy", BOOKS["legacy"]) == "latest-legacy"
    assert run._stem(str(tmp_path / "x" / "out"), tmp_path / "x" / "out") == "latest-x"
    results = {"meta": {"mode": "standin"}, "gate": {"passed": True, "reasons": []}}
    (tmp_path / "latest.json").write_text("keep")
    from unittest import mock

    with mock.patch("evals.scorecard.render_markdown", return_value="md"):
        json_path, _ = run.write_results(results, tmp_path, "latest-legacy")
    assert json_path.name == "latest-legacy.json" and (tmp_path / "latest.json").read_text() == "keep"


def test_a_billable_run_reads_the_oracle_of_the_book_it_runs(monkeypatch):
    seen = []
    monkeypatch.setattr(run, "unsigned_oracle_rows", lambda codes, oracle: seen.append(oracle) or [])
    check_may_start("live", ["x"], confirm_billable=True, out=io.StringIO(), oracle=oracle_for(BOOKS["legacy"]))
    check_may_start("live", ["x"], confirm_billable=True, out=io.StringIO(), oracle=oracle_for(DEFAULT_BOOK))
    assert seen == [oracle_for(BOOKS["legacy"]), oracle_for(DEFAULT_BOOK)]


def test_the_scripted_not_needed_answer_is_for_a_spreadsheet_export_only():
    """`intake.unclassified` is set aside by script only when its document is a spreadsheet."""
    from types import SimpleNamespace

    from evals.run import _is_sheet_item

    class Db:
        def __init__(self, fmt):
            self.doc = SimpleNamespace(meta={"format": fmt})

        def get(self, model, ident):
            return self.doc

    import uuid
    item = SimpleNamespace(evidence={"document_id": str(uuid.uuid4())})
    assert _is_sheet_item(Db("xlsx"), item) and _is_sheet_item(Db("csv"), item)
    assert not _is_sheet_item(Db(None), item)
    assert not _is_sheet_item(Db("pdf"), SimpleNamespace(evidence={}))

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
            check_may_start(mode, ["dataflake"], out=out, oracle=unsigned_oracle)
        assert COST_WARNING in out.getvalue()


def test_allow_unsigned_is_a_stated_exception_and_still_needs_the_owners_go_ahead(unsigned_oracle):
    out = io.StringIO()
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["dataflake"], allow_unsigned=True, out=out, oracle=unsigned_oracle)
    assert "--allow-unsigned" in out.getvalue() and COST_WARNING in out.getvalue()
    # with both flags the run may start; nothing is called here
    check_may_start("live", ["dataflake"], allow_unsigned=True, confirm_billable=True, out=io.StringIO(),
                    oracle=unsigned_oracle)


def test_unsigned_rows_are_listed_and_a_borrower_without_rows_counts_as_unsigned(unsigned_oracle):
    rows = unsigned_oracle_rows(["dataflake"], unsigned_oracle)
    assert len(rows) >= 5 and {r["owner_signed_off"] for r in rows} == {"no"}
    assert unsigned_oracle_rows(["not-a-borrower"], unsigned_oracle)[0]["item"] == "no oracle row"


def test_signed_rows_let_a_billable_run_start_only_with_the_owners_go_ahead(tmp_path):
    signed = _oracle(tmp_path, "yes")
    assert unsigned_oracle_rows(["dataflake"], signed) == []
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["dataflake"], out=io.StringIO(), oracle=signed)
    check_may_start("live", ["dataflake"], confirm_billable=True, out=io.StringIO(), oracle=signed)


def test_recorded_mode_refuses_when_there_are_no_recordings(tmp_path):
    with pytest.raises(RunRefused, match="no recorded model responses"):
        check_may_start("recorded", ["dataflake"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK))
    (tmp_path / "intake").mkdir()
    (tmp_path / "intake" / "x.json").write_text("{}")
    check_may_start("recorded", ["dataflake"], recordings=tmp_path, oracle=oracle_for(DEFAULT_BOOK))


def test_stand_in_needs_no_signature_and_no_flag():
    check_may_start("standin", ["dataflake"], out=io.StringIO(), oracle=oracle_for(DEFAULT_BOOK))
    with pytest.raises(RunRefused, match="unknown mode"):
        check_may_start("cheap", [], oracle=oracle_for(DEFAULT_BOOK))


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_the_other_modes_go_through_client_for_with_one_setting_changed(tmp_path, monkeypatch):
    book = load_book(only=["dataflake"])
    assert make_client("standin", book).mode == "standin"
    recorded = make_client("recorded", book, recordings=tmp_path)
    assert isinstance(recorded, RecordedClient) and recorded.root == tmp_path
    seen = []
    monkeypatch.setattr("app.agents.llm.client_for", lambda settings: seen.append(settings.squad_llm_mode) or "client")
    assert make_client("live", book) == "client" and make_client("record", book) == "client"
    assert seen == ["live", "record"]


@pytest.mark.skipif(not BOOK_BUILT, reason="the default book has not been generated")
def test_the_command_line_refuses_a_live_run_without_calling_anything(capsys, monkeypatch):
    monkeypatch.setattr(run, "make_client", lambda *a, **k: pytest.fail("a client was built for a refused run"))
    code = run.main(["--mode", "live", "--only", "dataflake", "--database-url", "postgresql+psycopg://unused/none"])
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
        check_may_start("live", ["dataflake"], confirm_billable=True, out=io.StringIO())
    with pytest.raises(TypeError):
        unsigned_oracle_rows(["dataflake"])


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
    assert run.main(["--mode", "standin", "--book", "both", "--only", "dataflake"]) == 2
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

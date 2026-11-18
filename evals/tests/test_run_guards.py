"""When a run may start. No test here calls a model, and none may."""
import io

import pytest
from app.agents.llm import RecordedClient

from evals import run
from evals.book import DEFAULT_BOOK, load_book, parse_printed, unsigned_oracle_rows
from evals.run import COST_WARNING, RunRefused, check_may_start, make_client

BOOK_BUILT = (DEFAULT_BOOK / "truth").exists()


def _oracle(tmp_path, signed: str):
    """A copy of the oracle with every row signed or unsigned, so these guards do not depend on
    whether the owner has signed the real one."""
    from evals.book import ORACLE

    lines = ORACLE.read_text().splitlines()
    body = [line.rsplit(",", 1)[0] + "," + signed for line in lines[1:]]
    path = tmp_path / "oracle.csv"
    path.write_text("\n".join([lines[0], *body]) + "\n")
    return path


@pytest.fixture(autouse=True)
def unsigned_oracle(tmp_path, monkeypatch):
    path = _oracle(tmp_path, "no")
    monkeypatch.setattr(run, "unsigned_oracle_rows", lambda codes: unsigned_oracle_rows(codes, path))
    return path


def test_live_and_record_refuse_unsigned_oracle_rows_and_print_the_cost_warning():
    for mode in ("live", "record"):
        out = io.StringIO()
        with pytest.raises(RunRefused, match="not signed by the owner"):
            check_may_start(mode, ["harrowgate-precision"], out=out)
        assert COST_WARNING in out.getvalue()


def test_allow_unsigned_is_a_stated_exception_and_still_needs_the_owners_go_ahead():
    out = io.StringIO()
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["harrowgate-precision"], allow_unsigned=True, out=out)
    assert "--allow-unsigned" in out.getvalue() and COST_WARNING in out.getvalue()
    # with both flags the run may start; nothing is called here
    check_may_start("live", ["harrowgate-precision"], allow_unsigned=True, confirm_billable=True, out=io.StringIO())


def test_unsigned_rows_are_listed_and_a_borrower_without_rows_counts_as_unsigned(unsigned_oracle):
    rows = unsigned_oracle_rows(["harrowgate-precision", "kestrel-bay-packaging"], unsigned_oracle)
    assert len(rows) >= 5 and {r["owner_signed_off"] for r in rows} == {"no"}
    assert unsigned_oracle_rows(["not-a-borrower"], unsigned_oracle)[0]["item"] == "no oracle row"


def test_signed_rows_let_a_billable_run_start_only_with_the_owners_go_ahead(tmp_path, monkeypatch):
    signed = _oracle(tmp_path, "yes")
    assert unsigned_oracle_rows(["harrowgate-precision"], signed) == []
    monkeypatch.setattr(run, "unsigned_oracle_rows", lambda codes: unsigned_oracle_rows(codes, signed))
    with pytest.raises(RunRefused, match="billable"):
        check_may_start("live", ["harrowgate-precision"], out=io.StringIO())
    check_may_start("live", ["harrowgate-precision"], confirm_billable=True, out=io.StringIO())


def test_recorded_mode_refuses_when_there_are_no_recordings(tmp_path):
    with pytest.raises(RunRefused, match="no recorded model responses"):
        check_may_start("recorded", ["harrowgate-precision"], recordings=tmp_path)
    (tmp_path / "intake").mkdir()
    (tmp_path / "intake" / "x.json").write_text("{}")
    check_may_start("recorded", ["harrowgate-precision"], recordings=tmp_path)


def test_stand_in_needs_no_signature_and_no_flag():
    check_may_start("standin", ["harrowgate-precision"], out=io.StringIO())
    with pytest.raises(RunRefused, match="unknown mode"):
        check_may_start("cheap", [])


@pytest.mark.skipif(not BOOK_BUILT, reason="synthetic/out has not been generated")
def test_the_other_modes_go_through_client_for_with_one_setting_changed(tmp_path, monkeypatch):
    book = load_book(only=["harrowgate-precision"])
    assert make_client("standin", book).mode == "standin"
    recorded = make_client("recorded", book, recordings=tmp_path)
    assert isinstance(recorded, RecordedClient) and recorded.root == tmp_path
    seen = []
    monkeypatch.setattr("app.agents.llm.client_for", lambda settings: seen.append(settings.squad_llm_mode) or "client")
    assert make_client("live", book) == "client" and make_client("record", book) == "client"
    assert seen == ["live", "record"]


@pytest.mark.skipif(not BOOK_BUILT, reason="synthetic/out has not been generated")
def test_the_command_line_refuses_a_live_run_without_calling_anything(capsys, monkeypatch):
    monkeypatch.setattr(run, "make_client", lambda *a, **k: pytest.fail("a client was built for a refused run"))
    code = run.main(["--mode", "live", "--only", "harrowgate-precision", "--database-url", "postgresql+psycopg://unused/none"])
    captured = capsys.readouterr()
    assert code == 2 and "Not started" in captured.err and COST_WARNING in captured.err


@pytest.mark.parametrize(("printed", "value"), [
    ("74,118", "74118"), ("(2,520)", "-2520"), ("-", "0"), ("1.51x", "1.51"), ("$ 48,250", "48250"), ("85%", "85")])
def test_printed_figures_are_read_the_way_an_accountant_reads_them(printed, value):
    assert str(parse_printed(printed)) == value


@pytest.mark.parametrize("text", ["Yes", "Not less than 1.05x", "12 months", "1,2,3x4", ""])
def test_text_that_is_not_one_figure_is_not_read_as_one(text):
    assert parse_printed(text) is None

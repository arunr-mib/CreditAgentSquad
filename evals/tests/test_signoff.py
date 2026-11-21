import csv
from pathlib import Path

import pytest

from evals import book, run, signoff

HEADER = "borrower_id,borrower_name,period_end,kind,item,expected_value,threshold,expected_outcome,terms_version,scenario,owner_signed_off\n"


def _oracle(tmp_path: Path) -> Path:
    path = tmp_path / "oracle.csv"
    path.write_text(HEADER
                    + "acme,Acme,2026-10-31,covenant_test,min_cash,4600000,>= 5000000,breach,tv-1,s,no\n"
                    + "acme,Acme,2026-10-31,signal,runway_below_watch,7.1,,high,,s,no\n"
                    + "acme,Acme,2026-10-31,signal,headroom,0.4,,low,,s,no\n"
                    + "kept,Kept,2026-09-30,covenant_test,dscr,1.5,>= 1.2,compliant,tv-2,s,yes\n")
    return path


def test_the_table_counts_unsigned_rows_by_borrower_and_kind(tmp_path):
    text = signoff.table(_oracle(tmp_path))
    assert text.splitlines()[0].startswith("3 unsigned rows (2 signals, 1 low severity) of 4")
    assert "| acme | 1 | 2 | 0 |" in text and "kept" not in text


def test_apply_signs_exactly_the_listed_rows_and_nothing_else(tmp_path):
    oracle = _oracle(tmp_path)
    rows = tmp_path / "rows.txt"
    rows.write_text("acme|2026-10-31|covenant_test|min_cash\n")
    assert signoff.apply(oracle, rows) == 1
    got = {r["item"]: r for r in csv.DictReader(oracle.open(newline=""))}
    assert got["min_cash"]["owner_signed_off"] == "yes" and got["runway_below_watch"]["owner_signed_off"] == "no"
    assert got["min_cash"]["expected_value"] == "4600000"  # no other column moved


def test_apply_refuses_an_empty_file_and_a_row_that_is_not_in_the_key(tmp_path):
    oracle = _oracle(tmp_path)
    empty, bad = tmp_path / "e.txt", tmp_path / "b.txt"
    empty.write_text("")
    bad.write_text("acme|2026-10-31|covenant_test|nope\n")
    before = oracle.read_text()
    with pytest.raises(ValueError, match="no rows"):
        signoff.apply(oracle, empty)
    with pytest.raises(ValueError, match="not in the oracle"):
        signoff.apply(oracle, bad)
    with pytest.raises(ValueError, match="no rows"):
        signoff.apply(oracle, None)  # never signs by default
    assert oracle.read_text() == before


def test_the_cli_has_no_sign_everything_switch_and_signs_nothing_without_a_file(tmp_path):
    oracle = _oracle(tmp_path)
    with pytest.raises(SystemExit):
        signoff.main(["apply", "--oracle", str(oracle), "--all"])
    with pytest.raises(ValueError, match="no rows"):
        signoff.main(["apply", "--oracle", str(oracle)])


def test_low_severity_signals_can_be_listed_as_a_block_and_signed(tmp_path):
    oracle = _oracle(tmp_path)
    keys = signoff.keys(oracle, low_signals=True)
    assert keys == ["acme|2026-10-31|signal|headroom"]
    rows = tmp_path / "rows.txt"
    rows.write_text("\n".join(keys) + "\n")
    signoff.apply(oracle, rows)
    assert [r["item"] for r in book.unsigned_oracle_rows(["acme"], oracle)] == ["min_cash", "runway_below_watch"]


def test_the_billable_guard_reads_the_signing(tmp_path):
    oracle = _oracle(tmp_path)
    with pytest.raises(run.RunRefused):
        run.check_may_start("live", ["acme"], oracle=oracle, confirm_billable=True)
    rows = tmp_path / "rows.txt"
    rows.write_text("\n".join(signoff.keys(oracle)) + "\n")
    signoff.apply(oracle, rows)
    assert book.unsigned_oracle_rows(["acme"], oracle) == []
    try:
        run.check_may_start("live", ["acme"], oracle=oracle, confirm_billable=True)
    except run.RunRefused as exc:  # other guards (recordings, database) may still refuse; not the signing
        assert "not signed" not in str(exc)


def test_the_real_key_is_described_in_plain_words_for_every_client(tmp_path):
    # the real key is signed now; describe its rows from an unsigned copy
    import csv
    src = book.oracle_for(book.BOOKS["innovation"])
    with src.open(newline="") as f:
        rows = list(csv.DictReader(f))
    copy = tmp_path / "oracle.csv"
    with copy.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        kept = {"kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain"}
        w.writerows({**r, "owner_signed_off": r["owner_signed_off"] if r["borrower_id"] in kept else "no"}
                    for r in rows)
    text = signoff.table(copy)
    assert text.count("\n| ") >= 16 and len(text.splitlines()) < 30
    for line in text.splitlines()[4:]:
        cell = line.rsplit("|", 2)[-2].strip()
        assert cell and "_" not in cell  # a sentence, not a scenario code

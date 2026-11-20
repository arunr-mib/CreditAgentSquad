"""The kept four are the v1 book, and the answer key is the owner's to sign."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from synthetic.books.innovation.roster import KEPT_IDS

LEGACY = Path(__file__).resolve().parents[2] / "out"
LEGACY_ORACLE = Path(__file__).resolve().parents[2] / "oracle.csv"


def test_the_four_kept_borrowers_are_byte_identical_to_the_v1_truth(generated):
    for borrower_id in KEPT_IDS:
        mine = (generated.out / "truth" / f"{borrower_id}.json").read_bytes()
        assert mine == (LEGACY / "truth" / f"{borrower_id}.json").read_bytes(), borrower_id


def test_their_documents_are_the_v1_documents(generated):
    legacy = {d["id"]: d["text_sha256"] for d in json.loads((LEGACY / "manifest.json").read_text())["documents"]
              if d["borrower_id"] in KEPT_IDS}
    mine = {d["id"]: d["text_sha256"] for d in generated.manifest["documents"] if d["borrower_id"] in KEPT_IDS}
    assert mine == legacy and len(mine) == 73


def test_kept_rows_stay_signed_and_new_rows_come_unsigned(generated):
    rows = list(csv.DictReader(generated.oracle.open(newline="")))
    kept = [r for r in rows if r["borrower_id"] in KEPT_IDS]
    new = [r for r in rows if r["borrower_id"] not in KEPT_IDS]
    legacy = [r for r in csv.DictReader(LEGACY_ORACLE.open(newline="")) if r["borrower_id"] in KEPT_IDS]
    def key(row):
        return (row["borrower_id"], row["kind"], row["item"])

    assert sorted(kept, key=key) == sorted(legacy, key=key) and all(r["owner_signed_off"] == "yes" for r in kept)
    assert len({r["borrower_id"] for r in new}) == 16 and all(r["owner_signed_off"] == "no" for r in new)
    assert {r["kind"] for r in new} == {"covenant_test", "funding_event", "exception"}


def test_regenerating_keeps_an_owner_signature_only_while_the_row_is_unchanged(tmp_path):
    from synthetic.books.innovation.generate import generate

    out, oracle = tmp_path / "out", tmp_path / "oracle.csv"
    generate(out, oracle=oracle)
    rows = list(csv.DictReader(oracle.open(newline="")))
    target = next(r for r in rows if r["borrower_id"] == "dataflake" and r["item"] == "min_unrestricted_cash")
    target["owner_signed_off"] = "yes"
    with oracle.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    generate(out, oracle=oracle)
    again = {(r["borrower_id"], r["kind"], r["item"]): r["owner_signed_off"] for r in csv.DictReader(oracle.open(newline=""))}
    assert again[("dataflake", "covenant_test", "min_unrestricted_cash")] == "yes"
    assert sum(1 for v in again.values() if v == "yes") == 1 + 16  # the signed row and the kept four's
    generate(out, seed=7, oracle=oracle)  # a different seed changes values: the signature does not survive
    changed = {(r["borrower_id"], r["kind"], r["item"]): r["owner_signed_off"] for r in csv.DictReader(oracle.open(newline=""))}
    assert changed[("dataflake", "covenant_test", "min_unrestricted_cash")] == "yes"  # the October figures are fixed

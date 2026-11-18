"""Build the synthetic book: ground truth, PDF documents, manifest and oracle.

    uv run python -m synthetic.generate [--out synthetic/out] [--seed 20261117]

The same seed always gives byte-identical truth files and identical PDF text.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from synthetic import expected
from synthetic.book import BorrowerBook, DocPlan, build_book, scenario_record
from synthetic.render import common
from synthetic.render.certificates import render_borrowing_base_certificate, render_compliance_certificate
from synthetic.render.legal import render_legal
from synthetic.render.statements import render_statements
from synthetic.scenarios import CURRENT_PERIOD, DEFAULT_SEED, LENDER, TODAY

SCHEMA = "synthetic-truth-1"
ORACLE_COLUMNS = (
    "borrower_id", "borrower_name", "period_end", "kind", "item", "expected_value", "threshold",
    "expected_outcome", "terms_version", "scenario", "owner_signed_off",
)  # fmt: skip


def plain(value):
    """Convert truth data to JSON-ready values: decimals as strings, dates as ISO text."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


def _render(book: BorrowerBook, doc: DocPlan, folder: Path) -> dict:
    spec, path = book.spec, folder / doc.filename
    if doc.type in ("credit_agreement", "amendment"):
        return render_legal(path, doc.payload["legal"], spec.name)
    if doc.type in ("annual_financial_statements", "interim_financial_statements"):
        return render_statements(path, spec, doc.payload, doc.title)
    if doc.type == "compliance_certificate":
        version = expected.terms_version_in_force(book.terms.versions, doc.period_end)
        covenants = version["terms"]["covenants"]
        return render_compliance_certificate(path, spec, doc.payload["certificate"], covenants, doc.document_date, doc.title)
    if doc.type == "borrowing_base_certificate":
        bb_terms = book.terms.versions[-1]["terms"]["borrowing_base"]
        return render_borrowing_base_certificate(path, spec, doc.payload["borrowing_base"], bb_terms, doc.document_date, doc.title)
    raise ValueError(doc.type)


def _resolve_citations(node, lookup):
    """Replace every citation placeholder with {field, document_id, section, page, quote}."""
    if isinstance(node, dict):
        if "_anchor" in node:
            resolved = lookup(node["_anchor"])
            rest = {k: _resolve_citations(v, lookup) for k, v in node.items() if k != "_anchor"}
            return {**rest, **resolved} if "field" not in rest else {"field": rest.pop("field"), **resolved, **rest}
        return {k: _resolve_citations(v, lookup) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_citations(v, lookup) for v in node]
    return node


def _truth(book: BorrowerBook, rendered: dict[str, dict], texts: dict[str, list[str]], seed: int) -> dict:
    spec = book.spec
    legal = {"credit-agreement": book.terms.agreement, **{a.slug: a for a in book.terms.amendments}}

    def lookup(anchor_ref: tuple[str, str]) -> dict:
        slug, anchor = anchor_ref
        doc_id = f"{spec.id}.{slug}"
        cite = legal[slug].cites[anchor]
        page = rendered[doc_id]["anchor_pages"][anchor]
        if common.squash(cite["quote"]) not in common.squash(texts[doc_id][page - 1]):
            raise AssertionError(f"{doc_id}: quote for {anchor} is not on page {page}")
        return {"document_id": doc_id, "section": cite["section"], "page": page, "quote": cite["quote"]}

    versions = []
    for version in book.terms.versions:
        resolved = _resolve_citations(version, lookup)
        resolved["clause_index"] = _resolve_citations(book.terms.clause_index, lookup)
        versions.append(resolved)
    scenario = scenario_record(book)
    scenario["details"] = _resolve_citations(scenario["details"], lookup)
    for doc in book.documents:
        for defect in doc.extra.get("defects", []):
            scenario["details"].setdefault("defects", []).append({"document_id": doc.id, **defect})

    def period_record(p) -> dict:
        return {
            "period_end": p.period_end,
            "months": p.months,
            "fiscal_year": p.fiscal_year,
            "quarter": p.quarter,
            "quality": p.quality,
            "scale": p.scale,
            "values": p.values,
            "memo": p.memo,
        }

    documents = []
    for doc in book.documents:
        documents.append(
            {
                "id": doc.id,
                "type": doc.type,
                "period_end": doc.period_end,
                "path": f"documents/{spec.id}/{doc.filename}",
                "pages": doc.pages,
                "title": doc.title,
                "received_date": doc.received_date,
                "document_date": doc.document_date,
                **doc.extra,
            }
        )
    truth = {
        "schema": SCHEMA,
        "seed": seed,
        "as_of": TODAY,
        "current_period": CURRENT_PERIOD,
        "borrower": {
            "id": spec.id,
            "name": spec.name,
            "legal_form": spec.legal_form,
            "industry": spec.industry,
            "city": spec.city,
            "state": spec.state,
            "fiscal_year_end_month": 12,
            "lender": LENDER,
            "relationship_manager": spec.relationship_manager,
            "analyst": spec.analyst,
            "risk_rating": spec.risk_rating,
            "statement_scale": spec.scale,
            "chief_financial_officer": spec.cfo,
            "auditor": spec.auditor,
        },
        "facilities": book.terms.facilities,
        "terms_versions": versions,
        "periods": [period_record(p) for p in book.periods],
        "comparative_periods": [period_record(book.comparative)],
        "certificates": book.certificates,
        "borrowing_base": book.borrowing_base,
        "system_of_record": book.system_of_record,
        "documents": documents,
        "scenario": scenario,
        "expected": book.expected,
    }
    return plain(truth)


def _oracle_rows(book: BorrowerBook) -> list[dict]:
    spec = book.spec
    base = {
        "borrower_id": spec.id,
        "borrower_name": spec.name,
        "period_end": CURRENT_PERIOD.isoformat(),
        "scenario": spec.scenario,
        "owner_signed_off": "no",
        "threshold": "",
        "terms_version": "",
        "expected_value": "",
    }
    rows = []
    for test in book.expected["covenant_tests"]:
        if test["period_end"] != CURRENT_PERIOD:
            continue
        rows.append(
            {
                **base,
                "kind": "covenant_test",
                "item": test["covenant_id"],
                "expected_value": "" if test["value"] is None else format(test["value"], "f"),
                "threshold": f"{test['operator']} {format(test['threshold'], 'f')}",
                "expected_outcome": test["outcome"],
                "terms_version": test["terms_version_id"],
            }
        )
    for result in book.expected["borrowing_base"]:
        if result["period_end"] != CURRENT_PERIOD:
            continue
        flags = [name for name, on in (("over_advance", result["over_advance"]), ("certificate_mismatch", not result["certificate_matches"])) if on]
        rows.append(
            {
                **base,
                "kind": "borrowing_base",
                "item": "availability",
                "expected_value": format(result["availability"], "f"),
                "expected_outcome": "+".join(flags) or "ok",
            }
        )
    for exception in book.expected["exceptions"]:
        rows.append({**base, "kind": "exception", "item": exception["subject"], "expected_outcome": exception["type"]})
    return rows


def _keep_sign_off(oracle: Path, rows: list[dict]) -> None:
    """The owner's sign-off survives regeneration for a row whose expected values are unchanged.
    A row whose values changed comes back unsigned, so the owner checks it again."""
    if not oracle.exists():
        return
    with oracle.open(newline="", encoding="utf-8") as handle:
        signed = {tuple(r.get(c, "") for c in ORACLE_COLUMNS if c != "owner_signed_off")
                  for r in csv.DictReader(handle) if r.get("owner_signed_off", "").strip().lower() == "yes"}
    for row in rows:
        if tuple(str(row.get(c, "")) for c in ORACLE_COLUMNS if c != "owner_signed_off") in signed:
            row["owner_signed_off"] = "yes"


def generate(out: Path, seed: int = DEFAULT_SEED, oracle: Path | None = None) -> dict:
    """Generate the whole book under `out`. Returns the manifest."""
    out = Path(out)
    oracle = Path(oracle) if oracle else out.parent / "oracle.csv"
    for stale in (out / "documents", out / "truth"):
        if stale.exists():
            shutil.rmtree(stale)
    (out / "truth").mkdir(parents=True, exist_ok=True)
    books = build_book(seed)
    manifest_docs, oracle_rows = [], []
    for book in books:
        folder = out / "documents" / book.spec.id
        rendered: dict[str, dict] = {}
        texts: dict[str, list[str]] = {}
        for doc in book.documents:
            result = _render(book, doc, folder)
            doc.pages = result["pages"]
            doc.extra = result.get("extra", {})
            rendered[doc.id] = result
            pages = common.page_texts(folder / doc.filename)
            texts[doc.id] = pages
            if len(pages) != doc.pages:
                raise AssertionError(f"{doc.id}: page count mismatch")
            if not any(common.MARKER in text for text in pages):
                raise AssertionError(f"{doc.id}: synthetic marker missing")
            digest = hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()
            manifest_docs.append(
                {
                    "id": doc.id,
                    "borrower_id": book.spec.id,
                    "type": doc.type,
                    "period_end": doc.period_end.isoformat() if doc.period_end else None,
                    "path": f"documents/{book.spec.id}/{doc.filename}",
                    "pages": doc.pages,
                    "text_sha256": digest,
                }
            )
        truth = _truth(book, rendered, texts, seed)
        text = json.dumps(truth, indent=1, ensure_ascii=False) + "\n"
        (out / "truth" / f"{book.spec.id}.json").write_text(text, encoding="utf-8")
        oracle_rows += _oracle_rows(book)
    manifest = {
        "schema": "synthetic-manifest-1",
        "seed": seed,
        "as_of": TODAY.isoformat(),
        "lender": LENDER,
        "counts": {
            "borrowers": len(books),
            "documents": len(manifest_docs),
            "pages": sum(d["pages"] for d in manifest_docs),
        },
        "borrowers": [{"id": b.spec.id, "name": b.spec.name, "scenario": b.spec.scenario} for b in books],
        "documents": manifest_docs,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    _keep_sign_off(oracle, oracle_rows)
    with oracle.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ORACLE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(oracle_rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic loan book.")
    parser.add_argument("--out", default="synthetic/out", help="output directory (default synthetic/out)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--oracle", default=None, help="oracle CSV path (default: beside the output directory)")
    args = parser.parse_args()
    started = time.monotonic()
    manifest = generate(Path(args.out), args.seed, args.oracle)
    counts = manifest["counts"]
    print(
        f"{counts['borrowers']} borrowers, {counts['documents']} documents, {counts['pages']} pages "
        f"written to {args.out} in {time.monotonic() - started:.1f}s"
    )


if __name__ == "__main__":
    main()

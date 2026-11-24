"""Build the innovation book: 16 venture-backed clients and the four kept C&I borrowers.

    uv run python -m synthetic.books.innovation.generate [--out synthetic/books/innovation/out] [--seed 20261120]

The same seed gives byte-identical truth files and identical PDF text. The kept four are produced by the frozen v1
generator with the v1 seed, so their truth files equal those in `synthetic/out`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
from pathlib import Path

from synthetic import generate as legacy
from synthetic.book import DocPlan
from synthetic.books.innovation import documents
from synthetic.books.innovation.book import ClientBook, build_clients, scenario_record
from synthetic.books.innovation.expected import COVENANTS
from synthetic.books.innovation.kept import build_kept
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, DEFAULT_SEED, LEGACY_SEED, LENDER
from synthetic.books.innovation.terms import dscr_covenant
from synthetic.render import common
from synthetic.render import innovation as render
from synthetic.render.legal import render_legal

HERE = Path(__file__).resolve().parent
LEGACY_ORACLE = HERE.parents[1] / "oracle.csv"
SCHEMA = "synthetic-truth-2"
NAMES = {**{cid: name for cid, name, _ in COVENANTS}, "dscr": dscr_covenant()["name"]}


def _render_client_doc(book: ClientBook, doc: DocPlan, folder: Path) -> dict:
    spec, path, payload = book.spec, folder / doc.filename, doc.payload
    if doc.type == "credit_agreement":
        return render_legal(path, payload["legal"], spec.name)
    if doc.type == "annual_financial_statements":
        return render.render_annual_statements(path, spec, payload, doc.title)
    if doc.type == "monthly_financials":
        return render.render_monthly_financials(path, spec, payload, doc.title)
    if doc.type == "mrr_report":
        return render.render_mrr_report(path, spec, payload, doc.title)
    if doc.type == "bank_statement":
        return render.render_bank_statement(path, spec, payload, doc.title)
    if doc.type == "compliance_certificate":
        return render.render_monthly_certificate(path, spec, documents.certificate_payload(spec, doc, NAMES), doc.title)
    if doc.type in ("term_sheet", "investor_update"):
        return render.render_notice(path, spec, payload["notice"], doc.title)
    if doc.type == "unclassified":  # the stray MRR export: the real workbook, and the print of it the PDF-only intake takes
        xlsx = folder / "mrr_export.xlsx"
        cells = render.write_export_workbook(xlsx, payload["rows"])
        result = render.render_export_print(path, payload["rows"])
        result["extra"]["workbook"] = {"path": f"documents/{spec.id}/mrr_export.xlsx",
                                       "cells_sha256": hashlib.sha256(cells.encode("utf-8")).hexdigest()}  # fmt: skip
        return result
    raise ValueError(doc.type)


def _period_record(p) -> dict:
    return {"period_end": p.period_end, "months": p.months, "fiscal_year": p.fiscal_year, "quality": p.quality,
            "scale": 1, "values": p.values, "memo": p.memo}  # fmt: skip


def _client_truth(book: ClientBook, rendered: dict[str, dict], texts: dict[str, list[str]], seed: int) -> dict:
    spec = book.spec

    def lookup(anchor_ref: tuple[str, str]) -> dict:
        slug, anchor = anchor_ref
        doc_id = f"{spec.id}.{slug}"
        cite = book.terms.agreement.cites[anchor]
        page = rendered[doc_id]["anchor_pages"][anchor]
        if common.squash(cite["quote"]) not in common.squash(texts[doc_id][page - 1]):
            raise AssertionError(f"{doc_id}: quote for {anchor} is not on page {page}")
        return {"document_id": doc_id, "section": cite["section"], "page": page, "quote": cite["quote"]}

    versions = []
    for raw in book.terms.versions():  # every version: Ferrogate's DSCR amendment is a second one
        version = legacy._resolve_citations(raw, lookup)
        version["clause_index"] = legacy._resolve_citations(book.terms.clause_index, lookup)
        versions.append(version)
    scenario = scenario_record(book)
    scenario["details"] = legacy._resolve_citations(scenario["details"], lookup)
    if spec.scenario == "cindrel_package":  # pages are known only after rendering
        figures = rendered[f"{spec.id}.mf-{CURRENT_PERIOD.isoformat()}"]["extra"]["figures"]
        scenario["details"]["new_line"]["page"] = figures["bs.deferred_revenue_current"]["page"]
        scenario["details"]["capitalised_software"]["page"] = figures["bs.capitalised_software"]["page"]
    docs = [
        {"id": d.id, "type": d.type, "period_end": d.period_end, "path": f"documents/{spec.id}/{d.filename}",
         "pages": d.pages, "title": d.title, "received_date": d.received_date, "document_date": d.document_date,
         **d.extra}
        for d in book.documents
    ]  # fmt: skip
    truth = {
        "schema": SCHEMA, "seed": seed, "as_of": AS_OF, "current_period": CURRENT_PERIOD,
        "borrower": {
            "id": spec.id, "name": spec.name, "legal_form": spec.legal_form, "industry": spec.sector,
            "stage": spec.stage, "city": spec.city, "state": spec.state, "fiscal_year_end_month": 12,
            "lender": LENDER, "relationship_manager": spec.rm, "analyst": spec.analyst,
            "risk_rating": spec.risk_rating, "statement_scale": 1, "chief_financial_officer": spec.cfo,
            "auditor": spec.auditor, "template_id": "vc-1",
        },
        "facilities": [book.terms.facility], "terms_versions": versions,
        "periods": [_period_record(p) for p in book.published], "comparative_periods": [_period_record(book.comparative)],
        "certificates": book.certificates, "borrowing_base": [], "system_of_record": [], "funding_events": book.funding_events,
        "documents": docs, "scenario": scenario, "expected": book.expected,
    }  # fmt: skip
    return legacy.plain(truth)


def _client_oracle_rows(book: ClientBook) -> list[dict]:
    spec = book.spec
    base = {"borrower_id": spec.id, "borrower_name": spec.name, "period_end": CURRENT_PERIOD.isoformat(),
            "scenario": spec.scenario, "owner_signed_off": "no", "threshold": "", "terms_version": "",
            "expected_value": ""}  # fmt: skip
    rows = []
    for test in book.expected["covenant_tests"]:
        if test["period_end"] != CURRENT_PERIOD:
            continue
        outcome = test["outcome"] + ("+not_meaningful" if test.get("note") else "")
        rows.append({**base, "kind": "covenant_test", "item": test["covenant_id"],
                     "expected_value": "" if test["value"] is None else format(test["value"], "f"),
                     "threshold": f"{test['operator']} {format(test['threshold'], 'f')}", "expected_outcome": outcome,
                     "terms_version": test["terms_version_id"]})  # fmt: skip
    for signal in book.expected["signals"]:  # every signal the rules fire for the current period, from the truth
        if signal["period_end"] != CURRENT_PERIOD:
            continue
        detail = signal["detail"].get("covenant_id") or signal["detail"].get("requirement")
        item = signal["rule"] + (f":{detail}" if detail else "")
        value = signal["value"]
        rows.append({**base, "kind": "signal", "item": item,
                     "expected_value": "" if value is None else format(value, "f"),
                     "expected_outcome": signal["severity"]})
    for event in book.funding_events:
        past = event["status"] in ("expected", "signed") and event["expected_close"] < AS_OF
        rows.append({**base, "kind": "funding_event", "item": f"{event['kind']}:{event['expected_close'].isoformat()}",
                     "expected_value": str(event["amount"]), "expected_outcome": "slipped" if past else event["status"]})
    for exception in book.expected["exceptions"]:
        rows.append({**base, "kind": "exception", "item": exception["subject"], "expected_outcome": exception["type"]})
    return rows


def _write_truth(out: Path, borrower_id: str, truth: dict) -> None:
    text = json.dumps(truth, indent=1, ensure_ascii=False) + "\n"
    (out / "truth" / f"{borrower_id}.json").write_text(text, encoding="utf-8")


def _render_all(borrower_id: str, plans: list[DocPlan], render_one, folder: Path, manifest: list[dict]):
    rendered: dict[str, dict] = {}
    texts: dict[str, list[str]] = {}
    for doc in plans:
        result = render_one(doc, folder)
        doc.pages = result["pages"]
        doc.extra = {**doc.extra, **result.get("extra", {})}
        rendered[doc.id] = result
        pages = common.page_texts(folder / doc.filename)
        texts[doc.id] = pages
        if len(pages) != doc.pages:
            raise AssertionError(f"{doc.id}: page count mismatch")
        if not any(common.MARKER in text for text in pages):
            raise AssertionError(f"{doc.id}: synthetic marker missing")
        manifest.append({"id": doc.id, "borrower_id": borrower_id, "type": doc.type,
                         "period_end": doc.period_end.isoformat() if doc.period_end else None,
                         "path": f"documents/{borrower_id}/{doc.filename}", "pages": doc.pages,
                         "text_sha256": hashlib.sha256("\f".join(pages).encode("utf-8")).hexdigest()})  # fmt: skip
        if "workbook" in result.get("extra", {}):
            manifest.append({"id": f"{doc.id}-xlsx", "borrower_id": borrower_id, "type": "unclassified", "period_end": None,
                             "path": result["extra"]["workbook"]["path"], "pages": 0,
                             "text_sha256": result["extra"]["workbook"]["cells_sha256"]})  # fmt: skip
    return rendered, texts


def generate(out: Path, seed: int = DEFAULT_SEED, oracle: Path | None = None, legacy_oracle: Path = LEGACY_ORACLE) -> dict:
    """Generate the whole book under `out`. Returns the manifest."""
    out = Path(out)
    oracle = Path(oracle) if oracle else out.parent / "oracle.csv"
    for stale in (out / "documents", out / "truth"):
        if stale.exists():
            shutil.rmtree(stale)
    (out / "truth").mkdir(parents=True, exist_ok=True)
    manifest_docs: list[dict] = []
    innovation_rows: list[dict] = []
    kept_rows: list[dict] = []
    clients = build_clients(seed)
    for book in clients:
        folder = out / "documents" / book.spec.id
        rendered, texts = _render_all(book.spec.id, book.documents, lambda d, f, b=book: _render_client_doc(b, d, f),
                                      folder, manifest_docs)  # fmt: skip
        _write_truth(out, book.spec.id, _client_truth(book, rendered, texts, seed))
        innovation_rows += _client_oracle_rows(book)
    kept = build_kept(LEGACY_SEED)
    for book in kept:
        folder = out / "documents" / book.spec.id
        rendered, texts = _render_all(book.spec.id, book.documents, lambda d, f, b=book: legacy._render(b, d, f), folder,
                                      manifest_docs)  # fmt: skip
        _write_truth(out, book.spec.id, legacy._truth(book, rendered, texts, LEGACY_SEED))
        kept_rows += legacy._oracle_rows(book)
    names = [(b.spec.id, b.spec.name, b.spec.scenario) for b in clients] + [(b.spec.id, b.spec.name, b.spec.scenario) for b in kept]
    manifest = {
        "schema": "synthetic-manifest-2", "seed": seed, "legacy_seed": LEGACY_SEED, "as_of": AS_OF.isoformat(),
        "lender": LENDER,
        "counts": {"borrowers": len(names), "documents": len(manifest_docs), "pages": sum(d["pages"] for d in manifest_docs)},
        "borrowers": [{"id": i, "name": n, "scenario": s} for i, n, s in names], "documents": manifest_docs,
    }  # fmt: skip
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    rows = innovation_rows + kept_rows
    legacy._keep_sign_off(legacy_oracle, kept_rows)  # the kept four keep the owner's sign-off
    legacy._keep_sign_off(oracle, innovation_rows)  # a regenerated innovation row stays signed only if unchanged
    with oracle.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=legacy.ORACLE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the innovation-banking book.")
    parser.add_argument("--out", default=str(HERE / "out"), help="output directory")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--oracle", default=None, help="oracle CSV path (default: beside the output directory)")
    args = parser.parse_args()
    started = time.monotonic()
    manifest = generate(Path(args.out), args.seed, args.oracle)
    counts = manifest["counts"]
    print(f"{counts['borrowers']} borrowers, {counts['documents']} documents, {counts['pages']} pages written to "
          f"{args.out} in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()

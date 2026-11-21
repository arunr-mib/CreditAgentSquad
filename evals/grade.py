"""Deterministic grading of a run against the synthetic book's ground truth.

Code grades; no model judges a model. The grader reads only the recording of what the product
did and the truth files, and imports nothing from the product, so a defect in the product's
own checks cannot hide itself here.

Named failures (spec section 16):

  invented-number    a usable fact whose value differs from the truth for its key and period, or
                     a figure shown to a person that is not a stored fact (a covenant value with
                     no fact behind it, a reference to a fact that does not exist, a digit typed
                     in agent-written text)
  false-compliant    a covenant recorded compliant where the truth says breach, or a
                     recommendation to resolve a covenant exception where the truth is a breach
  false-breach       a covenant recorded in breach where the truth says it passes
  missed-exception   an exception the scenario expects that was not raised
  false-exception    an exception raised for a clean borrower, or beyond the scenario's expected ones
  wrong-citation     a fact whose cited page does not contain its quote (or its row label)
  wrong-abstain      the product declined (cannot test, cannot compute, no result, an agent run
                     that did not complete) where the truth has an answer
  missed-abstain     the product answered where the truth says it could not (a covenant outcome
                     for a period that cannot be tested, a usable fact for an unreadable line)
  stale-terms        a covenant tested under the wrong terms version or threshold, or under
                     terms that are not approved

Other differences from the truth that have no name in that list (a signal that differs, a
recalculated borrowing base line that differs) are `disagreements`. Things worth a person's
attention that are not differences from the truth are `observations`.

Gate: any invented-number or false-compliant, in any pass, fails; so does a cycle that failed on an error
(run-error) and, outside the stand-in suite, a borrower with expected facts and none read (nothing-read).
An honest abstention on single facts is reported as accuracy, not gated. Accuracy of a real model is
reported, not gated. The stand-in suite must agree with the truth in full: no failure, no
disagreement, every expected fact extracted, apart from findings listed in
`evals/known_findings.json`, which can never excuse the two gated failures.
"""
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymupdf

from evals.book import (
    AR_BUCKETS,
    BANK_KEYS,
    BB_LINES,
    DOC_TYPES,
    OUTFLOWS,
    REPO,
    TOTALS,
    Book,
    Borrower,
    parse_printed,
    squash,
)

FAILURES = ("invented-number", "false-compliant", "false-breach", "missed-exception", "false-exception",
            "wrong-citation", "wrong-abstain", "missed-abstain", "stale-terms")
GATED = ("invented-number", "false-compliant")
KNOWN_FINDINGS = REPO / "evals" / "known_findings.json"
# approvals the autonomy policy always asks of a person; they are not exceptions
ROUTINE_ITEMS = frozenset({"review.commentary_approval", "package.release", "terms.approval_needed"})
# exceptions that stop a cycle before covenant testing: later documents are then not read
HALTING = frozenset({"intake.missing_document", "spread.image_only", "spread.does_not_foot"})
STAGES = ("awaiting_package", "intake", "spreading", "covenant_testing", "borrowing_base", "signals",
          "review_prep", "in_review", "actions_open", "closed")
PACK_TYPES = frozenset({"annual_financial_statements", "interim_financial_statements", "monthly_financials"})
STAGE_OF_ITEM = {"intake": "awaiting_package", "spread": "spreading", "covenant": "covenant_testing",
                 "terms": "covenant_testing", "bb": "borrowing_base", "signal": "signals", "review": "review_prep",
                 "funding_slipped": "signals", "cash": "covenant_testing"}
# agents the stand-in reader does not answer; the product must fall back safely for each
STANDIN_UNANSWERED = frozenset({"covenant", "early_warning", "terms"})
PASSING = ("compliant", "compliant_variance")
BREACHING = ("breach", "breach_reported_compliant")
USABLE = ("verified", "confirmed")
STATED = "stated."
COMPARATIVE = "@comparative"

_REF = re.compile(r"\{\{fact:([0-9a-fA-F-]{36})(?:\|[a-z0-9_]+)?\}\}")
_NOT_FIGURES = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"  # ISO dates
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?\b"  # month day, year
    r"|\b(?:q[1-4]|fy)\s?(?:19|20)\d{2}\b"  # quarter and fiscal-year labels
    r"|\b(?:section|article|schedule|exhibit|page)\s+\d+(?:\.\d+)*(?:\([a-z]\))?"  # references
    r"|\b(?:19|20)\d{2}\b",  # bare years
    re.I)


def _d(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def typed_figures(text: str) -> list[str]:
    """Digits typed in prose, after fact references, dates, quarter labels and section
    references are set aside. The model never types a number, so each one is a failure."""
    stripped = _NOT_FIGURES.sub(" ", _REF.sub(" ", text or ""))
    return re.findall(r"\(?\$?\d[\d,]*(?:\.\d+)?\)?[%xXkKmM]?", stripped)


# ---- the truth, per key ---------------------------------------------------------------------


class Truth:
    """What each fact should be for one borrower's current period."""

    def __init__(self, borrower: Borrower):
        self.b = borrower
        self.end = borrower.current_period
        self.period = borrower.period(self.end) or {"values": {}}
        self.docs = borrower.documents(self.end)
        packs = [d for d in self.docs if d["type"] in PACK_TYPES and "figures" in d]
        if len(packs) > 1:
            raise ValueError(f"{borrower.code} has {len(packs)} financial packs for {self.end}; the book must hold one")
        self.statements = packs[0] if packs else None
        self.cert = borrower.certificate(self.end)
        self.bb = borrower.borrowing_base(self.end)
        self.tests = {t["covenant_id"]: t for t in borrower.expected_tests(self.end)}
        self.expected_bb = borrower.expected_borrowing_base(self.end)
        self.halted = bool(HALTING & set(borrower.expected_exception_types()))
        # the book expects a figure of the pack held for a person: the cycle rests at spreading until
        # it is confirmed, so the figures held are not stored and the later documents are not read
        self.held = self._held_keys()
        self.holds_figures = bool(self.held)
        self._metric_cache: dict[tuple[str, str], Decimal | None] = {}

    # -- expected extracted facts: {fact key: (value, period_end iso, document file)} --

    def expected_facts(self, *, every_figure: bool = False) -> dict[str, tuple[Decimal, str, str]]:
        """The facts the cycle should have stored. `every_figure` ignores what the scenario says the cycle
        never reaches or holds: a figure the book prints is still graded if one is stored, wherever it is."""
        halted = self.halted and not every_figure
        stops_at_spreading = self.holds_figures and not every_figure
        out: dict[str, tuple[Decimal, str, str]] = {}
        s = self.statements
        # a statement with an image-only page is not spread at all (the product asks a person
        # first), so none of its figures are expected; any it does store are still graded
        if s is not None and (
                "spread.image_only" not in self.b.expected_exception_types() or every_figure):
            file, scale = Path(s["path"]).name, Decimal(s.get("scale", 1))
            held = set() if every_figure else self.held
            for key in s["figures"]:
                if key in held:
                    continue
                name = STATED + key if key in TOTALS else key
                out[name] = (Decimal(self.period["values"][key]), s["period_end"], file)
                prior = (s.get("comparative_printed") or {}).get(key)
                if prior is not None and s.get("comparative_period_end"):
                    out[name + COMPARATIVE] = (self._printed(key, prior, scale), s["comparative_period_end"], file)
        if not halted:
            for d in self.docs:
                if d["type"] in ("mrr_report", "bank_statement") and "figures" in d:
                    file, scale = Path(d["path"]).name, Decimal(d.get("scale", 1))
                    for key, figure in d["figures"].items():
                        name = BANK_KEYS.get(key, key) if d["type"] == "bank_statement" else key
                        out[name] = (self._printed(key, figure["printed"], scale), d["period_end"], file)
        if halted or stops_at_spreading:
            return out  # the cycle stops at intake or spreading; the other documents are not read
        if self.cert is not None:
            file = self._file("compliance_certificate")
            for covenant_id, entry in self.cert["reported"].items():
                if entry.get("value") is not None:  # "Not meaningful": the certificate prints text, not a figure
                    out[f"cert.{covenant_id}.value"] = (Decimal(entry["value"]), self.end.isoformat(), file)
                out[f"cert.{covenant_id}.threshold"] = (Decimal(entry["threshold"]), self.end.isoformat(), file)
                out[f"cert.{covenant_id}.in_compliance"] = (
                    Decimal(1 if entry["in_compliance"] else 0), self.end.isoformat(), file)
        if self.bb is not None:
            file = self._file("borrowing_base_certificate")
            for name, value in self.bb["certificate"].items():
                out[f"bbc.{BB_LINES.get(name, name)}"] = (Decimal(value), self.end.isoformat(), file)
            for n, row in enumerate(self.bb["ar_aging"], start=1):
                for theirs, ours in AR_BUCKETS.items():
                    out[f"bbc.ar.{n:03d}.{ours}"] = (Decimal(row["buckets"][theirs]), self.end.isoformat(), file)
                out[f"bbc.ar.{n:03d}.total"] = (Decimal(row["total"]), self.end.isoformat(), file)
            for n, row in enumerate(self.bb["inventory"], start=1):
                out[f"bbc.inventory.{n:03d}"] = (Decimal(row["amount"]), self.end.isoformat(), file)
        return out

    def _held_keys(self) -> set[str]:
        """The lines the scenario says the product holds for a person (a label the template does not
        know, a figure that may be the wrong measure). Read from the book's own scenario details."""
        if "spread.value_unverified" not in self.b.expected_exception_types():
            return set()
        details = self.b.truth["scenario"].get("details", {})
        held = {details.get("new_line", {}).get("belongs_to")}
        held |= {details.get("capitalised_software", {}).get(k) for k in ("balance_key", "spend_key")}
        return {k for k in held if k}

    def _file(self, doc_type: str) -> str:
        doc = next((d for d in self.docs if d["type"] == doc_type), None)
        return Path(doc["path"]).name if doc else ""

    @staticmethod
    def _printed(key: str, printed: str, scale: Decimal) -> Decimal:
        value = parse_printed(printed)
        if value is None:
            raise ValueError(f"the book prints {printed!r} for {key}, which is not a figure")
        sign = -1 if key in OUTFLOWS and not key.startswith(STATED) else 1
        return sign * value * scale

    # -- the truth for any fact the product stored --

    def value_for(self, fact: dict[str, Any]) -> Decimal | None:
        """The true value for this fact's key and period, or None when the book holds none."""
        key, end = fact["key"], fact["period_end"]
        expected = self.expected_facts(every_figure=True).get(key)
        if expected is not None and expected[1] == end:
            return expected[0]
        base = key[len(STATED):] if key.startswith(STATED) else key
        if COMPARATIVE in base or "~" in base:
            return None
        period = self.b.period(date.fromisoformat(end))
        if period is not None and base in period["values"]:
            return Decimal(period["values"][base])  # template lines and totals, any period on file
        parts = key.split(".")
        if parts[0] == "cov" and end == self.end.isoformat() and parts[1] in self.tests:
            test = self.tests[parts[1]]
            source = test if test.get("value") is not None else (test.get("after_repair") or {})
            name = {"value": "value", "threshold": "threshold", "headroom_pct": "headroom"}.get(parts[2])
            if name == "threshold":
                return _d(test.get("threshold"))
            return _d(source.get(name)) if name else None
        if key == "bb.availability":
            return self.availability(end)
        if parts[0] == "metric":
            return self.metric(parts[1], end)
        return None

    def availability(self, end: str) -> Decimal | None:
        review = self.b.expected_borrowing_base(date.fromisoformat(end))
        if review is not None:
            return Decimal(review["availability"])
        if any(f.get("borrowing_base") for f in self.b.truth["facilities"]):
            return None
        row = next((r for r in self.b.truth["system_of_record"] if r["date"] == end), None)
        if row is None or row.get("commitment") is None or row.get("revolver_outstanding") is None:
            return None
        return Decimal(row["commitment"]) - Decimal(row["revolver_outstanding"])

    def metric(self, name: str, end: str) -> Decimal | None:
        """The few review metrics that follow directly from the truth periods. The rest are
        not graded here (the book states no independent value for them)."""
        day = date.fromisoformat(end)
        period = self.b.period(day)
        if period is None:
            return None
        values = period["values"]
        if name == "cash":
            return Decimal(values["bs.cash"])
        if name == "total_debt":
            return sum((Decimal(values[k]) for k in ("bs.revolver", "bs.cpltd", "bs.long_term_debt",
                                                     "bs.subordinated_debt")), Decimal(0))
        if name in ("revenue_ttm", "net_income_ttm"):
            key = "is.revenue" if name == "revenue_ttm" else "is.net_income"
            if period["months"] == 12:
                return Decimal(values[key])
            prior_fye = self.b.period(date(day.year - 1, 12, 31))
            prior_ytd = self.b.period(date(day.year - 1, day.month, day.day))
            if prior_fye is None or prior_ytd is None:
                return None
            return Decimal(values[key]) + Decimal(prior_fye["values"][key]) - Decimal(prior_ytd["values"][key])
        return None


# ---- one borrower ---------------------------------------------------------------------------------


class _Pages:
    """Page text of the book's documents, read with PyMuPDF (not the product's index)."""

    def __init__(self, borrower: Borrower):
        self.dir = borrower.root / "documents" / borrower.code
        self._cache: dict[str, list[str]] = {}

    def text(self, file_name: str, page: int) -> str | None:
        if file_name not in self._cache:
            path = self.dir / file_name
            if not path.exists():
                self._cache[file_name] = []
            else:
                with pymupdf.open(path) as pdf:
                    self._cache[file_name] = [squash(p.get_text("text")) for p in pdf]
        pages = self._cache[file_name]
        return pages[page - 1] if 1 <= page <= len(pages) else None


def grade_borrower(borrower: Borrower, rec: dict[str, Any]) -> dict[str, Any]:
    truth = Truth(borrower)
    end = truth.end.isoformat()
    failures: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    def fail(name: str, item: str, detail: str) -> None:
        failures.append({"name": name, "item": item, "detail": detail})

    out: dict[str, Any] = {
        "borrower": borrower.code, "scenario": borrower.scenario, "error": rec.get("error"),
        "expected_exceptions": borrower.expected_exception_types()}
    if rec.get("error") or "cycle" not in rec:
        out.update({"stage_reached": None, "cycle_status": None, "raised_exceptions": [], "routine_approvals": [],
                    "failures": failures, "disagreements": [{"kind": "run-error", "item": borrower.code,
                                                             "detail": rec.get("error") or "no recording"}],
                    "observations": [], "extraction": _extraction_empty(len(truth.expected_facts())),
                    "covenants": {"expected": len(truth.tests), "correct": 0, "abstained": len(truth.tests)},
                    "needs_no_person": None, "stops": [], "agent_runs": [], "tokens": None, "ledger_ok": None,
                    "seconds": rec.get("seconds")})
        return out

    cycle = rec["cycle"]
    status = {s["stage"]: s["status"] for s in cycle["stages"]}
    failed_stages = [s for s in cycle["stages"] if s["status"] == "failed"]
    for s in failed_stages:
        disagreements.append({"kind": "stage-failed", "item": s["stage"], "detail": str(s["detail"].get("error"))})

    # ---- exceptions ----
    items = rec["work_items"]
    raised = sorted({w["type"] for w in items if w["type"] not in ROUTINE_ITEMS})
    routine = sorted({w["type"] for w in items if w["type"] in ROUTINE_ITEMS})
    expected = set(out["expected_exceptions"])
    open_blocking = {w["type"] for w in items if w["status"] == "open" and w["blocks_stage"]}
    # the cycle rests on a person for items the scenario expects, and nothing else is wrong
    resting_as_expected = (cycle["status"] == "open" and not failed_stages and bool(open_blocking)
                           and open_blocking <= expected and status.get(cycle["stage"]) == "needs_person")

    def reached(stage: str) -> bool:
        return status.get(stage) in ("done", "needs_person", "skipped") or (
            STAGES.index(cycle["stage"]) > STAGES.index(stage))

    not_reached: list[str] = []
    for kind in sorted(expected - set(raised)):
        stage = STAGE_OF_ITEM.get(kind.split(".")[0], "signals")
        if not reached(stage) and resting_as_expected:
            not_reached.append(kind)  # unmeasured, not missed: the cycle correctly waits before this stage
        else:
            fail("missed-exception", kind, f"expected for scenario {borrower.scenario}; the cycle rests at "
                                           f"{cycle['stage']} ({status.get(cycle['stage'])})")
    for kind in sorted(set(raised) - expected):
        titles = "; ".join(w["title"] for w in items if w["type"] == kind)[:300]
        fail("false-exception", kind, f"not expected for scenario {borrower.scenario}: {titles}")

    # ---- filing of the documents the cycle received ----
    for doc in rec.get("documents", []):
        meta = borrower.document_by_file(doc["file_name"])
        if meta is None or doc["doc_type"] is None:
            continue  # not filed: an intake exception covers it
        want_type = DOC_TYPES.get(meta["type"], meta["type"])
        got = (doc["doc_type"], doc["period_end"], doc.get("quality") if "statements" in want_type else None)
        want = (want_type, meta.get("period_end"), meta.get("quality") if "statements" in want_type else None)
        if got != want:
            disagreements.append({"kind": "document-filing", "item": doc["file_name"],
                                  "detail": f"filed as {got}, the truth is {want}"})

    # ---- facts ----
    expected_facts = truth.expected_facts()
    pages = _Pages(borrower)
    unreadable = set((truth.statements or {}).get("unreadable_keys", []))
    usable: dict[tuple[str, str], list[dict[str, Any]]] = {}
    ungraded = Counter()
    for fact in rec["facts"]:
        if fact["status"] not in USABLE:
            continue
        usable.setdefault((fact["key"], fact["period_end"]), []).append(fact)
        value, true_value = Decimal(fact["value"]), truth.value_for(fact)
        label = f"{fact['key']} @ {fact['period_end']}"
        base = fact["key"].removeprefix(STATED).replace(COMPARATIVE, "")
        if fact["kind"] == "extracted":
            text = pages.text(fact["document"] or "", fact["page"] or 0)
            if text is None or squash(fact["quote"] or "") not in text or (
                    fact["label"] and squash(fact["label"]) not in text):
                fail("wrong-citation", label, f"{fact['document']} page {fact['page']} does not print "
                                              f"{fact['quote']!r} with the label {fact['label']!r}")
            if base in truth.held and fact["period_end"] == end and COMPARATIVE not in fact["key"]:
                fail("missed-abstain", label, "the book expects this figure held for a person; the product stored it "
                                              "as verified")
            if base in unreadable and fact["period_end"] == end and COMPARATIVE not in fact["key"]:
                fail("missed-abstain", label, "the truth says this line cannot be read in the document received")
        if true_value is None:
            ungraded[fact["key"].split(".")[0]] += 1
        elif value != true_value:
            if fact["key"].startswith("cov.") and fact["key"].endswith(".threshold"):
                fail("stale-terms", label, f"threshold stored {value}, the terms in force give {true_value}")
            else:
                fail("invented-number", label, f"stored {value} ({fact['kind']}), truth {true_value}")

    correct = missing = wrong = 0
    by_document: dict[str, dict[str, int]] = {}
    for key, (true_value, period_end, file) in expected_facts.items():
        doc = by_document.setdefault(file, {"expected": 0, "correct": 0})
        doc["expected"] += 1
        stored = [f for f in usable.get((key, period_end), []) if f["kind"] == "extracted"]
        if not stored:
            missing += 1
        elif all(Decimal(f["value"]) == true_value for f in stored):
            correct += 1
            doc["correct"] += 1
        else:
            wrong += 1
    extraction = {"expected": len(expected_facts), "correct": correct, "missing": missing, "wrong": wrong,
                  "accuracy": _ratio(correct, len(expected_facts)),
                  "abstain_rate": _ratio(missing, len(expected_facts)), "by_document": by_document,
                  "ungraded_facts": dict(ungraded)}

    # ---- covenant tests ----
    tests = {t["covenant_id"]: t for t in rec["covenant_tests"] if t["period_end"] == end}
    all_fact_ids = set(rec.get("all_fact_ids", []))
    values_by_id = {f["id"]: Decimal(f["value"]) for f in rec["facts"]}
    covenants_correct = covenants_abstained = 0
    for covenant_id, want in truth.tests.items():
        got = tests.get(covenant_id)
        item = f"{covenant_id} @ {end}"
        if got is None or got["outcome"] == "cannot_test":
            if want["outcome"] == "cannot_test":
                covenants_correct += 1
            elif got is None and not reached("covenant_testing") and resting_as_expected:
                not_reached.append(f"covenant test {covenant_id}")
            else:
                covenants_abstained += 1
                fail("wrong-abstain", item, f"truth {want['outcome']} at {want.get('value')}; the product "
                                            + (f"cannot test: {got['error']}" if got else "recorded no test"))
            continue
        if want.get("value") is None and want.get("note"):
            # a not-meaningful measure (cash-flow-positive runway) has no number: any figure the
            # product holds for it was invented, whatever the reader said
            if got["value"] is not None or got.get("reported_value") is not None:
                fail("invented-number", item, f"the truth is '{want['note']}' (no figure); recorded value "
                                              f"{got['value']}, reported value {got.get('reported_value')}")
            for fact in rec["facts"]:
                if fact["period_end"] == end and fact["key"] in (f"cert.{covenant_id}.value", f"cov.{covenant_id}.value"):
                    fail("invented-number", item, f"a figure {fact['value']} is stored ({fact['key']}) where the truth is '{want['note']}'")
            if got.get("note") != want["note"]:
                disagreements.append({"kind": "covenant-outcome", "item": item,
                                      "detail": f"recorded note {got.get('note')!r}, truth {want['note']!r}"})
        if want["outcome"] == "cannot_test":
            fail("missed-abstain", item, f"recorded {got['outcome']} where the truth says the period cannot be tested")
            continue
        if got["outcome"] in PASSING and want["outcome"] in BREACHING:
            fail("false-compliant", item, f"recorded {got['outcome']} at {got['value']} against {got['threshold']}; "
                                          f"truth {want['outcome']} at {want['value']} against {want['threshold']}")
        elif got["outcome"] in BREACHING and want["outcome"] in PASSING:
            fail("false-breach", item, f"recorded {got['outcome']} at {got['value']} against {got['threshold']}; "
                                       f"truth {want['outcome']} at {want['value']} against {want['threshold']}")
        elif got["outcome"] == want["outcome"]:
            covenants_correct += 1
        else:
            disagreements.append({"kind": "covenant-outcome", "item": item,
                                  "detail": f"recorded {got['outcome']}, truth {want['outcome']}"})
        if got["terms_version"] != want["terms_version"] or got["terms_status"] not in ("approved", "superseded"):
            fail("stale-terms", item, f"tested under terms version {got['terms_version']} ({got['terms_status']}); "
                                      f"the truth tests under version {want['terms_version']}")
        elif _d(got["threshold"]) != Decimal(want["threshold"]):
            fail("stale-terms", item, f"threshold {got['threshold']}, the terms in force give {want['threshold']}")
        # a figure on the covenant table must be a stored fact
        for name, fact_name in (("value", "value_fact_id"), ("reported_value", "reported_fact_id")):
            if got[name] is None:
                continue
            fact_id = got[fact_name]
            if fact_id is None or fact_id not in all_fact_ids:
                fail("invented-number", item, f"the {name.replace('_', ' ')} {got[name]} is shown with no stored fact behind it")
            elif fact_id in values_by_id and values_by_id[fact_id] != Decimal(got[name]):
                fail("invented-number", item, f"the {name.replace('_', ' ')} {got[name]} differs from its fact ({values_by_id[fact_id]})")
    for covenant_id in sorted(set(tests) - set(truth.tests)):
        disagreements.append({"kind": "covenant-outcome", "item": f"{covenant_id} @ {end}",
                              "detail": "tested, but the truth expects no test of this covenant for the period"})

    # ---- borrowing base ----
    review = next((r for r in rec["borrowing_base"] if r["period_end"] == end), None)
    want_bb = truth.expected_bb if not truth.halted else None
    if want_bb is not None:
        if review is None or review["outcome"] == "cannot_compute":
            if review is None and not reached("borrowing_base") and resting_as_expected:
                not_reached.append("borrowing base review")
            else:
                fail("wrong-abstain", f"borrowing base @ {end}",
                     "the truth has a recalculated base; the product "
                     + ("could not compute one" if review else f"recorded no review (stage {status.get('borrowing_base')})"))
        else:
            for name, value in want_bb["calculated"].items():
                line = BB_LINES.get(name, name)
                ours = review["computed"].get(line)
                if ours is None or Decimal(ours) != Decimal(value):
                    disagreements.append({"kind": "borrowing-base-line", "item": f"{line} @ {end}",
                                          "detail": f"recalculated {ours}, truth {value}"})
            if (review["outcome"] == "over_advance") != bool(want_bb["over_advance"]):
                disagreements.append({"kind": "borrowing-base-outcome", "item": f"over-advance @ {end}",
                                      "detail": f"recorded {review['outcome']}, truth over_advance={want_bb['over_advance']}"})
            availability = [f for f in usable.get(("bb.availability", end), [])]
            if review["availability"] is not None and not any(
                    Decimal(f["value"]) == Decimal(review["availability"]) for f in availability):
                fail("invented-number", f"bb.availability @ {end}",
                     f"availability {review['availability']} is shown with no stored fact of that value")
    elif review is not None and truth.halted:
        fail("missed-abstain", f"borrowing base @ {end}", "a review was recorded for a cycle the truth says is halted")

    # ---- signals ----
    def signal_key(rule: str, covenant: Any, severity: str) -> tuple[str, str, str]:
        return (rule, str(covenant or ""), severity)

    want_signals = Counter(signal_key(s["rule"], (s.get("detail") or {}).get("covenant_id"), s["severity"])
                           for s in borrower.expected_signals(truth.end))
    got_signals = Counter(signal_key(s["rule_id"], (s.get("basis") or {}).get("covenant_id"), s["severity"])
                          for s in rec["signals"])
    signals_measured = status.get("signals") in ("done", "needs_person") or bool(rec["signals"])
    if signals_measured:
        for key in sorted(want_signals - got_signals):
            disagreements.append({"kind": "signal-missing", "item": " ".join(k for k in key if k),
                                  "detail": "expected by the truth, not fired"})
        for key in sorted(got_signals - want_signals):
            disagreements.append({"kind": "signal-unexpected", "item": " ".join(k for k in key if k),
                                  "detail": "fired, not expected by the truth"})
    elif want_signals and resting_as_expected:
        not_reached.append("signals")  # unmeasured: the cycle correctly waits on a person before this stage
    elif want_signals:
        disagreements.append({"kind": "signals-not-run", "item": f"signals @ {end}",
                              "detail": f"{sum(want_signals.values())} expected signal(s); the signals stage is "
                                        f"{status.get('signals')}"})
    untraced = 0
    for s in rec["signals"]:
        basis = s.get("basis") or {}
        linked = [str(i) for i in _fact_ids(basis) if i]
        for fact_id in linked:
            if fact_id.lower() not in all_fact_ids:
                fail("invented-number", f"signal {s['rule_id']}", f"its basis references fact {fact_id}, which is not a stored fact")
        loose = sum(1 for v in _basis_values(basis) if v.get("fact_id") is None)
        # a basis may carry its fact ids beside the values (metric_fact_ids) rather than on each one
        untraced += max(0, loose - len([i for i in (basis.get("metric_fact_ids") or {}).values() if i]))
    if untraced:
        observations.append({"kind": "untraced-figure", "item": "signal basis",
                             "detail": f"{untraced} figure(s) in signal bases carry no fact id"})

    # ---- text written by an agent and shown to a person ----
    unanswered: Counter = Counter()
    for run in rec["agent_runs"]:
        for note in run.get("guardrail_notes") or []:
            if isinstance(note, dict) and note.get("action") == "shown" and typed_figures(str(note.get("detail", ""))):
                fail("invented-number", f"{run['agent']} note", f"a note shown to a person types a figure: {note['detail']!r}"[:300])
        if run["status"] != "completed":
            if run["llm_mode"] == "standin" and run["agent"] in STANDIN_UNANSWERED:
                unanswered[run["agent"]] += 1  # the stand-in has no reader for this agent; not the product's abstain
            else:
                fail("wrong-abstain", f"{run['agent']} run", f"the run {run['status']}: {run.get('error') or 'no answer'}"[:300])
                if run["status"] == "failed":  # an error, not a model's answer: nothing was measured (gate: run-error)
                    disagreements.append({"kind": "run-error", "item": f"{run['agent']} run",
                                          "detail": run.get("error") or "the run failed"})
    for agent, count in sorted(unanswered.items()):
        observations.append({"kind": "standin-unanswered", "item": agent,
                             "detail": f"{count} {agent} call(s) were left unanswered by the stand-in; the product "
                                       "fell back without a recommendation or explanation"})
    # a recommendation to resolve a covenant exception where the truth is a true breach is the
    # same failure as a false "compliant": it tells a person the breach is not one
    for w in items:
        advice = (w.get("recommendation") or {}).get("recommendation")
        if w["type"] in ("covenant.breach", "covenant.reported_mismatch") and advice == "resolve":
            want = truth.tests.get(w.get("covenant_id") or "")
            if want is None or want["outcome"] in BREACHING:
                fail("false-compliant", f"recommendation on {w['type']} ({w.get('covenant_id')})",
                     "the Covenant Agent recommends resolve where the truth is a breach")
    for w in items:
        concern = str((w.get("evidence") or {}).get("agent_concern") or "")
        if typed_figures(concern):
            fail("invented-number", f"{w['type']} concern", f"an agent concern shown to a person types a figure: {concern!r}"[:300])
    for c in (rec.get("review") or {}).get("commentary", []):
        if c["author_type"] != "agent" or c["status"] == "superseded":
            continue
        where = f"commentary {c['section']} v{c['version']}"
        for ref in _REF.findall(c["body"]):
            if ref.lower() not in all_fact_ids:
                fail("invented-number", where, f"references fact {ref}, which is not a stored fact")
        figures = typed_figures(c["body"])
        if figures:
            fail("invented-number", where, f"types figure(s) {figures[:5]} instead of referencing facts")
    for s in rec["signals"]:
        text = str((s.get("explanation") or {}).get("text") or "")
        if typed_figures(text):
            fail("invented-number", f"signal {s['rule_id']} explanation", "the explanation types a figure")

    # ---- summary ----
    exceptional = [w for w in items if w["type"] not in ROUTINE_ITEMS]
    last_done = cycle.get("last_stage_done")
    tokens = None
    if any(r["llm_mode"] != "standin" for r in rec["agent_runs"]):
        tokens = {"input": sum(r["input_tokens"] for r in rec["agent_runs"]),
                  "output": sum(r["output_tokens"] for r in rec["agent_runs"]),
                  "cache_read": sum(r["cache_read_tokens"] for r in rec["agent_runs"])}
    if rec.get("ledger") and not rec["ledger"]["ok"]:
        disagreements.append({"kind": "ledger", "item": "hash chain", "detail": str(rec["ledger"]["problem"])})
    out.update({
        "stage_reached": cycle["stage"], "stage_status": status.get(cycle["stage"]), "cycle_status": cycle["status"],
        "last_stage_done": last_done, "raised_exceptions": raised, "routine_approvals": routine,
        "not_reached": not_reached, "failures": failures, "disagreements": disagreements,
        "observations": observations, "extraction": extraction,
        "covenants": {"expected": len(truth.tests), "correct": covenants_correct, "abstained": covenants_abstained},
        "needs_no_person": not exceptional,
        "stops": rec.get("stops", []),
        "agent_runs": [{"agent": r["agent"], "status": r["status"], "llm_mode": r["llm_mode"],
                        "served_model": r["served_model"], "guardrail_notes": r["guardrail_notes"]}
                       for r in rec["agent_runs"]],
        "held_cells": held_cells(items), "unshown_text": unshown_text(rec),
        "tokens": tokens, "ledger_ok": (rec.get("ledger") or {}).get("ok"), "seconds": rec.get("seconds")})
    return out


def held_cells(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each figure the product held for a person, with the reason, from the work items' evidence."""
    out = []
    for w in items:
        for cell in (w.get("evidence") or {}).get("cells") or []:
            if isinstance(cell, dict):
                out.append({"item": w.get("type"), "key": cell.get("key"), "printed_label": cell.get("printed_label"),
                            "row_label": cell.get("row_label"), "reason": cell.get("reason"),
                            "page": cell.get("page")})
    return out


def _output_payloads(content: list[dict[str, Any]]) -> list[Any]:
    payloads: list[Any] = []
    for block in content:
        if block.get("type") == "tool_use":
            payloads.append(block.get("input"))
        elif block.get("type") == "text":
            try:
                payloads.append(json.loads(block.get("text") or ""))
            except ValueError:
                payloads.append(block.get("text") or "")
    return payloads


_PROSE_FIELDS = re.compile(r"note|concern|explanation|reason|rationale|comment|summary|missing_evidence", re.I)


def _prose(value: Any, inside: bool = False) -> list[str]:
    """Free text an agent wrote in its answer: strings under a field whose name says it is prose
    (notes, a concern, an explanation), at any depth. Row labels, bucket names, printed figures
    and line keys sit under other fields and are not prose the agent wrote."""
    if isinstance(value, str):
        return [value] if inside and len(value.split()) >= 4 else []  # a label or an id is not a sentence
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in _prose(v, inside or bool(_PROSE_FIELDS.search(str(k))))]
    if isinstance(value, list):
        return [s for v in value for s in _prose(v, inside)]
    return []


def unshown_text(rec: dict[str, Any]) -> list[dict[str, Any]]:
    """Prose the model wrote that no person was shown: notes and concerns in the raw answer whose
    text is not among the run's shown notes. Kept in the evaluation's results only."""
    shown = {str(n.get("detail", "")).strip() for r in rec.get("agent_runs") or []
             for n in (r.get("guardrail_notes") or []) if isinstance(n, dict) and n.get("action") == "shown"}
    out = []
    for o in rec.get("model_outputs") or []:
        agent = (o.get("record_key") or "").split("/", 1)[0]
        for payload in _output_payloads(o.get("content") or []):
            for text in _prose(payload) if not isinstance(payload, str) else []:
                if text.strip() not in shown:
                    out.append({"agent": agent, "record_key": o.get("record_key"), "text": text,
                                "typed_figures": typed_figures(text)})
    return out


def _basis_values(basis: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(basis, dict):
        if "value" in basis and "fact_id" in basis:
            found.append(basis)
        for value in basis.values():
            found.extend(_basis_values(value))
    elif isinstance(basis, list):
        for value in basis:
            found.extend(_basis_values(value))
    return found


def _fact_ids(basis: Any) -> list[Any]:
    found = []
    if isinstance(basis, dict):
        for key, value in basis.items():
            if key == "fact_id":
                found.append(value)
            elif key.endswith("fact_ids") and isinstance(value, dict):
                found.extend(value.values())
            elif key.endswith("fact_ids") and isinstance(value, list):
                found.extend(value)
            else:
                found.extend(_fact_ids(value))
    elif isinstance(basis, list):
        for value in basis:
            found.extend(_fact_ids(value))
    return found


def _ratio(numerator: int, denominator: int) -> float | None:
    """A share, or None when there is nothing to measure. Never zero for 'unmeasured'."""
    return None if denominator == 0 else round(numerator / denominator, 4)


def _extraction_empty(expected: int) -> dict[str, Any]:
    return {"expected": expected, "correct": 0, "missing": expected, "wrong": 0, "accuracy": _ratio(0, expected),
            "abstain_rate": _ratio(expected, expected), "by_document": {}, "ungraded_facts": {}}


# ---- a pass, the gate, the results document -----------------------------------------------------------


def grade_pass(book: Book, recordings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    borrowers = {b.code: grade_borrower(b, recordings[b.code]) for b in book if b.code in recordings}
    counts = dict.fromkeys(FAILURES, 0)
    for graded in borrowers.values():
        for failure in graded["failures"]:
            counts[failure["name"]] += 1
    expected_pairs = {(c, t) for c, g in borrowers.items() for t in g["expected_exceptions"]}
    raised_pairs = {(c, t) for c, g in borrowers.items() for t in g["raised_exceptions"]}
    unmeasured_pairs = {(c, t) for c, g in borrowers.items() for t in g.get("not_reached", [])}
    measured_expected = expected_pairs - unmeasured_pairs
    hits = len(measured_expected & raised_pairs)
    facts_expected = sum(g["extraction"]["expected"] for g in borrowers.values())
    facts_correct = sum(g["extraction"]["correct"] for g in borrowers.values())
    facts_missing = sum(g["extraction"]["missing"] for g in borrowers.values())
    tests_expected = sum(g["covenants"]["expected"] for g in borrowers.values())
    measured_cycles = [g for g in borrowers.values() if g["needs_no_person"] is not None]
    token_rows = [g["tokens"] for g in borrowers.values() if g["tokens"]]
    metrics = {
        "extraction_accuracy": _ratio(facts_correct, facts_expected),
        "extraction_facts_expected": facts_expected, "extraction_facts_correct": facts_correct,
        "extraction_abstain_rate": _ratio(facts_missing, facts_expected),
        "cycles_needing_no_person": _ratio(sum(1 for g in measured_cycles if g["needs_no_person"]), len(measured_cycles)),
        "cycles_expected_to_need_no_person": _ratio(sum(1 for g in borrowers.values() if not g["expected_exceptions"]),
                                                    len(borrowers)),
        "exception_precision": _ratio(len(raised_pairs & expected_pairs), len(raised_pairs)),
        "exception_recall": _ratio(hits, len(measured_expected)),
        "covenant_outcome_accuracy": _ratio(sum(g["covenants"]["correct"] for g in borrowers.values()), tests_expected),
        "covenant_abstain_rate": _ratio(sum(g["covenants"]["abstained"] for g in borrowers.values()), tests_expected),
        "cycles_run": len(borrowers), "cycles_closed": sum(1 for g in borrowers.values() if g["cycle_status"] == "closed"),
        "cycles_reaching_signals": sum(1 for g in borrowers.values()
                                       if g["stage_reached"] and STAGES.index(g["stage_reached"]) >= STAGES.index("signals")),
        "disagreements": sum(len(g["disagreements"]) for g in borrowers.values()),
        "input_tokens": sum(t["input"] for t in token_rows) if token_rows else None,
        "output_tokens": sum(t["output"] for t in token_rows) if token_rows else None,
    }
    return {"borrowers": borrowers, "failure_counts": counts, "metrics": metrics}


def load_known_findings(path: Path = KNOWN_FINDINGS) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("findings", [])


def _finding_keys(graded: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Every difference found for one borrower as (borrower, name, item)."""
    keys = [(graded["borrower"], f["name"], f["item"]) for f in graded["failures"]]
    keys += [(graded["borrower"], d["kind"], d["item"]) for d in graded["disagreements"]]
    extraction = graded["extraction"]
    if extraction["expected"] and extraction["correct"] != extraction["expected"]:
        keys.append((graded["borrower"], "extraction-incomplete", "facts expected"))
    return keys


def evaluate_gate(passes: list[dict[str, Any]], *, mode: str, known: list[dict[str, Any]] | None = None,
                  complete_book: bool = True) -> dict[str, Any]:
    """The gate is checked on every pass separately: one bad pass fails the build."""
    known = known or []
    known_keys = {(k["borrower"], k["name"], k["item"]) for k in known if k["name"] not in GATED}
    reasons: list[str] = []
    unexplained: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    run_errors: list[dict[str, Any]] = []
    nothing_read: list[dict[str, Any]] = []
    for n, graded_pass in enumerate(passes, start=1):
        for name in GATED:
            count = graded_pass["failure_counts"][name]
            if count:
                reasons.append(f"pass {n}: {count} {name}")
        for graded in graded_pass["borrowers"].values():
            # a cycle that failed on an error is never a pass, in any mode, and no known finding excuses it
            for d in graded["disagreements"]:
                if d["kind"] in ("run-error", "stage-failed"):
                    run_errors.append({"pass": n, "borrower": graded["borrower"], "stage": d["item"],
                                       "message": str(d["detail"])[:300]})
        if mode != "standin":
            # a borrower expected to have facts, with none read at all, is an empty run (an honest abstention
            # on one fact is not gated: it shows in extraction accuracy)
            for graded in graded_pass["borrowers"].values():
                ext = graded["extraction"]
                if ext["expected"] and ext["missing"] >= ext["expected"]:
                    nothing_read.append({"pass": n, "borrower": graded["borrower"], "expected": ext["expected"]})
            continue
        for graded in graded_pass["borrowers"].values():
            for key in _finding_keys(graded):
                seen.add(key)
                if key[1] in GATED or key in known_keys:
                    continue
                unexplained.append({"pass": str(n), "borrower": key[0], "name": key[1], "item": key[2]})
    if run_errors:
        shown = "; ".join(f"{e['borrower']} ({e['stage']}): {e['message']}" for e in run_errors[:3])
        reasons.insert(0, f"run-error: {len(run_errors)} cycle(s) failed on an error, so nothing was measured. "
                          f"First: {shown}")
    if nothing_read:
        reasons.append(f"nothing-read: {len(nothing_read)} borrower(s) expected to have facts had none read: "
                       + ", ".join(f"{e['borrower']} (0 of {e['expected']})" for e in nothing_read[:5]))
    if mode == "standin" and unexplained:
        reasons.append(f"the stand-in suite does not agree with the truth in full: {len(unexplained)} difference(s) "
                       "not listed as known findings")
    stale = sorted(known_keys - seen) if mode == "standin" and complete_book else []
    if stale:
        reasons.append(f"{len(stale)} known finding(s) no longer occur; remove them from evals/known_findings.json: "
                       + "; ".join("/".join(k) for k in stale[:5]))
    return {"passed": not reasons, "reasons": reasons, "run_errors": run_errors, "nothing_read": nothing_read,
            "rule": ("any invented-number or false-compliant in any pass fails; the stand-in suite must also agree "
                     "with the truth in full, apart from listed known findings" if mode == "standin" else
                     "any invented-number or false-compliant in any pass fails; any cycle that failed on an error "
                     "fails; a borrower with expected facts and none read (nothing-read) fails; other accuracy is reported, not gated"),
            "known_findings_applied": sorted("/".join(k) for k in known_keys & seen),
            "unexplained": unexplained, "stale_known_findings": ["/".join(k) for k in stale]}


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def build_results(book: Book, recordings_by_pass: list[dict[str, dict[str, Any]]], *, mode: str, decide: bool,
                  seconds: float | None = None, standin_disagreements: list[dict[str, Any]] | None = None,
                  unsigned_oracle_rows: int | None = None, scope: list[str] | None = None,
                  known: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from evals.run import STANDIN_LABEL, SUITE

    passes = [grade_pass(book, recordings) for recordings in recordings_by_pass]
    known = load_known_findings() if known is None else known
    in_scope = [k for k in known if book.get(k["borrower"]) is not None]
    gate = evaluate_gate(passes, mode=mode, known=in_scope, complete_book=True)
    first = passes[0]
    return {
        "meta": {
            "suite": SUITE, "mode": mode, "standin": mode == "standin",
            "label": STANDIN_LABEL if mode == "standin" else f"Mode {mode}: answers came from "
            + ("recorded model responses." if mode == "recorded" else "a live model."),
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "commit": _commit(),
            "borrowers": len(book), "scope": scope or "whole book", "decide": decide, "passes": len(passes),
            "seconds": seconds, "unsigned_oracle_rows": unsigned_oracle_rows,
            "standin_print_vs_truth_disagreements": standin_disagreements or []},
        "gate": gate, "metrics": first["metrics"], "failure_counts": first["failure_counts"],
        "borrowers": first["borrowers"], "known_findings": in_scope,
        "passes": [{"metrics": p["metrics"], "failure_counts": p["failure_counts"]} for p in passes],
    }

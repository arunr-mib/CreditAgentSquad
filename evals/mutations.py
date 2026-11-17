"""Mutation checks: prove the product's guardrails and the grader are not asleep.

Each mutation tampers with the stand-in reader's answer in one specific way a real model could
get wrong, runs the live cycle, and records who caught it:

  product   the product refused it: a work item or a guardrail note that the untampered run
            does not have
  grader    the grader named a failure (or a disagreement with the truth) that the untampered
            run does not have, beyond the echo of the product's own refusal
  SLIPPED   neither. That is a real finding about the product and the grader; it is reported,
            never patched away here.

`EXPECTED` records what each mutation was seen to do when this file was written, so the test
suite notices when a guardrail stops catching something (or starts to).
"""
import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Engine

from evals.book import Book
from evals.grade import grade_borrower
from evals.standin import StandInReader

ECHO = frozenset({"false-exception", "wrong-abstain", "extraction-incomplete"})  # the product's refusal, seen by the grader
Answer = dict[str, Any]


@dataclass(frozen=True)
class Mutation:
    name: str
    what: str  # what the tampered reader gets wrong, in plain words
    borrower: str
    agent: str
    change: Callable[[Answer], Answer]


def _cell(answer: Answer, key: str, column: str = "cells") -> dict[str, Any]:
    return next(c for c in answer[column] if c["key"] == key)


def _bump(figure: str) -> str:
    """Change the last digit, keeping the figure well formed."""
    index = max(i for i, ch in enumerate(figure) if ch.isdigit())
    return figure[:index] + str((int(figure[index]) + 1) % 10) + figure[index + 1:]


# ---- spreading -------------------------------------------------------------------------------


def wrong_figure(answer: Answer) -> Answer:
    cell = _cell(answer, "is.revenue")
    cell["printed_figure"] = _bump(cell["printed_figure"])
    return answer


def figure_from_another_row(answer: Answer) -> Answer:
    _cell(answer, "is.revenue")["printed_figure"] = _cell(answer, "is.cogs")["printed_figure"]
    return answer


def prior_year_figure(answer: Answer) -> Answer:
    _cell(answer, "is.revenue")["printed_figure"] = _cell(answer, "is.revenue", "comparative_cells")["printed_figure"]
    return answer


def whole_prior_year_column(answer: Answer) -> Answer:
    answer["cells"] = copy.deepcopy(answer["comparative_cells"])
    answer["comparative_cells"] = []
    return answer


def dropped_line(answer: Answer) -> Answer:
    answer["cells"] = [c for c in answer["cells"] if c["key"] != "bs.inventory"]
    answer["absent_keys"] = sorted({*answer["absent_keys"], "bs.inventory"})
    return answer


def dropped_line_and_its_totals(answer: Answer) -> Answer:
    gone = {"bs.other_current_assets", "stated.bs.total_current_assets", "stated.bs.total_assets"}
    answer["cells"] = [c for c in answer["cells"] if c["key"] not in gone]
    answer["absent_keys"] = sorted({*answer["absent_keys"], "bs.other_current_assets"})
    return answer


def dropped_supplemental_line(answer: Answer) -> Answer:
    answer["cells"] = [c for c in answer["cells"] if c["key"] != "sup.cash_taxes_paid"]
    answer["absent_keys"] = sorted({*answer["absent_keys"], "sup.cash_taxes_paid"})
    return answer


def units_phrase_omitted(answer: Answer) -> Answer:
    answer["scale_statement"], answer["scale_page"] = "", 0
    return answer


def units_phrase_invented(answer: Answer) -> Answer:
    answer["scale_statement"] = "(in thousands of U.S. dollars)"
    return answer


def rows_mapped_to_each_others_lines(answer: Answer) -> Answer:
    a, b = _cell(answer, "bs.accounts_payable"), _cell(answer, "bs.accrued_liabilities")
    a["key"], b["key"] = "bs.accrued_liabilities", "bs.accounts_payable"
    return answer


def debt_row_mapped_to_a_payable(answer: Answer) -> Answer:
    a, b = _cell(answer, "bs.revolver"), _cell(answer, "bs.accounts_payable")
    a["key"], b["key"] = "bs.accounts_payable", "bs.revolver"
    return answer


def note_types_a_figure(answer: Answer) -> Answer:
    answer["notes"] = [*answer["notes"], "Net sales rose to 74,118 for the period."]
    return answer


# ---- compliance certificate ---------------------------------------------------------------------


def _row(answer: Answer, covenant_id: str) -> dict[str, Any]:
    return next(r for r in answer["rows"] if r["covenant_id"] == covenant_id)


def certificate_claims_compliance(answer: Answer) -> Answer:
    row = next(r for r in answer["rows"] if r["compliance_printed"] == "No")
    row["compliance_printed"] = "Yes"
    return answer


def breach_reported_as_a_passing_value(answer: Answer) -> Answer:
    row = next(r for r in answer["rows"] if r["compliance_printed"] == "No")
    row["actual_printed"], row["compliance_printed"] = "1.25x", "Yes"
    return answer


def misread_threshold(answer: Answer) -> Answer:
    row = _row(answer, "fccr")
    row["required_printed"] = row["required_printed"].replace("1.05x", "1.50x")
    return answer


def threshold_from_another_row(answer: Answer) -> Answer:
    _row(answer, "fccr")["required_printed"] = _row(answer, "total_leverage")["required_printed"]
    return answer


def certificate_units_omitted(answer: Answer) -> Answer:
    answer["scale_statement"], answer["scale_page"] = "", 0
    return answer


def certificate_rows_swapped(answer: Answer) -> Answer:
    a, b = _row(answer, "fccr"), _row(answer, "total_leverage")
    a["covenant_id"], b["covenant_id"] = "total_leverage", "fccr"
    return answer


# ---- borrowing base certificate -------------------------------------------------------------------


def aging_note_dropped(answer: Answer) -> Answer:
    next(r for r in answer["aging_rows"] if r["note_printed"] == "Affiliate")["note_printed"] = ""
    return answer


def aging_figure_misread(answer: Answer) -> Answer:
    row = answer["aging_rows"][0]
    row["figures_printed"][0] = _bump(row["figures_printed"][0])
    return answer


def aging_row_dropped(answer: Answer) -> Answer:
    answer["aging_rows"] = answer["aging_rows"][1:]
    return answer


def certificate_line_misnamed(answer: Answer) -> Answer:
    a = next(line for line in answer["certificate_lines"] if line["line"] == "outstanding")
    b = next(line for line in answer["certificate_lines"] if line["line"] == "commitment")
    a["line"], b["line"] = "commitment", "outstanding"
    return answer


# ---- intake ---------------------------------------------------------------------------------------


def _document(answer: Answer, doc_type: str) -> dict[str, Any]:
    return next(d for d in answer["documents"] if d["doc_type"] == doc_type)


def misclassified_document(answer: Answer) -> Answer:
    _document(answer, "compliance_certificate")["doc_type"] = "interim_statements"
    return answer


def statements_called_audited(answer: Answer) -> Answer:
    _document(answer, "interim_statements")["quality"] = "audited"
    return answer


def certificate_dated_by_its_signing_date(answer: Answer) -> Answer:
    _document(answer, "compliance_certificate")["period_end_text"] = "November 7, 2026"
    return answer


# ---- review commentary ------------------------------------------------------------------------------


def commentary_types_a_figure(answer: Answer) -> Answer:
    section = next(s for s in answer["sections"] if s["section"] == "performance")
    section["body"] += " Net sales were 74,118 for the period."
    return answer


def commentary_cites_an_unknown_fact(answer: Answer) -> Answer:
    section = next(s for s in answer["sections"] if s["section"] == "covenants")
    section["body"] += " Liquidity stood at {{fact:00000000-0000-4000-8000-000000000000}}."
    return answer


CLEAN_BB = "harrowgate-precision"  # clean, statements in thousands, borrowing base, a dollar covenant
REPORTED_BREACH = "pellham-grain"  # fixed charge coverage fails and the certificate says so
DOLLARS = "sablewood-dental"  # clean, statements in whole dollars
HIDDEN_BREACH = "kestrel-bay-packaging"  # leverage fails; the certificate claims compliance

MUTATIONS: tuple[Mutation, ...] = (
    Mutation("spread-wrong-figure", "a figure with one digit wrong (it still parses)", CLEAN_BB, "spreading", wrong_figure),
    Mutation("spread-figure-from-another-row", "a real figure from the wrong row", CLEAN_BB, "spreading", figure_from_another_row),
    Mutation("spread-prior-year-figure", "a figure from the prior-year column under the current header", CLEAN_BB, "spreading", prior_year_figure),
    Mutation("spread-whole-prior-year-column", "the whole prior-year column spread as the period", CLEAN_BB, "spreading", whole_prior_year_column),
    Mutation("spread-dropped-line", "a printed line dropped and claimed absent", CLEAN_BB, "spreading", dropped_line),
    Mutation("spread-dropped-line-and-totals", "a line dropped together with the printed totals above it", CLEAN_BB, "spreading", dropped_line_and_its_totals),
    Mutation("spread-dropped-supplemental-line", "a supplemental line (no total covers it) dropped and claimed absent", CLEAN_BB, "spreading", dropped_supplemental_line),
    Mutation("spread-units-omitted", "the 'in thousands' phrase not reported", CLEAN_BB, "spreading", units_phrase_omitted),
    Mutation("spread-units-invented", "an 'in thousands' phrase reported for a statement in whole dollars", DOLLARS, "spreading", units_phrase_invented),
    Mutation("spread-rows-swapped-within-a-total", "two rows of one subtotal mapped to each other's template lines", CLEAN_BB, "spreading", rows_mapped_to_each_others_lines),
    Mutation("spread-debt-mapped-to-payables", "the line of credit and accounts payable mapped to each other's lines", CLEAN_BB, "spreading", debt_row_mapped_to_a_payable),
    Mutation("spread-debt-mapped-to-payables-on-a-breach", "the same mis-mapping on a borrower whose leverage fails", HIDDEN_BREACH, "spreading", debt_row_mapped_to_a_payable),
    Mutation("spread-note-types-a-figure", "a note that types a figure", CLEAN_BB, "spreading", note_types_a_figure),
    Mutation("cert-claims-compliance", "a certificate read as claiming compliance where it reports a breach", REPORTED_BREACH, "certificate", certificate_claims_compliance),
    Mutation("cert-breach-read-as-passing-value", "the breaching covenant's reported value read as a passing one", REPORTED_BREACH, "certificate", breach_reported_as_a_passing_value),
    Mutation("cert-misread-threshold", "a threshold misread (1.05x read as 1.50x)", CLEAN_BB, "certificate", misread_threshold),
    Mutation("cert-threshold-from-another-row", "a threshold taken from another covenant's row", CLEAN_BB, "certificate", threshold_from_another_row),
    Mutation("cert-units-omitted", "the certificate's 'in thousands' phrase not reported", CLEAN_BB, "certificate", certificate_units_omitted),
    Mutation("cert-rows-swapped", "two covenant rows attributed to each other's covenants", CLEAN_BB, "certificate", certificate_rows_swapped),
    Mutation("bb-aging-note-dropped", "an affiliate customer's note not reported", CLEAN_BB, "collateral", aging_note_dropped),
    Mutation("bb-aging-figure-misread", "an aging figure with one digit wrong", CLEAN_BB, "collateral", aging_figure_misread),
    Mutation("bb-aging-row-dropped", "a customer left out of the aging", CLEAN_BB, "collateral", aging_row_dropped),
    Mutation("bb-lines-misnamed", "commitment and loans outstanding attributed to each other's lines", CLEAN_BB, "collateral", certificate_line_misnamed),
    Mutation("intake-misclassified", "a compliance certificate classified as interim statements", CLEAN_BB, "intake", misclassified_document),
    Mutation("intake-statements-called-audited", "management statements classified as audited", CLEAN_BB, "intake", statements_called_audited),
    Mutation("intake-wrong-period", "a certificate filed by its signing date instead of its period end", CLEAN_BB, "intake", certificate_dated_by_its_signing_date),
    Mutation("review-types-a-figure", "commentary that types a figure", CLEAN_BB, "review", commentary_types_a_figure),
    Mutation("review-cites-unknown-fact", "commentary that references a fact that does not exist", CLEAN_BB, "review", commentary_cites_an_unknown_fact),
)
BY_NAME = {m.name: m for m in MUTATIONS}


def _differences(graded: dict[str, Any]) -> set[tuple[str, str]]:
    found = {(f["name"], f["item"]) for f in graded["failures"]}
    found |= {(d["kind"], d["item"]) for d in graded["disagreements"]}
    return found


def _notes(graded: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {(r["agent"], str(n.get("check")), str(n.get("action"))) for r in graded["agent_runs"]
            for n in (r.get("guardrail_notes") or []) if isinstance(n, dict) and n.get("action") != "shown"}


def classify(baseline: dict[str, Any], graded: dict[str, Any]) -> dict[str, Any]:
    """Who caught the tampering, judged against the untampered run of the same borrower."""
    new_items = sorted(set(graded["raised_exceptions"]) - set(baseline["raised_exceptions"]))
    new_notes = sorted(_notes(graded) - _notes(baseline))
    new_differences = sorted(_differences(graded) - _differences(baseline))
    by_grader = [d for d in new_differences if d[0] not in ECHO]
    product, grader = bool(new_items or new_notes), bool(by_grader)
    caught = "product and grader" if product and grader else "product" if product else "grader" if grader else "SLIPPED"
    evidence = []
    if new_items:
        evidence.append("work item: " + ", ".join(new_items))
    if new_notes:
        evidence.append("guardrail note: " + ", ".join(f"{a} {c} -> {x}" for a, c, x in new_notes))
    if by_grader:
        evidence.append("grader: " + ", ".join(f"{name} [{item}]" for name, item in by_grader[:4])
                        + (f" and {len(by_grader) - 4} more" if len(by_grader) > 4 else ""))
    return {"caught_by": caught, "product": product, "grader": grader, "new_work_items": new_items,
            "new_guardrail_notes": [list(n) for n in new_notes], "grader_names": sorted({d[0] for d in by_grader}),
            "evidence": "; ".join(evidence) or "nothing changed: the tampered answer was accepted and graded clean",
            "stage_reached": graded.get("stage_reached"), "error": graded.get("error")}


def run_mutations(engine: Engine, book: Book, names: list[str] | None = None, *, decide: bool = True,
                  progress: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    """Run each mutation against its borrower. A borrower is loaded once; every run starts from
    that same loaded state and is rolled back."""
    from evals.run import LoadedBorrower

    wanted = [BY_NAME[n] for n in names] if names else list(MUTATIONS)
    outcomes = []
    for code in dict.fromkeys(m.borrower for m in wanted):
        borrower = book.get(code)
        if borrower is None:
            raise KeyError(f"{code} is not in the book in scope")
        with LoadedBorrower(engine, book, borrower) as loaded:
            clean_reader = StandInReader(book)
            baseline = grade_borrower(borrower, loaded.run(lambda r=clean_reader: r, decide=decide))
            for mutation in (m for m in wanted if m.borrower == code):
                applied: list[str] = []

                def tamper(agent, answer, context, mutation=mutation, applied=applied):
                    if agent != mutation.agent:
                        return answer
                    applied.append(context["record_key"])
                    return mutation.change(copy.deepcopy(answer))

                reader = StandInReader(book, tamper=tamper)
                graded = grade_borrower(borrower, loaded.run(lambda r=reader: r, decide=decide))
                outcome = {"name": mutation.name, "what": mutation.what, "borrower": code, "agent": mutation.agent,
                           "applied": bool(applied), **classify(baseline, graded)}
                if not applied:
                    outcome["caught_by"] = "NOT APPLIED"
                    outcome["evidence"] = f"the {mutation.agent} agent was never asked, so nothing was tampered with"
                outcomes.append(outcome)
                if progress:
                    progress(f"{mutation.name:38s} {code:22s} {outcome['caught_by']:20s} {outcome['evidence'][:150]}")
    return outcomes

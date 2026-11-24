"""A note may point at a place in the document only if the code-built structure says it exists."""
import json
import pathlib

import pytest
from app.guardrails.narrative import DocumentStructure, References, check_narrative

ST = DocumentStructure(page_count=5, note_numbers=frozenset({1}), endings=frozenset({"9001", "9002"}),
                       years=frozenset({2025, 2026}))
EVALS = pathlib.Path(__file__).resolve().parents[3] / "evals"
ROOT = EVALS / "recordings" / "spreading"
# recordings of the clients renamed on 22 Nov are archived, not replayed; their wording is still real model text
ARCHIVE = EVALS / "recordings-archive" / "renamed-2026-11-22"


def ok(text, st=ST, echo=""):
    return check_narrative(text, {}, structure=st, echo=echo) == []


@pytest.mark.parametrize("text", [
    "Note 1 on page 5 (capitalised software roll-forward) covers only the single month.",
    "Page 5 (Note 1 - Capitalised software) is a month-only rollforward.",
    "Debt schedule rows on page 5 have no separate template line.",
    "Dividends paid on page 4 is mapped to cf.distributions.",
    "The collateral account (ending 9001) is pledged.",
    "The statement for October 1 to October 31, 2026 is a bank statement.",
    "Covers the nine months ended September 30, 2026 with a nine-month 2025 comparative.",
    "Only the two bank lines are reported; the two bank account total lines too.",
    "See page 2 for the equity components.",
    "(page 3) shows the balance sheet.",
])
def test_honest_notes_pass(text):
    assert ok(text)


@pytest.mark.parametrize("text", [
    "Leverage on page 5 was high.",
    "Total leverage on page 5.",
    "Note 4.25 is the ratio.",
    "Note 2 on page 5 is odd.",          # no such note heading
    "Debt on page 6 is large.",          # above the page count
    "Debt schedule on page 5x was fine.",
    "The account (ending 4.25%) is fine.",
    "Ending 125000 is the rollforward.",   # six digits: an amount, not an account mask
    "The account (ending 1234) is fine.",  # not printed in the document
    "Coverage was two times coverage.",
    "EBITDA was 2025 in the nine months.",
    "Revenue of 2026 on page 5.",
])
def test_figure_carriers_still_refused(text):
    assert not ok(text)


def test_without_structure_nothing_is_allowed():
    assert check_narrative("Note 1 on page 5 is a rollforward.", {}) != []


def test_units_phrase_passes_by_echo_only():
    t = "The cover page states units as 'In thousands of u.s. dollars'."
    assert not ok(t)
    assert ok(t, echo="In thousands of U.S. dollars")


def test_structure_from_pages():
    st = DocumentStructure.from_pages(["Cover 2025", "x", "Note 1 - Software\nrows", "Account ending 9001 total 2026"])
    assert st.page_count == 4 and st.note_numbers == {1} and "9001" in st.endings and st.years == {2025, 2026}


def _recorded_notes():
    for p in sorted([*ROOT.rglob("*.json"), *(ARCHIVE / "spreading").rglob("*.json")]):
        d = json.loads(p.read_text())
        for block in d.get("content", []):
            inp = block.get("input") if block.get("type") == "tool_use" else None
            if inp is None and block.get("type") == "text":
                try:
                    inp = json.loads(block["text"])
                except Exception:
                    continue
            if isinstance(inp, dict):
                yield from inp.get("notes", [])


def test_recorded_notes_all_pass_with_the_structure_of_their_documents():
    st = DocumentStructure(5, frozenset({1}), frozenset({"9001", "9002"}), frozenset({2025, 2026}))
    notes = list(_recorded_notes())
    assert len(notes) >= 200
    failing = [n for n in notes
               if check_narrative(n, {}, structure=st,
                                  echo="In thousands of U.S. dollars (in thousands)")]
    # One note of the 23 Nov re-record names a page range. The guardrail refuses the two page numbers and the product
    # dropped the note (evals/results/rerecord-2026-11-23-batch1). Pinned as refused, not excused: whether a range
    # inside the document's pages should pass is the owner's decision.
    assert failing == ["The one-month columns on pages 2 to 4 were not spread."]


# ---- references in a covenant answer: terms versions and section numbers -------------------------

REFS = References(versions=frozenset({1, 2}), sections=frozenset({"6.3", "9.1", "6.12"}))


def refs_ok(text, refs=REFS):
    return check_narrative(text, {}, refs=refs) == []


@pytest.mark.parametrize("text", [
    "Only one terms version 1 is on file.",
    "The approved version 1 governs.",
    "Version 2 of the terms was not used.",
    "Rerunning the test under terms version 2 gave the same failure.",
    "A search found only the agreement's own Section 9.1 clause.",
    "Revenue to Plan (Section 6.3) is the test.",
    "The test in Section 6.12(b) applies.",
])
def test_known_versions_and_sections_pass_anywhere(text):
    assert refs_ok(text)


@pytest.mark.parametrize("text", [
    "Under version 7 the ratio was higher.",       # no such version
    "The limit stood at Section 4.25 on that day.",  # not a section the run read
    "Leverage was version 1.5x.",
    "Rerunning under version 2 gave the same failure.",   # a bare "version N" is not a qualified version
    "Leverage is terms version 1.5x.",
    "Section 9.1x was the multiple.",
    "The shortfall is not limited to one month.",   # "to one" stays refused; the retry handles it
    "Growth over a four-quarter climb.",
])
def test_other_versions_sections_and_quantities_stay_refused(text):
    assert not refs_ok(text)


def test_a_four_quarter_basis_names_a_window():
    assert refs_ok("Measured quarterly on a four-quarter basis.")


def _recorded_covenant_answer(path):
    found = [*(ROOT.parent / "covenant").glob(path), *(ARCHIVE / "covenant").glob(path)]
    assert len(found) == 1, found
    d = json.loads(found[0].read_text())
    return json.loads(d["content"][-1]["text"])


def _problems(answer, refs):
    from decimal import Decimal

    from app.guardrails.narrative import FactView, referenced_fact_ids
    from app.guardrails.numbers import extract_figures
    facts = {i: FactView(i, Decimal(1), "ratio") for i in referenced_fact_ids(answer["explanation"])}
    out = [p.subject for p in check_narrative(answer["explanation"], facts, refs=refs)]
    for c in answer["claims"]:
        allowed = [f.value for f in extract_figures(c["quote"])]
        out += [p.subject for p in check_narrative(c["text"], facts, refs=refs, allowed_figures=allowed)]
    return out


def test_recorded_covenant_answers_pass_with_the_references_the_run_builds():
    # the re-recorded (claude-opus-5-5, v2) answers name their sections and versions properly: with the references
    # built from the run they pass; without them they are refused outright
    # the plan-miss client's answer, recorded before its rename (archived under the code it was recorded with)
    # (its 23 Nov re-record, meridew-analytics, wrote a bare "under version 1" in exchange 06, was refused and
    # passed on the retry, 07; the archived answer stays the pinned one)
    plan_miss = _recorded_covenant_answer("corvane-analytics/2026-10-31/revenue_vs_plan/06.json")
    assert _problems(plan_miss, References(frozenset({1}), frozenset({"6.3"}))) == []
    pellham = _recorded_covenant_answer("pellham-grain/2026-09-30/fccr/06.json")
    # Pellham's re-recorded wording cites a year and a version the run's references do not hold (those are
    # attacks the product still refuses), so only the refusal without references is pinned here
    assert _problems(pellham, References()) != []


def test_a_decimal_at_the_start_of_a_page_line_is_not_a_section_heading():
    from app.guardrails.narrative import sections_printed
    assert sections_printed("3.25 : 1 test\n4.50 times\n") == set()
    assert sections_printed("3.25 Minimum Revenue\nSee Section 6.3 and § 9.1.\n7.2. Waivers") == {"3.25", "6.3", "9.1", "7.2"}
    assert not refs_ok("The limit stood at Section 3.25.", References(sections=frozenset(sections_printed("3.25 : 1 test"))))


def test_only_printed_ending_or_mask_contexts_register_an_account_ending():
    st = DocumentStructure.from_pages([
        "Collateral account (ending 9001) pledged\nAccount ending 9002 total\nacct xxxx9003\nEnding 125000\n"
        "Ending 4417\nEnding balance 5555\nCard ****9004"])
    assert st.endings == {"9001", "9002", "9003", "9004"}

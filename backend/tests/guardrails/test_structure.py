"""A note may point at a place in the document only if the code-built structure says it exists."""
import json
import pathlib

import pytest
from app.guardrails.narrative import DocumentStructure, check_narrative

ST = DocumentStructure(page_count=5, note_numbers=frozenset({1}), endings=frozenset({"9001", "9002"}),
                       years=frozenset({2025, 2026}))
ROOT = pathlib.Path(__file__).resolve().parents[3] / "evals" / "recordings" / "spreading"


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
    for p in sorted(ROOT.rglob("*.json")):
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
    assert failing == []

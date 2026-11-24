"""What units a statement says it is in. Pure code: no I/O.

A reader that reports "(000's omitted)" honestly is no help if code does not know the phrase means
thousands: every figure would be stored a thousand times too small. So the phrases are read here,
broadly, and a units phrase that is not understood is a question for a person, never a default.
"""
import re

_THOUSANDS = re.compile(
    r"\bin\s+thousands?\b|\bthousands?\s+of\b|\bamounts?\s+in\s+thousands?\b|\bexpressed\s+in\s+(?:thousands?|\$?\s?k)\b"
    r"|\(\s*000'?s?\s*\)|\b000'?s?\s+omitted\b|\bin\s+(?:\$|usd\s*|us\$\s*)?000'?s?\b|[$]\s?000'?s?\b"
    r"|(?:usd|us\$|\$)\s*'000\b|'000s?\b|\(\s*(?:in\s+)?(?:\$|usd\s*)?k\s*\)|\bin\s+\$?k\b|\$k\b", re.I)
_MILLIONS = re.compile(
    r"\bin\s+millions?\b|\bmillions?\s+of\b|\bamounts?\s+in\s+millions?\b|\bexpressed\s+in\s+millions?\b"
    r"|\(\s*(?:in\s+)?(?:\$|usd\s*)?mm?\s*\)|[$]\s?mm?\b(?!\w)|\b000,?000'?s?\s+omitted\b|\bin\s+\$?mm\b", re.I)
_DOLLARS = re.compile(r"\bin\s+(?:whole\s+)?(?:u\.?s\.?\s+)?dollars\b|\bwhole\s+dollars\b|\bin\s+usd\b(?!\s*')", re.I)


def units_in(text: str) -> set[str]:
    """Every unit of account the text names: "thousands", "millions", "dollars"."""
    found = set()
    if _THOUSANDS.search(text):
        found.add("thousands")
    if _MILLIONS.search(text):
        found.add("millions")
    if _DOLLARS.search(text) and not found:
        found.add("dollars")
    return found


def scale_of(phrase: str) -> int | None:
    """1000 or 1 for a units phrase that is understood; None for one that is not (including
    millions, which the template does not take)."""
    found = units_in(phrase)
    if found == {"thousands"}:
        return 1000
    if found == {"dollars"}:
        return 1
    return None

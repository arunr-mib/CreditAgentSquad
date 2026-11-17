"""Does a printed row label fit the line it was assigned to? Pure code: no I/O.

A reader can copy a figure perfectly and still file it under the wrong line: long-term debt
under "other liabilities" foots just as well and can hide a breach. So an assignment is accepted
only when the row's label, as code read it from the page, is a known name for that line, or a
person has already confirmed that label for that line for this borrower. Anything else is put
to a person once; their confirmation is what makes an unfamiliar label familiar.
"""
import re
from collections.abc import Iterable, Mapping

_STOP = {"and", "of", "the", "to", "for", "in", "on", "a", "an", "at", "by", "per"}
STRONG = 0.8   # a printed label reads as a line when it shares at least this much with a known name


def tokens(label: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z0-9]+", label.lower()) if w not in _STOP)


def similarity(a: str, b: str) -> float:
    """Shared words over all words, from 0 to 1."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def best_match(printed: str, candidates: Mapping[str, Iterable[str]]) -> tuple[str | None, float]:
    best_key, best = None, 0.0
    for key, labels in candidates.items():
        score = max((similarity(printed, label) for label in labels), default=0.0)
        if score > best:
            best_key, best = key, score
    return best_key, best


def mapping_doubt(printed: str, assigned: str, candidates: Mapping[str, Iterable[str]], *,
                  confirmed: bool = False) -> str | None:
    """A reason to hold the assignment for a person, or None. `candidates` maps each known key
    (including the assigned one) to the labels it is known by. `confirmed` is True when a person
    has already accepted this printed label for this line for this borrower."""
    if confirmed:
        return None
    if not printed.strip():
        return f"no row label could be read from the page for {assigned}"
    own = max((similarity(printed, label) for label in candidates.get(assigned, ())), default=0.0)
    others = {k: v for k, v in candidates.items() if k != assigned}
    other_key, other = best_match(printed, others)
    if other_key is not None and other >= STRONG and other > own:
        return f"the label {printed!r} reads as {other_key}, not {assigned}"
    if own >= STRONG:
        return None
    return f"the label {printed!r} is not a known name for {assigned}"

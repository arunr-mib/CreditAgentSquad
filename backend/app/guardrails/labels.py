"""Does a printed row label fit the line it was assigned to? Pure code: no I/O.

A reader can copy a figure perfectly and still file it under the wrong line: long-term debt
under "other liabilities" foots just as well and can hide a breach. Code cannot know every
label a borrower might print, so the rule is deliberately narrow: it raises a doubt only when
the printed label clearly reads as a DIFFERENT known line. An unfamiliar label raises nothing.
"""
import re
from collections.abc import Iterable, Mapping

_STOP = {"and", "of", "the", "to", "for", "in", "on", "a", "an", "at", "by", "per"}
STRONG = 0.8   # the printed label reads as another line at least this well
MARGIN = 0.3   # and that much better than as the assigned line


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


def mapping_doubt(printed: str, assigned: str, candidates: Mapping[str, Iterable[str]]) -> str | None:
    """A reason to doubt the assignment, or None. `candidates` maps each known key (including
    the assigned one) to the labels it is known by."""
    own = max((similarity(printed, label) for label in candidates.get(assigned, ())), default=0.0)
    others = {k: v for k, v in candidates.items() if k != assigned}
    other_key, other = best_match(printed, others)
    if other_key is not None and other >= STRONG and other - own >= MARGIN:
        return f"the label {printed!r} reads as {other_key}, not {assigned}"
    return None

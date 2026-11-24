"""Every invented name in the innovation book, with what the owner's web check found.

    uv run python -m synthetic.books.innovation.names

The 16 client names were web-checked on 22 November 2026 (standard web search, name plus a sector word; indicative
only, not a trademark or registry search): `docs/product/name-check-2026-11-22.md`. The owner had eight renamed the same
day; each new name was searched and came back clear. The CFO names were not searched. Names reused from the v1 book
(the relationship managers, analysts, credit officers, auditors and the kept four) were checked with v1, and the kept
four again on 22 November (clear). No web search is done here."""

from __future__ import annotations

from synthetic.books.innovation.roster import CLIENTS

_RENAMED = "renamed 22 Nov (owner decision); the new name was web-checked on 22 Nov: clear"
_CLEAR = "web-checked on 22 Nov: clear"

LOOKS_LIKE = {
    "datamarrow": _RENAMED,
    "tarnavi-ai": _RENAMED,
    "calvere-health": _RENAMED + " (nearest: CalvertHealth, a nonprofit)",
    "tavernel-grid": _RENAMED,
    "vantrell-labs": _RENAMED + " (nearest: Vantrel, an exam-prep startup)",
    "meridew-analytics": _RENAMED,
    "brackmere-medical": _RENAMED,
    "cindrel-tech": _RENAMED,
    "veridia-payments": "web-checked on 22 Nov: similar (weak) to 'Veridian'; kept by the owner",
    "brightvane-energy": _CLEAR,
    "mosswell-robotics": _CLEAR,
    "kelvra-bio": _CLEAR,
    "orbitline-systems": _CLEAR,
    "pellucid-sensors": _CLEAR,
    "nimbusfield-security": _CLEAR,
    "ferrogate-cloud": _CLEAR,
}


def invented_names() -> list[dict]:
    rows = []
    for spec in CLIENTS:
        rows.append(
            {
                "kind": "company",
                "name": spec.name,
                "sector": spec.sector,
                "watch": LOOKS_LIKE.get(spec.id, ""),
            }
        )
    for spec in CLIENTS:
        rows.append(
            {
                "kind": "person",
                "name": spec.cfo,
                "sector": f"chief financial officer, {spec.name}",
                "watch": "",
            }
        )
    return rows


def main() -> None:
    print("| Kind | Name | Where | Web check |\n|---|---|---|---|")
    for row in invented_names():
        print(f"| {row['kind']} | {row['name']} | {row['sector']} | {row['watch'] or '-'} |")


if __name__ == "__main__":
    main()

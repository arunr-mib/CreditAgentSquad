"""Every invented name in the innovation book, for the owner to check before anything is shown outside the team.

    uv run python -m synthetic.books.innovation.names

No web search is done here: the list says what to check, not what was found. Names reused from the v1 book (the
relationship managers, analysts, credit officers, auditors and the kept four) were checked with v1."""

from __future__ import annotations

from synthetic.books.innovation.roster import CLIENTS

LOOKS_LIKE = {
    "stripple-tech": "close in sound to a well-known payments company",
    "tessaract-labs": "a spelling variant of a common word used by many products",
    "dataflake": "data-infrastructure names are crowded",
    "veridia-payments": "close to 'Veridian', used by several companies",
    "halcyon-grid": "a common word used by many companies",
    "quillon-ai": "close to other 'Quill' product names",
}


def invented_names() -> list[dict]:
    rows = []
    for spec in CLIENTS:
        rows.append({"kind": "company", "name": spec.name, "sector": spec.sector, "watch": LOOKS_LIKE.get(spec.id, "")})
    for spec in CLIENTS:
        rows.append({"kind": "person", "name": spec.cfo, "sector": f"chief financial officer, {spec.name}", "watch": ""})
    return rows


def main() -> None:
    print("| Kind | Name | Where | Check first because |\n|---|---|---|---|")
    for row in invented_names():
        print(f"| {row['kind']} | {row['name']} | {row['sector']} | {row['watch'] or '-'} |")


if __name__ == "__main__":
    main()

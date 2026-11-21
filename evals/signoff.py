"""The owner's answer key, as one short table, and the step that records the owner's reply.

Nothing here signs by default: `apply` marks a row signed only if its key is written in the file the
owner's reply produced. The billable guard (`evals.run.check_may_start`) reads the result."""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

from evals.book import BOOKS, oracle_for

KEY = ("borrower_id", "period_end", "kind", "item")

# what the key expects, in plain words, per scenario the generator names
EXPECTS = {
    "pledged_cash": "certificate counts pledged cash: minimum-cash covenant reported compliant but actually "
                    "breached; Squad flags the mismatch (exception), plus a high runway-below-watch signal and a signed December extension",
    "late_package": "October package is late, so the three October tests cannot be tested; Squad raises "
                    "missing bank statements and missing MRR report",
    "runway_falling": "losing more than a month of runway per month for three months; one medium signal, tests compliant",
    "clean": "nothing wrong: all three covenant tests compliant, no exception; only a low headroom note",
    "funding_expected": "tests compliant; a funding event is expected and on track (recorded, not an exception)",
    "stripple_package": "tests compliant on paper but figures are held for a person (MRR export unclassified, "
                        "one statement value unverified); Squad does not reach the 3 tests",
    "plan_miss": "revenue under 80 percent of plan: covenant breach exception, with medium plan and headroom signals",
    "funding_slipped": "tests compliant; the equity round slipped past its date: funding exception, plus a high runway-below-watch signal",
    "restricted_account": "bank statements disagree with the certificate (restricted cash): Squad raises a "
                          "cash-mismatch exception; tests compliant with a noted variance",
    "cash_flow_positive": "Ferrogate is cash-flow positive: runway 'not meaningful' (counts as compliant, with that note); "
                          "DSCR 6.54 vs 1.25 compliant",
}


def _rows(oracle: Path) -> tuple[list[str], list[dict[str, str]]]:
    with oracle.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _unsigned(r: dict[str, str]) -> bool:
    return r["owner_signed_off"].strip().lower() != "yes"


def _key(r: dict[str, str]) -> tuple[str, ...]:
    return tuple(r[k] for k in KEY)


def table(oracle: Path) -> str:
    _, rows = _rows(oracle)
    unsigned = [r for r in rows if _unsigned(r)]
    by: dict[str, Counter] = defaultdict(Counter)
    scenario: dict[str, str] = {}
    for r in unsigned:
        by[r["borrower_id"]][r["kind"]] += 1
        if r["kind"] == "signal" and r["expected_outcome"] == "low":
            by[r["borrower_id"]]["low"] += 1
        scenario.setdefault(r["borrower_id"], r["scenario"])
    signals = sum(1 for r in unsigned if r["kind"] == "signal")
    low = sum(1 for r in unsigned if r["kind"] == "signal" and r["expected_outcome"] == "low")
    out = [f"{len(unsigned)} unsigned rows ({signals} signal{'s' if signals != 1 else ''}, {low} low severity) "
           f"of {len(rows)}; the already-signed rows are not shown.", "",
           "| Client | Covenant tests | Signals | Exceptions and events | Low signals | What the key expects |",
           "|---|---|---|---|---|---|"]
    for code in sorted(by):
        c = by[code]
        events = c["exception"] + c["funding_event"] + c["borrowing_base"]
        expects = EXPECTS.get(scenario[code], scenario[code])
        out.append(f"| {code} | {c['covenant_test']} | {c['signal']} | {events} | {c['low']} | {expects} |")
    return "\n".join(out)


def keys(oracle: Path, *, low_signals: bool = False) -> list[str]:
    """Row ids of the unsigned rows (optionally only the low-severity signals), for the owner's reply file."""
    _, rows = _rows(oracle)
    return ["|".join(_key(r)) for r in rows
            if _unsigned(r) and (not low_signals or (r["kind"] == "signal" and r["expected_outcome"] == "low"))]


def apply(oracle: Path, rows_file: Path | None) -> int:
    """Sign exactly the rows listed in `rows_file` (`borrower_id|period_end|kind|item` per line)."""
    lines = [ln.strip() for ln in (rows_file.read_text().splitlines() if rows_file else []) if ln.strip()]
    if not lines:
        raise ValueError("no rows given: list the row ids the owner approved in a file (--rows)")
    wanted = {tuple(ln.split("|")) for ln in lines}
    fields, rows = _rows(oracle)
    missing = sorted(wanted - {_key(r) for r in rows})
    if missing:
        raise ValueError(f"not in the oracle: {missing[:3]}")
    signed = 0
    for r in rows:
        if _unsigned(r) and _key(r) in wanted:
            r["owner_signed_off"] = "yes"
            signed += 1
    with oracle.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return signed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.signoff")
    parser.add_argument("command", choices=("table", "keys", "apply"))
    parser.add_argument("--oracle", default=str(oracle_for(BOOKS["innovation"])))
    parser.add_argument("--rows", help="file of approved row ids, one per line (apply only)")
    parser.add_argument("--low-signals", action="store_true", help="keys: only the low-severity signals")
    args = parser.parse_args(argv)
    oracle = Path(args.oracle)
    if args.command == "table":
        print(table(oracle))
    elif args.command == "keys":
        print("\n".join(keys(oracle, low_signals=args.low_signals)))
    else:
        print(f"signed {apply(oracle, Path(args.rows) if args.rows else None)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

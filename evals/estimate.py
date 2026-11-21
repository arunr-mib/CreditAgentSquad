"""A cost ESTIMATE for a live record pass. Nothing here calls a model. Method:

1. run the stand-in over the borrowers in scope and count the requests it answers per agent
   (intake, spreading, certificate, collateral, review);
2. for agents the stand-in does not answer, count from the call sites in the stand-in cycle:
   covenant = one investigation per covenant.breach / covenant.reported_mismatch work item, each
   taking the mean number of exchanges seen in the recordings; early_warning = one call per
   borrower whose cycle fires a signal; review = the stand-in's one answer per borrower times the
   exchanges per cycle seen in the recordings (the recorded review often needs a second exchange);
3. tokens per call = the mean recorded usage of that agent: uncached input, cache writes (1.25x
   input), cache reads and output are priced separately. An agent never recorded has no
   calibration and the estimate refuses to price it at zero;
4. range = 0.6x to 1.6x of the middle (the book's documents differ from the three recorded
   borrowers', and a retried exchange costs a call).

Every figure is an ESTIMATE. `python -m evals.estimate` runs the stand-in only; no key is needed.
"""
import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from evals.book import BOOKS, REPO

# USD per 1M tokens. Source: the Claude API skill's model table, cached 2026-11-03 (Anthropic first-party rates).
# Cache writes are 1.25x input (5-minute cache); cache reads are the published read price.
PRICES = {
    "claude-opus-5-5": {"input": Decimal("4.00"), "output": Decimal("20.00"),
                        "cache_write": Decimal("5.00"), "cache_read": Decimal("0.20")},
    "claude-sonnet-5-5": {"input": Decimal("2.00"), "output": Decimal("10.00"),
                          "cache_write": Decimal("2.50"), "cache_read": Decimal("0.10")},
}
PRICE_SOURCE = "Claude API skill model table, cached 2026-11-03"
LOW, HIGH = Decimal("0.6"), Decimal("1.6")
KEPT_THREE = ("briarstone-beverage", "harrowgate-precision", "kestrel-bay-packaging")
STALE_AGENTS = ("intake", "spreading")  # progress.md: these two agents' prompts moved after the kept three were recorded
COVENANT_ITEMS = ("covenant.breach", "covenant.reported_mismatch")
RECORDINGS = REPO / "evals" / "recordings"
MILLION = Decimal(1_000_000)


@dataclass
class Calibration:
    input_tokens: int  # uncached input
    output_tokens: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass
class Line:
    agent: str
    calls: int
    mid: Decimal


@dataclass
class Estimate:
    lines: list[Line]
    total_low: Decimal
    total_mid: Decimal
    total_high: Decimal


def calibrate(recordings: Path = RECORDINGS) -> dict[str, Calibration]:
    """Mean recorded usage per call, by agent (the first directory under `recordings`)."""
    by: dict[str, list[tuple[int, int, int, int]]] = {}
    for path in sorted(recordings.rglob("*.json")):
        usage = json.loads(path.read_text()).get("usage") or {}
        if not usage:
            continue
        by.setdefault(path.relative_to(recordings).parts[0], []).append((
            usage.get("input_tokens", 0), usage.get("output_tokens", 0),
            usage.get("cache_creation_input_tokens", 0), usage.get("cache_read_input_tokens", 0)))
    return {agent: Calibration(*(sum(col) // len(rows) for col in zip(*rows, strict=True)))
            for agent, rows in by.items()}


def estimate(calls: dict[str, int], calibration: dict[str, Calibration], price: dict[str, Decimal]) -> Estimate:
    lines, total = [], Decimal(0)
    for agent, n in sorted(calls.items()):
        if agent not in calibration:
            raise KeyError(f"no recorded usage for {agent}: record one call first or give a calibration")
        c = calibration[agent]
        cost = Decimal(n) * (Decimal(c.input_tokens) * price["input"] + Decimal(c.output_tokens) * price["output"]
                             + Decimal(c.cache_write_tokens) * price["cache_write"]
                             + Decimal(c.cache_read_tokens) * price["cache_read"]) / MILLION
        lines.append(Line(agent, n, cost))
        total += cost
    return Estimate(lines, total * LOW, total, total * HIGH)


def _usd(x: Decimal) -> str:
    return f"${x.quantize(Decimal('0.01'))}"


def render(scenarios: dict[str, Estimate], notes: list[str], rerecord: dict[str, Estimate] | None = None,
           calibration: dict[str, Calibration] | None = None, scope: str = "") -> str:
    models = list(scenarios)
    prices = ", ".join(f"{m} at ${PRICES[m]['input']} input / ${PRICES[m]['output']} output per million tokens"
                       for m in models if m in PRICES)
    out = [f"ESTIMATE, not a measurement. Prices: {prices or ', '.join(models)} ({PRICE_SOURCE}); tokens per call "
           f"from the three recorded borrowers; the range is {LOW}x to {HIGH}x.", ""]
    if scope:
        out += [scope, ""]
    main_model = models[0]
    out += [f"## Calls and cost by agent, {main_model} (ESTIMATE)", "",
            "| agent | calls (ESTIMATE) | mid (ESTIMATE) |", "|---|---:|---:|"]
    for line in scenarios[main_model].lines:
        out.append(f"| {line.agent} | {line.calls} | {_usd(line.mid)} |")
    out += ["", "## Totals (ESTIMATE)", "",
            "| model | low (ESTIMATE) | mid (ESTIMATE) | high (ESTIMATE) |", "|---|---:|---:|---:|"]
    for m, e in scenarios.items():
        out.append(f"| {m} | {_usd(e.total_low)} | {_usd(e.total_mid)} | {_usd(e.total_high)} |")
    if rerecord:
        out += ["", "## Extra if the kept three borrowers are re-recorded (ESTIMATE, a separate line)", "",
                "| model | low (ESTIMATE) | mid (ESTIMATE) | high (ESTIMATE) |", "|---|---:|---:|---:|"]
        for m, e in rerecord.items():
            out.append(f"| {m} | {_usd(e.total_low)} | {_usd(e.total_mid)} | {_usd(e.total_high)} |")
        out += ["", "| agent | calls (ESTIMATE) | mid, " + main_model + " (ESTIMATE) |", "|---|---:|---:|"]
        for line in rerecord[main_model].lines:
            out.append(f"| {line.agent} | {line.calls} | {_usd(line.mid)} |")
        total_mid = scenarios[main_model].total_mid + rerecord[main_model].total_mid
        total_high = scenarios[main_model].total_high + rerecord[main_model].total_high
        out += ["", f"Everything together on {main_model} (ESTIMATE): mid {_usd(total_mid)}, high {_usd(total_high)}."]
    if calibration:
        out += ["", "## Tokens per call used (mean of the recordings)", "",
                "| agent | input | cache write | cache read | output |", "|---|---:|---:|---:|---:|"]
        for agent, c in sorted(calibration.items()):
            out.append(f"| {agent} | {c.input_tokens} | {c.cache_write_tokens} | {c.cache_read_tokens} | {c.output_tokens} |")
    if notes:
        out += ["", "## How these numbers were made, and what they leave out", ""] + [f"- {n}" for n in notes]
    return "\n".join(out) + "\n"


def recorded_per_cycle(agent: str, recordings: Path = RECORDINGS) -> Decimal:
    """Mean number of recorded exchanges per (borrower, period) for an agent."""
    files = list((recordings / agent).rglob("*.json"))
    cycles = {p.parent for p in files}
    return Decimal(len(files)) / Decimal(len(cycles)) if cycles else Decimal(1)


def count_calls(recordings: list[dict], *, calibration_dir: Path = RECORDINGS) -> tuple[dict[str, int], list[str]]:
    """Requests per agent for the borrowers in `recordings` (a stand-in dry run's per-borrower recordings)."""
    calls: Counter[str] = Counter()
    notes: list[str] = []
    covenant_items = 0
    with_signals = 0
    for rec in recordings:
        for output in rec.get("model_outputs", []):
            calls[output["record_key"].split("/")[0]] += 1
        covenant_items += sum(1 for w in rec.get("work_items", []) if w.get("type") in COVENANT_ITEMS)
        with_signals += 1 if rec.get("signals") else 0
    exchanges_cov = recorded_per_cycle("covenant", calibration_dir)
    exchanges_review = recorded_per_cycle("review", calibration_dir)
    base_review = calls.get("review", 0)
    calls["review"] = math.ceil(base_review * exchanges_review)
    calls["covenant"] = math.ceil(covenant_items * exchanges_cov)
    calls["early_warning"] = with_signals
    notes.append(f"covenant: {covenant_items} exception work items in the stand-in cycles x {exchanges_cov} recorded "
                 f"exchanges per investigation = {calls['covenant']} calls (counted from the call site, the stand-in does not answer it).")
    notes.append(f"early_warning: one call for each of the {with_signals} borrowers whose cycle fires a signal (call site).")
    notes.append(f"review: {base_review} stand-in answers x {exchanges_review:.2f} exchanges per recorded cycle "
                 f"= {calls['review']} calls.")
    return dict(calls), notes


def stale_rerecord_calls(recordings: Path = RECORDINGS) -> dict[str, int]:
    """What re-recording the kept three costs: their stale intake and spreading recordings, and the
    review exchange (briarstone review/02) that was never recorded."""
    calls: Counter[str] = Counter()
    for agent in STALE_AGENTS:
        calls[agent] = sum(len(list((recordings / agent / code).rglob("*.json"))) for code in KEPT_THREE
                           if (recordings / agent / code).exists())
    calls["review"] = sum(1 for code in KEPT_THREE
                          if not list((recordings / "review" / code).rglob("02.json"))
                          and (recordings / "review" / code).exists())
    return {a: n for a, n in calls.items() if n}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.estimate", description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=str(REPO / "docs" / "live-run-estimate-2026-11-21.md"))
    parser.add_argument("--book", default=str(BOOKS["innovation"]))
    args = parser.parse_args(argv)

    from evals.book import load_book
    from evals.run import run_suite

    book = load_book(args.book)
    scope_codes = [b.code for b in book if b.code not in KEPT_THREE]
    results = run_suite(mode="standin", book_root=args.book, only=scope_codes, keep_recordings=True)
    recs = [r for p in results["recordings"] for r in p.values() if isinstance(r, dict)]
    calls, notes = count_calls(recs)
    cal = calibrate()
    rerecord_calls = stale_rerecord_calls()
    scenarios = {m: estimate(calls, cal, PRICES[m]) for m in PRICES}
    rerecord = {m: estimate(rerecord_calls, cal, PRICES[m]) for m in PRICES}
    notes += [
        "The kept three borrowers are re-recorded only if the owner does not accept the stale replay (--accept-stale); "
        "the separate line is their stale intake and spreading calls plus briarstone's missing review/02.",
        "Spreading is priced at the mean of three recorded statement spreads (about 12k cached input, 6.4k output); "
        "the stand-in's spreads of monthly packs, MRR and bank statements are likely shorter, so the spreading line leans high; "
        "the 0.6x to 1.6x range is a judgement, not a statistic.",
        "Tokens are taken as the same for the cheaper model (same tokenizer family per the skill); Sonnet's quality on these "
        "readings is unmeasured here, so its figure is a price comparison, not a recommendation. No configuration was changed.",
        "Not counted: the Terms Agent (not called in these cycles), re-runs after a product fix, the one-borrower trial, and any "
        "retry the real model causes beyond the recorded exchange counts.",
    ]
    scope = f"Scope: {len(scope_codes)} borrowers (the 16 innovation clients and Pellham Grain); lumora-health makes no model call in the stand-in cycle."
    text = render(scenarios, notes, rerecord, cal, scope)
    Path(args.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Turn a results document into a readable scorecard. The first lines always say which mode
produced it; a stand-in run says plainly that it is not model performance."""
from typing import Any


def _pct(value: float | None) -> str:
    return "not measured" if value is None else f"{value * 100:.1f}%"


def _num(value: Any) -> str:
    return "not measured" if value is None else f"{value:,}" if isinstance(value, int) else str(value)


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_summary(results: dict[str, Any]) -> str:
    """A few lines for the terminal."""
    meta, metrics, gate = results["meta"], results["metrics"], results["gate"]
    failures = ", ".join(f"{name} {count}" for name, count in results["failure_counts"].items() if count) or "none"
    lines = [
        meta["label"],
        f"Borrowers {meta['borrowers']}; cycles reaching signals or beyond {metrics['cycles_reaching_signals']}; "
        f"closed {metrics['cycles_closed']}; run time {meta['seconds']}s.",
        f"Extraction accuracy {_pct(metrics['extraction_accuracy'])} "
        f"({metrics['extraction_facts_correct']} of {metrics['extraction_facts_expected']} expected facts); "
        f"covenant outcome accuracy {_pct(metrics['covenant_outcome_accuracy'])}.",
        f"Exception precision {_pct(metrics['exception_precision'])}, recall {_pct(metrics['exception_recall'])}; "
        f"cycles needing no person {_pct(metrics['cycles_needing_no_person'])}.",
        f"Named failures: {failures}. Other disagreements with the truth: {metrics['disagreements']}.",
        f"Gate: {'PASSED' if gate['passed'] else 'FAILED'}" + ("" if gate["passed"] else " - " + "; ".join(gate["reasons"])),
    ]
    return "\n".join(lines)


def render_markdown(results: dict[str, Any]) -> str:
    meta, metrics, gate = results["meta"], results["metrics"], results["gate"]
    out: list[str] = []
    out.append(f"# Evaluation scorecard: {meta['suite']} ({meta['mode']})")
    out.append("")
    if meta["standin"]:
        out.append("**STAND-IN RUN. NOT MODEL PERFORMANCE.** A perfect reader built from the synthetic book's ground "
                   "truth answered in place of the model. This run proves the pipeline, the workflow and the grader "
                   "end to end; it says nothing about how a model reads these documents.")
    else:
        out.append(f"**Mode: {meta['mode']}.** {meta['label']}")
    out.append("")
    out.append(f"- Generated {meta['generated_at']}; commit `{meta['commit'] or 'unknown'}`; "
               f"{meta['borrowers']} borrower(s) ({_cell(meta['scope'])}); {meta['passes']} pass(es); "
               f"run time {meta['seconds']} seconds.")
    out.append(f"- Scripted decisions where a person is needed: {'yes' if meta['decide'] else 'no'}.")
    out.append(f"- Oracle rows in scope not signed by the owner: {_num(meta['unsigned_oracle_rows'])}.")
    out.append("- Graded by deterministic code against `truth/<borrower>.json`; no model judged a model.")
    out.append("")
    out.append(f"## Gate: {'PASSED' if gate['passed'] else 'FAILED'}")
    out.append("")
    out.append(f"Rule: {gate['rule']}.")
    for reason in gate["reasons"]:
        out.append(f"- {reason}")
    if gate["known_findings_applied"]:
        out.append(f"- {len(gate['known_findings_applied'])} difference(s) are listed as known findings "
                   "(see below); they are open defects, not passes.")
    out.append("")

    out.append("## Headline numbers")
    out.append("")
    out.append("| Measure | Value |")
    out.append("|---|---|")
    rows = [
        ("Extraction accuracy (verified facts equal to truth, over facts expected)",
         f"{_pct(metrics['extraction_accuracy'])} ({metrics['extraction_facts_correct']} of {metrics['extraction_facts_expected']})"),
        ("Extraction abstain rate (expected facts with no usable fact)", _pct(metrics["extraction_abstain_rate"])),
        ("Covenant outcome accuracy", _pct(metrics["covenant_outcome_accuracy"])),
        ("Covenant abstain rate (cannot test where the truth has an outcome)", _pct(metrics["covenant_abstain_rate"])),
        ("Exception precision", _pct(metrics["exception_precision"])),
        ("Exception recall", _pct(metrics["exception_recall"])),
        ("Cycles needing no person (beyond the commentary approval every review needs)",
         f"{_pct(metrics['cycles_needing_no_person'])} (the book expects {_pct(metrics['cycles_expected_to_need_no_person'])})"),
        ("Cycles reaching the signals stage or beyond", f"{metrics['cycles_reaching_signals']} of {metrics['cycles_run']}"),
        ("Cycles closed", f"{metrics['cycles_closed']} of {metrics['cycles_run']}"),
        ("Other disagreements with the truth", _num(metrics["disagreements"])),
        ("Model tokens in / out", f"{_num(metrics['input_tokens'])} / {_num(metrics['output_tokens'])}"),
    ]
    out.extend(f"| {name} | {value} |" for name, value in rows)
    out.append("")
    out.append("| Named failure | Count |")
    out.append("|---|---|")
    out.extend(f"| {name}{' (gated)' if name in ('invented-number', 'false-compliant') else ''} | {count} |"
               for name, count in results["failure_counts"].items())
    out.append("")
    if len(results.get("passes", [])) > 1:
        out.append("Every pass is gated separately:")
        out.append("")
        for n, p in enumerate(results["passes"], start=1):
            counts = ", ".join(f"{k} {v}" for k, v in p["failure_counts"].items() if v) or "no named failures"
            out.append(f"- pass {n}: extraction {_pct(p['metrics']['extraction_accuracy'])}; {counts}")
        out.append("")

    out.append("## Borrowers")
    out.append("")
    out.append("| Borrower | Scenario | Stage reached | Expected exceptions | Raised exceptions | Extraction | Covenants | Differences |")
    out.append("|---|---|---|---|---|---|---|---|")
    for code, g in results["borrowers"].items():
        if g.get("error"):
            out.append(f"| `{code}` | {g['scenario']} | run failed | {_cell(', '.join(g['expected_exceptions']) or 'none')} "
                       f"| - | - | - | {_cell(g['error'][:160])} |")
            continue
        e, c = g["extraction"], g["covenants"]
        stage = g["stage_reached"] + (" (closed)" if g["cycle_status"] == "closed" else f" ({g['stage_status']})")
        differences = len(g["failures"]) + len(g["disagreements"])
        out.append(
            f"| `{code}` | {g['scenario']} | {stage} | {_cell(', '.join(g['expected_exceptions']) or 'none')} "
            f"| {_cell(', '.join(g['raised_exceptions']) or 'none')} "
            f"| {_pct(e['accuracy'])} ({e['correct']}/{e['expected']}) | {c['correct']}/{c['expected']} "
            f"| {differences or 'none'} |")
    out.append("")

    findings = [(code, f["name"], f["item"], f["detail"]) for code, g in results["borrowers"].items() for f in g["failures"]]
    findings += [(code, d["kind"], d["item"], d["detail"]) for code, g in results["borrowers"].items()
                 for d in g["disagreements"]]
    out.append("## Differences from the truth")
    out.append("")
    if not findings:
        out.append("None. Every borrower's outcome agrees with the book.")
    else:
        known = {(k["borrower"], k["name"], k["item"]): k for k in results.get("known_findings", [])}
        out.append("| Borrower | Failure | Item | Detail | Known finding |")
        out.append("|---|---|---|---|---|")
        for code, name, item, detail in findings:
            note = known.get((code, name, item), {}).get("cause", "")
            out.append(f"| `{code}` | {name} | {_cell(item)} | {_cell(detail)[:260]} | {_cell(note)[:200]} |")
    out.append("")

    stops = [(code, s) for code, g in results["borrowers"].items() for s in g.get("stops", [])]
    if stops:
        out.append("## Where a person was needed")
        out.append("")
        out.append("| Borrower | Stage | Open items | Scripted decisions |")
        out.append("|---|---|---|---|")
        for code, s in stops:
            open_items = ", ".join(sorted({i["type"] for i in s["open_items"]})) or f"none (stage {s['stage_status']})"
            decisions = ", ".join(f"{d['type']}: {d['decision']} by {d['by_role']}"
                                  + (f" REFUSED {d['error']}" if d["error"] else "") for d in s["decisions"]) or "none (left open)"
            out.append(f"| `{code}` | {s['stage']} | {_cell(open_items)} | {_cell(decisions)} |")
        out.append("")

    observations = [(code, o) for code, g in results["borrowers"].items() for o in g.get("observations", [])]
    notes = [(code, r["agent"], n) for code, g in results["borrowers"].items() for r in g.get("agent_runs", [])
             for n in (r.get("guardrail_notes") or []) if isinstance(n, dict) and n.get("action") != "shown"]
    if observations or notes or meta["standin_print_vs_truth_disagreements"]:
        out.append("## Observations")
        out.append("")
        for code, o in observations:
            out.append(f"- `{code}`: {o['kind']}: {o['detail']}")
        for code, agent, n in notes:
            out.append(f"- `{code}`: guardrail note on {agent}: {n.get('check')} -> {n.get('action')}: {_cell(n.get('detail', ''))[:200]}")
        for d in meta["standin_print_vs_truth_disagreements"]:
            out.append(f"- `{d['borrower']}`: the stand-in found print and truth disagree on {d['what']}: "
                       f"printed {d['printed']!r}, truth {d['truth']!r}")
        out.append("")
    if results.get("mutations"):
        out.append("## Mutation checks")
        out.append("")
        out.append("Each check tampers with the stand-in's answer in one way a model could be wrong, runs the live "
                   "cycle, and records who caught it. `product`: refused into a work item or a guardrail note. "
                   "`grader`: accepted by the product and named only by the grader, which is a finding about the "
                   "product. `recovered`: code reads that part from the page itself, so the reader's mistake "
                   "has no effect. `SLIPPED`: caught by neither.")
        out.append("")
        counts: dict[str, int] = {}
        for m in results["mutations"]:
            counts[m["caught_by"]] = counts.get(m["caught_by"], 0) + 1
        out.append("Totals: " + ", ".join(f"{name} {count}" for name, count in sorted(counts.items())) + ".")
        out.append("")
        out.append("| Mutation | What the reader got wrong | Borrower | Caught by | Evidence |")
        out.append("|---|---|---|---|---|")
        for m in results["mutations"]:
            out.append(f"| {_cell(m['name'])} | {_cell(m['what'])} | `{m['borrower']}` | {m['caught_by']} "
                       f"| {_cell(m['evidence'])[:300]} |")
        out.append("")
    return "\n".join(out) + "\n"

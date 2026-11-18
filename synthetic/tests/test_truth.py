"""The truth files, the expected results and the oracle."""

from __future__ import annotations

import csv
import json
from decimal import ROUND_HALF_UP, Decimal

from synthetic.scenarios import ROSTER

D = Decimal
CURRENT = "2026-09-30"
TEST_ENDS = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]
TOP_LEVEL = [
    "borrower", "facilities", "terms_versions", "periods", "certificates", "borrowing_base",
    "system_of_record", "documents", "scenario", "expected",
]  # fmt: skip
EXPECTED_EXCEPTIONS = {
    "clean": [],
    "hidden_breach": ["covenant.reported_mismatch"],
    "unapproved_amendment": ["covenant.reported_mismatch", "terms.unapproved_amendment"],
    "addback_over_cap": [],
    "deteriorating_trend": ["signal.high"],
    "late_reporting": ["intake.missing_document", "intake.missing_document"],
    "miscounted_ineligible": ["bb.certificate_mismatch"],
    "over_advance": ["bb.over_advance"],
    "scale_trap": [],
    "restated_comparative": ["spread.restatement"],
    "missing_page": ["spread.does_not_foot"],
    "image_only": ["spread.image_only"],
    "step_up": ["covenant.reported_mismatch"],
    "reported_breach": ["covenant.breach"],
}
CURRENT_OUTCOMES = {
    "hidden_breach": {"total_leverage": "breach_reported_compliant", "current_ratio": "compliant"},
    "unapproved_amendment": {"total_leverage": "breach_reported_compliant", "interest_coverage": "compliant_variance"},
    "addback_over_cap": {"total_leverage": "compliant_variance", "fccr": "compliant_variance"},
    "step_up": {"total_leverage": "breach_reported_compliant", "fccr": "compliant"},
    "reported_breach": {"fccr": "breach", "total_leverage": "compliant", "min_tnw": "compliant"},
}


def _by_scenario(generated, code: str) -> dict:
    matches = [t for t in generated.truths.values() if t["scenario"]["code"] == code]
    assert len(matches) == 1, code
    return matches[0]


def _period(truth: dict, end: str) -> dict:
    return next(p for p in truth["periods"] + truth["comparative_periods"] if p["period_end"] == end)


def test_one_truth_file_per_borrower_in_the_spec_shape(generated):
    assert sorted(generated.truths) == sorted(s.id for s in ROSTER)
    for bid, truth in generated.truths.items():
        for key in TOP_LEVEL:
            assert key in truth, (bid, key)
        assert truth["borrower"]["lender"] == "Bank of Stoic"
        assert len(truth["periods"]) == 11
        assert [p["period_end"] for p in truth["periods"]][0] == "2024-03-31"
        assert set(truth["expected"]) == {"covenant_tests", "borrowing_base", "signals", "exceptions"}
        assert 1 <= len(truth["facilities"]) <= 2
        months = [r["date"] for r in truth["system_of_record"]]
        assert len(months) == 34 and months[0] == "2024-01-31" and months[-1] == "2026-10-31"
        for p in truth["periods"]:
            assert all(isinstance(x, str) for x in p["values"].values())
            v = {k: D(x) for k, x in p["values"].items()}
            assert v["bs.total_assets"] == v["bs.total_liabilities_and_equity"]
            prior = _period(truth, f"{p['fiscal_year'] - 1}-12-31")
            assert v["cf.net_change_in_cash"] == v["bs.cash"] - D(prior["values"]["bs.cash"])
        # The system of record agrees with the balance sheet at every quarter end.
        for p in truth["periods"]:
            record = next(r for r in truth["system_of_record"] if r["date"] == p["period_end"])
            assert D(record["revolver_outstanding"]) == D(p["values"]["bs.revolver"])


def test_no_floats_anywhere_in_truth(generated):
    def walk(node):
        assert not isinstance(node, float)
        for child in node.values() if isinstance(node, dict) else node if isinstance(node, list) else []:
            walk(child)

    for truth in generated.truths.values():
        walk(truth)


def test_expected_covenant_tests_cover_every_period_from_q1_2025(generated):
    for bid, truth in generated.truths.items():
        covenant_ids = {c["id"] for v in truth["terms_versions"] for c in v["terms"]["covenants"]}
        assert 2 <= len(covenant_ids) <= 4
        seen = {(t["period_end"], t["covenant_id"]) for t in truth["expected"]["covenant_tests"]}
        assert seen == {(end, cid) for end in TEST_ENDS for cid in covenant_ids}, bid
        for t in truth["expected"]["covenant_tests"]:
            if t["period_end"] != CURRENT:
                assert t["outcome"] == "compliant", (bid, t["period_end"], t["covenant_id"])
            assert t["terms_version_id"].startswith(f"tv-{bid}-")


def test_each_scenario_raises_exactly_its_exceptions(generated):
    assert {t["scenario"]["code"] for t in generated.truths.values()} == set(EXPECTED_EXCEPTIONS)
    for bid, truth in generated.truths.items():
        code = truth["scenario"]["code"]
        kinds = sorted(e["type"] for e in truth["expected"]["exceptions"])
        assert kinds == EXPECTED_EXCEPTIONS[code], (bid, code)
        assert all(e["period_end"] == CURRENT for e in truth["expected"]["exceptions"])
        current = {t["covenant_id"]: t["outcome"] for t in truth["expected"]["covenant_tests"] if t["period_end"] == CURRENT}
        if code in CURRENT_OUTCOMES:
            assert current == CURRENT_OUTCOMES[code], bid
        elif code in ("late_reporting", "missing_page", "image_only"):
            assert set(current.values()) == {"cannot_test"}, bid
        else:
            assert set(current.values()) == {"compliant"}, bid


def test_clean_borrowers_have_no_exceptions_and_no_loud_signals(generated):
    clean = [t for t in generated.truths.values() if t["scenario"]["code"] == "clean"]
    assert len(clean) >= 8
    for truth in clean:
        assert truth["expected"]["exceptions"] == []
        loud = [s for s in truth["expected"]["signals"] if s["period_end"] == CURRENT and s["severity"] != "low"]
        assert loud == [], truth["borrower"]["id"]
        for result in truth["expected"]["borrowing_base"]:
            assert result["certificate_matches"] and not result["over_advance"]


def test_unapproved_amendment_is_absent_from_every_approved_terms_version(generated):
    truth = _by_scenario(generated, "unapproved_amendment")
    details = truth["scenario"]["details"]
    amendment_id = details["document_id"]
    assert any(d["id"] == amendment_id and d["type"] == "amendment" for d in truth["documents"]), "the amendment is on file"
    assert details["approved_cap"] != details["amended_cap"]
    for version in truth["terms_versions"]:
        assert version["status"] in ("approved", "superseded")  # a proposed version is never seeded
        assert version["approved_by"] != version["prepared_by"]
        assert amendment_id not in version["source_documents"]
        text = json.dumps(version)
        assert amendment_id not in text
        assert details["amended_cap"] not in text
        addback = version["terms"]["definitions"]["ebitda"]["addbacks"][0]
        assert addback["cap"] == {"type": "amount", "value": details["approved_cap"]}
    current = next(
        t for t in truth["expected"]["covenant_tests"] if t["period_end"] == CURRENT and t["covenant_id"] == "total_leverage"
    )
    assert current["pass"] is False and details["under_amendment"]["pass"] is True
    assert D(details["under_amendment"]["value"]) == D(current["reported_value"])


def test_only_one_borrower_has_an_approved_amendment_and_versions_do_not_overlap(generated):
    for bid, truth in generated.truths.items():
        versions = truth["terms_versions"]
        open_ended = [v for v in versions if v["status"] == "approved" and v["effective_to"] is None]
        assert len(open_ended) == 1, bid
        assert len(versions) == (2 if bid == "marlowe-ridge-logistics" else 1)
    marlowe = generated.truths["marlowe-ridge-logistics"]
    first, second = marlowe["terms_versions"]
    assert first["status"] == "superseded" and first["effective_to"] == "2025-06-30"
    assert second["effective_from"] == "2025-07-01"
    used = {t["period_end"]: t["terms_version"] for t in marlowe["expected"]["covenant_tests"]}
    assert used["2025-06-30"] == 1 and used["2025-09-30"] == 2


def test_step_up_threshold_takes_effect_in_2026(generated):
    truth = _by_scenario(generated, "step_up")
    tests = [t for t in truth["expected"]["covenant_tests"] if t["covenant_id"] == "total_leverage"]
    old = {t["threshold"] for t in tests if t["period_end"] < "2026-01-01"}
    new = {t["threshold"] for t in tests if t["period_end"] >= "2026-01-01"}
    assert len(old) == 1 and len(new) == 1 and D(min(new)) < D(min(old))
    current = tests[-1]
    assert D(current["threshold"]) < D(current["value"]) < D(current["reported_threshold"])
    assert current["reported_in_compliance"] is True and current["pass"] is False


def test_leverage_matches_a_hand_calculation(generated):
    """Recompute one covenant from the truth strings alone, with no help from the generator."""
    truth = generated.truths["harrowgate-precision"]
    now, prior_year, year_ago = _period(truth, CURRENT), _period(truth, "2025-12-31"), _period(truth, "2025-09-30")

    def ttm(key: str) -> Decimal:
        return D(now["values"][key]) + D(prior_year["values"][key]) - D(year_ago["values"][key])

    ebitda = ttm("is.net_income") + ttm("is.interest_expense") + ttm("is.income_tax_expense") + ttm("is.depreciation_amortization")
    debt = sum(D(now["values"][k]) for k in ("bs.revolver", "bs.cpltd", "bs.long_term_debt", "bs.subordinated_debt"))
    by_hand = (debt / ebitda).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    test = next(
        t for t in truth["expected"]["covenant_tests"] if t["period_end"] == CURRENT and t["covenant_id"] == "total_leverage"
    )
    assert D(test["value"]) == by_hand
    fixed_charges = ttm("sup.cash_interest_paid") + ttm("sup.scheduled_principal")
    cash_flow = ebitda - (ttm("cf.capex") - ttm("sup.financed_capex")) - ttm("sup.cash_taxes_paid")
    fccr = next(t for t in truth["expected"]["covenant_tests"] if t["period_end"] == CURRENT and t["covenant_id"] == "fccr")
    assert D(fccr["value"]) == (cash_flow / fixed_charges).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def test_borrowing_base_results(generated):
    with_base = [t for t in generated.truths.values() if t["borrowing_base"]]
    assert len(with_base) == 8
    for truth in with_base:
        terms = truth["terms_versions"][-1]["terms"]["borrowing_base"]
        assert [e["period_end"] for e in truth["borrowing_base"]] == ["2026-07-31", "2026-08-31", CURRENT]
        for entry, result in zip(truth["borrowing_base"], truth["expected"]["borrowing_base"], strict=True):
            c = {k: D(v) for k, v in result["calculated"].items()}
            gross = sum(D(x) for row in entry["ar_aging"] for x in row["buckets"].values())
            assert c["gross_ar"] == gross
            assert c["eligible_ar"] == c["gross_ar"] - c["total_ineligible_ar"]
            assert c["ar_availability"] == c["eligible_ar"] * D("0.85")  # a whole number by construction
            assert c["inventory_availability"] == min(c["eligible_inventory"] * D("0.50"), D(terms["components"][1]["sublimit"]))
            assert c["borrowing_base"] == c["ar_availability"] + c["inventory_availability"] - c["reserves"]
            assert c["availability"] == min(c["borrowing_base"], D(terms["commitment"])) - D(entry["outstanding"]) - D(entry["letters_of_credit"])
            assert result["over_advance"] == (c["availability"] < 0)
        # At the quarter end the collateral reports tie to the balance sheet.
        september = _period(truth, CURRENT)["values"]
        last = truth["borrowing_base"][-1]
        assert sum(D(row["total"]) for row in last["ar_aging"]) == D(september["bs.accounts_receivable"])
        assert sum(D(i["amount"]) for i in last["inventory"]) == D(september["bs.inventory"])
        assert D(last["outstanding"]) == D(september["bs.revolver"])
    over = _by_scenario(generated, "over_advance")["expected"]["borrowing_base"][-1]
    assert over["over_advance"] and over["certificate_matches"]
    miscount = _by_scenario(generated, "miscounted_ineligible")
    result = miscount["expected"]["borrowing_base"][-1]
    assert not result["certificate_matches"] and not result["over_advance"]
    lines = {d["line"]: D(d["certificate"]) - D(d["calculated"]) for d in result["differences"]}
    assert lines["ineligible_over_age"] == -D(miscount["scenario"]["details"]["over_90_counted_as_eligible"])
    assert lines["eligible_ar"] > 0
    assert sum(D(r["calculated"]["ineligible_concentration"]) > 0 for t in with_base for r in t["expected"]["borrowing_base"]) >= 1


def test_signals(generated):
    trend = _by_scenario(generated, "deteriorating_trend")
    rules = {s["rule"] for s in trend["expected"]["signals"] if s["period_end"] == CURRENT}
    assert {
        "revenue_ttm_decline", "ebitda_margin_decline", "dso_increase", "dpo_increase", "leverage_increase",
        "covenant_headroom_low", "covenant_headroom_falling", "line_usage_high", "payment_past_due",
    } <= rules  # fmt: skip
    late = _by_scenario(generated, "late_reporting")
    late_signals = [s for s in late["expected"]["signals"] if s["period_end"] == CURRENT]
    assert [s["rule"] for s in late_signals] == ["reporting_late"] and D(late_signals[0]["value"]) > 15
    assert not any(d["period_end"] == CURRENT for d in late["documents"])
    assert all(c["period_end"] != CURRENT for c in late["certificates"])
    over = _by_scenario(generated, "over_advance")
    assert "availability_low" in {s["rule"] for s in over["expected"]["signals"]}
    for truth in generated.truths.values():
        highs = [s for s in truth["expected"]["signals"] if s["period_end"] == CURRENT and s["severity"] == "high"]
        chasing = any(e["type"] == "intake.missing_document" for e in truth["expected"]["exceptions"])
        # a late-reporting warning joins the open chaser instead of raising its own item
        own_item = [s for s in highs if not (s["rule"] == "reporting_late" and chasing)]
        raised = [e for e in truth["expected"]["exceptions"] if e["type"] == "signal.high"]
        assert len(own_item) == len(raised)


def test_scale_trap_and_variance_details(generated):
    trap = _by_scenario(generated, "scale_trap")
    assert trap["scenario"]["details"] == {"statement_scale": 1000, "certificate_scale": 1}
    assert all(c["scale"] == 1 for c in trap["certificates"])
    assert all(p["scale"] == 1000 for p in trap["periods"])
    over_cap = _by_scenario(generated, "addback_over_cap")
    details = over_cap["scenario"]["details"]
    assert D(details["taken_by_borrower"]) > D(details["cap"])
    for t in over_cap["expected"]["covenant_tests"]:
        if t["period_end"] == CURRENT:
            assert t["pass"] and t["reported_in_compliance"] and D(t["reported_value"]) != D(t["value"])


def test_oracle_lists_every_current_expectation_unsigned(generated):
    with generated.oracle.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    wanted = 0
    for truth in generated.truths.values():
        e = truth["expected"]
        wanted += sum(t["period_end"] == CURRENT for t in e["covenant_tests"])
        wanted += sum(r["period_end"] == CURRENT for r in e["borrowing_base"])
        wanted += len(e["exceptions"])
    assert len(rows) == wanted
    assert {r["owner_signed_off"] for r in rows} == {"no"}
    assert {r["period_end"] for r in rows} == {CURRENT}
    assert {r["kind"] for r in rows} == {"covenant_test", "borrowing_base", "exception"}
    for column in ("borrower_id", "borrower_name", "item", "expected_outcome", "scenario"):
        assert all(r[column] for r in rows)

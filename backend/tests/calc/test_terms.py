import copy
from datetime import date
from decimal import Decimal as D

import pytest
from app.calc import errors as E
from app.calc.terms import Terms, TermsVersion, compare_terms, terms_in_force, threshold_in_force
from pydantic import ValidationError

CITE = {"field": "threshold", "document_id": "doc-ca-1", "section": "6.12(a)", "page": 41,
        "quote": "not less than 1.20 to 1.00"}


def terms_doc():
    return {
        "definitions": {
            "ebitda": {
                "base": "ebitda",
                "addbacks": [
                    {"name": "restructuring", "source_key": "is.nonrecurring_expense",
                     "cap": {"type": "pct_of", "value": "0.10", "of": "ebitda"},
                     "citation": {"document_id": "doc-ca-1", "section": "1.01", "page": 7, "quote": "not to exceed 10%"}},
                ],
            }
        },
        "covenants": [
            {
                "id": "fccr", "name": "Fixed Charge Coverage Ratio", "archetype": "coverage",
                "params": {"numerator_base": "adjusted_ebitda", "deductions": ["unfinanced_capex", "cash_taxes"],
                           "denominator": ["cash_interest", "scheduled_principal"]},
                "test": {"operator": ">=", "threshold": "1.20", "steps": [{"from": "2026-01-01", "value": "1.25"}],
                         "unit": "ratio"},
                "measurement": {"basis": "ttm", "frequency": "quarterly"},
                "rounding": {"dp": 2, "mode": "half_up"},
                "citations": [dict(CITE)],
            },
            {
                "id": "leverage", "name": "Total Leverage Ratio", "archetype": "leverage",
                "params": {"debt": "total_debt", "ebitda": "adjusted_ebitda"},
                "test": {"operator": "<=", "threshold": "3.50", "steps": [], "unit": "ratio"},
                "measurement": {"basis": "ttm", "frequency": "quarterly"},
                "rounding": {"dp": 2, "mode": "half_up"},
                "citations": [],
            },
        ],
        "reporting_requirements": [
            {"id": "annual_fs", "document_type": "financial_statements", "frequency": "annual",
             "due_days_after_period_end": 120, "quality": "audited",
             "citation": {"document_id": "doc-ca-1", "section": "5.01", "page": 30, "quote": "within 120 days"}},
        ],
        "borrowing_base": {
            "commitment": "5000000",
            "components": [
                {"collateral": "accounts_receivable", "advance_rate": "0.85",
                 "eligibility": {"max_age_days": 90, "cross_aging_pct": "0.50", "concentration_limit_pct": "0.25",
                                 "exclude": ["intercompany", "foreign", "government", "contra"]}},
                {"collateral": "inventory", "advance_rate": "0.50", "sublimit": "1500000",
                 "eligibility": {"exclude": ["work_in_process", "consigned"]}},
            ],
            "reserves": [{"name": "rent", "amount": "50000"}],
            "frequency": "monthly",
            "citation": {"document_id": "doc-ca-1", "section": "2.01", "page": 12, "quote": "Borrowing Base"},
        },
    }


def covenant(**changes):
    doc = terms_doc()
    doc["covenants"][0].update(changes)
    return doc


def rejects(doc, fragment=None):
    with pytest.raises(ValidationError) as info:
        Terms.model_validate(doc)
    if fragment:
        assert fragment in str(info.value)


# ---- parsing --------------------------------------------------------------------------


def test_spec_example_parses_to_decimals_and_dates():
    terms = Terms.model_validate(terms_doc())
    fccr = terms.covenants[0]
    assert fccr.test.threshold == D("1.20") and fccr.test.steps[0].from_ == date(2026, 1, 1)
    assert fccr.typed_params.denominator == ["cash_interest", "scheduled_principal"]
    assert terms.definitions["ebitda"].addbacks[0].cap.value == D("0.10")
    bb = terms.borrowing_base
    assert bb.commitment == D("5000000") and bb.components[0].advance_rate == D("0.85")
    assert bb.components[0].eligibility.max_age_days == 90 and bb.components[1].sublimit == D("1500000")
    assert bb.components[0].sublimit is None


def test_round_trips_through_json_with_decimals_as_strings():
    terms = Terms.model_validate(terms_doc())
    dumped = terms.model_dump(mode="json", by_alias=True, exclude_none=False)
    assert dumped["covenants"][0]["test"]["threshold"] == "1.20"
    assert dumped["covenants"][0]["test"]["steps"][0] == {"from": "2026-01-01", "value": "1.25"}
    assert Terms.model_validate(dumped) == terms


def test_borrowing_base_may_be_null_but_not_missing():
    doc = terms_doc()
    doc["borrowing_base"] = None
    assert Terms.model_validate(doc).borrowing_base is None
    del doc["borrowing_base"]
    rejects(doc, "borrowing_base")


# ---- unknown keys are rejected everywhere -----------------------------------------------


@pytest.mark.parametrize("path", [
    (),
    ("definitions", "ebitda"),
    ("definitions", "ebitda", "addbacks", 0),
    ("definitions", "ebitda", "addbacks", 0, "cap"),
    ("definitions", "ebitda", "addbacks", 0, "citation"),
    ("covenants", 0),
    ("covenants", 0, "params"),
    ("covenants", 0, "test"),
    ("covenants", 0, "test", "steps", 0),
    ("covenants", 0, "measurement"),
    ("covenants", 0, "rounding"),
    ("covenants", 0, "citations", 0),
    ("reporting_requirements", 0),
    ("borrowing_base",),
    ("borrowing_base", "components", 0),
    ("borrowing_base", "components", 0, "eligibility"),
    ("borrowing_base", "reserves", 0),
])
def test_unknown_key_is_rejected(path):
    doc = terms_doc()
    target = doc
    for part in path:
        target = target[part]
    target["surprise"] = "1"
    rejects(doc)


# ---- nothing is defaulted ---------------------------------------------------------------


@pytest.mark.parametrize("path", [
    ("definitions",), ("covenants",), ("reporting_requirements",),
    ("covenants", 0, "params"), ("covenants", 0, "params", "deductions"),
    ("covenants", 0, "params", "numerator_base"), ("covenants", 0, "test", "threshold"),
    ("covenants", 0, "test", "operator"), ("covenants", 0, "test", "unit"),
    ("covenants", 0, "measurement", "basis"), ("covenants", 0, "rounding"), ("covenants", 0, "rounding", "dp"),
    ("covenants", 1, "params", "debt"),
    ("borrowing_base", "commitment"), ("borrowing_base", "components", 0, "advance_rate"),
    ("borrowing_base", "components", 1, "eligibility", "exclude"), ("borrowing_base", "reserves"),
    ("definitions", "ebitda", "base"), ("definitions", "ebitda", "addbacks", 0, "source_key"),
])
def test_missing_calculation_field_is_rejected_not_defaulted(path):
    doc = terms_doc()
    target = doc
    for part in path[:-1]:
        target = target[part]
    del target[path[-1]]
    rejects(doc)


def test_floats_are_rejected():
    doc = terms_doc()
    doc["covenants"][0]["test"]["threshold"] = 1.2
    rejects(doc, "float")
    doc = terms_doc()
    doc["borrowing_base"]["components"][0]["advance_rate"] = 0.85
    rejects(doc, "float")
    doc = terms_doc()
    doc["definitions"]["ebitda"]["addbacks"][0]["cap"] = {"type": "amount", "value": 500000.0}
    rejects(doc, "float")


def test_bad_operator_archetype_mode_and_basis_are_rejected():
    rejects(covenant(test={"operator": "=>", "threshold": "1.20", "steps": [], "unit": "ratio"}))
    rejects(covenant(archetype="coverage_ratio"))
    rejects(covenant(rounding={"dp": 2, "mode": "half_even"}))
    rejects(covenant(measurement={"basis": "point", "frequency": "quarterly"}), "basis")


# ---- add-back caps -----------------------------------------------------------------------


def test_cap_absent_and_null_mean_uncapped_and_zero_is_a_real_cap():
    doc = terms_doc()
    addbacks = doc["definitions"]["ebitda"]["addbacks"]
    addbacks.append({"name": "no_cap_key", "source_key": "is.other_operating_expense"})
    addbacks.append({"name": "null_cap", "source_key": "is.sga", "cap": None})
    addbacks.append({"name": "zero_cap", "source_key": "is.cogs", "cap": {"type": "amount", "value": "0"}})
    parsed = {a.name: a for a in Terms.model_validate(doc).definitions["ebitda"].addbacks}
    assert parsed["no_cap_key"].cap is None and parsed["null_cap"].cap is None
    assert parsed["zero_cap"].cap is not None and parsed["zero_cap"].cap.value == D("0")
    assert parsed["restructuring"].cap.type == "pct_of" and parsed["restructuring"].cap.of == "ebitda"


def test_cap_refusals():
    for cap in ({"type": "amount", "value": "-1"}, {"type": "pct_of", "value": "0.10"},
                {"type": "amount", "value": "1", "of": "ebitda"}, {"type": "pct", "value": "0.1", "of": "ebitda"},
                {"type": "pct_of", "value": "0.10", "of": "ebitdax"},
                {"type": "pct_of", "value": "0.10", "of": {"op": "line", "key": "nope", "period": "ttm"}}):
        doc = terms_doc()
        doc["definitions"]["ebitda"]["addbacks"][0]["cap"] = cap
        rejects(doc)
    doc = terms_doc()
    doc["definitions"]["ebitda"]["addbacks"][0]["cap"] = {
        "type": "pct_of", "value": "0.10", "of": {"op": "line", "key": "is.revenue", "period": "ttm"}}
    Terms.model_validate(doc)


def test_addback_source_must_be_a_known_flow_line():
    for key in ("is.restructuring", "bs.cash"):
        doc = terms_doc()
        doc["definitions"]["ebitda"]["addbacks"][0]["source_key"] = key
        rejects(doc)
    doc = terms_doc()
    doc["definitions"]["ebitda"]["base"] = "ebitdax"
    rejects(doc)


# ---- duplicates ---------------------------------------------------------------------------


def test_duplicate_components_are_rejected():
    doc = terms_doc()
    doc["covenants"][0]["params"]["denominator"] = ["cash_interest", "cash_interest"]
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["covenants"][0]["params"]["deductions"] = ["cash_taxes", "cash_taxes"]
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["covenants"].append(copy.deepcopy(doc["covenants"][0]))
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["definitions"]["ebitda"]["addbacks"].append(copy.deepcopy(doc["definitions"]["ebitda"]["addbacks"][0]))
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["borrowing_base"]["components"].append(copy.deepcopy(doc["borrowing_base"]["components"][0]))
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["borrowing_base"]["reserves"].append({"name": "rent", "amount": "1"})
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["covenants"][0]["test"]["steps"].append({"from": "2026-01-01", "value": "1.30"})
    rejects(doc, "duplicate")
    doc = terms_doc()
    doc["borrowing_base"]["components"][0]["eligibility"]["exclude"].append("foreign")
    rejects(doc, "duplicate")


# ---- archetype parameters -------------------------------------------------------------------


def base_covenant(archetype, params, basis="point"):
    return {"id": "c", "name": "C", "archetype": archetype, "params": params,
            "test": {"operator": ">=", "threshold": "1", "steps": [], "unit": "ratio"},
            "measurement": {"basis": basis, "frequency": "quarterly"},
            "rounding": {"dp": 2, "mode": "half_up"}, "citations": []}


def with_covenant(cov):
    doc = terms_doc()
    doc["covenants"] = [cov]
    return doc


def test_coverage_needs_at_least_one_denominator_and_known_members():
    doc = terms_doc()
    doc["covenants"][0]["params"]["denominator"] = []
    rejects(doc)
    doc = terms_doc()
    doc["covenants"][0]["params"]["denominator"] = ["rent"]
    rejects(doc)
    doc = terms_doc()
    doc["covenants"][0]["params"]["deductions"] = ["dividends"]
    rejects(doc)
    doc = terms_doc()
    doc["covenants"][0]["params"]["deductions"] = []
    Terms.model_validate(doc)


def test_parameterless_archetypes_take_no_params():
    for archetype, basis in (("current_ratio", "point"), ("debt_to_tnw", "point"), ("max_capex", "fy")):
        Terms.model_validate(with_covenant(base_covenant(archetype, {}, basis)))
        rejects(with_covenant(base_covenant(archetype, {"x": 1}, basis)))


def test_min_tangible_net_worth_step_up_is_required_but_nullable():
    Terms.model_validate(with_covenant(base_covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": None})))
    ok = Terms.model_validate(with_covenant(base_covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": "0.50"})))
    assert ok.covenants[0].typed_params.step_up_pct_of_net_income == D("0.50")
    rejects(with_covenant(base_covenant("min_tangible_net_worth", {})))
    rejects(with_covenant(base_covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": 0.5})))


def test_min_liquidity_needs_a_real_boolean():
    Terms.model_validate(with_covenant(base_covenant("min_liquidity", {"include_availability": True})))
    rejects(with_covenant(base_covenant("min_liquidity", {"include_availability": "yes"})))
    rejects(with_covenant(base_covenant("min_liquidity", {})))


def test_custom_expression_is_validated():
    good = {"op": "div", "num": {"op": "named", "name": "adjusted_ebitda"},
            "den": {"op": "line", "key": "is.interest_expense", "period": "ttm"}}
    Terms.model_validate(with_covenant(base_covenant("custom", {"expression": good}, "ttm")))
    bad = {"op": "div", "num": {"op": "named", "name": "ebitdax"}, "den": {"op": "const", "value": "1"}}
    rejects(with_covenant(base_covenant("custom", {"expression": bad}, "ttm")))
    rejects(with_covenant(base_covenant("custom", {"expression": {"op": "pow"}}, "ttm")))
    rejects(with_covenant(base_covenant("custom", {}, "ttm")))


def test_adjusted_ebitda_needs_an_ebitda_definition():
    doc = terms_doc()
    doc["definitions"] = {}
    rejects(doc, "adjusted_ebitda")


def test_borrowing_base_component_rules():
    doc = terms_doc()
    doc["borrowing_base"]["components"][1]["eligibility"]["max_age_days"] = 90
    rejects(doc)  # ageing does not apply to inventory
    doc = terms_doc()
    doc["borrowing_base"]["components"][0]["eligibility"]["max_age_days"] = 45
    rejects(doc)  # not a bucket boundary
    doc = terms_doc()
    doc["borrowing_base"]["components"][0]["advance_rate"] = "1.5"
    rejects(doc)
    doc = terms_doc()
    del doc["borrowing_base"]["components"][0]["eligibility"]["max_age_days"]
    rejects(doc)  # cross-ageing needs an age limit
    del doc["borrowing_base"]["components"][0]["eligibility"]["cross_aging_pct"]
    Terms.model_validate(doc)


# ---- step thresholds ----------------------------------------------------------------------


def test_threshold_in_force_on_and_around_the_step_date():
    test = Terms.model_validate(terms_doc()).covenants[0].test
    assert threshold_in_force(test, date(2025, 12, 31)) == D("1.20")
    assert threshold_in_force(test, date(2026, 1, 1)) == D("1.25")
    assert threshold_in_force(test, date(2026, 3, 31)) == D("1.25")


def test_latest_step_wins_regardless_of_order():
    doc = terms_doc()
    doc["covenants"][0]["test"]["steps"] = [
        {"from": "2026-07-01", "value": "1.35"}, {"from": "2026-01-01", "value": "1.25"}]
    test = Terms.model_validate(doc).covenants[0].test
    assert threshold_in_force(test, date(2026, 6, 30)) == D("1.25")
    assert threshold_in_force(test, date(2026, 7, 1)) == D("1.35")
    assert threshold_in_force(test, date(2025, 6, 30)) == D("1.20")


# ---- which version governs -------------------------------------------------------------------


def version(number, status, start, end, doc=None):
    return TermsVersion.model_validate({
        "version": number, "status": status, "effective_from": start, "effective_to": end,
        "prepared_by": "analyst-1", "approved_by": None if status == "proposed" else "officer-1",
        "terms": doc or terms_doc(),
    })


V1 = version(1, "superseded", "2024-01-01", "2025-06-30")
V2 = version(2, "approved", "2025-07-01", None)
V3 = version(3, "proposed", "2025-10-01", None)


def test_version_whose_dates_contain_the_period_end_governs():
    assert terms_in_force([V1, V2, V3], date(2024, 12, 31)).version is V1
    assert terms_in_force([V1, V2, V3], date(2025, 6, 30)).version is V1  # last day of the old terms
    assert terms_in_force([V1, V2, V3], date(2025, 7, 1)).version is V2  # first day of the new terms
    assert terms_in_force([V3, V2, V1], date(2025, 12, 31)).version is V2


def test_proposed_version_never_governs():
    result = terms_in_force([V3], date(2025, 12, 31))
    assert result.version is None and result.error.code == E.NO_TERMS_IN_FORCE
    assert result.error.detail["proposed_versions"] == [3]
    assert terms_in_force([V1, V2, V3], date(2025, 12, 31)).version is V2


def test_no_terms_in_force_before_the_first_version_or_with_none():
    assert terms_in_force([V1, V2], date(2023, 12, 31)).error.code == E.NO_TERMS_IN_FORCE
    assert terms_in_force([], date(2025, 12, 31)).error.code == E.NO_TERMS_IN_FORCE


def test_overlapping_approved_versions_are_ambiguous():
    overlap = version(4, "approved", "2025-01-01", None)
    result = terms_in_force([V2, overlap], date(2025, 12, 31))
    assert result.version is None and result.error.code == E.AMBIGUOUS_TERMS


def test_terms_in_force_accepts_dicts_and_reports_invalid_ones():
    raw = V2.model_dump(mode="json", by_alias=True)
    assert terms_in_force([raw], date(2025, 12, 31)).version == V2
    raw["terms"]["covenants"][0]["test"]["threshold"] = 1.2
    assert terms_in_force([raw], date(2025, 12, 31)).error.code == E.INVALID_TERMS


def test_version_dates_must_be_ordered():
    with pytest.raises(ValidationError):
        version(1, "approved", "2025-07-01", "2025-06-30")


# ---- terms drift --------------------------------------------------------------------------------


def diff(used_doc, approved_doc=None, **kw):
    return {d.path: (d.kind, d.used, d.approved) for d in compare_terms(used_doc, approved_doc or terms_doc(), **kw)}


def test_identical_terms_have_no_differences():
    assert compare_terms(terms_doc(), Terms.model_validate(terms_doc())) == []


def test_numerically_equal_decimals_are_not_differences():
    used = terms_doc()
    used["covenants"][0]["test"]["threshold"] = "1.2"
    used["borrowing_base"]["components"][0]["advance_rate"] = "0.850"
    assert compare_terms(used, terms_doc()) == []


def test_threshold_and_step_differences():
    used = terms_doc()
    used["covenants"][0]["test"]["threshold"] = "1.10"
    used["covenants"][0]["test"]["steps"] = []
    used["covenants"][1]["test"]["steps"] = [{"from": "2026-01-01", "value": "3.25"}]
    assert diff(used) == {
        "covenants[fccr].test.threshold": ("changed", D("1.10"), D("1.20")),
        "covenants[fccr].test.steps[2026-01-01]": ("removed", None, D("1.25")),
        "covenants[leverage].test.steps[2026-01-01]": ("added", D("3.25"), None),
    }


def test_addback_and_cap_differences():
    used = terms_doc()
    addbacks = used["definitions"]["ebitda"]["addbacks"]
    addbacks[0]["cap"] = None
    addbacks.append({"name": "synergies", "source_key": "is.other_operating_expense",
                     "cap": {"type": "amount", "value": "250000"}})
    found = diff(used)
    assert found["definitions[ebitda].addbacks[restructuring].cap"][0] == "changed"
    assert found["definitions[ebitda].addbacks[restructuring].cap"][1] is None
    assert found["definitions[ebitda].addbacks[synergies]"][0] == "added"
    assert len(found) == 2


def test_covenant_param_and_presence_differences():
    used = terms_doc()
    used["covenants"][0]["params"]["deductions"] = ["cash_taxes"]
    del used["covenants"][1]
    found = diff(used)
    assert found["covenants[fccr].params.deductions"] == ("changed", ["cash_taxes"], ["cash_taxes", "unfinanced_capex"])
    assert found["covenants[leverage]"][0] == "removed"
    assert len(found) == 2


def test_borrowing_base_differences():
    used = terms_doc()
    used["borrowing_base"]["components"][0]["advance_rate"] = "0.90"
    used["borrowing_base"]["components"][0]["eligibility"]["exclude"].remove("government")
    used["borrowing_base"]["reserves"] = []
    found = diff(used)
    assert found["borrowing_base.components[accounts_receivable].advance_rate"] == ("changed", D("0.90"), D("0.85"))
    assert "borrowing_base.components[accounts_receivable].eligibility.exclude" in found
    assert found["borrowing_base.reserves[rent]"] == ("removed", None, D("50000"))
    none = terms_doc()
    none["borrowing_base"] = None
    assert diff(none)["borrowing_base"][0] == "removed"


def test_citations_are_ignored_unless_asked_for():
    used = terms_doc()
    used["covenants"][0]["citations"][0]["quote"] = "not less than 1.10 to 1.00"
    assert compare_terms(used, terms_doc()) == []
    assert [d.path for d in compare_terms(used, terms_doc(), include_citations=True)] == [
        "covenants[fccr].citations[0].quote"]

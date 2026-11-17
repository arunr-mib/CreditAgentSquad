from datetime import date
from decimal import Decimal as D

from app.calc import errors as E
from app.calc.expr import ENGINE_VERSION, evaluate, validate_node
from app.calc.periods import FactValue, provider_from_facts

PE = date(2025, 6, 30)
PRIOR_FYE = date(2024, 12, 31)
PRIOR_PE = date(2024, 6, 30)

FACTS = {
    ("is.net_income", PE, 6): FactValue(D("-30000"), "f-ni-h1"),
    ("is.net_income", PRIOR_FYE, 12): FactValue(D("360000"), "f-ni-fy"),
    ("is.net_income", PRIOR_PE, 6): FactValue(D("180000"), "f-ni-h1-prior"),
    ("is.interest_expense", PE, 6): D("60000"),
    ("is.interest_expense", PRIOR_FYE, 12): D("120000"),
    ("is.interest_expense", PRIOR_PE, 6): D("60000"),
    ("is.nonrecurring_expense", PE, 6): D("200000"),
    ("is.nonrecurring_expense", PRIOR_FYE, 12): D("0"),
    ("is.nonrecurring_expense", PRIOR_PE, 6): D("0"),
    ("bs.cash", PE, 6): FactValue(D("200000"), "f-cash"),
    ("bs.revolver", PE, 6): D("600000"),
    ("bs.total_equity", PE, 6): D("-50000"),
    ("bs.intangibles", PE, 6): D("0"),
    ("bs.cash", PRIOR_PE, 6): D("250000"),
}
PROVIDER = provider_from_facts(FACTS)

NI_TTM = {"op": "line", "key": "is.net_income", "period": "ttm"}  # -30,000 + 360,000 - 180,000 = 150,000
INT_TTM = {"op": "line", "key": "is.interest_expense", "period": "ttm"}  # 60 + 120 - 60 = 120,000
NONREC_TTM = {"op": "line", "key": "is.nonrecurring_expense", "period": "ttm"}  # 200,000
CASH = {"op": "line", "key": "bs.cash", "period": "point"}
REVOLVER = {"op": "line", "key": "bs.revolver", "period": "point"}


def const(v):
    return {"op": "const", "value": v}


def run(node, **kw):
    return evaluate(node, PE, PROVIDER, **kw)


def codes(result):
    return [e.code for e in result.errors]


# ---- arithmetic ------------------------------------------------------------------


def test_const_and_line():
    assert run(const("1.25")).value == D("1.25")
    result = run(CASH)
    assert result.ok and result.value == D("200000")
    assert result.engine_version == ENGINE_VERSION


def test_add_sub_mul_min_max():
    assert run({"op": "add", "args": [NI_TTM, INT_TTM]}).value == D("270000")
    assert run({"op": "sub", "args": [REVOLVER, CASH, const("50000")]}).value == D("350000")
    assert run({"op": "mul", "args": [const("0.10"), INT_TTM]}).value == D("12000")
    assert run({"op": "min", "args": [CASH, REVOLVER, const("900000")]}).value == D("200000")
    assert run({"op": "max", "args": [CASH, REVOLVER]}).value == D("600000")


def test_div_and_rounding_only_at_the_end():
    node = {"op": "div", "num": REVOLVER, "den": {"op": "add", "args": [NI_TTM, INT_TTM]}}
    result = run(node, rounding={"dp": 2, "mode": "half_up"})
    # 600,000 / 270,000 = 2.2222...
    assert result.rounded == D("2.22") and str(result.rounded) == "2.22"
    assert result.value != result.rounded and abs(result.value - D("2.222222222222")) < D("1e-12")
    # A product of the unrounded quotient: 2.2222... x 9 = 20, not 2.22 x 9 = 19.98.
    result = run({"op": "mul", "args": [node, const("9")]}, rounding={"dp": 2, "mode": "half_up"})
    assert result.rounded == D("20.00")


def test_rounding_is_half_up():
    assert run(const("1.245"), rounding={"dp": 2, "mode": "half_up"}).rounded == D("1.25")
    assert run(const("2.5"), rounding={"dp": 0, "mode": "half_up"}).rounded == D("3")
    assert run(const("1.245")).rounded is None


def test_bad_rounding_spec_is_an_error():
    for bad in ({"dp": 2, "mode": "half_even"}, {"dp": 2}, {"dp": 2, "mode": "half_up", "x": 1},
                {"dp": -1, "mode": "half_up"}, {"dp": 2.0, "mode": "half_up"}, "2dp"):
        result = run(const("1"), rounding=bad)
        assert codes(result) == [E.INVALID_ROUNDING] and result.rounded is None


def test_denominator_zero_or_negative_is_an_error():
    zero = run({"op": "div", "num": CASH, "den": {"op": "line", "key": "bs.intangibles", "period": "point"}})
    assert zero.value is None and codes(zero) == [E.NON_POSITIVE_DENOMINATOR]
    negative = run({"op": "div", "num": CASH, "den": {"op": "line", "key": "bs.total_equity", "period": "point"}})
    assert negative.value is None and codes(negative) == [E.NON_POSITIVE_DENOMINATOR]
    assert negative.errors[0].detail["denominator"] == D("-50000")


# ---- trace -------------------------------------------------------------------------


def test_trace_lists_every_input_fact_once_in_order():
    node = {"op": "div", "num": {"op": "add", "args": [NI_TTM, INT_TTM]}, "den": INT_TTM}
    result = run(node, calc_id="calc-42")
    assert result.calc_id == "calc-42"
    assert [(i.key, i.period_end, i.months, i.sign) for i in result.trace.inputs] == [
        ("is.net_income", PE, 6, 1),
        ("is.net_income", PRIOR_FYE, 12, 1),
        ("is.net_income", PRIOR_PE, 6, -1),
        ("is.interest_expense", PE, 6, 1),
        ("is.interest_expense", PRIOR_FYE, 12, 1),
        ("is.interest_expense", PRIOR_PE, 6, -1),
    ]
    assert [i.fact_id for i in result.trace.inputs[:3]] == ["f-ni-h1", "f-ni-fy", "f-ni-h1-prior"]
    assert result.trace.inputs[0].value == D("-30000")
    # Every node is traced with its value; the last step is the root.
    assert result.trace.steps[-1].op == "div" and result.trace.steps[-1].value == result.value
    assert [s.op for s in result.trace.steps] == ["line", "line", "add", "line", "div"]


# ---- refusals ------------------------------------------------------------------------


def test_missing_input_names_line_and_period():
    node = {"op": "add", "args": [{"op": "line", "key": "is.revenue", "period": "ttm"}, CASH]}
    result = run(node, rounding={"dp": 0, "mode": "half_up"})
    assert result.value is None and result.rounded is None
    assert [(e.code, e.key, e.period_end, e.months) for e in result.errors] == [
        (E.MISSING_INPUT, "is.revenue", PE, 6),
        (E.MISSING_INPUT, "is.revenue", PRIOR_FYE, 12),
        (E.MISSING_INPUT, "is.revenue", PRIOR_PE, 6),
    ]
    assert [i.key for i in result.trace.inputs] == ["bs.cash"]  # what was read is still traced


def test_unknown_op_unknown_key_and_unknown_line():
    assert codes(run({"op": "pow", "args": [CASH]})) == [E.UNKNOWN_OP]
    assert codes(run({"op": "line", "key": "bs.cash", "period": "point", "scale": "1000"})) == [E.UNKNOWN_KEY]
    assert codes(run({"op": "line", "key": "bs.cash_and_stuff", "period": "point"})) == [E.UNKNOWN_LINE]
    assert codes(run({"op": "div", "num": CASH, "den": REVOLVER, "args": []})) == [E.UNKNOWN_KEY]


def test_malformed_nodes_are_errors_not_exceptions():
    for bad in (None, "bs.cash", 5, [], {}, {"op": "line", "key": "bs.cash"}, {"op": "add", "args": []},
                {"op": "add", "args": CASH}, {"op": "sub", "args": [CASH]}, {"op": "div", "num": CASH},
                {"op": "const"}, {"op": "const", "value": "abc"}, {"op": "const", "value": None},
                {"op": "named"}, {"op": "line", "key": "bs.cash", "period": "qtd"}):
        result = run(bad)
        assert result.value is None and len(result.errors) == 1, bad
        assert result.errors[0].code in (E.INVALID_NODE, E.INVALID_VALUE, E.INVALID_PERIOD_MODE), bad


def test_float_constant_is_refused():
    result = run({"op": "mul", "args": [CASH, const(1.25)]})
    assert result.value is None and codes(result) == [E.FLOAT_NOT_ALLOWED]


def test_float_fact_is_refused():
    result = evaluate(CASH, PE, lambda k, p, m: FactValue(200000.0, "f"))
    assert result.value is None and codes(result) == [E.FLOAT_NOT_ALLOWED]


def test_duplicate_component_in_a_sum_is_an_error():
    result = run({"op": "add", "args": [INT_TTM, NI_TTM, dict(INT_TTM)]})
    assert result.value is None and codes(result) == [E.DUPLICATE_COMPONENT]
    result = run({"op": "sub", "args": [REVOLVER, CASH, CASH]})
    assert codes(result) == [E.DUPLICATE_COMPONENT]
    # The same line in numerator and denominator is not a duplicate component.
    assert run({"op": "div", "num": {"op": "add", "args": [NI_TTM, INT_TTM]}, "den": INT_TTM}).ok


# ---- named definitions ---------------------------------------------------------------

DEFS = {
    "earnings": {"op": "add", "args": [NI_TTM, INT_TTM]},  # 270,000
    "coverage": {"op": "div", "num": {"op": "named", "name": "earnings"}, "den": INT_TTM},  # 2.25
    "loop_a": {"op": "add", "args": [{"op": "named", "name": "loop_b"}, const("1")]},
    "loop_b": {"op": "named", "name": "loop_a"},
}


def test_named_definitions_resolve_and_nest():
    result = run({"op": "named", "name": "coverage"}, definitions=DEFS, rounding={"dp": 2, "mode": "half_up"})
    assert result.rounded == D("2.25")
    assert len(result.trace.inputs) == 6
    assert [s.label for s in result.trace.steps if s.op == "named"] == ["earnings", "coverage"]


def test_unknown_and_circular_definitions_are_errors():
    assert codes(run({"op": "named", "name": "ebitda"}, definitions=DEFS)) == [E.UNKNOWN_DEFINITION]
    assert codes(run({"op": "named", "name": "ebitda"})) == [E.UNKNOWN_DEFINITION]
    result = run({"op": "named", "name": "loop_a"}, definitions=DEFS)
    assert result.value is None and codes(result) == [E.CIRCULAR_DEFINITION]


def test_a_definition_used_twice_is_evaluated_once():
    calls = []

    def get(key, period_end, months):
        calls.append(key)
        return PROVIDER(key, period_end, months)

    node = {"op": "div", "num": {"op": "named", "name": "earnings"},
            "den": {"op": "max", "args": [{"op": "named", "name": "earnings"}, const("1")]}}
    result = evaluate(node, PE, get, definitions=DEFS)
    assert result.value == D("1") and len(calls) == 6


# ---- add-backs -----------------------------------------------------------------------


def addback(cap="omit", name="restructuring", source=NONREC_TTM):
    node = {"op": "addback", "name": name, "source": source}
    if cap != "omit":
        node["cap"] = cap
    return node


def test_addback_null_cap_and_absent_cap_are_uncapped():
    for node in (addback(None), addback()):
        result = run({"op": "add", "args": [NI_TTM, node]})
        assert result.value == D("350000")  # 150,000 + 200,000
        (ab,) = result.trace.addbacks
        assert (ab.name, ab.raw, ab.cap_type, ab.cap_limit, ab.applied, ab.capped) == (
            "restructuring", D("200000"), None, None, D("200000"), False)


def test_addback_cap_zero_is_not_the_same_as_no_cap():
    result = run({"op": "add", "args": [NI_TTM, addback({"type": "amount", "value": "0"})]})
    assert result.value == D("150000")
    (ab,) = result.trace.addbacks
    assert (ab.raw, ab.cap_type, ab.cap_limit, ab.applied, ab.capped) == (D("200000"), "amount", D("0"), D("0"), True)


def test_addback_amount_cap_binds_only_when_exceeded():
    capped = run(addback({"type": "amount", "value": "150000"}))
    assert capped.value == D("150000") and capped.trace.addbacks[0].capped is True
    loose = run(addback({"type": "amount", "value": "500000"}))
    assert loose.value == D("200000") and loose.trace.addbacks[0].capped is False
    exact = run(addback({"type": "amount", "value": "200000"}))
    assert exact.value == D("200000") and exact.trace.addbacks[0].capped is False


def test_addback_cap_as_percent_of_another_expression():
    defs = {"earnings": DEFS["earnings"]}
    cap = {"type": "pct_of", "value": "0.10", "of": {"op": "named", "name": "earnings"}}
    result = run({"op": "add", "args": [{"op": "named", "name": "earnings"}, addback(cap)]}, definitions=defs)
    # cap = 10% x 270,000 = 27,000; 270,000 + 27,000
    assert result.value == D("297000")
    (ab,) = result.trace.addbacks
    assert (ab.raw, ab.cap_type, ab.cap_value, ab.cap_limit, ab.applied, ab.capped) == (
        D("200000"), "pct_of", D("0.10"), D("27000.00"), D("27000.00"), True)


def test_addback_refusals():
    assert codes(run(addback({"type": "amount", "value": "-1"}))) == [E.NEGATIVE_CAP]
    assert codes(run(addback({"type": "share", "value": "0.1"}))) == [E.INVALID_NODE]
    assert codes(run(addback({"type": "amount", "value": "1", "of": CASH}))) == [E.UNKNOWN_KEY]
    assert codes(run(addback({"type": "pct_of", "value": "0.1"}))) == [E.INVALID_NODE]
    assert codes(run(addback({"type": "amount", "value": 500000.0}))) == [E.FLOAT_NOT_ALLOWED]
    assert codes(run(addback("500000"))) == [E.INVALID_NODE]
    assert codes(run({"op": "addback", "source": NONREC_TTM, "cap": None})) == [E.INVALID_NODE]
    # A percent cap of a negative base would turn the add-back into a deduction: refuse.
    negative_base = {"type": "pct_of", "value": "0.10", "of": {"op": "line", "key": "bs.total_equity", "period": "point"}}
    assert codes(run(addback(negative_base))) == [E.NEGATIVE_CAP]


def test_addback_missing_source_is_an_error_not_zero():
    source = {"op": "line", "key": "is.sga", "period": "ttm"}
    result = run({"op": "add", "args": [NI_TTM, addback(None, source=source)]})
    assert result.value is None and {e.code for e in result.errors} == {E.MISSING_INPUT}
    assert result.trace.addbacks == []


def test_the_same_addback_twice_is_a_duplicate_component():
    other_source = {"op": "line", "key": "is.interest_expense", "period": "ttm"}
    result = run({"op": "add", "args": [NI_TTM, addback(None), addback(None, source=other_source)]})
    assert result.value is None and codes(result) == [E.DUPLICATE_COMPONENT]


# ---- shift (extension used for year-on-year metrics) ---------------------------------


def test_shift_evaluates_at_an_earlier_period_end():
    node = {"op": "sub", "args": [CASH, {"op": "shift", "months": -12, "arg": CASH}]}
    result = run(node)
    assert result.value == D("-50000")  # 200,000 - 250,000
    assert [(i.key, i.period_end) for i in result.trace.inputs] == [("bs.cash", PE), ("bs.cash", PRIOR_PE)]
    assert codes(run({"op": "shift", "months": "12", "arg": CASH})) == [E.INVALID_NODE]
    assert codes(run({"op": "shift", "months": -24, "arg": CASH})) == [E.MISSING_INPUT]


# ---- validation without evaluation ----------------------------------------------------


def test_validate_node_reports_structure_errors_without_facts():
    good = {"op": "div", "num": {"op": "named", "name": "anything"},
            "den": {"op": "add", "args": [INT_TTM, addback({"type": "amount", "value": "5"})]}}
    assert validate_node(good) == []
    bad = {"op": "div", "num": {"op": "line", "key": "nope", "period": "ttm"},
           "den": {"op": "add", "args": [INT_TTM, INT_TTM]}, "extra": 1}
    assert sorted(e.code for e in validate_node(bad)) == [E.UNKNOWN_KEY]
    bad.pop("extra")
    assert sorted(e.code for e in validate_node(bad)) == [E.DUPLICATE_COMPONENT, E.UNKNOWN_LINE]


def test_period_end_must_be_a_date():
    result = evaluate(CASH, "2025-06-30", PROVIDER)
    assert result.value is None and codes(result) == [E.INVALID_PERIOD]

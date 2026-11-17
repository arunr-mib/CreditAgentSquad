import copy
from decimal import Decimal as D

import pytest
from app.calc import errors as E
from app.calc.borrowing_base import ArRow, InventoryRow, compute_borrowing_base, reconcile
from app.calc.terms import BorrowingBase

TERMS = {
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
}


def ar(customer, current="0", d1_30="0", d31_60="0", d61_90="0", over_90="0", flags=()):
    return ArRow(customer, D(current), D(d1_30), D(d31_60), D(d61_90), D(over_90), frozenset(flags))


# customer            current   1-30    31-60   61-90   over 90     total
AGING = [
    ar("Alpha", "400000", "100000"),                                   # 500,000
    ar("Beta", "200000", "50000", "30000", "20000", "40000"),          # 340,000; 40,000 aged (11.8%)
    ar("Gamma", "20000", "0", "0", "10000", "70000"),                  # 100,000; 70% aged: cross-aged
    ar("Delta", "150000", over_90="10000", flags=["intercompany"]),    # 160,000 excluded
    ar("Epsilon", "60000", flags=["foreign"]),                         # 60,000 excluded
    ar("Zeta", "900000"),                                              # 900,000; over concentration
    ar("Eta", "250000", "50000"),                                      # 300,000
    ar("Theta", "50000", over_90="50000"),                             # 100,000; exactly 50% aged
]
INVENTORY = [
    InventoryRow("raw_materials", D("600000")),
    InventoryRow("work_in_process", D("200000")),
    InventoryRow("finished_goods", D("900000")),
    InventoryRow("consigned", D("100000")),
]

# Hand computation, in the documented order:
#   total receivables                                         2,460,000
#   1 exclusions   Delta 160,000 + Epsilon 60,000               220,000
#   2 age          Beta 40,000 + Gamma 70,000 + Theta 50,000    160,000
#   3 cross-aging  Gamma remainder (70% > 50%)                   30,000
#     eligible before concentration                           2,050,000
#   4 concentration limit 25% x 2,050,000 = 512,500; Zeta 900,000 - 512,500 = 387,500
#   eligible receivables                                      1,662,500
#   receivables availability 85%                              1,413,125
#   inventory 1,800,000 less WIP 200,000 and consigned 100,000 = 1,500,000 eligible
#   inventory availability 50% = 750,000 (sublimit 1,500,000 not reached)
#   borrowing base = 1,413,125 + 750,000 - 50,000 reserves    2,113,125
#   availability = min(2,113,125, 5,000,000) - 1,700,000 - 100,000 = 313,125
EXPECTED = {
    "ar_total": "2460000",
    "ar_ineligible_excluded": "220000",
    "ar_ineligible_age": "160000",
    "ar_ineligible_cross_aging": "30000",
    "ar_ineligible_concentration": "387500",
    "ar_ineligible_total": "797500",
    "ar_eligible": "1662500",
    "ar_availability": "1413125",
    "inventory_total": "1800000",
    "inventory_ineligible": "300000",
    "inventory_eligible": "1500000",
    "inventory_availability_before_sublimit": "750000",
    "inventory_availability": "750000",
    "reserves": "50000",
    "borrowing_base": "2113125",
    "commitment": "5000000",
    "borrowing_limit": "2113125",
    "outstanding": "1700000",
    "letters_of_credit": "100000",
    "availability": "313125",
    "over_advance": "0",
}


def compute(aging=AGING, inventory=INVENTORY, terms=TERMS, outstanding="1700000", lcs="100000"):
    return compute_borrowing_base(aging, inventory, terms, D(outstanding), D(lcs))


def changed(**eligibility):
    terms = copy.deepcopy(TERMS)
    for key, value in eligibility.items():
        if value is None:
            terms["components"][0]["eligibility"].pop(key, None)
        else:
            terms["components"][0]["eligibility"][key] = value
    return terms


def test_worked_example_every_line():
    result = compute()
    assert result.errors == []
    assert {k: str(v) for k, v in result.lines.items()} == EXPECTED
    assert result.availability == D("313125") and result.over_advance == D("0")
    assert result.is_over_advance is False
    assert result.excluded_by_flag == {"intercompany": D("160000"), "foreign": D("60000")}
    assert result.inventory_ineligible_by_category == {"work_in_process": D("200000"), "consigned": D("100000")}


def test_no_double_counting_per_customer():
    result = compute()
    by_customer = {c.customer: c for c in result.customers}
    gamma = by_customer["Gamma"]
    assert (gamma.total, gamma.excluded, gamma.age, gamma.cross_aging, gamma.concentration, gamma.eligible) == (
        D("100000"), D("0"), D("70000"), D("30000"), D("0"), D("0"))
    delta = by_customer["Delta"]  # excluded as a whole: its over-90 balance is not also counted as aged
    assert (delta.excluded, delta.age, delta.eligible, delta.excluded_flag) == (D("160000"), D("0"), D("0"), "intercompany")
    zeta = by_customer["Zeta"]
    assert (zeta.concentration, zeta.eligible) == (D("387500"), D("512500"))
    for c in result.customers:
        assert c.excluded + c.age + c.cross_aging + c.concentration + c.eligible == c.total
    assert sum(c.eligible for c in result.customers) == D("1662500")


def test_cross_aging_triggers_only_above_the_percentage():
    by_customer = {c.customer: c for c in compute().customers}
    theta = by_customer["Theta"]  # exactly 50% aged: not cross-aged
    assert (theta.age, theta.cross_aging, theta.eligible) == (D("50000"), D("0"), D("50000"))
    aging = [ar("Theta", "49999", over_90="50001"), ar("Alpha", "400000")]
    theta = compute(aging, terms=changed(concentration_limit_pct=None)).customers[0]
    assert (theta.age, theta.cross_aging, theta.eligible) == (D("50001"), D("49999"), D("0"))


def test_cross_aging_not_applied_when_terms_have_none():
    result = compute(terms=changed(cross_aging_pct=None))
    gamma = {c.customer: c for c in result.customers}["Gamma"]
    assert (gamma.age, gamma.cross_aging, gamma.eligible) == (D("70000"), D("0"), D("30000"))
    assert result.lines["ar_ineligible_cross_aging"] == D("0")


def test_age_limit_follows_the_bucket_boundary():
    result = compute(terms=changed(max_age_days=60, cross_aging_pct=None, concentration_limit_pct=None))
    # over 60 days: Beta 20,000 + 40,000; Gamma 10,000 + 70,000; Theta 50,000
    assert result.lines["ar_ineligible_age"] == D("190000")
    none = compute(terms=changed(max_age_days=None, cross_aging_pct=None, concentration_limit_pct=None))
    assert none.lines["ar_ineligible_age"] == D("0") and none.lines["ar_eligible"] == D("2240000")


def test_concentration_edge_cases():
    # Exactly at the limit: four equal customers are each 25% of eligible, so nothing is cut.
    four = [ar(name, "100000") for name in ("A", "B", "C", "D")]
    assert compute(four, []).lines["ar_ineligible_concentration"] == D("0")
    # One dollar over the limit of 25% x 400,001 = 100,000.25: the excess is 0.75, shown to the dollar.
    over = [ar("A", "100001"), ar("B", "100000"), ar("C", "100000"), ar("D", "100000")]
    result = compute(over, [])
    assert result.customers[0].concentration == D("0.75")
    assert result.lines["ar_ineligible_concentration"] == D("1") and result.lines["ar_eligible"] == D("400000")
    # The limit is measured on what is left after age: an aged-down customer is not over it.
    aged = [ar("A", "100000", over_90="60000"), ar("B", "100000"), ar("C", "100000"), ar("D", "100000")]
    result = compute(aged, [], terms=changed(cross_aging_pct=None))
    assert result.lines["ar_ineligible_age"] == D("60000") and result.lines["ar_ineligible_concentration"] == D("0")
    # A single customer is held to the limit of its own eligible balance.
    assert compute([ar("Only", "400000")], []).lines["ar_eligible"] == D("100000")
    # No limit in the terms: nothing is cut.
    assert compute(terms=changed(concentration_limit_pct=None)).lines["ar_ineligible_concentration"] == D("0")


def test_exclusion_flags():
    aging = [ar("A", "100", flags=["government"]), ar("B", "200", flags=["contra", "foreign"]),
             ar("C", "300", flags=["bill_and_hold"]), ar("D", "400")]
    result = compute(aging, [], terms=changed(concentration_limit_pct=None))
    # B carries two excluded flags but is counted once, under the first one listed in the terms.
    assert result.excluded_by_flag == {"foreign": D("200"), "government": D("100")}
    assert result.lines["ar_ineligible_excluded"] == D("300")
    assert result.lines["ar_eligible"] == D("700")  # bill_and_hold is not excluded by these terms


def test_inventory_sublimit_binds():
    terms = copy.deepcopy(TERMS)
    terms["components"][1]["sublimit"] = "600000"
    result = compute(terms=terms)
    assert result.lines["inventory_availability_before_sublimit"] == D("750000")
    assert result.lines["inventory_availability"] == D("600000")
    assert result.lines["borrowing_base"] == D("1963125")  # 1,413,125 + 600,000 - 50,000
    del terms["components"][1]["sublimit"]
    assert compute(terms=terms).lines["inventory_availability"] == D("750000")  # absent sublimit: no limit


def test_over_advance():
    result = compute(outstanding="2200000")
    # 2,113,125 - 2,200,000 - 100,000
    assert result.availability == D("-186875") and result.over_advance == D("186875")
    assert result.is_over_advance is True
    exact = compute(outstanding="2013125")
    assert exact.availability == D("0") and exact.over_advance == D("0") and exact.is_over_advance is False


def test_commitment_caps_the_borrowing_limit():
    terms = copy.deepcopy(TERMS)
    terms["commitment"] = "2000000"
    result = compute(terms=terms)
    assert result.lines["borrowing_base"] == D("2113125") and result.lines["borrowing_limit"] == D("2000000")
    assert result.availability == D("200000")


def test_rounding_happens_once_at_the_end_of_each_line():
    terms = copy.deepcopy(TERMS)
    terms["components"][0]["eligibility"] = {"exclude": []}
    terms["reserves"] = []
    result = compute([ar("A", "1001")], [InventoryRow("finished_goods", D("501"))], terms, "0", "0")
    assert result.lines["ar_availability"] == D("851")  # 850.85
    assert result.lines["inventory_availability"] == D("251")  # 250.5, half-up
    assert result.lines["borrowing_base"] == D("1101")  # 850.85 + 250.5 = 1,101.35, not 851 + 251


def test_receivables_only_terms_leave_inventory_lines_empty():
    terms = copy.deepcopy(TERMS)
    del terms["components"][1]
    result = compute(terms=terms)
    assert result.errors == []
    assert result.lines["inventory_eligible"] is None and result.lines["inventory_availability"] is None
    assert result.lines["borrowing_base"] == D("1363125")  # 1,413,125 - 50,000


def test_refusals():
    negative = compute([ar("A", "100", d1_30="-5")], [])
    assert negative.availability is None and [e.code for e in negative.errors] == [E.NEGATIVE_AMOUNT]
    duplicate = compute([ar("A", "100"), ar("A", "50")], [])
    assert [e.code for e in duplicate.errors] == [E.DUPLICATE_ROW] and duplicate.lines["borrowing_base"] is None
    no_terms = compute(terms=None)
    assert [e.code for e in no_terms.errors] == [E.INVALID_TERMS]
    bad_terms = compute(terms={"commitment": "1"})
    assert [e.code for e in bad_terms.errors] == [E.INVALID_TERMS]
    with pytest.raises(TypeError):
        ArRow("A", 100.0, D("0"), D("0"), D("0"), D("0"))
    with pytest.raises(TypeError):
        InventoryRow("finished_goods", 1.5)
    with pytest.raises(TypeError):
        compute_borrowing_base(AGING, INVENTORY, TERMS, 1700000.0, D("0"))


def test_rows_from_mappings_and_validated_terms_model():
    row = ArRow.from_mapping({"customer": "A", "current": "100", "days_1_30": "0", "days_31_60": "0",
                              "days_61_90": "0", "over_90": "25", "flags": ["foreign"]})
    assert row == ar("A", "100", over_90="25", flags=["foreign"]) and row.total == D("125")
    with pytest.raises(ValueError):
        ArRow.from_mapping({"customer": "A", "current": "100"})
    assert InventoryRow.from_mapping({"category": "consigned", "amount": "5"}) == InventoryRow("consigned", D("5"))
    model = BorrowingBase.model_validate(TERMS)
    assert compute(terms=model).lines == compute().lines


# ---- reconciliation with the certificate ---------------------------------------------------------


def test_reconcile_matches_line_by_line():
    certificate = {k: D(v) for k, v in EXPECTED.items()}
    rows = reconcile(compute(), certificate, D("1"))
    assert [r.line for r in rows] == list(EXPECTED)
    assert all(r.status == "match" and r.difference == D("0") for r in rows)


def test_reconcile_reports_each_difference():
    # The borrower left the cross-aged remainder in eligible receivables.
    certificate = {
        "ar_ineligible_cross_aging": D("0"),
        "ar_eligible": D("1700000"),
        "ar_availability": D("1445000"),
        "borrowing_base": D("2145000"),
        "availability": D("345000"),
        "inventory_eligible": D("1500001"),
        "dilution_reserve": D("10000"),
    }
    rows = {r.line: r for r in reconcile(compute(), certificate, D("1"))}
    assert rows["ar_ineligible_cross_aging"].status == "mismatch"
    assert rows["ar_ineligible_cross_aging"].difference == D("30000")  # computed - certificate
    eligible = rows["ar_eligible"]
    assert (eligible.computed, eligible.certificate, eligible.difference, eligible.status) == (
        D("1662500"), D("1700000"), D("-37500"), "mismatch")
    assert rows["availability"].difference == D("-31875")
    assert rows["inventory_eligible"].status == "match"  # within the one dollar tolerance
    assert rows["dilution_reserve"].status == "unknown_line" and rows["dilution_reserve"].computed is None
    assert [r.line for r in reconcile(compute(), certificate, D("1")) if r.status == "mismatch"] == [
        "ar_ineligible_cross_aging", "ar_eligible", "ar_availability", "borrowing_base", "availability"]


def test_reconcile_refuses_floats_and_flags_uncomputed_lines():
    with pytest.raises(TypeError):
        reconcile(compute(), {"availability": 313125.0}, D("1"))
    with pytest.raises(TypeError):
        reconcile(compute(), {"availability": D("313125")}, 1.0)
    failed = compute([ar("A", "100"), ar("A", "50")], [])
    (row,) = reconcile(failed, {"availability": D("5")}, D("1"))
    assert row.status == "not_computed" and row.computed is None

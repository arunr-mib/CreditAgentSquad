"""Borrowing base recalculation and reconciliation to the certificate (spec section 8).

Receivables ineligibles are applied per customer in this order, each to what the earlier
steps left, so no dollar is counted twice:

  1. exclusions     a customer carrying any flag the terms exclude (intercompany, foreign,
                    government, ...) is ineligible in full, attributed to the first
                    matching flag in the terms' order;
  2. age            balances in buckets older than `max_age_days`;
  3. cross-aging    if the aged balance is MORE than `cross_aging_pct` of the customer's
                    total balance, the rest of that customer's balance;
  4. contra         where the terms exclude "contra", the customer's contra amount (the
                    payable owed back to that customer), up to what steps 1-3 left;
  5. concentration  the part of a customer's remaining balance above
                    `concentration_limit_pct` x total receivables remaining after steps 1-4
                    (one pass; the limit is not recomputed after the cut).

"contra" in the terms' exclude list never excludes a whole customer: it makes each customer's
contra amount ineligible at step 4. Without it, contra amounts are ignored.

An absent limit in the terms is not applied. Amounts are exact inside the calculation; each
reported line is rounded once, to whole dollars, half-up.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from typing import Any

from pydantic import ValidationError

from . import errors as E
from .decimal_utils import CALC_CONTEXT, ZERO, is_decimal, round_half_up, to_decimal
from .errors import CalcError
from .terms import BorrowingBase

BUCKETS = ("current", "days_1_30", "days_31_60", "days_61_90", "over_90")
CONTRA = "contra"  # in the terms' exclude list this is an amount per customer, not a customer flag
# The oldest day a bucket can hold; a bucket is aged when its youngest day exceeds max_age_days.
_BUCKET_START = {"current": 0, "days_1_30": 1, "days_31_60": 31, "days_61_90": 61, "over_90": 91}

LINE_NAMES = (
    "ar_total", "ar_ineligible_excluded", "ar_ineligible_age", "ar_ineligible_cross_aging",
    "ar_ineligible_contra", "ar_ineligible_concentration", "ar_ineligible_total", "ar_eligible", "ar_availability",
    "inventory_total", "inventory_ineligible", "inventory_eligible",
    "inventory_availability_before_sublimit", "inventory_availability",
    "reserves", "borrowing_base", "commitment", "borrowing_limit", "outstanding", "letters_of_credit",
    "availability", "over_advance",
)


def _money(value: Any, what: str) -> Decimal:
    if not is_decimal(value):
        raise TypeError(f"{what} must be a finite Decimal, got {type(value).__name__}")
    return value


@dataclass(frozen=True)
class ArRow:
    """One customer's receivables by days past due."""

    customer: str
    current: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    over_90: Decimal
    flags: frozenset[str] = frozenset()
    contra: Decimal = ZERO  # amount this customer is also owed (offsetting payable)

    def __post_init__(self) -> None:
        for bucket in (*BUCKETS, "contra"):
            _money(getattr(self, bucket), f"{self.customer} {bucket}")
        object.__setattr__(self, "flags", frozenset(self.flags))

    @property
    def total(self) -> Decimal:
        return sum((getattr(self, b) for b in BUCKETS), ZERO)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ArRow:
        """Parse a row with decimals as strings; `flags` and `contra` are optional, every bucket is required."""
        allowed = {"customer", "flags", "contra", *BUCKETS}
        if set(data) - allowed or {"customer", *BUCKETS} - set(data):
            raise ValueError(
                f"receivables row needs customer and {BUCKETS} (flags and contra optional), got {sorted(data)}")
        return cls(data["customer"], *(to_decimal(data[b]) for b in BUCKETS), frozenset(data.get("flags", ())),
                   to_decimal(data.get("contra", ZERO)))


@dataclass(frozen=True)
class InventoryRow:
    category: str
    amount: Decimal

    def __post_init__(self) -> None:
        _money(self.amount, f"inventory {self.category}")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> InventoryRow:
        if set(data) != {"category", "amount"}:
            raise ValueError(f"inventory row needs exactly category and amount, got {sorted(data)}")
        return cls(data["category"], to_decimal(data["amount"]))


@dataclass(frozen=True)
class CustomerDetail:
    """Exact (unrounded) split of one customer's balance; the six parts sum to `total`."""

    customer: str
    total: Decimal
    excluded: Decimal
    age: Decimal
    cross_aging: Decimal
    contra: Decimal
    concentration: Decimal
    eligible: Decimal
    excluded_flag: str | None = None


@dataclass
class BorrowingBaseResult:
    lines: dict[str, Decimal | None] = field(default_factory=lambda: dict.fromkeys(LINE_NAMES))
    customers: list[CustomerDetail] = field(default_factory=list)
    excluded_by_flag: dict[str, Decimal] = field(default_factory=dict)
    inventory_ineligible_by_category: dict[str, Decimal] = field(default_factory=dict)
    reserves_by_name: dict[str, Decimal] = field(default_factory=dict)
    errors: list[CalcError] = field(default_factory=list)

    @property
    def borrowing_base(self) -> Decimal | None:
        return self.lines["borrowing_base"]

    @property
    def availability(self) -> Decimal | None:
        """min(borrowing base, commitment) - outstanding - letters of credit; negative when over-advanced."""
        return self.lines["availability"]

    @property
    def over_advance(self) -> Decimal | None:
        return self.lines["over_advance"]

    @property
    def is_over_advance(self) -> bool | None:
        return None if self.over_advance is None else self.over_advance > ZERO


def compute_borrowing_base(
    ar_rows: Sequence[ArRow],
    inventory_rows: Sequence[InventoryRow],
    terms: BorrowingBase | Mapping[str, Any] | None,
    outstanding: Decimal,
    letters_of_credit: Decimal,
) -> BorrowingBaseResult:
    """Recalculate the borrowing base from the ageing, the inventory listing and the terms.

    Rows for a collateral type the terms do not lend against are ignored and that type's
    lines stay None. Bad data (negative amounts, a customer listed twice, invalid terms) is
    returned as errors with every line None; floats raise TypeError.
    """
    _money(outstanding, "outstanding")
    _money(letters_of_credit, "letters_of_credit")
    result = BorrowingBaseResult()
    if terms is None:
        result.errors.append(CalcError(E.INVALID_TERMS, "the terms in force have no borrowing base"))
        return result
    try:
        bb = terms if isinstance(terms, BorrowingBase) else BorrowingBase.model_validate(terms)
    except ValidationError as exc:
        result.errors.append(CalcError(
            E.INVALID_TERMS, f"borrowing base terms are invalid ({exc.error_count()} problem(s))",
            detail={"problems": [{"loc": ".".join(map(str, e["loc"])), "msg": e["msg"]} for e in exc.errors()]}))
        return result

    seen: set[str] = set()
    for row in ar_rows:
        if row.customer in seen:
            result.errors.append(CalcError(E.DUPLICATE_ROW, f"customer {row.customer!r} appears more than once in the ageing",
                                           key=row.customer))
        seen.add(row.customer)
        for bucket in (*BUCKETS, "contra"):
            if getattr(row, bucket) < ZERO:
                result.errors.append(CalcError(E.NEGATIVE_AMOUNT, f"{row.customer} {bucket} is negative",
                                               key=row.customer, detail={"bucket": bucket, "amount": getattr(row, bucket)}))
    for item in inventory_rows:
        if item.amount < ZERO:
            result.errors.append(CalcError(E.NEGATIVE_AMOUNT, f"inventory {item.category} is negative", key=item.category))
    if outstanding < ZERO or letters_of_credit < ZERO:
        result.errors.append(CalcError(E.NEGATIVE_AMOUNT, "outstanding and letters of credit cannot be negative"))
    if result.errors:
        return result

    with localcontext(CALC_CONTEXT):
        exact: dict[str, Decimal | None] = dict.fromkeys(LINE_NAMES)
        ar_availability = inventory_availability = ZERO
        receivables = bb.component("accounts_receivable")
        if receivables is not None:
            ar_availability = _receivables(ar_rows, receivables, result, exact)
        inventory = bb.component("inventory")
        if inventory is not None:
            inventory_availability = _inventory(inventory_rows, inventory, result, exact)

        result.reserves_by_name = {r.name: r.amount for r in bb.reserves}
        reserves = sum(result.reserves_by_name.values(), ZERO)
        base = ar_availability + inventory_availability - reserves
        limit = min(base, bb.commitment)
        availability = limit - outstanding - letters_of_credit
        exact.update({
            "reserves": reserves, "borrowing_base": base, "commitment": bb.commitment, "borrowing_limit": limit,
            "outstanding": outstanding, "letters_of_credit": letters_of_credit,
            "availability": availability, "over_advance": max(ZERO, -availability),
        })
        result.lines = {name: None if value is None else round_half_up(value, 0) for name, value in exact.items()}
    return result


def _receivables(rows: Sequence[ArRow], component: Any, result: BorrowingBaseResult, exact: dict[str, Any]) -> Decimal:
    rules = component.eligibility
    aged_buckets = [] if rules.max_age_days is None else [b for b in BUCKETS if _BUCKET_START[b] > rules.max_age_days]
    working: list[dict[str, Any]] = []
    for row in rows:
        total = row.total
        flag = next((f for f in rules.exclude if f != CONTRA and f in row.flags), None)
        excluded = total if flag is not None else ZERO
        age = cross = contra = ZERO
        if flag is None:
            age = sum((getattr(row, b) for b in aged_buckets), ZERO)
            if rules.cross_aging_pct is not None and age > rules.cross_aging_pct * total:
                cross = total - age
            if CONTRA in rules.exclude:
                contra = min(row.contra, total - age - cross)
        working.append({"row": row, "total": total, "flag": flag, "excluded": excluded, "age": age, "cross": cross,
                        "contra": contra, "remaining": total - excluded - age - cross - contra})
        if flag is not None:
            result.excluded_by_flag[flag] = result.excluded_by_flag.get(flag, ZERO) + excluded

    before_concentration = sum((w["remaining"] for w in working), ZERO)
    limit = None if rules.concentration_limit_pct is None else rules.concentration_limit_pct * before_concentration
    for w in working:
        concentration = ZERO if limit is None else max(ZERO, w["remaining"] - limit)
        result.customers.append(CustomerDetail(
            w["row"].customer, w["total"], w["excluded"], w["age"], w["cross"], w["contra"], concentration,
            w["remaining"] - concentration, w["flag"]))

    def total_of(name: str) -> Decimal:
        return sum((getattr(c, name) for c in result.customers), ZERO)

    eligible = total_of("eligible")
    availability = component.advance_rate * eligible
    exact.update({
        "ar_total": total_of("total"), "ar_ineligible_excluded": total_of("excluded"),
        "ar_ineligible_age": total_of("age"), "ar_ineligible_cross_aging": total_of("cross_aging"),
        "ar_ineligible_contra": total_of("contra"), "ar_ineligible_concentration": total_of("concentration"),
        "ar_ineligible_total": total_of("total") - eligible, "ar_eligible": eligible,
        "ar_availability": availability,
    })
    return availability


def _inventory(rows: Sequence[InventoryRow], component: Any, result: BorrowingBaseResult, exact: dict[str, Any]) -> Decimal:
    excluded = set(component.eligibility.exclude)
    total = ineligible = ZERO
    for item in rows:
        total += item.amount
        if item.category in excluded:
            ineligible += item.amount
            by_category = result.inventory_ineligible_by_category
            by_category[item.category] = by_category.get(item.category, ZERO) + item.amount
    eligible = total - ineligible
    before_sublimit = component.advance_rate * eligible
    availability = before_sublimit if component.sublimit is None else min(before_sublimit, component.sublimit)
    exact.update({
        "inventory_total": total, "inventory_ineligible": ineligible, "inventory_eligible": eligible,
        "inventory_availability_before_sublimit": before_sublimit, "inventory_availability": availability,
    })
    return availability


def unused_availability(commitment: Decimal, outstanding: Decimal, letters_of_credit: Decimal = ZERO) -> Decimal:
    """Availability on a line with no borrowing base: commitment - outstanding - letters of credit.

    Store it as the `bb.availability` fact so a liquidity covenant can read it. Negative when
    the line is drawn over its commitment.
    """
    for name, value in (("commitment", commitment), ("outstanding", outstanding), ("letters_of_credit", letters_of_credit)):
        if _money(value, name) < ZERO:
            raise ValueError(f"{name} cannot be negative")
    return CALC_CONTEXT.subtract(CALC_CONTEXT.subtract(commitment, outstanding), letters_of_credit)


@dataclass(frozen=True)
class LineDifference:
    line: str
    computed: Decimal | None
    certificate: Decimal
    difference: Decimal | None  # computed - certificate
    status: str  # match | mismatch | unknown_line | not_computed


def reconcile(
    computed: BorrowingBaseResult,
    certificate: Mapping[str, Decimal],
    tolerance: Decimal,
) -> list[LineDifference]:
    """Compare every certificate line with the recalculation, in the certificate's order.

    `certificate` uses the names in `LINE_NAMES`. A line matches when the absolute difference
    is within `tolerance` (inclusive). A name the recalculation does not know is `unknown_line`;
    a known line with no computed value is `not_computed`.
    """
    _money(tolerance, "tolerance")
    if tolerance < ZERO:
        raise ValueError("tolerance cannot be negative")
    rows: list[LineDifference] = []
    for name, reported in certificate.items():
        _money(reported, f"certificate {name}")
        if name not in computed.lines:
            rows.append(LineDifference(name, None, reported, None, "unknown_line"))
            continue
        value = computed.lines[name]
        if value is None:
            rows.append(LineDifference(name, None, reported, None, "not_computed"))
            continue
        difference = value - reported
        rows.append(LineDifference(name, value, reported, difference,
                                   "match" if abs(difference) <= tolerance else "mismatch"))
    return rows

"""Borrowing base data: receivables aging by customer, inventory by category, and the
borrower's own certificate, for the last three month-ends.

Amounts are whole dollars. Every customer that can be eligible carries balances in
multiples of 400 dollars, and one excluded (affiliate) account absorbs the remainder, so
the aging ties to the balance sheet at a quarter end while every advance-rate and
concentration product is a whole number. No line depends on a rounding convention.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from synthetic import expected
from synthetic.scenarios import BorrowerSpec

D = Decimal
BB_DATES = (date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30))
BUCKETS = ("0_30", "31_60", "61_90", "over_90")
STEP = D(400)

_FIRST = (
    "Alder", "Bexley", "Corbin", "Dovetail", "Elmhurst", "Fenwick", "Glenhaven", "Hartsfield", "Ironbridge",
    "Juniper", "Kingsway", "Lowell", "Maplecrest", "Norwood", "Oakmont", "Prescott", "Quarry", "Redfern",
    "Stonegate", "Tamarack", "Underhill", "Valemount", "Westbrook", "Yarrow", "Ashdown", "Birchfield",
    "Coldwater", "Dunleith", "Easton", "Foxhollow",
)  # fmt: skip
_SECOND = {
    "manufacturing": ("Industries", "Equipment", "Fabrication", "Assembly", "Machine Works", "Systems"),
    "distribution": ("Supply", "Hardware", "Markets", "Stores", "Wholesale", "Contractors"),
    "food processing": ("Foods", "Grocers", "Markets", "Provisions", "Kitchens", "Restaurants"),
}
_SUFFIX = ("Inc.", "LLC", "Co.", "Corp.")
_INVENTORY = {
    "manufacturing": (("raw_materials", 34), ("finished_goods", 50), ("work_in_process", None)),
    "food processing": (("raw_materials", 38), ("finished_goods", 49), ("work_in_process", None)),
    "distribution": (("finished_goods", 91), ("consigned", None)),
}


def _floor(amount: Decimal, step: Decimal = STEP) -> Decimal:
    return (amount // step) * step


def bb_terms_for(spec: BorrowerSpec, commitment: Decimal) -> dict:
    """Borrowing base terms in the spec's shape (the citation is added with the agreement)."""
    sublimit = _floor(commitment * D("0.40"), D(250_000))
    reserve = max(D(50_000), _floor(commitment * D("0.012"), D(25_000)))
    return {
        "commitment": f"{commitment:f}",
        "components": [
            {
                "collateral": "accounts_receivable",
                "advance_rate": "0.85",
                "eligibility": {
                    "max_age_days": 90,
                    "cross_aging_pct": "0.50",
                    "concentration_limit_pct": "0.25",
                    "exclude": ["intercompany", "foreign", "government", "contra"],
                },
            },
            {
                "collateral": "inventory",
                "advance_rate": "0.50",
                "sublimit": f"{sublimit:f}",
                "eligibility": {"exclude": ["work_in_process", "consigned"]},
            },
        ],
        "reserves": [{"name": "Rent reserve", "amount": f"{reserve:f}"}],
        "frequency": "monthly",
    }


def _customers(spec: BorrowerSpec, rng: random.Random, problem_weight: int | None) -> list[dict]:
    """Customer roster with weights in basis points of total receivables."""
    count = rng.randint(12, 15)
    firsts = rng.sample(_FIRST, count)
    seconds = _SECOND[spec.industry]
    short = spec.name.split()[0]
    customers = [
        {"name": f"{short} Holdings, LLC (affiliate)", "category": "intercompany", "weight": None},
        {
            "name": f"{firsts[0]} {rng.choice(seconds)} Ltd. (Canada)",
            "category": "foreign",
            "weight": rng.randint(250, 450),
        },
    ]
    if rng.randint(0, 1):
        customers.append(
            {"name": f"County of {firsts[1]} Purchasing Office", "category": "government", "weight": rng.randint(150, 300)}
        )
    trade = [
        {
            "name": f"{first} {rng.choice(seconds)}, {rng.choice(_SUFFIX)}",
            "category": "trade",
            "weight": rng.randint(300, 1400),
        }
        for first in firsts[2:]
    ]
    fixed = sum(c["weight"] for c in customers[1:]) + 300  # about 3 percent is left for the affiliate
    problem = None
    if problem_weight is not None:
        problem = trade[1]
        problem["weight"] = problem_weight
        problem["problem"] = True
        fixed += problem_weight
    if spec.concentrated_customer:
        trade[2]["weight"] = 3100
        trade[2]["anchor"] = True
        fixed += 3100
    others = [c for c in trade if c is not problem and not c.get("anchor")]
    scale = D(10000 - fixed) / D(sum(c["weight"] for c in others))
    for c in others:
        c["weight"] = int(D(c["weight"]) * scale)
    for c in trade:
        c["late_share"] = rng.choice((0, 0, 0, 1, 2, 3))  # percent of the balance over 90 days
        c["mid_share"] = rng.randint(18, 30)
        c["old_share"] = rng.randint(3, 9)
    trade[3]["contra"] = True
    for c in customers[1:]:
        c.update(late_share=0, mid_share=rng.randint(18, 30), old_share=rng.randint(3, 9))
    return customers + trade


def _aging(customers: list[dict], total: Decimal, month: int, problem_mode: str | None) -> list[dict]:
    rows = []
    for c in customers[1:]:
        balance = _floor(total * D(c["weight"]) / D(10000))
        late = _floor(balance * D(c["late_share"]) / 100)
        old = _floor(balance * D(c["old_share"] + month) / 100)
        mid = _floor(balance * D(c["mid_share"] - month) / 100)
        if c.get("problem"):
            # The problem account's invoices age one bucket a month and pass 90 days in September.
            share = D("0.62") if problem_mode == "cross_age" else D("0.34")
            stuck, small, medium = _floor(balance * share), _floor(balance * D("0.05")), _floor(balance * D("0.10"))
            late, old, mid = [(D(0), small, stuck), (D(0), stuck, medium), (stuck, small, medium)][month]
        buckets = {"0_30": balance - mid - old - late, "31_60": mid, "61_90": old, "over_90": late}
        contra = _floor(balance * D("0.06")) if c.get("contra") else D(0)
        rows.append({"customer": c["name"], "category": c["category"], "contra": contra, "buckets": buckets})
    affiliate = total - sum((sum(r["buckets"].values()) for r in rows), D(0))
    if affiliate <= 0:
        raise ValueError("the affiliate account must absorb a positive remainder")
    first = {
        "customer": customers[0]["name"],
        "category": "intercompany",
        "contra": D(0),
        "buckets": {"0_30": affiliate, "31_60": D(0), "61_90": D(0), "over_90": D(0)},
    }
    rows = [first, *rows]
    for row in rows:
        row["total"] = sum(row["buckets"].values(), D(0))
    return sorted(rows, key=lambda r: r["customer"])


def _inventory(spec: BorrowerSpec, total: Decimal) -> list[dict]:
    rows, used = [], D(0)
    for category, share in _INVENTORY[spec.industry]:
        amount = total - used if share is None else _floor(total * D(share) / 100)
        used += amount
        rows.append({"category": category, "amount": amount})
    return rows


def build_borrowing_base(
    spec: BorrowerSpec,
    seed: int,
    bb_terms: dict,
    receivables: dict[date, Decimal],
    inventory: dict[date, Decimal],
    outstanding: dict[date, Decimal],
) -> list[dict]:
    """Three month-ends of collateral data with the borrower's certificate for each."""
    letters = D(spec.letters_of_credit)
    problem_mode = {"over_advance": "cross_age", "miscounted_ineligible": "miscount"}.get(spec.scenario)
    commitment = D(bb_terms["commitment"])

    def build(problem_weight: int | None) -> list[dict]:
        rng = random.Random(f"{seed}:{spec.id}:collateral")
        customers = _customers(spec, rng, problem_weight)
        entries = []
        for month, as_of in enumerate(BB_DATES):
            aging = _aging(customers, receivables[as_of], month, problem_mode)
            stock = _inventory(spec, inventory[as_of])
            calculated = expected.borrowing_base(bb_terms, aging, stock, outstanding[as_of], letters)
            certificate = dict(calculated)
            if problem_mode == "miscount" and month == 2:
                # The borrower's certificate treats the problem account's over-90 invoices as current.
                doctored = [
                    {**row, "buckets": {**row["buckets"], "61_90": row["buckets"]["61_90"] + row["buckets"]["over_90"], "over_90": D(0)}}
                    if any(c.get("problem") and c["name"] == row["customer"] for c in customers)
                    else row
                    for row in aging
                ]
                certificate = expected.borrowing_base(bb_terms, doctored, stock, outstanding[as_of], letters)
            entries.append(
                {
                    "period_end": as_of,
                    "ar_aging": aging,
                    "inventory": stock,
                    "certificate": certificate,
                    "outstanding": outstanding[as_of],
                    "letters_of_credit": letters,
                    "_calculated": calculated,
                }
            )
        return entries

    if problem_mode == "cross_age":
        # Grow the problem account until its cross-aging pushes the line over the borrowing base.
        for weight in range(900, 4600, 100):
            entries = build(weight)
            if entries[2]["_calculated"]["availability"] <= -(commitment * D("0.01")):
                return entries
        raise ValueError(f"{spec.id}: could not construct an over-advance")
    return build(900 if problem_mode == "miscount" else None)

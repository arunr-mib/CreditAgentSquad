"""The roster is the owner's (design spec 2.1), and every invented name is listed for checking."""

from __future__ import annotations

import re

from synthetic.books.innovation.names import invented_names
from synthetic.books.innovation.roster import (
    AS_OF,
    BY_ID,
    CLIENTS,
    CURRENT_PERIOD,
    KEPT_IDS,
    LEGACY_SEED,
    SCENARIOS,
)
from synthetic.scenarios import ROSTER

# spec 2.1, as the owner wrote it: unrestricted cash, average monthly net burn over the last three months, RML
OWNER = {
    "datamarrow": (4_600_000, 650_000, "7.1"), "calvere-health": (4_000_000, 420_000, "9.5"),
    "brightvane-energy": (5_500_000, 450_000, "12.2"), "mosswell-robotics": (7_800_000, 600_000, "13.0"),
    "tavernel-grid": (2_600_000, 200_000, "13.0"), "tarnavi-ai": (12_000_000, 800_000, "15.0"),
    "kelvra-bio": (9_200_000, 500_000, "18.4"), "orbitline-systems": (3_900_000, 210_000, "18.6"),
    "cindrel-tech": (6_600_000, 300_000, "22.0"), "veridia-payments": (14_000_000, 550_000, "25.5"),
    "vantrell-labs": (11_000_000, 400_000, "27.5"), "pellucid-sensors": (6_300_000, 220_000, "28.6"),
}  # fmt: skip
REAL_BANKS = ("JPMorgan", "Chase", "Wells Fargo", "Citibank", "Citigroup", "Silicon Valley Bank", "SVB",
              "Bank of America", "HSBC", "Goldman", "Morgan Stanley", "First Republic", "Signature Bank", "Comerica",
              "Capital One")  # fmt: skip


def test_sixteen_clients_with_distinct_short_ids_and_the_owners_twelve_exactly():
    assert len(CLIENTS) == 16 == len({c.id for c in CLIENTS}) == len({c.name for c in CLIENTS})
    assert all(len(c.id) <= 32 for c in CLIENTS)  # Borrower.code is at most 32 characters
    for client_id, (cash, burn, rml) in OWNER.items():
        spec = BY_ID[client_id]
        assert (spec.cash, spec.burn, spec.rml) == (cash, burn, rml), client_id
    assert {c.id for c in CLIENTS} - set(OWNER) == {
        "meridew-analytics",
        "nimbusfield-security",
        "brackmere-medical",
        "ferrogate-cloud",
    }
    assert BY_ID["ferrogate-cloud"].rml is None and BY_ID["ferrogate-cloud"].burn < 0


def test_every_scenario_is_declared_and_the_kept_four_are_in_the_v1_roster():
    assert {c.scenario for c in CLIENTS} == set(SCENARIOS)
    v1 = {spec.id: spec for spec in ROSTER}
    assert set(KEPT_IDS) <= set(v1) and len(KEPT_IDS) == 4
    assert {v1[i].scenario for i in KEPT_IDS} == {"hidden_breach", "clean", "over_advance", "reported_breach"}
    assert LEGACY_SEED == 20261117  # the v1 seed: the kept four are built with it


def test_the_dates_are_a_thursday_in_mid_november_and_a_month_end():
    assert AS_OF.strftime("%A") == "Thursday" and (AS_OF.year, AS_OF.month) == (2026, 11)
    assert (CURRENT_PERIOD.year, CURRENT_PERIOD.month, CURRENT_PERIOD.day) == (2026, 10, 31)


def test_the_invented_names_are_listed_for_the_owner_to_check():
    rows = invented_names()
    assert len(rows) == 32 and len({r["name"] for r in rows}) == 32
    assert [r["name"] for r in rows if r["kind"] == "company"] == [c.name for c in CLIENTS]
    assert any(r["watch"] for r in rows)
    assert not [r for r in rows for bank in REAL_BANKS if re.search(rf"\b{re.escape(bank)}\b", r["name"])]


def test_a_renamed_client_keeps_the_draws_of_its_old_code_so_no_figure_moved():
    from synthetic.books.innovation.renames import SEED_CODE, seed_code

    ids = {c.id for c in CLIENTS}
    assert len(SEED_CODE) == 8 and set(SEED_CODE) <= ids and not set(SEED_CODE.values()) & ids
    assert seed_code("kelvra-bio") == "kelvra-bio"
    assert all(seed_code(new) == old for new, old in SEED_CODE.items())

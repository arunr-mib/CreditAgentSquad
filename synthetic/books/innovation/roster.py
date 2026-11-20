"""The 16 innovation clients (spec 2.1) and the constants of the book. Figures marked (spec) are the owner's."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from synthetic.scenarios import AUDITORS, RMS

# The demo analysts (backend seed_users.DEMO_USERS): every innovation client is owned by one of them, so the
# briefing's "needs you" is populated for the analysts the walkthroughs sign in as. Priya carries the scenarios.
PRIYA = "Priya Raman"
TOMAS = "Tomas Keller"

LENDER = "Bank of Stoic"
AS_OF = date(2026, 11, 19)  # a Thursday
CURRENT_PERIOD = date(2026, 10, 31)
DEFAULT_SEED = 20261120
LEGACY_SEED = 20261117  # the kept four are built with the v1 seed so that they stay byte-identical
KEPT_IDS = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")

SCENARIOS: dict[str, str] = {
    "clean": "Clean performer: covenants pass with room, documents complete and on time, no loud signal.",
    "pledged_cash": (
        "Pledged cash counted: the certificate adds cash pledged to a lease letter of credit to unrestricted cash "
        "and claims compliance; true unrestricted cash is below the minimum."
    ),
    "late_package": (
        "Late monthly package: the October bank statements and MRR report have not arrived, 12 and 4 days "
        "after their due dates; October cannot be tested yet."
    ),
    "runway_falling": "Runway falling: burn is rising and runway has lost more than a month in each of three months running, still above 12 months.",
    "funding_expected": "Clean book with an expected funding event the bank is tracking.",
    "stripple_package": (
        "Awkward October package: a new balance-sheet line (contract liabilities), capitalised software that can be "
        "misread as spending, and an MRR export with no company name and the wrong year."
    ),
    "plan_miss": (
        "Plan miss: trailing-three-months revenue is under 80 percent of the approved plan in September and October."
    ),
    "funding_slipped": (
        "Funding slipped: the round the bank was told would close on 6 November has not closed; runway is under "
        "9 months."
    ),
    "restricted_account": (
        "Restricted account: a new escrow collateral account was opened in October; the certificate counts it as "
        "unrestricted cash while the bank statements show it restricted."
    ),
    "cash_flow_positive": "Cash-flow positive: average net burn is negative, so runway is not meaningful (and not a division).",
}


@dataclass(frozen=True)
class FundingSpec:
    kind: str  # equity_round | extension | milestone_tranche | venture_debt
    amount: int
    expected_close: date
    status: str  # expected | signed
    note: str


@dataclass(frozen=True)
class ClientSpec:
    id: str
    name: str
    sector: str
    stage: str
    city: str
    state: str
    cash: int  # unrestricted cash at 2026-10-31 (spec)
    burn: int  # average monthly net burn, Aug-Oct 2026 (spec); negative means cash generative
    rml: str | None  # runway in months at 2026-10-31, one decimal (spec); None when not meaningful
    mrr: int  # MRR at 2026-10-31
    growth: str  # monthly MRR growth
    gross_margin: str
    customers: int  # customers at 2026-10-31
    pledged: int  # cash pledged or restricted at 2026-10-31
    venture_debt: int  # drawn from Bank of Stoic at 2026-10-31
    min_cash: int  # minimum unrestricted cash covenant
    scenario: str
    shape: str  # burn shape: steady | dip | rising | positive
    rm: str
    analyst: str
    cfo: str
    auditor: str
    closing_date: date
    risk_rating: int = 5
    sti: int = 0  # short-term investments, which are not cash for the covenants
    history: tuple[
        tuple[str, str, int], ...
    ] = ()  # (YYYY-MM, "equity" | "debt", amount) inside the 22 months
    funding: tuple[FundingSpec, ...] = ()
    min_rml: str = "6.0"
    plan_floor: str = "0.80"
    capsw_frac: str = "0.07"  # capitalised software spend as a share of revenue
    legal_form: str = "corporation"
    extra: dict = field(default_factory=dict)


def _c(**kw) -> ClientSpec:
    return ClientSpec(**kw)


CLIENTS: tuple[ClientSpec, ...] = (
    _c(
        id="dataflake",
        name="Dataflake Inc",
        sector="Data infrastructure",
        stage="Series A",
        city="Austin",
        state="TX",
        cash=4_600_000,
        burn=650_000,
        rml="7.1",
        mrr=640_000,
        growth="0.030",
        gross_margin="0.70",
        customers=140,
        pledged=1_500_000,
        venture_debt=2_000_000,
        min_cash=5_000_000,
        scenario="pledged_cash",
        shape="steady",
        rm=RMS[0],
        analyst=PRIYA,
        cfo="Imogen Farrow",
        auditor=AUDITORS[0],
        closing_date=date(2024, 9, 12),
        risk_rating=6,
        funding=(
            FundingSpec(
                "extension",
                8_000_000,
                date(2026, 12, 12),
                "signed",
                "Series B extension, term sheet signed, closing 12 December",
            ),
        ),
        extra={"pledged_note": "pledged to secure a hosting lease letter of credit"},
    ),
    _c(
        id="lumora-health",
        name="Lumora Health",
        sector="Digital health",
        stage="Series B",
        city="Boston",
        state="MA",
        cash=4_000_000,
        burn=420_000,
        rml="9.5",
        mrr=470_000,
        growth="0.028",
        gross_margin="0.68",
        customers=96,
        pledged=400_000,
        venture_debt=2_000_000,
        min_cash=2_500_000,
        scenario="late_package",
        shape="steady",
        rm=RMS[1],
        analyst=PRIYA,
        cfo="Tobias Wenlock",
        auditor=AUDITORS[1],
        closing_date=date(2024, 6, 20),
        risk_rating=5,
    ),
    _c(
        id="brightvane-energy",
        name="Brightvane Energy",
        sector="Climate hardware",
        stage="Series A",
        city="Denver",
        state="CO",
        cash=5_500_000,
        burn=450_000,
        rml="12.2",
        mrr=380_000,
        growth="0.025",
        gross_margin="0.55",
        customers=62,
        pledged=600_000,
        venture_debt=1_500_000,
        min_cash=3_000_000,
        scenario="runway_falling",
        shape="rising",
        rm=RMS[2],
        analyst=PRIYA,
        cfo="Odalys Prentiss",
        auditor=AUDITORS[2],
        closing_date=date(2024, 11, 4),
        risk_rating=5,
    ),
    _c(
        id="mosswell-robotics",
        name="Mosswell Robotics",
        sector="Robotics",
        stage="Series A",
        city="Pittsburgh",
        state="PA",
        cash=7_800_000,
        burn=600_000,
        rml="13.0",
        mrr=700_000,
        growth="0.020",
        gross_margin="0.62",
        customers=85,
        pledged=500_000,
        venture_debt=2_500_000,
        min_cash=4_000_000,
        scenario="clean",
        shape="dip",
        rm=RMS[3],
        analyst=TOMAS,
        cfo="Reuben Castellane",
        auditor=AUDITORS[3],
        closing_date=date(2024, 3, 15),
        risk_rating=4,
    ),
    _c(
        id="halcyon-grid",
        name="Halcyon Grid",
        sector="Energy software",
        stage="Seed+",
        city="Portland",
        state="OR",
        cash=2_600_000,
        burn=200_000,
        rml="13.0",
        mrr=160_000,
        growth="0.035",
        gross_margin="0.74",
        customers=41,
        pledged=150_000,
        venture_debt=1_000_000,
        min_cash=1_500_000,
        scenario="funding_expected",
        shape="dip",
        rm=RMS[0],
        analyst=TOMAS,
        cfo="Marguerite Oyelowo",
        auditor=AUDITORS[0],
        closing_date=date(2025, 2, 10),
        risk_rating=5,
        funding=(
            FundingSpec(
                "equity_round",
                12_000_000,
                date(2027, 3, 31),
                "expected",
                "Series A expected in the first quarter of 2027",
            ),
        ),
    ),
    _c(
        id="quillon-ai",
        name="Quillon AI",
        sector="Applied AI",
        stage="Series B",
        city="San Francisco",
        state="CA",
        cash=12_000_000,
        burn=800_000,
        rml="15.0",
        mrr=1_150_000,
        growth="0.030",
        gross_margin="0.75",
        customers=210,
        pledged=800_000,
        venture_debt=5_000_000,
        min_cash=6_000_000,
        scenario="clean",
        shape="dip",
        rm=RMS[1],
        analyst=TOMAS,
        cfo="Sunniva Hartigan",
        auditor=AUDITORS[1],
        closing_date=date(2024, 1, 25),
        risk_rating=4,
        sti=3_000_000,
    ),
    _c(
        id="kelvra-bio",
        name="Kelvra Bio",
        sector="Biotech tools",
        stage="Series B",
        city="San Diego",
        state="CA",
        cash=9_200_000,
        burn=500_000,
        rml="18.4",
        mrr=520_000,
        growth="0.020",
        gross_margin="0.66",
        customers=74,
        pledged=400_000,
        venture_debt=3_000_000,
        min_cash=3_500_000,
        scenario="funding_expected",
        shape="dip",
        rm=RMS[2],
        analyst=TOMAS,
        cfo="Lysander Boateng",
        auditor=AUDITORS[2],
        closing_date=date(2024, 8, 8),
        risk_rating=4,
        history=(("2026-01", "equity", 10_000_000),),
        funding=(
            FundingSpec(
                "milestone_tranche",
                4_000_000,
                date(2027, 2, 26),
                "expected",
                "Milestone tranche, expected in February 2027",
            ),
        ),
    ),
    _c(
        id="orbitline-systems",
        name="Orbitline Systems",
        sector="Space software",
        stage="Series A",
        city="Huntsville",
        state="AL",
        cash=3_900_000,
        burn=210_000,
        rml="18.6",
        mrr=260_000,
        growth="0.030",
        gross_margin="0.70",
        customers=38,
        pledged=250_000,
        venture_debt=1_500_000,
        min_cash=2_000_000,
        scenario="clean",
        shape="dip",
        rm=RMS[3],
        analyst=TOMAS,
        cfo="Evander Pruitt",
        auditor=AUDITORS[3],
        closing_date=date(2025, 1, 17),
        risk_rating=4,
    ),
    _c(
        id="stripple-tech",
        name="Stripple Tech",
        sector="Fintech infrastructure",
        stage="Series B",
        city="Chicago",
        state="IL",
        cash=6_600_000,
        burn=300_000,
        rml="22.0",
        mrr=1_350_000,
        growth="0.025",
        gross_margin="0.78",
        customers=175,
        pledged=500_000,
        venture_debt=4_000_000,
        min_cash=3_500_000,
        scenario="stripple_package",
        shape="dip",
        rm=RMS[0],
        analyst=PRIYA,
        cfo="Cosima Aldridge",
        auditor=AUDITORS[0],
        closing_date=date(2024, 5, 30),
        risk_rating=5,
        capsw_frac="0.10",
    ),
    _c(
        id="veridia-payments",
        name="Veridia Payments",
        sector="Payments",
        stage="Series C",
        city="Atlanta",
        state="GA",
        cash=14_000_000,
        burn=550_000,
        rml="25.5",
        mrr=2_400_000,
        growth="0.018",
        gross_margin="0.70",
        customers=390,
        pledged=1_200_000,
        venture_debt=8_000_000,
        min_cash=7_000_000,
        scenario="clean",
        shape="dip",
        rm=RMS[1],
        analyst=TOMAS,
        cfo="Anselm Okonkwo-Reyes",
        auditor=AUDITORS[1],
        closing_date=date(2023, 10, 19),
        risk_rating=4,
        sti=3_000_000,
        history=(("2026-04", "debt", 5_000_000),),
    ),
    _c(
        id="tessaract-labs",
        name="Tessaract Labs",
        sector="Developer tools",
        stage="Series B",
        city="Seattle",
        state="WA",
        cash=11_000_000,
        burn=400_000,
        rml="27.5",
        mrr=1_050_000,
        growth="0.020",
        gross_margin="0.80",
        customers=520,
        pledged=600_000,
        venture_debt=4_000_000,
        min_cash=5_500_000,
        scenario="clean",
        shape="dip",
        rm=RMS[2],
        analyst=TOMAS,
        cfo="Philippa Strand",
        auditor=AUDITORS[2],
        closing_date=date(2024, 2, 2),
        risk_rating=4,
        sti=2_000_000,
    ),
    _c(
        id="pellucid-sensors",
        name="Pellucid Sensors",
        sector="Industrial IoT",
        stage="Series A",
        city="Minneapolis",
        state="MN",
        cash=6_300_000,
        burn=220_000,
        rml="28.6",
        mrr=330_000,
        growth="0.022",
        gross_margin="0.58",
        customers=54,
        pledged=300_000,
        venture_debt=1_000_000,
        min_cash=3_000_000,
        scenario="clean",
        shape="dip",
        rm=RMS[3],
        analyst=TOMAS,
        cfo="Garrick Lindahl",
        auditor=AUDITORS[3],
        closing_date=date(2024, 12, 5),
        risk_rating=4,
    ),
    _c(
        id="corvane-analytics",
        name="Corvane Analytics",
        sector="B2B SaaS",
        stage="Series B",
        city="Raleigh",
        state="NC",
        cash=8_400_000,
        burn=600_000,
        rml="14.0",
        mrr=801_000,
        growth="0.030",
        gross_margin="0.74",
        customers=118,
        pledged=500_000,
        venture_debt=3_000_000,
        min_cash=4_000_000,
        scenario="plan_miss",
        shape="dip",
        rm=RMS[0],
        analyst=PRIYA,
        cfo="Henrietta Voss",
        auditor=AUDITORS[0],
        closing_date=date(2024, 7, 11),
        risk_rating=6,
        extra={"jun_mrr": 900_000, "after_june": ["0.98", "0.95", "0.92", "0.89"], "plan_growth": "1.12"},
    ),
    _c(
        id="nimbusfield-security",
        name="Nimbusfield Security",
        sector="Cybersecurity",
        stage="Series A",
        city="Reston",
        state="VA",
        cash=3_300_000,
        burn=400_000,
        rml="8.3",
        mrr=300_000,
        growth="0.030",
        gross_margin="0.72",
        customers=66,
        pledged=250_000,
        venture_debt=2_000_000,
        min_cash=2_000_000,
        scenario="funding_slipped",
        shape="steady",
        rm=RMS[1],
        analyst=PRIYA,
        cfo="Wilhelmina Achterberg",
        auditor=AUDITORS[1],
        closing_date=date(2025, 3, 6),
        risk_rating=6,
        funding=(
            FundingSpec(
                "equity_round",
                15_000_000,
                date(2026, 11, 6),
                "expected",
                "Series A-2; the bank was told it would close on 6 November",
            ),
        ),
    ),
    _c(
        id="tidewell-medical",
        name="Tidewell Medical",
        sector="Medical devices",
        stage="Series B",
        city="Nashville",
        state="TN",
        cash=4_300_000,
        burn=350_000,
        rml="12.3",
        mrr=540_000,
        growth="0.022",
        gross_margin="0.64",
        customers=88,
        pledged=1_100_000,
        venture_debt=2_500_000,
        min_cash=3_000_000,
        scenario="restricted_account",
        shape="steady",
        rm=RMS[2],
        analyst=PRIYA,
        cfo="Barnaby Ekwueme",
        auditor=AUDITORS[2],
        closing_date=date(2024, 4, 18),
        risk_rating=5,
        extra={"newly_restricted": 1_000_000, "restricted_before": 100_000},
    ),
    _c(
        id="ferrogate-cloud",
        name="Ferrogate Cloud",
        sector="Cloud infrastructure",
        stage="Series C",
        city="Dallas",
        state="TX",
        cash=16_000_000,
        burn=-250_000,
        rml=None,
        mrr=3_000_000,
        growth="0.015",
        gross_margin="0.80",
        customers=300,
        pledged=700_000,
        venture_debt=6_000_000,
        min_cash=8_000_000,
        scenario="cash_flow_positive",
        shape="positive",
        rm=RMS[3],
        analyst=PRIYA,
        cfo="Ignatius Valcourt",
        auditor=AUDITORS[3],
        closing_date=date(2023, 12, 14),
        risk_rating=3,
        sti=4_000_000,
    ),
)
BY_ID: dict[str, ClientSpec] = {c.id: c for c in CLIENTS}

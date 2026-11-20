"""Terms, the agreement text, and what each client reports and sends (certificates, accounts, MRR, software)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from synthetic.books.innovation import model, reports
from synthetic.books.innovation.expected import DUE_DAYS, build_plan, cert_months
from synthetic.books.innovation.terms import build_terms
from synthetic.render import common
from synthetic.render.legal import render_legal

LAST = model.LAST


def terms_for(sim):
    return build_terms(sim.spec, build_plan(sim.spec, sim.series))


def test_agreement_cites_every_number_in_the_terms_on_the_page_it_prints(sims, tmp_path):
    sim = sims["dataflake"]
    terms = terms_for(sim)
    result = render_legal(tmp_path / "ca.pdf", terms.agreement, sim.spec.name)
    pages = common.page_texts(tmp_path / "ca.pdf")
    cites = terms.agreement.cites
    for anchor, cite in cites.items():
        assert common.squash(cite["quote"]) in common.squash(pages[result["anchor_pages"][anchor] - 1]), (
            anchor
        )
    assert "$5,000,000" in cites["cov_cash"]["quote"] and "6.0 months" in cites["cov_runway"]["quote"]
    assert "80%" in cites["cov_plan"]["quote"]
    assert (
        "excluding any cash that is pledged, escrowed or otherwise restricted"
        in cites["def_unrestricted_cash"]["quote"]
    )
    assert cites["def_unrestricted_cash"]["section"] == "1.1"
    for anchor, days in (
        ("rep_monthly", 30),
        ("rep_certificate", 30),
        ("rep_mrr", 15),
        ("rep_bank", 7),
        ("rep_annual", 180),
    ):
        assert f"{days} days" in cites[anchor]["quote"]


def test_every_client_has_the_three_covenants_and_five_reporting_requirements(sims):
    for sim in sims.values():
        spec, plan = sim.spec, build_plan(sim.spec, sim.series)
        terms = terms_for(sim)
        covenants = terms.version["terms"]["covenants"]
        assert [c["id"] for c in covenants] == [
            "min_unrestricted_cash",
            "min_runway_months",
            "revenue_vs_plan",
        ]
        assert [c["test"]["unit"] for c in covenants] == ["usd", "months", "pct"]
        assert [c["measurement"]["basis"] for c in covenants] == ["point", "t3m", "t3m"]
        assert {c["measurement"]["frequency"] for c in covenants} == {"monthly"}
        assert [c["test"]["threshold"] for c in covenants] == [str(spec.min_cash), "6.0", "0.80"]
        assert [(p["period_end"], int(p["amount"])) for p in covenants[2]["params"]["plan"]] == [
            (m.isoformat(), plan[m]) for m in sorted(plan)
        ]
        requirements = {r["id"]: r for r in terms.version["terms"]["reporting_requirements"]}
        assert {k: v["due_days_after_period_end"] for k, v in requirements.items()} == {
            "monthly_financials": 30,
            "compliance_certificate": 30,
            "mrr_report": 15,
            "bank_statements": 7,
            "annual_statements": 180,
        }
        assert DUE_DAYS["bank_statement"] == 7 and all(
            r["frequency"] == "monthly" for k, r in requirements.items() if k != "annual_statements"
        )
        anchors = {c["citation"]["_anchor"][1] for c in requirements.values()}
        assert anchors <= set(terms.agreement.cites)
        assert (
            terms.facility["commitment"] == str(spec.venture_debt)
            and terms.facility["borrowing_base"] is False
        )
        assert terms.version["status"] == "approved" and terms.version["terms"]["borrowing_base"] is None


def test_watch_levels_are_not_in_the_terms_they_are_signal_parameters(sims):
    """Owner default: the 12-month watch level is a signal parameter, the covenant floor is 6.0 months."""
    terms = terms_for(sims["dataflake"])
    assert (
        "watch" not in str(terms.version["terms"])
        and terms.version["terms"]["covenants"][1]["test"]["threshold"] == "6.0"
    )


def test_certificates_are_honest_except_the_two_designed_distortions(sims):
    for sim in sims.values():
        plan = build_plan(sim.spec, sim.series)
        certificates = reports.build_certificates(sim.spec, sim.series, plan)
        assert sorted(model.MONTHS.index(c["period_end"]) for c in certificates) == sorted(
            cert_months(sim.spec)
        )
    dataflake = reports.build_certificates(
        sims["dataflake"].spec, sims["dataflake"].series, {m: 1 for m in model.MONTHS}
    )
    october = dataflake[-1]["reported"]["min_unrestricted_cash"]
    assert october["value"] == D(6_100_000) and october["in_compliance"] is True
    assert {"Cash held in the pledged collateral account": 1_500_000}.items() <= {
        line["label"]: line["amount"] for line in october["calculation"]
    }.items()
    september = dataflake[-2]["reported"]["min_unrestricted_cash"]
    assert september["value"] == D(sims["dataflake"].series.cash(LAST - 1))
    ferrogate = reports.build_certificates(
        sims["ferrogate-cloud"].spec, sims["ferrogate-cloud"].series, {m: 1 for m in model.MONTHS}
    )[-1]["reported"]["min_runway_months"]
    assert ferrogate["value"] is None and ferrogate["in_compliance"] is True
    assert not [
        c
        for c in reports.build_certificates(
            sims["lumora-health"].spec, sims["lumora-health"].series, {m: 1 for m in model.MONTHS}
        )
        if c["period_end"] == date(2026, 10, 31)
    ]


def test_bank_accounts_tie_to_the_balance_sheet_and_roll_from_month_to_month(sims):
    for sim in sims.values():
        for i in (LAST - 2, LAST - 1, LAST):
            accounts = reports.bank_accounts(sim.spec, sim.months, i)
            balances = sim.months[i].balances
            assert (
                sum(a["closing"] for a in accounts if not a["restricted"]) == balances["bs.cash_unrestricted"]
            )
            assert sum(a["closing"] for a in accounts if a["restricted"]) == balances["bs.cash_restricted"]
            assert all(a["credits"] >= 0 and a["debits"] >= 0 for a in accounts)
            assert all(a["opening"] + a["credits"] - a["debits"] == a["closing"] for a in accounts), (
                sim.spec.id
            )
        before = {a["tail"]: a["closing"] for a in reports.bank_accounts(sim.spec, sim.months, LAST - 1)}
        after = {
            a["tail"]: a["opening"]
            for a in reports.bank_accounts(sim.spec, sim.months, LAST)
            if a["tail"] in before
        }
        assert before == after, sim.spec.id
    tidewell = reports.bank_accounts(sims["tidewell-medical"].spec, sims["tidewell-medical"].months, LAST)
    assert [(a["tail"], a["closing"]) for a in tidewell if a["restricted"]] == [
        ("9001", 100_000),
        ("9002", 1_000_000),
    ]


def test_the_mrr_bridge_adds_up_and_the_software_roll_ties(sims):
    for sim in sims.values():
        for i in range(LAST - 5, LAST + 1):
            bridge = reports.mrr_bridge(sim.months, i)
            assert (
                bridge["opening"]
                + bridge["new"]
                + bridge["expansion"]
                - bridge["contraction"]
                - bridge["churn"]
                == bridge["mrr"]
            )
            assert min(bridge["new"], bridge["churn"]) >= 0 and bridge["arr"] == 12 * bridge["mrr"], (
                sim.spec.id,
                i,
            )
            roll = reports.software_roll(sim.months, i)
            assert roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"], (
                sim.spec.id,
                i,
            )
    assert len(reports.mrr_bridge(sims["dataflake"].months, LAST)["trend"]) == 6


def test_printed_certificate_figures():
    assert reports.format_actual("usd", D(6_100_000)) == "$6,100,000"
    assert reports.format_actual("months", D("9.4")) == "9.4 months"
    assert reports.format_actual("pct", D("1.0530")) == "105.30%"
    assert reports.format_actual("months", None) == "Not meaningful (cash-flow positive)"
    assert reports.format_required("pct", D("0.80")) == "Not less than 80.00% of plan"


def test_ferrogate_gains_a_ttm_dscr_covenant_from_may_2026_mirroring_the_legacy_shape(sims, tmp_path):
    sim = sims["ferrogate-cloud"]
    terms = terms_for(sim)
    assert [c["id"] for c in terms.version["terms"]["covenants"]] == [
        "min_unrestricted_cash",
        "min_runway_months",
        "revenue_vs_plan",
    ]
    versions = terms.versions()
    assert [(v["version"], v["status"], v["effective_from"], v["effective_to"]) for v in versions] == [
        (1, "superseded", sim.spec.closing_date.isoformat(), "2026-05-30"),
        (2, "approved", "2026-05-31", None),
    ]
    dscr = versions[1]["terms"]["covenants"][3]
    assert dscr["id"] == "dscr" and dscr["archetype"] == "coverage"
    assert dscr["params"] == {
        "numerator_base": "ebitda",
        "deductions": [],
        "denominator": ["interest_expense", "scheduled_principal"],
    }
    assert dscr["test"] == {"operator": ">=", "threshold": "1.25", "steps": [], "unit": "ratio"}
    assert dscr["measurement"] == {"basis": "ttm", "frequency": "monthly"}
    assert dscr["rounding"] == {"dp": 2, "mode": "half_up"}
    assert [c["id"] for c in versions[1]["terms"]["covenants"][:3]] == [
        c["id"] for c in terms.version["terms"]["covenants"]
    ]
    assert versions[1]["id"] == "tv-ferrogate-cloud-2"
    anchors = {c["_anchor"][1] for c in dscr["citations"]}
    assert anchors == {"cov_dscr", "def_dscr"} <= set(terms.agreement.cites)
    result = render_legal(tmp_path / "ca.pdf", terms.agreement, sim.spec.name)
    pages = common.page_texts(tmp_path / "ca.pdf")
    for anchor, cite in terms.agreement.cites.items():
        assert common.squash(cite["quote"]) in common.squash(pages[result["anchor_pages"][anchor] - 1]), (
            anchor
        )
    assert "1.25 to 1.00" in terms.agreement.cites["cov_dscr"]["quote"]
    assert "shall not permit" in terms.agreement.cites["cov_dscr"]["quote"]


def test_only_ferrogate_has_a_second_terms_version(sims):
    for sim in sims.values():
        assert len(terms_for(sim).versions()) == (2 if sim.spec.id == "ferrogate-cloud" else 1)


def test_ferrogate_certificates_report_the_dscr_line_with_the_true_ttm_figure(sims):
    from synthetic.books.innovation.expected import q

    sim = sims["ferrogate-cloud"]
    certificates = reports.build_certificates(sim.spec, sim.series, build_plan(sim.spec, sim.series))
    assert certificates and all(c["period_end"] >= date(2026, 5, 31) for c in certificates)
    for certificate in certificates:
        line = certificate["reported"]["dscr"]
        i = model.MONTHS.index(certificate["period_end"])
        assert line["value"] == q(sim.series.dscr(i), 2) and line["threshold"] == D("1.25")
        assert line["unit"] == "ratio" and line["in_compliance"] is True
    assert reports.format_required("ratio", D("1.25")) == "Not less than 1.25 to 1.00"
    for other in ("dataflake", "tidewell-medical"):
        spec, series = sims[other].spec, sims[other].series
        assert all(
            "dscr" not in c["reported"]
            for c in reports.build_certificates(spec, series, build_plan(spec, series))
        )


def test_terms_versions_share_no_mutable_covenant_objects(sims):
    terms = terms_for(sims["ferrogate-cloud"])
    first, second = terms.versions()
    first["terms"]["covenants"][0]["test"]["threshold"] = "changed"
    first["terms"]["covenants"][0]["params"]["x"] = 1
    assert second["terms"]["covenants"][0]["test"]["threshold"] != "changed"
    assert terms.version["terms"]["covenants"][0]["test"]["threshold"] != "changed"
    assert terms.versions()[1]["terms"]["covenants"][0]["test"]["threshold"] != "changed"


def test_ferrogate_agreement_prints_the_dscr_definition_and_covenant_verbatim(sims, tmp_path):
    terms = terms_for(sims["ferrogate-cloud"])
    result = render_legal(tmp_path / "ca.pdf", terms.agreement, "Ferrogate Cloud")
    pages = common.page_texts(tmp_path / "ca.pdf")
    for anchor in ("def_dscr", "cov_dscr"):
        quote = terms.agreement.cites[anchor]["quote"]
        assert common.squash(quote) in common.squash(pages[result["anchor_pages"][anchor] - 1]), anchor


def test_documents_usd_prints_negatives_in_parentheses_like_the_renderer():
    from synthetic.books.innovation.documents import usd
    from synthetic.render.innovation import usd as printed

    assert usd(-750_000) == "($750,000)" == printed(-750_000)
    assert usd(750_000) == "$750,000" and usd(0) == "$0"

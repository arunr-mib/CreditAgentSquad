"""The documents each client sends: which exist, when they arrived, and what is printed on them."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from synthetic.book import DocPlan
from synthetic.books.innovation import reports
from synthetic.books.innovation.expected import DUE_DAYS, Series
from synthetic.books.innovation.model import LAST, MONTHS, Month, Period
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, ClientSpec
from synthetic.books.innovation.terms import SLUG, ClientTerms

D = Decimal
PACKAGE_MONTHS = (LAST - 2, LAST - 1, LAST)  # the three months with documents on file
CINDREL_LABELS = {
    "bs.deferred_revenue_current": "Contract liabilities",
    "bs.capitalised_software": "Capitalised software development costs",
    "cf.capitalised_software_spend": "Software development costs",
}


def month_name(end: date) -> str:
    return end.strftime("%B %Y")


def usd(value) -> str:
    v = int(value)
    return f"(${abs(v):,})" if v < 0 else f"${v:,}"


def _received(rng: random.Random, end: date, low: int, high: int) -> date:
    return min(end + timedelta(days=rng.randint(low, high)), AS_OF - timedelta(days=1))


def plan_documents(spec: ClientSpec, opening: Month, months: list[Month], periods: list[Period], fy2024: Period,
                   series: Series, certificates: list[dict], terms: ClientTerms, rng: random.Random) -> list[DocPlan]:
    """All documents on file for a client at the as-of date."""
    docs: list[DocPlan] = []
    by_end = {c["period_end"]: c for c in certificates}

    def add(slug: str, doc_type: str, title: str, period_end: date | None, received: date, payload: dict) -> DocPlan:
        doc = DocPlan(f"{spec.id}.{slug}", slug, doc_type, title, period_end, received, received, payload)
        docs.append(doc)
        return doc

    add(SLUG, "credit_agreement", f"Venture Loan and Security Agreement between {spec.name} and Bank of Stoic", None,
        spec.closing_date, {"legal": terms.agreement})
    fy2025 = periods[11]
    add("afs-2025", "annual_financial_statements", "Audited financial statements, fiscal 2025", fy2025.period_end,
        date(2026, 4, 3) + timedelta(days=rng.randint(0, 24)),
        {"end": fy2025.period_end, "prior_end": fy2024.period_end, "balances": months[11].balances,
         "prior_balances": opening.balances, "flows": fy2025.values, "prior_flows": fy2024.values})  # fmt: skip
    for i in PACKAGE_MONTHS:
        end, month = MONTHS[i], months[i]
        if spec.scenario == "late_package" and i == LAST:
            continue  # the October package has not arrived
        labels = CINDREL_LABELS if spec.scenario == "cindrel_package" and i == LAST else {}
        add(f"bank-{end.isoformat()}", "bank_statement", f"Account statement, {month_name(end)}", end,
            _received(rng, end, 2, 6),
            {"end": end, "accounts": reports.bank_accounts(spec, months, i), "notes": reports.bank_notes(spec, i)})
        add(f"mrr-{end.isoformat()}", "mrr_report", f"MRR report, {month_name(end)}", end, _received(rng, end, 4, 10),
            {"end": end, **reports.mrr_bridge(months, i)})
        add(f"mf-{end.isoformat()}", "monthly_financials", f"Management financial statements, {month_name(end)}", end,
            _received(rng, end, 10, 18),
            {"end": end, "months": end.month, "prior_end": date(2025, 12, 31), "balances": month.balances,
             "prior": months[11].balances, "ytd": periods[i].values, "month": {**month.flows, **month.balances},
             "labels": dict(labels), "software_roll": reports.software_roll(months, i)})  # fmt: skip
        cert = by_end[end]
        add(f"mcc-{end.isoformat()}", "compliance_certificate", f"Monthly compliance certificate, {month_name(end)}",
            end, _received(rng, end, 11, 18), {"certificate": cert, "end": end})
    return docs


def certificate_payload(spec: ClientSpec, doc: DocPlan, names: dict[str, str]) -> dict:
    """The renderer's view of a certificate: figures as printed."""
    cert = doc.payload["certificate"]
    reported = {}
    for covenant_id, entry in cert["reported"].items():
        reported[covenant_id] = {
            "in_compliance": entry["in_compliance"],
            "required_text": reports.format_required(entry["unit"], entry["threshold"]),
            "actual_text": reports.format_actual(entry["unit"], entry["value"]),
            "calculation": [(line["label"], usd(line["amount"])) for line in entry["calculation"]],
        }
    return {"end": cert["period_end"], "document_date": doc.document_date, "signed_by": cert["signed_by"],
            "reported": reported, "names": names}  # fmt: skip


def notice_documents(spec: ClientSpec, series: Series, months: list[Month], rng: random.Random) -> list[DocPlan]:
    """Term sheets and investor updates for the clients with a funding event the bank is tracking."""
    docs: list[DocPlan] = []
    oct_month = months[LAST]
    for event in spec.funding:
        close = event.expected_close
        if spec.id in ("datamarrow", "nimbusfield-security"):
            signed = spec.id == "datamarrow"
            doc_date = date(2026, 11, 10) if signed else date(2026, 9, 24)
            round_name = "Series B extension" if signed else "Series A-2 preferred stock financing"
            payload = {
                "heading": "SUMMARY OF TERMS (TERM SHEET)", "subheading": f"{round_name} - dated {doc_date:%B} {doc_date.day}, {doc_date.year}",
                "sections": [
                    ("Issuer", f"{spec.name}, a Delaware corporation."),
                    ("Transaction", f"Sale of {usd(event.amount)} of preferred stock to the lead investor and existing "
                                    "investors, as the " + round_name + "."),
                    ("Expected closing", f"On or about {close:%B} {close.day}, {close.year}, subject to the conditions below."),
                    ("Conditions", "Completion of confirmatory diligence, definitive documents, and the Lender's "
                                   "consent where the loan agreement requires it."),
                ],
                "table": [["Term", "Summary"], ["Amount", usd(event.amount)], ["Security", "Preferred stock"],
                          ["Expected closing", f"{close:%B} {close.day}, {close.year}"]],
                "closing": "This summary is non-binding except for confidentiality. " + ("Signed by the Company and the "
                           "lead investor." if signed else "Not yet signed by all parties."),
                "footer": "Term sheet",
            }  # fmt: skip
            docs.append(DocPlan(f"{spec.id}.term-sheet-{doc_date.isoformat()}", f"term-sheet-{doc_date.isoformat()}",
                                "term_sheet", f"Term sheet, {round_name}", None, doc_date,
                                doc_date + timedelta(days=1 if not signed else 2), {"notice": payload}))
    if spec.funding:
        update = {
            "heading": "INVESTOR UPDATE", "subheading": f"{month_name(CURRENT_PERIOD)}",
            "sections": [
                ("Highlights", f"Monthly recurring revenue closed the month at {usd(oct_month.balances['saas.mrr'])} "
                               f"({usd(oct_month.balances['saas.arr'])} annualised) across "
                               f"{oct_month.balances['saas.customers']:,} customers."),
                ("Cash and runway", f"Cash in operating accounts was {usd(series.cash(LAST))} at month end."),
                ("Financing", spec.funding[0].note + "."),
            ],
            "table": [["Metric", month_name(CURRENT_PERIOD)], ["MRR", usd(oct_month.balances["saas.mrr"])],
                      ["Customers", f"{oct_month.balances['saas.customers']:,}"],
                      ["Cash in operating accounts", usd(series.cash(LAST))]],
            "closing": "Sent to the Company's investors. Figures are management's and unaudited.",
            "footer": "Investor update",
        }  # fmt: skip
        received = date(2026, 11, 9) + timedelta(days=rng.randint(0, 4))
        docs.append(DocPlan(f"{spec.id}.investor-update-{CURRENT_PERIOD.isoformat()}",
                            f"investor-update-{CURRENT_PERIOD.isoformat()}", "investor_update",
                            f"Investor update, {month_name(CURRENT_PERIOD)}", CURRENT_PERIOD, received, received,
                            {"notice": update}))
    return docs


def cindrel_export(spec: ClientSpec, months: list[Month]) -> tuple[DocPlan, list[tuple[str, int, int]]]:
    """The stray MRR export: ten months of 2025 (the wrong year), no company name anywhere."""
    rows = [(MONTHS[i].strftime("%Y-%m"), months[i].balances["saas.mrr"], months[i].balances["saas.customers"])
            for i in range(10)]  # fmt: skip
    doc = DocPlan(f"{spec.id}.mrr-export", "mrr_export", "unclassified", "mrr_export", None, date(2026, 11, 5),
                  date(2026, 11, 5), {"rows": rows}, extra={"held": True})
    return doc, rows


def package_due(doc_type: str, period_end: date = CURRENT_PERIOD) -> date:
    return period_end + timedelta(days=DUE_DAYS[doc_type])

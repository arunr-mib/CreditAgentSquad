"""A stand-in for the model: a "perfect reader" that answers each agent request from the
synthetic book's ground truth and from what is printed in the document it was handed.

THIS IS NOT A MODEL. It proves the pipeline, the workflow and the grader end to end when no
model key is available. Nothing it produces says anything about model performance, and every
response it gives is labelled `stand-in` (`mode`, the served model name and the request id).

It answers the way a careful reader would:

- it reports a figure only when the label and the figure are printed on the page it cites, so
  a missing page or an image-only page simply yields fewer items, never a guess;
- it copies printed text character for character and never computes anything;
- where the print and the truth file disagree it reports the print and records the
  disagreement in `disagreements` (a finding about the book, not something to smooth over).

`tamper` is a hook for the mutation checks: a function `(agent, answer, context) -> answer`
applied to the answer before it is returned, to prove the product and the grader catch a
reader that is wrong.
"""
import base64
import hashlib
import json
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pymupdf
from app.agents.llm import LLMRequest, LLMResponse

from evals.book import DOC_TYPES, TOTALS, Book, Borrower, long_date, parse_printed, squash

STANDIN_MODEL = "stand-in-perfect-reader"
Tamper = Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]]

# what each printed line of the borrowing base certificate means
BBC_LABELS = {
    "Gross accounts receivable per aging": "ar_total",
    "Less: affiliate, foreign and government accounts": "ar_ineligible_excluded",
    "Less: invoices more than 90 days past invoice date": "ar_ineligible_age",
    "Less: cross-aged accounts": "ar_ineligible_cross_aging",
    "Less: contra accounts": "ar_ineligible_contra",
    "Less: concentration in excess of limit": "ar_ineligible_concentration",
    "Total ineligible accounts": "ar_ineligible_total",
    "Eligible Accounts": "ar_eligible",
    "Accounts receivable availability": "ar_availability",
    "Gross inventory": "inventory_total",
    "Less: ineligible inventory": "inventory_ineligible",
    "Eligible Inventory": "inventory_eligible",
    "Inventory availability before sublimit": "inventory_availability_before_sublimit",
    "Inventory availability": "inventory_availability",
    "Less: Reserves": "reserves",
    "Borrowing Base": "borrowing_base",
    "Revolving Commitment": "commitment",
    "Lesser of Borrowing Base and Revolving Commitment": "borrowing_limit",
    "Revolving Loans outstanding": "outstanding",
    "Letters of credit outstanding": "letters_of_credit",
    "Availability (over-advance)": "availability",
}
# a bank statement's balances are the product's bank facts, not statement lines
BANK_KEYS = {"bs.cash_unrestricted": "bank.cash_unrestricted", "bs.cash_restricted": "bank.cash_restricted"}
_TITLE = re.compile(r"financial statements|compliance certificate|borrowing base certificate|agreement|amendment|waiver"
                    r"|term sheet|investor update|monthly recurring revenue|account statement", re.I)
_UNITS = re.compile(r"\(in (?:thousands of |whole )?U\.S\. dollars[^)]*\)", re.I)
_DOCUMENT = re.compile(r'<document number="(\d+)" file="([^"]*)" pages="(\d+)">\n(.*?)\n</document>', re.S)


class StandInError(Exception):
    """The stand-in was asked something it cannot answer (an unknown agent or borrower)."""


def _lines(page: pymupdf.Page) -> list[str]:
    return [line.strip() for line in page.get_text("text").split("\n") if line.strip()]


def _is_figure(text: str) -> bool:
    return parse_printed(text) is not None


class StandInReader:
    """Serves `LLMClient.create` from the book. One instance may serve every borrower."""

    mode = "standin"

    def __init__(self, book: Book, tamper: Tamper | None = None):
        self.book = book
        self.tamper = tamper
        self.requests: list[LLMRequest] = []
        self.disagreements: list[dict[str, Any]] = []  # print vs truth, found while reading
        self.answers: list[dict[str, Any]] = []  # {record_key, agent, answer} as returned

    # ---- entry point -------------------------------------------------------------------

    def create(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        parts = request.record_key.split("/")
        if len(parts) < 3:
            raise StandInError(f"cannot read the record key {request.record_key!r}")
        agent, code = parts[0], parts[1]
        borrower = self.book.get(code)
        if borrower is None:
            raise StandInError(f"{code} is not in the book")
        handler = {"intake": self._intake, "spreading": self._spreading, "certificate": self._certificate,
                   "collateral": self._collateral, "review": self._review}.get(agent)
        if handler is None:
            raise StandInError(f"the stand-in has no reader for the agent {agent!r}")
        context: dict[str, Any] = {"borrower": code, "record_key": request.record_key}
        answer = handler(borrower, request, context)
        if self.tamper is not None:
            answer = self.tamper(agent, answer, context)
        self.answers.append({"record_key": request.record_key, "agent": agent, "answer": answer})
        return LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn",
                           model=STANDIN_MODEL, usage={}, request_id="stand-in")

    # ---- request content ----------------------------------------------------------------

    @staticmethod
    def _blocks(request: LLMRequest) -> list[dict[str, Any]]:
        content = request.messages[0]["content"]
        return content if isinstance(content, list) else [{"type": "text", "text": str(content)}]

    def _text(self, request: LLMRequest) -> str:
        return "\n".join(b.get("text", "") for b in self._blocks(request) if b.get("type") == "text")

    def _pdf(self, borrower: Borrower, request: LLMRequest) -> tuple[pymupdf.Document, dict[str, Any] | None]:
        """The PDF the request carries and the truth entry that describes it (matched by content)."""
        block = next((b for b in self._blocks(request) if b.get("type") == "document"), None)
        if block is None:
            raise StandInError(f"{request.record_key}: the request carries no document")
        data = base64.standard_b64decode(block["source"]["data"])
        meta = borrower.document_by_sha(hashlib.sha256(data).hexdigest())
        return pymupdf.open(stream=data, filetype="pdf"), meta

    def _disagree(self, context: dict[str, Any], what: str, printed: Any, truth: Any) -> None:
        self.disagreements.append({"borrower": context["borrower"], "record_key": context["record_key"],
                                   "what": what, "printed": printed, "truth": truth})

    # ---- intake ---------------------------------------------------------------------------

    def _intake(self, borrower: Borrower, request: LLMRequest, context: dict[str, Any]) -> dict[str, Any]:
        documents = []
        for number, file_name, _pages, head in _DOCUMENT.findall(self._text(request)):
            meta = borrower.document_by_file(file_name)
            flat = squash(head)
            if meta is None or head.strip() == "[no readable text]":
                documents.append({"document_number": int(number), "doc_type": "other", "period_end_text": "",
                                  "effective_date_text": "", "quality": "na", "title_as_printed": "",
                                  "concern": "The first pages have no readable text, so the document could not be identified."
                                  if meta is not None else "This file is not one the reader recognises for this borrower."})
                continue
            doc_type = DOC_TYPES.get(meta["type"], meta["type"])
            period_text = effective_text = ""
            if meta.get("period_end"):
                wanted = long_date(date.fromisoformat(meta["period_end"]))
                period_text = wanted if squash(wanted) in flat else ""
            elif meta.get("document_date"):
                wanted = long_date(date.fromisoformat(meta["document_date"]))
                effective_text = wanted if squash(wanted) in flat else ""
            title = next((line.strip() for line in head.split("\n")
                          if _TITLE.search(line) and " | " not in line), "")
            documents.append({
                "document_number": int(number), "doc_type": doc_type, "period_end_text": period_text,
                "effective_date_text": effective_text,
                "quality": meta.get("quality", "na") if "statements" in doc_type else "na",
                "title_as_printed": title,
                # the held export: a print of a workbook that names no company and carries no period
                "concern": "The file names no company and shows a different year." if meta.get("held") else ""})
        return {"documents": documents}

    # ---- spreading ------------------------------------------------------------------------

    def _spreading(self, borrower: Borrower, request: LLMRequest, context: dict[str, Any]) -> dict[str, Any]:
        pdf, meta = self._pdf(borrower, request)
        empty = {"scale_statement": "", "scale_page": 0, "cells": [], "comparative_cells": [], "absent_keys": [],
                 "notes": []}
        if meta is None or "figures" not in meta:
            return {**empty, "notes": ["This document is not a set of financial statements the reader recognises."]}
        context["document"] = meta["id"]
        pages = {n: _lines(page) for n, page in enumerate(pdf, start=1)}
        flat = {n: squash(" ".join(lines)) for n, lines in pages.items()}
        current = long_date(date.fromisoformat(meta["period_end"]))
        comparative = long_date(date.fromisoformat(meta["comparative_period_end"])) \
            if meta.get("comparative_period_end") else None

        scale_statement, scale_page = "", 0
        for n in sorted(pages):
            found = next((m.group(0) for line in pages[n] if (m := _UNITS.search(line))), None)
            if found and any(v["page"] == n for v in meta["figures"].values()):
                scale_statement, scale_page = found, n
                break

        cells, comparative_cells, unread = [], [], []
        for key, figure in meta["figures"].items():
            page, label, printed = figure["page"], figure["label"], figure["printed"]
            name = BANK_KEYS[key] if meta["type"] == "bank_statement" and key in BANK_KEYS else (
                f"stated.{key}" if key in TOTALS else key)
            lines = pages.get(page, [])
            # a careful reader reports a figure only when the row is really there: the label,
            # then the figure for the period, then the comparative figure
            at = next((i for i in range(len(lines) - 1) if lines[i] == label and lines[i + 1] == printed), None)
            if at is None or squash(current) not in flat.get(page, ""):
                unread.append(key)
                continue
            cells.append({"key": name, "page": page, "printed_figure": printed, "printed_label": label,
                          "column_header": current})
            prior = (meta.get("comparative_printed") or {}).get(key)
            on_row = at + 2 < len(lines) and lines[at + 2] == prior
            if prior is not None and comparative and on_row and squash(comparative) in flat.get(page, ""):
                comparative_cells.append({"key": name, "page": page, "printed_figure": prior,
                                          "printed_label": label, "column_header": comparative})
        notes = []
        image_pages = [n for n, lines in pages.items() if not lines]
        if image_pages:
            notes.append("One or more pages are images with no readable text, so their lines are not reported.")
        if any(d.get("type") == "missing_page" for d in meta.get("defects", [])):
            notes.append("A page appears to be missing from the statements, so the lines printed on it are not reported.")
        if unread and not notes:
            notes.append("Some lines listed for this document were not found on the page and are not reported.")
        for key in unread:
            if key not in meta.get("unreadable_keys", []):
                self._disagree(context, f"figure {key}", "not on the cited page", meta["figures"][key])
        return {"scale_statement": scale_statement, "scale_page": scale_page, "cells": cells,
                "comparative_cells": comparative_cells, "absent_keys": sorted(meta.get("absent_keys", [])),
                "notes": notes}

    # ---- compliance certificate -------------------------------------------------------------

    def _certificate(self, borrower: Borrower, request: LLMRequest, context: dict[str, Any]) -> dict[str, Any]:
        pdf, meta = self._pdf(borrower, request)
        if meta is not None:
            context["document"] = meta["id"]
        # the covenants the request lists (id | name) are the ones the reader is asked about
        asked = dict(re.findall(r"^- ([a-z0-9_]+) \| (.+)$", self._text(request), re.M))
        by_name = {name.strip().lower(): cid for cid, name in asked.items()}
        rows, scale_statement, scale_page = [], "", 0
        for n, page in enumerate(pdf, start=1):
            lines = _lines(page)
            for line in lines:
                if not scale_statement and line.lower().startswith("dollar amounts in this certificate"):
                    scale_statement, scale_page = line, n
            start = _certificate_header_end(lines)
            if start is None or rows:
                continue
            dropped: list[list[str]] = []
            found = _certificate_rows(lines, start, dropped)
            for cells in dropped:
                self._disagree(context, "certificate row not readable", cells, None)
            for name, _section, required, actual, compliance in found:
                # a covenant name may wrap: try the whole name, then its first line
                covenant_id = by_name.get(name.lower()) or by_name.get(name.split(" | ")[0].lower())
                if covenant_id is not None:
                    rows.append({"covenant_id": covenant_id, "page": n, "printed_label": name,
                                 "actual_printed": actual, "required_printed": required,
                                 "compliance_printed": compliance})
        truth = borrower.certificate(date.fromisoformat(meta["period_end"])) if meta and meta.get("period_end") else None
        notes = []
        if truth is not None:
            scale = truth.get("scale", 1)
            for row in rows:
                reported = truth["reported"].get(row["covenant_id"])
                if reported is None:
                    self._disagree(context, f"certificate row {row['covenant_id']}", row["actual_printed"], None)
                    continue
                factor = scale if reported.get("unit", "ratio") == "usd" else 1
                if not _printed_matches(row["actual_printed"], reported, factor):
                    self._disagree(context, f"certificate value {row['covenant_id']}", row["actual_printed"], reported["value"])
                if (row["compliance_printed"] == "Yes") != bool(reported["in_compliance"]):
                    self._disagree(context, f"certificate compliance {row['covenant_id']}", row["compliance_printed"],
                                   reported["in_compliance"])
            if sorted(set(asked) - {r["covenant_id"] for r in rows}):
                notes.append("The certificate does not report every covenant in the approved terms.")
        return {"rows": rows, "scale_statement": scale_statement, "scale_page": scale_page, "notes": notes}

    # ---- borrowing base certificate -----------------------------------------------------------

    def _collateral(self, borrower: Borrower, request: LLMRequest, context: dict[str, Any]) -> dict[str, Any]:
        pdf, meta = self._pdf(borrower, request)
        if meta is not None:
            context["document"] = meta["id"]
        certificate_lines, aging_headers, aging_rows, inventory_rows = [], [], [], []
        scale_statement, scale_page = "", 0
        for n, page in enumerate(pdf, start=1):
            lines = _lines(page)
            if "BORROWING BASE CERTIFICATE" in lines:
                found = next((m.group(0) for line in lines if (m := _UNITS.search(line))), None)
                if found:
                    scale_statement, scale_page = found, n
                for i, line in enumerate(lines[:-1]):
                    name = BBC_LABELS.get(line)
                    if name is not None and _is_figure(lines[i + 1]) and not lines[i + 1].endswith("%"):
                        certificate_lines.append({"line": name, "page": n, "printed_label": line,
                                                  "printed_figure": lines[i + 1]})
            elif "Accounts Receivable Aging by Customer" in lines and "Note" in lines:
                start = lines.index("Customer")
                aging_headers = lines[start + 1:lines.index("Note", start)]
                width = len(aging_headers)
                i = lines.index("Note", start) + 1
                while i + width < len(lines) and lines[i] != "Total":
                    figures = lines[i + 1:i + 1 + width]
                    if not all(_is_figure(f) for f in figures):
                        break
                    after = i + 1 + width
                    # the note column: one more line on the row, unless that line starts the next row
                    following = lines[after + 1:after + 1 + width]
                    is_next_row = after >= len(lines) or lines[after] == "Total" or (
                        len(following) == width and all(_is_figure(f) for f in following))
                    note = "" if is_next_row else lines[after]
                    aging_rows.append({"page": n, "customer_printed": lines[i], "figures_printed": figures,
                                       "note_printed": note})
                    i = after if is_next_row else after + 1
            elif "Inventory Report by Category" in lines and "Amount" in lines:
                i = lines.index("Amount") + 1
                while i + 1 < len(lines) and not lines[i].lower().startswith("total") and _is_figure(lines[i + 1]):
                    inventory_rows.append({"page": n, "category_printed": lines[i], "amount_printed": lines[i + 1]})
                    i += 2
        truth = borrower.borrowing_base(date.fromisoformat(meta["period_end"])) if meta and meta.get("period_end") else None
        if truth is not None:
            printed_names = [r["customer_printed"] for r in aging_rows]
            if printed_names != [r["customer"] for r in truth["ar_aging"]]:
                self._disagree(context, "aging customers", printed_names, [r["customer"] for r in truth["ar_aging"]])
            if len(inventory_rows) != len(truth["inventory"]):
                self._disagree(context, "inventory rows", len(inventory_rows), len(truth["inventory"]))
        return {"certificate_lines": certificate_lines, "aging_headers": aging_headers, "aging_rows": aging_rows,
                "inventory_rows": inventory_rows, "scale_statement": scale_statement, "scale_page": scale_page,
                "notes": []}

    # ---- review commentary ----------------------------------------------------------------------

    def _review(self, borrower: Borrower, request: LLMRequest, context: dict[str, Any]) -> dict[str, Any]:
        """A minimal grounded draft: every figure is a reference to a fact on the sheet, and no
        digit is typed. It is a placeholder for a model's prose, not an example of it."""
        text = self._text(request)
        marker, listing = "Review sheet (structure; figures appear as fact ids):\n", "\n\nFacts you may reference:\n"
        try:
            sheet = json.loads(text[text.index(marker) + len(marker):text.index(listing)])
        except (ValueError, json.JSONDecodeError):
            return {"sections": []}

        def ref(fact_id: str | None) -> str | None:
            return f"{{{{fact:{fact_id}}}}}" if fact_id else None

        def words(label: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r"\d", "", label)).strip(" ,")

        sections = []
        performance = []
        for metric in sheet.get("metrics", []):
            now, then = ref(metric.get("current")), ref(metric.get("year_earlier"))
            if now and then:
                performance.append(f"{words(metric['label'])} was {now}, compared with {then} a year earlier.")
            elif now:
                performance.append(f"{words(metric['label'])} was {now}.")
        covenants = []
        for test in sheet.get("covenants", []):
            value, threshold = ref(test.get("value")), ref(test.get("threshold"))
            outcome = str(test.get("outcome", "")).replace("_", " ")
            if value and threshold:
                covenants.append(f"{words(test['covenant'])} was calculated at {value} against a requirement of "
                                 f"{threshold}; the result recorded is {outcome}.")
        collateral = sheet.get("collateral") or {}
        if performance:
            sections.append({"section": "performance", "body": " ".join(performance[:6])})
        if covenants:
            sections.append({"section": "covenants", "body": " ".join(covenants)})
        if ref(collateral.get("availability")):
            sections.append({"section": "collateral", "body": (
                f"Availability under the borrowing base was {ref(collateral['availability'])}; the recalculation "
                f"outcome recorded is {str(collateral.get('outcome', '')).replace('_', ' ')}.")})
        open_items = [w for w in sheet.get("work_items", []) if w.get("status") == "open"]
        sections.insert(0, {"section": "summary", "body": (
            "Stand-in draft for the reviewer to replace. The figures for the period are set out in the sections "
            "below, each taken from the facts on this sheet. "
            + ("There are open items awaiting a decision." if open_items else "No items are awaiting a decision."))})
        return {"sections": sections}


def _certificate_header_end(lines: list[str]) -> int | None:
    """Where the rows of the covenant table start: after the Covenant, Section, Required, Actual and
    In compliance headers, which a page may print as separate lines or run together."""
    for i in range(len(lines) - 3):
        if lines[i:i + 3] == ["Covenant", "Section", "Required"]:
            j = i + 3
            while j < len(lines) and lines[j].startswith(("Actual", "In compliance")):
                j += 1
            return j
    return None


def _certificate_rows(lines: list[str], start: int,
                      dropped: list[list[str]] | None = None) -> list[tuple[str, str, str, str, str]]:
    """Rows after the header: covenant, section, required, actual, in-compliance. A cell may wrap onto the
    next line, so a row ends at the Yes/No that closes it and its cells are the lines before it."""
    rows: list[tuple[str, str, str, str, str]] = []
    current: list[str] = []
    for line in lines[start:]:
        if line in ("Yes", "No"):
            at = next((k for k, c in enumerate(current) if re.fullmatch(r"\d+(\.\d+)*", c)), None)
            if at is not None and 0 < at < len(current) - 1:
                rows.append((" ".join(current[:at]), current[at], " ".join(current[at + 1:-1]), current[-1], line))
            elif dropped is not None:
                dropped.append([*current, line])
            current = []
        elif line.lower().startswith(("dollar amounts", "certif")):
            break
        else:
            current.append(line)
    return rows


def _printed_matches(printed: str, reported: dict[str, Any], factor: int) -> bool:
    """Does the printed actual say what the truth says: text for a value that is not meaningful, otherwise
    the figure with its unit word, percent sign or "to 1.00" removed, at the precision printed."""
    if reported["value"] is None:
        return printed.lower().startswith("not meaningful")
    head = printed.removesuffix(" months").removesuffix(" to 1.00").strip()
    value = parse_printed(head)
    if value is None:
        return False
    truth = _dec(reported["value"]) / factor
    if printed.endswith("%"):
        truth *= 100
    if reported.get("unit", "ratio") in ("pct", "ratio"):
        exponent = value.as_tuple().exponent
        places = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        return value == truth.quantize(Decimal(1).scaleb(-places))
    return value * factor == _dec(reported["value"])


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))

"""The synthetic book as the evaluation reads it: truth files, the documents they describe and
the owner's oracle. Nothing here imports the product, so the grader's view of the truth is
independent of the code it grades."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BOOKS = {"legacy": REPO / "synthetic" / "out",
         "innovation": REPO / "synthetic" / "books" / "innovation" / "out"}
DEFAULT_BOOK = BOOKS["innovation"]


def oracle_for(root: Path | str) -> Path:
    """The owner's oracle for the book generated into `root`: both generators write it beside `out/`."""
    return Path(root).parent / "oracle.csv"


_GENERATORS = {"legacy": "synthetic.generate", "innovation": "synthetic.books.innovation.generate"}

# the book's document type names -> the product's
DOC_TYPES = {"annual_financial_statements": "annual_statements",
             "interim_financial_statements": "interim_statements",
             "unclassified": "other"}
# borrowing base certificate lines: the book's names -> the product's fact names
BB_LINES = {
    "gross_ar": "ar_total", "ineligible_excluded": "ar_ineligible_excluded",
    "ineligible_over_age": "ar_ineligible_age", "ineligible_cross_aging": "ar_ineligible_cross_aging",
    "ineligible_contra": "ar_ineligible_contra", "ineligible_concentration": "ar_ineligible_concentration",
    "total_ineligible_ar": "ar_ineligible_total", "eligible_ar": "ar_eligible",
    "gross_inventory": "inventory_total", "ineligible_inventory": "inventory_ineligible",
    "eligible_inventory": "inventory_eligible", "lesser_of_base_and_commitment": "borrowing_limit",
}
AR_BUCKETS = {"0_30": "current", "31_60": "days_31_60", "61_90": "days_61_90", "over_90": "over_90"}
# template lines that are totals (the statement prints them; the product computes them and keeps
# the printed figure as `stated.<key>`)
TOTALS = frozenset({
    "is.gross_profit", "is.operating_income", "is.pretax_income", "is.net_income",
    "bs.total_current_assets", "bs.total_assets", "bs.total_current_liabilities", "bs.total_liabilities",
    "bs.total_liabilities_and_equity", "cf.cfo", "cf.cfi", "cf.cff", "cf.net_change_in_cash",
    # vc-1 (the innovation book's template)
    "is.total_revenue", "is.vc_gross_profit", "is.vc_operating_loss", "is.vc_net_loss",
    "bs.vc_total_cash", "bs.vc_total_assets", "bs.vc_total_liabilities", "bs.vc_total_equity",
    "bs.vc_total_liabilities_and_equity", "cf.vc_net_change_in_cash"})
# lines printed as outflows in brackets and stored positive
OUTFLOWS = frozenset({"cf.capex", "cf.term_debt_repayments", "cf.distributions"})


def long_date(day: date) -> str:
    """A date as the book prints it: September 30, 2026."""
    return f"{day:%B} {day.day}, {day.year}"


def parse_printed(text: str) -> Decimal | None:
    """Read one printed figure the way an accountant does: brackets are negative, a dash is
    zero, commas, currency signs, a trailing x or % are dropped. None when it is not a figure."""
    t = text.strip().replace("$", "").replace(",", "").replace(" ", "")
    if t in ("-", "–", "—"):
        return Decimal(0)
    negative = t.startswith("(") and t.endswith(")")
    if negative:
        t = t[1:-1]
    t = t.rstrip("x%")
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return -value if negative else value


def squash(text: str) -> str:
    """Text with all whitespace removed and typographic quotes and dashes folded, for 'is this
    printed on the page' checks that must not depend on line breaks."""
    folded = (text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
              .replace("–", "-").replace("—", "-").replace("−", "-").replace(" ", " "))
    return "".join(folded.split())


@dataclass
class Borrower:
    """One borrower's truth file with the lookups the stand-in and the grader need."""

    truth: dict[str, Any]
    root: Path
    _sha: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    @property
    def code(self) -> str:
        return self.truth["borrower"]["id"]

    @property
    def scenario(self) -> str:
        return self.truth["scenario"]["code"]

    @property
    def current_period(self) -> date:
        return date.fromisoformat(self.truth["current_period"])

    @property
    def as_of(self) -> date:
        return date.fromisoformat(self.truth["as_of"])

    def documents(self, period_end: date | None = None) -> list[dict[str, Any]]:
        docs = self.truth["documents"]
        if period_end is None:
            return list(docs)
        return [d for d in docs if d.get("period_end") == period_end.isoformat()]

    def document_by_file(self, file_name: str) -> dict[str, Any] | None:
        return next((d for d in self.truth["documents"] if Path(d["path"]).name == file_name), None)

    def document_by_sha(self, sha256: str) -> dict[str, Any] | None:
        if not self._sha:
            for d in self.truth["documents"]:
                path = self.root / d["path"]
                if path.exists():
                    self._sha[hashlib.sha256(path.read_bytes()).hexdigest()] = d
        return self._sha.get(sha256)

    def period(self, period_end: date) -> dict[str, Any] | None:
        every = self.truth.get("comparative_periods", []) + self.truth["periods"]
        return next((p for p in every if p["period_end"] == period_end.isoformat()), None)

    def certificate(self, period_end: date) -> dict[str, Any] | None:
        return next((c for c in self.truth["certificates"] if c["period_end"] == period_end.isoformat()), None)

    def borrowing_base(self, period_end: date) -> dict[str, Any] | None:
        return next((b for b in self.truth["borrowing_base"] if b["period_end"] == period_end.isoformat()), None)

    def covenant_names(self) -> dict[str, str]:
        """covenant id -> name, over every terms version on file."""
        names: dict[str, str] = {}
        for version in self.truth["terms_versions"]:
            for covenant in version["terms"]["covenants"]:
                names.setdefault(covenant["id"], covenant["name"])
        return names

    def expected_exception_types(self) -> list[str]:
        return sorted({x["type"] for x in self.truth["expected"]["exceptions"]})

    def expected_tests(self, period_end: date) -> list[dict[str, Any]]:
        return [t for t in self.truth["expected"]["covenant_tests"] if t["period_end"] == period_end.isoformat()]

    def expected_borrowing_base(self, period_end: date) -> dict[str, Any] | None:
        return next((b for b in self.truth["expected"]["borrowing_base"]
                     if b["period_end"] == period_end.isoformat()), None)

    def expected_signals(self, period_end: date) -> list[dict[str, Any]]:
        return [s for s in self.truth["expected"]["signals"] if s["period_end"] == period_end.isoformat()]


@dataclass
class Book:
    root: Path
    borrowers: dict[str, Borrower]

    def __iter__(self):
        return iter(self.borrowers.values())

    def __len__(self) -> int:
        return len(self.borrowers)

    def get(self, code: str) -> Borrower | None:
        return self.borrowers.get(code)


def load_book(root: Path | str = DEFAULT_BOOK, only: list[str] | None = None) -> Book:
    root = Path(root)
    files = sorted((root / "truth").glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no truth files under {root}/truth; run: uv run python -m synthetic.generate")
    borrowers = {}
    for path in files:
        truth = json.loads(path.read_text())
        if only and truth["borrower"]["id"] not in only:
            continue
        borrowers[truth["borrower"]["id"]] = Borrower(truth, root)
    missing = sorted(set(only or []) - set(borrowers))
    if missing:
        raise KeyError(f"borrowers not in the book: {', '.join(missing)}")
    return Book(root, borrowers)


def generate_book(out: Path | str, book: str = "legacy") -> Path:
    """Build a synthetic book into `out` (about five seconds). Its oracle is written beside `out`."""
    subprocess.run([sys.executable, "-m", _GENERATORS[book], "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    return Path(out)


def unsigned_oracle_rows(codes: list[str], oracle: Path) -> list[dict[str, str]]:
    """Oracle rows for these borrowers that the owner has not signed. A borrower with no oracle
    row at all counts as unsigned: there is nothing the owner agreed to grade against."""
    with oracle.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    wanted = set(codes)
    unsigned = [r for r in rows if r["borrower_id"] in wanted and r.get("owner_signed_off", "").strip().lower() != "yes"]
    covered = {r["borrower_id"] for r in rows}
    unsigned.extend({"borrower_id": code, "kind": "none", "item": "no oracle row", "owner_signed_off": "no"}
                    for code in sorted(wanted - covered))
    return unsigned

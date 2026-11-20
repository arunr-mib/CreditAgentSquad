"""The four C&I borrowers kept from the v1 book: same truth, terms, documents and answer-key rows.

They are built by the frozen v1 modules with the v1 seed, so they stay byte-identical to `synthetic/out`, and the
recordings and signed oracle rows that rest on them stay valid."""

from __future__ import annotations

from synthetic.book import BorrowerBook, build_borrower
from synthetic.books.innovation.roster import KEPT_IDS, LEGACY_SEED
from synthetic.scenarios import ROSTER


def build_kept(seed: int = LEGACY_SEED) -> list[BorrowerBook]:
    by_id = {spec.id: spec for spec in ROSTER}
    return [build_borrower(by_id[borrower_id], seed) for borrower_id in KEPT_IDS]

"""Names shared by the publishing tests."""
from datetime import date

from app.domain.credit import Borrower
from sqlalchemy import select

CODES = ("kestrel-bay-packaging", "briarstone-beverage", "thornbury-metal", "sablewood-dental")
PERIOD = date(2026, 9, 30)


def borrower_of(db, code: str) -> Borrower:
    return db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()

"""Demo users, one or more per role. Names are invented. Run: python -m app.seed_users"""
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.roles import Role
from app.core.security import hash_password
from app.domain.org import User

DEMO_USERS = [
    ("priya.raman@bankofstoic.example", "Priya Raman", "Senior Credit Analyst", Role.ANALYST),
    ("tomas.keller@bankofstoic.example", "Tomas Keller", "Credit Analyst", Role.ANALYST),
    ("dana.whitfield@bankofstoic.example", "Dana Whitfield", "Portfolio Manager", Role.PORTFOLIO_MANAGER),
    ("marcus.oyelaran@bankofstoic.example", "Marcus Oyelaran", "Relationship Manager", Role.PORTFOLIO_MANAGER),
    ("helen.strand@bankofstoic.example", "Helen Strand", "Senior Credit Officer", Role.CREDIT_OFFICER),
    ("li.zhang@bankofstoic.example", "Li Zhang", "Credit Administration Lead", Role.CREDIT_ADMIN),
    ("omar.haddad@bankofstoic.example", "Omar Haddad", "Loan Administrator", Role.CREDIT_ADMIN),
    ("ruth.calloway@bankofstoic.example", "Ruth Calloway", "Credit Review Officer", Role.CREDIT_REVIEW),
    ("admin@bankofstoic.example", "Platform Administrator", "Administrator", Role.ADMIN),
]


def seed_users(db: Session, password: str | None = None) -> int:
    password = password or os.environ.get("SQUAD_DEMO_PASSWORD", "squad-demo")
    created = 0
    for email, name, title, role in DEMO_USERS:
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            continue
        user = User(email=email, name=name, title=title, role=role.value, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        ledger.record(db, actor_type="system", actor_id="seed", action="user.created",
                      entity_type="user", entity_id=user.id, payload={"email": email, "role": role.value})
        created += 1
    return created


if __name__ == "__main__":
    from app.core.db import get_engine

    with Session(get_engine()) as session:
        print(f"created {seed_users(session)} users")
        session.commit()

"""The date the workspace treats as today. A stored setting lets a demo move time forward so
quarter ends arrive and reporting falls due; without it, the real date is used."""
from datetime import date

from sqlalchemy.orm import Session

from app.core import ledger
from app.domain.governance import AppSetting

_KEY = "clock"


def today(db: Session) -> date:
    row = db.get(AppSetting, _KEY)
    if row is not None and row.value.get("today"):
        return date.fromisoformat(row.value["today"])
    return date.today()


def set_today(db: Session, value: date, *, actor: tuple[str, str] = ("system", "clock")) -> None:
    row = db.get(AppSetting, _KEY)
    previous = row.value.get("today") if row else None
    if row is None:
        db.add(AppSetting(key=_KEY, value={"today": value.isoformat()}))
    else:
        row.value = {"today": value.isoformat()}
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="clock.set", entity_type="app_setting",
                  entity_id=_KEY, payload={"from": previous, "to": value})
    db.flush()

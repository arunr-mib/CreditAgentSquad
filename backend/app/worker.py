"""Background worker: runs queued jobs and, on a schedule, moves every open cycle forward.

Run: PYTHONPATH=backend python -m app.worker            (loop)
     PYTHONPATH=backend python -m app.worker --once     (drain the queue once and exit)
"""
import argparse
import logging
import time

from sqlalchemy.orm import Session

from app.core import clock
from app.core.db import get_engine
from app.domain import calendar, funding, hooks, workflow  # noqa: F401  (hooks registers handlers and decisions)

log = logging.getLogger("squad.worker")
TICK_SECONDS = 30
IDLE_SECONDS = 2


def run_once(db: Session) -> dict[str, int]:
    """One pass: refresh the calendar, mark slipped funding, wake waiting cycles, then run every queued job."""
    today = clock.today(db)
    overdue = calendar.refresh_statuses(db, today)
    slipped = len(funding.check_funding_events(db, today))
    moved = workflow.tick(db)
    ran = workflow.drain(db)
    db.commit()
    return {"obligations_now_overdue": overdue, "funding_slipped": slipped, "cycles_woken": moved, "jobs_run": ran}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    engine = get_engine()
    last_tick = 0.0
    while True:
        with Session(engine) as db:
            if args.once or time.monotonic() - last_tick >= TICK_SECONDS:
                result = run_once(db)
                last_tick = time.monotonic()
                if any(result.values()):
                    log.info("pass: %s", result)
            else:
                ran = workflow.drain(db, limit=50)
                db.commit()
                if ran:
                    log.info("jobs run: %d", ran)
        if args.once:
            return
        time.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    main()

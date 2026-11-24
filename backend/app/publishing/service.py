"""Generate, freeze, release and schedule review packages.

Generating a package assembles the content, renders the files, freezes a snapshot (every fact used
with its value and provenance, the commentary versions and the file hashes) and writes ledger
events. Release is a separate step for a person with the right role; a package that carries draft
commentary, or that does not pass verification, is refused with the reason.
"""
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc.periods import month_end
from app.core import clock, ledger
from app.core.config import get_settings
from app.core.roles import Permission, can
from app.domain.credit import Borrower
from app.domain.org import User
from app.domain.reviews import Package, PackageSchedule, Snapshot
from app.publishing.content import ContentError, build_content, has_draft_commentary

FORMATS = ("docx", "xlsx", "pptx")
MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
CADENCES = ("monthly", "quarterly")
ACTOR = ("system", "publishing")
# what the snapshot hash does not cover: things that differ between two runs over identical content
UNHASHED = ("files", "package_id", "generated_at", "snapshot_sha256")


class ReleaseRefused(ValueError):
    """The package cannot be released as it stands; the message says why and what to do."""


def canonical(content: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in content.items() if k not in UNHASHED}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True)


def content_hash(content: dict[str, Any]) -> str:
    """sha256 over the canonical content: the facts, the commentary versions and the structure
    built from them. File hashes sit beside it in the snapshot (Office files carry timestamps,
    so two renderings of identical content are not byte-identical)."""
    return hashlib.sha256(canonical(content).encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def package_dir(package_id: uuid.UUID) -> Path:
    return Path(get_settings().file_store_dir) / "packages" / str(package_id)


def render_files(content: dict[str, Any], formats: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    """Render each requested format. Returns [{format, name, data, fact_ids, borrower_id}]."""
    from app.publishing import deck, excel, word

    stem = _slug(content["borrowers"][0]["borrower"]["code"] if content["scope"] == "borrower" else content["scope"])
    stem = f"{stem}-{content['period_end']}"
    out: list[dict[str, Any]] = []
    for fmt in formats:
        if fmt == "docx":
            data, used = word.render_memo(content)
            out.append({"format": "docx", "name": f"{stem}-review-memo.docx", "data": data, "fact_ids": used,
                        "borrower_id": None})
        elif fmt == "pptx":
            data, used = deck.render_deck(content)
            out.append({"format": "pptx", "name": f"{stem}-review-deck.pptx", "data": data, "fact_ids": used,
                        "borrower_id": None})
        elif fmt == "xlsx":
            for b in content["borrowers"]:
                data, used = excel.render_workbook(content, b)
                out.append({"format": "xlsx", "name": f"{_slug(b['borrower']['code'])}-{content['period_end']}-spread.xlsx",
                            "data": data, "fact_ids": used, "borrower_id": b["borrower"]["id"]})
        else:
            raise ContentError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")
    return out


def generate_package(db: Session, *, scope: str, period_end: date, borrower_id: uuid.UUID | None = None,
                     meeting_id: uuid.UUID | None = None, formats: tuple[str, ...] | list[str] = FORMATS,
                     actor: tuple[str, str] = ACTOR, trigger: str = "on_demand", title: str | None = None) -> Package:
    unknown = [f for f in formats if f not in FORMATS]
    if unknown or not formats:
        raise ContentError(f"choose at least one format from {', '.join(FORMATS)}"
                           + (f"; {', '.join(unknown)} is not one" if unknown else ""))
    formats = [f for f in FORMATS if f in set(formats)]
    content = build_content(db, scope=scope, period_end=period_end, borrower_id=borrower_id, meeting_id=meeting_id)
    digest = content_hash(content)
    content["snapshot_sha256"] = digest  # printed in the files, so a reader can match file to snapshot
    rendered = render_files(content, formats)
    package = Package(title=title or content["title"], scope=scope, borrower_id=borrower_id, meeting_id=meeting_id,
                      period_end=date.fromisoformat(content["period_end"]), trigger=trigger, status="draft",
                      prepared_by_id=actor[1])
    db.add(package)
    db.flush()
    directory = package_dir(package.id)
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for item in rendered:
        path = directory / item["name"]
        path.write_bytes(item["data"])
        files.append({"format": item["format"], "name": item["name"], "path": str(path),
                      "sha256": hashlib.sha256(item["data"]).hexdigest(), "size": len(item["data"]),
                      "borrower_id": item["borrower_id"], "fact_ids": sorted(item["fact_ids"])})
    snapshot = Snapshot(
        as_of=datetime.now(UTC), scope=scope, borrower_id=borrower_id, sha256=digest,
        content={**content, "package_id": str(package.id), "generated_at": datetime.now(UTC).isoformat(),
                 "files": [{k: f[k] for k in ("format", "name", "sha256", "size", "borrower_id")} for f in files]})
    db.add(snapshot)
    db.flush()
    package.files, package.snapshot_id, package.status = files, snapshot.id, "generated"
    drafts = has_draft_commentary(content)
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="snapshot.frozen", entity_type="snapshot",
                  entity_id=snapshot.id, payload={"sha256": digest, "facts": len(content["facts"]),
                                                  "derived": len(content["derived"]), "package_id": package.id})
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="package.generated", entity_type="package",
                  entity_id=package.id,
                  payload={"scope": scope, "period_end": package.period_end, "trigger": trigger,
                           "snapshot_id": snapshot.id, "snapshot_sha256": digest, "draft_commentary": drafts,
                           "warnings": content["warnings"],
                           "files": [{"format": f["format"], "name": f["name"], "sha256": f["sha256"]} for f in files]})
    db.flush()
    return package


def snapshot_of(db: Session, package: Package) -> Snapshot | None:
    return db.get(Snapshot, package.snapshot_id) if package.snapshot_id else None


def release_package(db: Session, package: Package, user: User) -> Package:
    if not can(user.role, Permission.RELEASE_PACKAGE):
        raise PermissionError(f"Your role cannot do this ({Permission.RELEASE_PACKAGE.value}).")
    snapshot = snapshot_of(db, package)
    if package.status == "released":
        raise ReleaseRefused("This package has already been released.")
    if package.status != "generated" or snapshot is None:
        raise ReleaseRefused("This package has no generated files yet. Generate it before releasing.")
    drafts = has_draft_commentary(snapshot.content)
    if drafts:
        raise ReleaseRefused(
            "This package contains commentary that is still a draft (" + "; ".join(drafts) + "). "
            "Approve the commentary, generate the package again, then release it.")
    from app.publishing.verify import verify_package

    report = verify_package(db, package)
    if not report.ok:
        raise ReleaseRefused(
            f"This package did not pass verification: {len(report.problems)} figure(s) or file(s) do not resolve "
            f"to the snapshot (first: {report.problems[0].describe()}). Generate the package again.")
    package.status, package.released_by, package.released_at = "released", user.id, datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=user.id, action="package.released", entity_type="package",
                  entity_id=package.id,
                  payload={"snapshot_id": snapshot.id, "snapshot_sha256": snapshot.sha256,
                           "figures_verified": report.figures_checked,
                           "files": [{"name": f["name"], "sha256": f["sha256"]} for f in package.files]})
    db.flush()
    return package


# schedules ---------------------------------------------------------------------------------------
def period_ends(cadence: str, around: date) -> list[date]:
    """Period ends for a cadence from the year before `around` to the year after."""
    step = 1 if cadence == "monthly" else 3
    return [month_end(y, m) for y in range(around.year - 1, around.year + 2) for m in range(step, 13, step)]


def due_date(period_end: date, days_after: int) -> date:
    return period_end + timedelta(days=days_after)


def first_run(cadence: str, days_after: int, today: date) -> date:
    """The first date on or after today when a period's package falls due."""
    return next(due_date(p, days_after) for p in period_ends(cadence, today) if due_date(p, days_after) >= today)


def create_schedule(db: Session, *, title: str, scope: str, cadence: str, days_after_period_end: int,
                    formats: list[str], borrower_id: uuid.UUID | None = None, next_run: date | None = None,
                    actor: tuple[str, str] = ACTOR) -> PackageSchedule:
    if cadence not in CADENCES:
        raise ValueError(f"cadence must be one of {', '.join(CADENCES)}")
    if scope not in ("borrower", "portfolio"):
        raise ValueError("a schedule is for one borrower or for the portfolio")
    if scope == "borrower" and (borrower_id is None or db.get(Borrower, borrower_id) is None):
        raise ValueError("a borrower schedule needs a borrower that exists")
    if not formats or any(f not in FORMATS for f in formats):
        raise ValueError(f"formats must be chosen from {', '.join(FORMATS)}")
    if days_after_period_end < 0:
        raise ValueError("days after period end cannot be negative")
    row = PackageSchedule(title=title, scope=scope, borrower_id=borrower_id if scope == "borrower" else None,
                          cadence=cadence, days_after_period_end=days_after_period_end, formats=list(formats),
                          next_run=next_run or first_run(cadence, days_after_period_end, clock.today(db)))
    db.add(row)
    db.flush()
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="package_schedule.created",
                  entity_type="package_schedule", entity_id=row.id,
                  payload={"scope": scope, "cadence": cadence, "days_after_period_end": days_after_period_end,
                           "formats": list(formats), "next_run": row.next_run})
    return row


@dataclass
class ScheduleRun:
    schedule: PackageSchedule
    period_end: date
    package: Package | None = None
    error: str | None = None


def run_due_schedules(db: Session, today: date | None = None) -> list[ScheduleRun]:
    """Generate every scheduled package that has fallen due, once, and move each schedule on.

    A schedule's `next_run` is a period end plus its days of grace. When that date arrives the
    package for that period is generated and `next_run` moves to the following period's due date,
    so running again on the same day generates nothing. A package that cannot be assembled (no
    cycle for the period yet) leaves the schedule where it is, to be tried again, and says why.
    """
    today = today or clock.today(db)
    runs: list[ScheduleRun] = []
    schedules = db.execute(select(PackageSchedule).where(
        PackageSchedule.active.is_(True), PackageSchedule.next_run.is_not(None), PackageSchedule.next_run <= today)
        .order_by(PackageSchedule.next_run, PackageSchedule.created_at)).scalars().all()
    for s in schedules:
        ends = period_ends(s.cadence, s.next_run)
        due = [p for p in ends if due_date(p, s.days_after_period_end) <= s.next_run]
        if not due:
            continue
        period_end = due[-1]
        run = ScheduleRun(s, period_end)
        try:
            with db.begin_nested():
                run.package = generate_package(db, scope=s.scope, period_end=period_end, borrower_id=s.borrower_id,
                                               formats=list(s.formats), actor=("system", "schedule"),
                                               trigger="scheduled", title=None)
        except ContentError as exc:
            run.error = str(exc)
            ledger.record(db, actor_type="system", actor_id="schedule", action="package_schedule.not_generated",
                          entity_type="package_schedule", entity_id=s.id,
                          payload={"period_end": period_end, "due": s.next_run, "reason": run.error})
            runs.append(run)
            continue
        following = next(p for p in ends if p > period_end)
        previous, s.next_run = s.next_run, due_date(following, s.days_after_period_end)
        ledger.record(db, actor_type="system", actor_id="schedule", action="package_schedule.ran",
                      entity_type="package_schedule", entity_id=s.id,
                      payload={"period_end": period_end, "due": previous, "package_id": run.package.id,
                               "next_run": s.next_run})
        runs.append(run)
    db.flush()
    return runs

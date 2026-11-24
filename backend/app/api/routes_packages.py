"""Review packages: generate, list, download, verify, release, and schedules."""
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.disposition import content_disposition
from app.api.serialize import row
from app.core import clock
from app.core.db import get_db
from app.core.roles import Permission, can
from app.domain.credit import Borrower
from app.domain.org import User
from app.domain.reviews import Package, PackageSchedule
from app.publishing import service
from app.publishing.content import ContentError, has_draft_commentary
from app.publishing.verify import verify_package

router = APIRouter(tags=["packages"])


def may_prepare(user: User = Depends(current_user)) -> User:
    """A package is prepared by someone who writes reviews or who releases them."""
    if not (can(user.role, Permission.EDIT_COMMENTARY) or can(user.role, Permission.RELEASE_PACKAGE)):
        raise HTTPException(403, f"Your role cannot do this ({Permission.EDIT_COMMENTARY.value}).")
    return user


def _package_or_404(db: Session, package_id: uuid.UUID) -> Package:
    package = db.get(Package, package_id)
    if package is None:
        raise HTTPException(404, "Package not found.")
    return package


def package_out(db: Session, package: Package, *, detail: bool = False) -> dict:
    out = row(package, exclude=("files",))
    out["files"] = [{"format": f["format"], "name": f["name"], "sha256": f["sha256"], "size": f["size"],
                     "borrower_id": f.get("borrower_id"), "facts_used": len(f.get("fact_ids", []))}
                    for f in package.files]
    borrower = db.get(Borrower, package.borrower_id) if package.borrower_id else None
    out["borrower_name"] = borrower.name if borrower else None
    snapshot = service.snapshot_of(db, package)
    if snapshot is not None:
        drafts = has_draft_commentary(snapshot.content)
        out["snapshot"] = {"id": str(snapshot.id), "sha256": snapshot.sha256, "as_of": snapshot.as_of.isoformat(),
                           "facts": len(snapshot.content.get("facts", {})),
                           "derived": len(snapshot.content.get("derived", {}))}
        out["draft_commentary"] = drafts
        out["can_release"] = package.status == "generated" and not drafts
        if detail:
            out["warnings"] = snapshot.content.get("warnings", [])
            out["commentary"] = [{"borrower": b["borrower"]["name"], "id": c["id"], "section": c["section"],
                                  "version": c["version"], "status": c["status"]}
                                 for b in snapshot.content["borrowers"] for c in b["commentary"]]
    return out


class PackageIn(BaseModel):
    scope: str = "borrower"  # borrower | portfolio | meeting
    period_end: date
    borrower_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    formats: list[str] = Field(default_factory=lambda: list(service.FORMATS))
    title: str | None = None


@router.post("/packages", status_code=201)
def create_package(body: PackageIn, db: Session = Depends(get_db), user: User = Depends(may_prepare)) -> dict:
    try:
        package = service.generate_package(
            db, scope=body.scope, period_end=body.period_end, borrower_id=body.borrower_id,
            meeting_id=body.meeting_id, formats=body.formats, actor=("user", str(user.id)), title=body.title)
    except ContentError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return package_out(db, package, detail=True)


@router.get("/packages")
def list_packages(borrower_id: uuid.UUID | None = None, scope: str | None = None, status: str | None = None,
                  db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    query = select(Package).order_by(Package.created_at.desc(), Package.id)
    if borrower_id:
        query = query.where(Package.borrower_id == borrower_id)
    if scope:
        query = query.where(Package.scope == scope)
    if status:
        query = query.where(Package.status == status)
    return [package_out(db, p) for p in db.execute(query).scalars()]


@router.get("/packages/{package_id}")
def get_package(package_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    return package_out(db, _package_or_404(db, package_id), detail=True)


@router.get("/packages/{package_id}/files/{name}")
def download_file(package_id: uuid.UUID, name: str, db: Session = Depends(get_db),
                  _: User = Depends(current_user)) -> Response:
    package = _package_or_404(db, package_id)
    entry = next((f for f in package.files if f["name"] == name), None)  # only names the package lists
    if entry is None or not Path(entry["path"]).exists():
        raise HTTPException(404, "File not found.")
    return Response(Path(entry["path"]).read_bytes(), media_type=service.MEDIA_TYPES[entry["format"]],
                    headers={"Content-Disposition": content_disposition("attachment", entry["name"]),
                             "X-Content-SHA256": entry["sha256"]})


@router.post("/packages/{package_id}/verify")
def verify(package_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """Reopen every file and check each figure against the snapshot."""
    return verify_package(db, _package_or_404(db, package_id)).to_dict()


@router.post("/packages/{package_id}/release")
def release(package_id: uuid.UUID, db: Session = Depends(get_db),
            user: User = Depends(require(Permission.RELEASE_PACKAGE))) -> dict:
    package = _package_or_404(db, package_id)
    try:
        service.release_package(db, package, user)
    except service.ReleaseRefused as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return package_out(db, package, detail=True)


class ScheduleIn(BaseModel):
    title: str
    scope: str = "portfolio"  # borrower | portfolio
    borrower_id: uuid.UUID | None = None
    cadence: str = "quarterly"  # monthly | quarterly
    days_after_period_end: int = Field(default=60, ge=0, le=366)
    formats: list[str] = Field(default_factory=lambda: list(service.FORMATS))
    next_run: date | None = None


@router.get("/package-schedules")
def list_schedules(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    return [row(s) for s in db.execute(select(PackageSchedule).order_by(PackageSchedule.next_run.nulls_last(),
                                                                         PackageSchedule.title)).scalars()]


@router.post("/package-schedules", status_code=201)
def create_schedule(body: ScheduleIn, db: Session = Depends(get_db),
                    user: User = Depends(require(Permission.RELEASE_PACKAGE))) -> dict:
    try:
        schedule = service.create_schedule(
            db, title=body.title, scope=body.scope, borrower_id=body.borrower_id, cadence=body.cadence,
            days_after_period_end=body.days_after_period_end, formats=body.formats, next_run=body.next_run,
            actor=("user", str(user.id)))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return row(schedule)


@router.post("/package-schedules/run")
def run_schedules(db: Session = Depends(get_db), _: User = Depends(require(Permission.RELEASE_PACKAGE))) -> dict:
    """Generate every scheduled package that has fallen due on the workspace's date."""
    today = clock.today(db)
    runs = service.run_due_schedules(db, today)
    db.commit()
    return {"today": today.isoformat(),
            "runs": [{"schedule_id": str(r.schedule.id), "period_end": r.period_end.isoformat(),
                      "package_id": str(r.package.id) if r.package else None, "error": r.error,
                      "next_run": r.schedule.next_run.isoformat() if r.schedule.next_run else None} for r in runs]}

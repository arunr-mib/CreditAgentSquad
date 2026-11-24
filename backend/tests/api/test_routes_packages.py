"""The packages API over one seeded borrower: generate, list, download, verify, release, schedules."""
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from app.core import clock
from app.core.config import get_settings
from app.core.ledger import LedgerEvent
from app.domain import review_service
from app.domain.credit import Borrower
from app.domain.monitoring import Cycle
from app.domain.org import User
from app.domain.reviews import ReviewSheet
from app.seed_book import seed_book
from app.seed_users import seed_users
from sqlalchemy import select

REPO = Path(__file__).resolve().parents[3]
PERIOD = "2026-09-30"
API = "/api/v1"


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    return out


@pytest.fixture()
def world(db, client, book, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw")
    seed_book(db, root=book, current="seeded", only=["sablewood-dental"])
    borrower = db.execute(select(Borrower).where(Borrower.code == "sablewood-dental")).scalar_one()
    yield borrower
    get_settings.cache_clear()
    os.environ.pop("FILE_STORE_DIR", None)


def sign_in(client, who):
    r = client.post(f"{API}/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def body(borrower, **extra):
    return {"scope": "borrower", "borrower_id": str(borrower.id), "period_end": PERIOD, **extra}


def test_generate_list_download_verify_and_release(client, db, world):
    borrower = world
    for method, path in (("get", "/packages"), ("post", "/packages"), ("get", "/package-schedules")):
        assert getattr(client, method)(API + path).status_code == 401
    sign_in(client, "ruth.calloway")  # credit review reads, and prepares nothing
    assert client.post(f"{API}/packages", json=body(borrower)).status_code == 403
    sign_in(client, "priya.raman")
    assert client.post(f"{API}/packages", json=body(borrower, formats=["pdf"])).status_code == 422
    missing = client.post(f"{API}/packages", json=body(borrower, period_end="2027-03-31"))
    assert missing.status_code == 422 and "no monitoring cycle" in missing.json()["detail"]
    made = client.post(f"{API}/packages", json=body(borrower))
    assert made.status_code == 201, made.text
    package = made.json()
    assert package["status"] == "generated" and package["borrower_name"] == borrower.name
    assert [f["format"] for f in package["files"]] == ["docx", "xlsx", "pptx"]
    assert all("path" not in f and len(f["sha256"]) == 64 for f in package["files"])
    assert len(package["snapshot"]["sha256"]) == 64 and package["draft_commentary"] == [] and package["can_release"]
    pid = package["id"]

    listed = client.get(f"{API}/packages", params={"borrower_id": str(borrower.id)}).json()
    assert [p["id"] for p in listed] == [pid]
    assert client.get(f"{API}/packages", params={"status": "released"}).json() == []
    assert client.get(f"{API}/packages/{pid}").json()["snapshot"] == package["snapshot"]
    assert client.get(f"{API}/packages/00000000-0000-4000-8000-000000000000").status_code == 404

    for f in package["files"]:
        got = client.get(f"{API}/packages/{pid}/files/{f['name']}")
        assert got.status_code == 200 and got.content[:2] == b"PK" and len(got.content) == f["size"]
        assert got.headers["x-content-sha256"] == f["sha256"] and "attachment" in got.headers["content-disposition"]
    assert "wordprocessingml" in client.get(f"{API}/packages/{pid}/files/{package['files'][0]['name']}").headers["content-type"]
    assert client.get(f"{API}/packages/{pid}/files/other.docx").status_code == 404

    report = client.post(f"{API}/packages/{pid}/verify").json()
    assert report["ok"] is True and report["problems"] == [] and report["figures_checked"] > 900
    assert report["snapshot_sha256"] == package["snapshot"]["sha256"]

    assert client.post(f"{API}/packages/{pid}/release").status_code == 403  # an analyst cannot release
    sign_in(client, "helen.strand")
    released = client.post(f"{API}/packages/{pid}/release")
    assert released.status_code == 200 and released.json()["status"] == "released"
    officer = db.execute(select(User).where(User.email == "helen.strand@bankofstoic.example")).scalar_one()
    assert released.json()["released_by"] == str(officer.id)
    again = client.post(f"{API}/packages/{pid}/release")
    assert again.status_code == 409 and "already been released" in again.json()["detail"]
    actions = [e.action for e in db.execute(select(LedgerEvent).where(LedgerEvent.entity_id == pid)
                                            .order_by(LedgerEvent.seq)).scalars()]
    assert actions == ["package.generated", "package.released"]
    assert client.get(f"{API}/ledger/verify").json()["ok"] is True


def test_draft_commentary_blocks_release_with_a_clear_message(client, db, world):
    borrower = world
    cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.status == "open")).scalar_one()
    sheet = ReviewSheet(borrower_id=borrower.id, cycle_id=cycle.id)
    db.add(sheet)
    db.flush()
    analyst = db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()
    review_service.write_section(db, sheet, section="summary", user=analyst,
                                 body="The borrower remains in compliance with every covenant this quarter.")
    sign_in(client, "dana.whitfield")
    package = client.post(f"{API}/packages", json=body(borrower, formats=["docx"])).json()
    assert package["draft_commentary"] == [f"{borrower.name}: summary"] and package["can_release"] is False
    assert package["commentary"][0]["status"] == "draft"
    refused = client.post(f"{API}/packages/{package['id']}/release")
    assert refused.status_code == 409
    assert "still a draft" in refused.json()["detail"] and "Approve the commentary" in refused.json()["detail"]
    assert client.get(f"{API}/packages/{package['id']}").json()["status"] == "generated"


def test_schedules_are_created_listed_and_run_once(client, db, world):
    borrower = world
    sign_in(client, "priya.raman")
    wanted = {"title": "Sablewood quarterly review", "scope": "borrower", "borrower_id": str(borrower.id),
              "cadence": "quarterly", "days_after_period_end": 45, "formats": ["docx"], "next_run": "2026-11-14"}
    assert client.post(f"{API}/package-schedules", json=wanted).status_code == 403
    sign_in(client, "helen.strand")
    assert client.post(f"{API}/package-schedules", json={**wanted, "cadence": "weekly"}).status_code == 422
    made = client.post(f"{API}/package-schedules", json=wanted)
    assert made.status_code == 201 and made.json()["next_run"] == "2026-11-14"
    assert [s["title"] for s in client.get(f"{API}/package-schedules").json()] == ["Sablewood quarterly review"]
    clock.set_today(db, date(2026, 11, 13))
    assert client.post(f"{API}/package-schedules/run").json()["runs"] == []
    clock.set_today(db, date(2026, 11, 14))
    (run,) = client.post(f"{API}/package-schedules/run").json()["runs"]
    assert run["period_end"] == PERIOD and run["error"] is None and run["next_run"] == "2027-02-14"
    assert client.post(f"{API}/package-schedules/run").json()["runs"] == []
    scheduled = client.get(f"{API}/packages").json()
    assert [(p["id"], p["trigger"]) for p in scheduled] == [(run["package_id"], "scheduled")]

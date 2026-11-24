#!/usr/bin/env bash
# One command to run the Credit Agent Squad demo on your own machine.
#
#   ./scripts/demo.sh            set everything up (first run takes a few minutes) and start it
#   ./scripts/demo.sh --reset    empty the demo database first, then do the same
#
# Needs: uv (https://docs.astral.sh/uv), Node 20+ with pnpm, and PostgreSQL 16 running locally
# (or Docker, in which case this script starts a PostgreSQL container for you).
# Everything is synthetic data; no model is called and nothing is billable.
#
# Ports can be moved:  API_PORT=8010 WEB_PORT=5183 ./scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
RESET=0
[ "${1:-}" = "--reset" ] && RESET=1

say() { printf '\n== %s\n' "$*"; }
fail() { printf '\nStopped: %s\n' "$*" >&2; exit 1; }

command -v uv >/dev/null || fail "uv is not installed. See https://docs.astral.sh/uv/getting-started/installation/"
command -v node >/dev/null || fail "Node.js is not installed (version 20 or later)."
if ! command -v pnpm >/dev/null; then
  command -v corepack >/dev/null || fail "pnpm is not installed. Run: npm install -g pnpm"
  corepack enable pnpm
fi

if [ ! -f .env ]; then
  say "Creating .env from .env.example"
  cp .env.example .env
  secret="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  # portable in-place edit (GNU and BSD sed differ)
  uv run python - "$secret" <<'PY'
import pathlib, sys
path = pathlib.Path(".env")
path.write_text(path.read_text().replace("SESSION_SECRET=change-me", f"SESSION_SECRET={sys.argv[1]}"))
PY
fi

say "Installing Python packages"
uv sync --quiet

# DATABASE_URL from the environment wins over .env, as it does in the application
DB_URL="${DATABASE_URL:-$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)}"
[ -n "$DB_URL" ] || fail "DATABASE_URL is not set in .env"
export DATABASE_URL="$DB_URL"
export SQUAD_ENV="${SQUAD_ENV:-local}"

can_connect() {
  uv run python - <<'PY' >/dev/null 2>&1
import os, psycopg
psycopg.connect(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3).close()
PY
}

# user, password and database name out of the URL, for creating them when they do not exist
read -r DB_USER DB_PASS DB_NAME DB_HOST DB_PORT < <(uv run python - <<'PY'
import os
from urllib.parse import urlparse
u = urlparse(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://"))
print(u.username, u.password or "", u.path.lstrip("/"), u.hostname or "localhost", u.port or 5432)
PY
)

create_role_and_database() {
  # $@ is a psql invocation that connects as a superuser
  "$@" -v ON_ERROR_STOP=1 -d postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}') THEN CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}'; END IF; END \$\$;" >/dev/null &&
  { "$@" -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 ||
    "$@" -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}" >/dev/null; }
}

if ! can_connect; then
  say "The demo database is not reachable; trying to create it"
  if command -v psql >/dev/null && create_role_and_database psql -h "$DB_HOST" -p "$DB_PORT" 2>/dev/null; then
    echo "Created with your own PostgreSQL login."
  elif command -v sudo >/dev/null && id postgres >/dev/null 2>&1 && create_role_and_database sudo -u postgres psql 2>/dev/null; then
    echo "Created as the postgres system user."
  elif command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    echo "Starting PostgreSQL 16 in Docker (container: credit-agent-squad-db)."
    docker start credit-agent-squad-db >/dev/null 2>&1 || docker run -d --name credit-agent-squad-db \
      -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASS" -e POSTGRES_DB="$DB_NAME" \
      -p "${DB_PORT}:5432" postgres:16 >/dev/null
    for _ in $(seq 1 30); do can_connect && break; sleep 1; done
  fi
  can_connect || fail "cannot reach or create the database at ${DB_HOST}:${DB_PORT}/${DB_NAME}.
Start PostgreSQL 16 and run, as a PostgreSQL superuser:
  CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
then run this script again."
fi

if [ "$RESET" = 1 ]; then
  say "Emptying the demo database"
  uv run python - <<'PY'
import os, psycopg
with psycopg.connect(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://"), autocommit=True) as conn:
    conn.execute("DROP SCHEMA public CASCADE")
    conn.execute("CREATE SCHEMA public")
PY
fi

if [ ! -f synthetic/out/manifest.json ]; then
  say "Generating the synthetic book (21 borrowers, 360 documents)"
  uv run python -m synthetic.generate
fi

say "Creating or updating the database tables"
(cd backend && uv run alembic upgrade head 2>&1 | grep -v "UserWarning\|warnings.warn\|squad_runtime\|UV_NATIVE_TLS" || true)

loaded="$(uv run python - <<'PY'
import os, psycopg
with psycopg.connect(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")) as conn:
    print(conn.execute("SELECT count(*) FROM borrowers").fetchone()[0])
PY
)"
if [ "$loaded" = "0" ]; then
  say "Loading the demo users and the synthetic book (about two minutes)"
  PYTHONPATH=backend uv run python -m app.seed_book
else
  echo "The book is already loaded (${loaded} borrowers)."
fi

say "Installing the workspace's packages"
(cd frontend && pnpm install --silent)

say "Starting the API on port ${API_PORT} and the workspace on port ${WEB_PORT}"
mkdir -p var/log
PYTHONPATH=backend uv run uvicorn app.main:app --port "$API_PORT" > var/log/api.log 2>&1 &
API_PID=$!
(cd frontend && PORT="$WEB_PORT" API_TARGET="http://localhost:${API_PORT}" pnpm dev > ../var/log/web.log 2>&1) &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT INT TERM

up() { uv run python -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)" "$1" >/dev/null 2>&1; }
for _ in $(seq 1 60); do up "http://localhost:${API_PORT}/api/v1/health" && up "http://localhost:${WEB_PORT}/" && break; sleep 1; done
up "http://localhost:${API_PORT}/api/v1/health" || fail "the API did not start; see var/log/api.log"
up "http://localhost:${WEB_PORT}/" || fail "the workspace did not start; see var/log/web.log"

cat <<EOF

Credit Agent Squad is running.

  Open      http://localhost:${WEB_PORT}
  Sign in   priya.raman@bankofstoic.example      (credit analyst)
            dana.whitfield@bankofstoic.example   (portfolio manager)
            helen.strand@bankofstoic.example     (credit officer: approves what others prepare)
  Password  squad-demo   (the same for every demo account)

Synthetic data only. Logs are in var/log/. Press Ctrl+C to stop.
EOF
wait

#!/bin/sh
# Start command for a hosted demo (one container: migrations, optional demo data, worker, API).
# Used by railway.json. Set in the host's variables:
#   DATABASE_URL     postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
#   SESSION_SECRET   a long random string
#   SEED_DEMO=1      load the synthetic book and demo users into an empty database
#   FILE_STORE_DIR   where document files are kept (default /data/files)
# PORT is set by the host.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/backend"
export FILE_STORE_DIR="${FILE_STORE_DIR:-/data/files}"
mkdir -p "$FILE_STORE_DIR"

alembic upgrade head

if [ "${SEED_DEMO:-0}" = "1" ]; then
  cd "$ROOT"
  loaded="$(python -c "
from sqlalchemy import text
from app.core.db import get_engine
with get_engine().connect() as c:
    print(c.execute(text('select count(*) from borrowers')).scalar())")"
  [ -f synthetic/out/manifest.json ] || python -m synthetic.generate
  if [ "$loaded" = "0" ]; then
    echo "Loading the synthetic book and demo users"
    python -m app.seed_book
  else
    # the database outlives the container's disk: put the document files back
    python -m app.cli restore-files --book synthetic/out || true
  fi
  cd "$ROOT/backend"
fi

python -m app.worker &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

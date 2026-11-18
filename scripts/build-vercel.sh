#!/usr/bin/env bash
# Assemble the folder that is deployed to Vercel: the built workspace as static files, the API
# as one Python function, and the synthetic book it serves documents from.
#
#   ./scripts/build-vercel.sh            writes .vercel-build/
#   cd .vercel-build && vercel deploy    (or: vercel deploy --prod)
#
# It is a separate folder on purpose: the repository's own pyproject.toml pulls in a PDF library
# build too large for a serverless function, so the function gets deploy/vercel/requirements.txt.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=.vercel-build

[ -f synthetic/out/manifest.json ] || uv run python -m synthetic.generate
(cd frontend && pnpm install --silent && pnpm build)

rm -rf "$OUT"
mkdir -p "$OUT/synthetic" "$OUT/public"
cp -r deploy/vercel/api deploy/vercel/vercel.json deploy/vercel/requirements.txt "$OUT/"
cp -r backend "$OUT/backend"
find "$OUT/backend" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -rf "$OUT/backend/tests"
cp -r synthetic/out "$OUT/synthetic/out"
cp -r frontend/dist/. "$OUT/public/"
[ -d .vercel ] && cp -r .vercel "$OUT/.vercel" || true
echo "Built $OUT: $(du -sh "$OUT" | cut -f1) ($(find "$OUT" -type f | wc -l) files)"

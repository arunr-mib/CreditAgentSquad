#!/usr/bin/env bash
# Assemble the folder that is deployed to Vercel: the built workspace as static files, the API
# as one Python function, and the synthetic book it serves documents from.
#
#   ./scripts/build-vercel.sh               v1 (frozen): writes .vercel-build/ from the legacy book
#   cd .vercel-build && vercel deploy       (or: vercel deploy --prod)
#
#   ./scripts/build-vercel.sh --target v2   v2: writes .vercel-build-v2/ from the innovation book,
#                                           with api/target.json (schema squad2, role squad2_runtime)
#                                           and never a copy of the repository's .vercel/ (linked to v1).
#                                           Deploy it only with scripts/hosted/deploy-v2.sh.
#
# It is a separate folder on purpose: the repository's own pyproject.toml pulls in a PDF library
# build too large for a serverless function, so the function gets deploy/vercel/requirements.txt.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET=v1
if [ "${1:-}" = "--target" ]; then TARGET="${2:-}"; elif [ -n "${1:-}" ]; then TARGET=bad; fi
case "$TARGET" in
  v1) OUT=.vercel-build;    BOOK=synthetic/out;                  GEN="uv run python -m synthetic.generate" ;;
  v2) OUT=.vercel-build-v2; BOOK=synthetic/books/innovation/out; GEN="uv run python -m synthetic.books.innovation.generate" ;;
  *) echo "usage: $0 [--target v1|v2]" >&2; exit 2 ;;
esac

if [ "$TARGET" = v1 ]; then
  [ -f "$BOOK/manifest.json" ] || $GEN
else
  # the documents are git-ignored: a fresh checkout or worktree has the manifest but not the PDFs
  { [ -f "$BOOK/manifest.json" ] && [ -d "$BOOK/documents" ]; } || $GEN
fi
(cd frontend && pnpm install --silent && pnpm build)

rm -rf "$OUT"
mkdir -p "$OUT/synthetic" "$OUT/public"
cp -r deploy/vercel/api deploy/vercel/vercel.json deploy/vercel/requirements.txt "$OUT/"
find "$OUT/api" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -f "$OUT/api/target.json"
cp -r backend "$OUT/backend"
find "$OUT/backend" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -rf "$OUT/backend/tests"
cp -r "$BOOK" "$OUT/synthetic/out"   # both targets serve their book from the same path
cp -r frontend/dist/. "$OUT/public/"
if [ "$TARGET" = v1 ]; then
  [ -d .vercel ] && cp -r .vercel "$OUT/.vercel" || true
else
  printf '{"target": "v2", "schema": "squad2", "runtime_role": "squad2_runtime"}\n' > "$OUT/api/target.json"
fi
echo "Built $OUT ($TARGET): $(du -sh "$OUT" | cut -f1) ($(find "$OUT" -type f | wc -l) files)"

#!/usr/bin/env bash
# The only way v2 is deployed. Builds the v2 target, links the build folder to the v2 project by name,
# refuses unless check_link.py passes, then deploys with the project pinned. The Vercel token is the
# environment's network secret: the CLI gets a dummy value and the proxy replaces it.
#   V2_PROJECT=credit-squad ./scripts/hosted/deploy-v2.sh [--no-build]
set -euo pipefail
cd "$(dirname "$0")/../.."
PROJECT="${V2_PROJECT:-credit-squad}"
VC=(npx --yes vercel@66.0.0)
TOKEN=(--token proxy-injected)
export VERCEL_TELEMETRY_DISABLED=1
[ "${1:-}" = "--no-build" ] || ./scripts/build-vercel.sh --target v2
[ -f .vercel-build-v2/api/target.json ] || { echo "no v2 build in .vercel-build-v2" >&2; exit 1; }
cd .vercel-build-v2
[ ! -e .vercel ] || [ "${1:-}" = "--no-build" ] || { echo "a fresh build must not carry .vercel/" >&2; exit 1; }
# ids exported in the shell (v1's, say) would override the link; the deploy is pinned from the checked link below
unset VERCEL_ORG_ID VERCEL_PROJECT_ID
# no terminal on stdin: from a TTY the CLI would pull development variables into .env.local here
"${VC[@]}" link --yes --project "$PROJECT" "${TOKEN[@]}" </dev/null >/dev/null
rm -f .env.local
uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT"
ids=$(uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT" --export) || { echo "refused: the link could not be pinned" >&2; exit 1; }
case "$ids" in *"VERCEL_PROJECT_ID="*) eval "$ids" ;; *) echo "refused: no project id to pin" >&2; exit 1 ;; esac
"${VC[@]}" deploy --prod --yes "${TOKEN[@]}"

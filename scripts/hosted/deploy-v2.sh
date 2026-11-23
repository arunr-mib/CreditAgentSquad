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
"${VC[@]}" link --yes --project "$PROJECT" "${TOKEN[@]}" >/dev/null
uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT"
eval "$(uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT" --export)"
"${VC[@]}" deploy --prod --yes "${TOKEN[@]}"

Chain the test run and the commit with `&&`, never `;`, so a failing test stops the commit.

Confirmed 2026-11-17: a commit went out with two failing tests because the command ran the tests, printed the failures, and then committed anyway. The failures were stale tests, fixed in the next commit, but the branch was red for one commit.

Rule: `uv run pytest ... && git add ... && git commit ...`. When output is filtered through `grep`, check the exit status of pytest itself (for example with `set -o pipefail`), because a pipe hides it.

Applies to: every commit in this repository.

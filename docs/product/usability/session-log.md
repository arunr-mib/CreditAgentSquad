# Session log

`SYNTHETIC - FOR DEMONSTRATION`

> `SITE` = `https://credit-squad.vercel.app` (or `https://credit-squad-v2.vercel.app`): write the address actually used in the first row's notes.

One line per session, written right after it. Participant codes only, never names. The book is reloaded before every session; a session does not start unless the check printed `ready`.

- **Check before:** the output of `uv run python -I scripts/hosted/v2_setup.py check --base "$SITE"` run within the hour before the session (`ready`, or what it printed instead), and the time it was run.
- **Reset after:** whether the book was reloaded after the session (yes/no) and the ledger export file (`docs/product/usability/ledger/<date>-P<n>.json`).
- **Unusual:** a slow first load (cold start), a paused database, a sign-in that failed, an old client name on screen, an error message (exact words), recording consent given or refused.

| Session | Date | Participant | Role | Facilitator | Note-taker | Check before (result, time) | Reset after (yes/no, ledger export file) | Unusual |
|---|---|---|---|---|---|---|---|---|
| 1 | | P1 | analyst | | | | | |
| 2 | | P2 | analyst | | | | | |
| 3 | | P3 | analyst | | | | | |
| 4 | | P4 | analyst | | | | | |
| 5 | | P5 | credit officer | | | | | |

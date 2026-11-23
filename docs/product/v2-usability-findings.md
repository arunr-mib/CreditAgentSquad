# v2 usability findings

`SYNTHETIC - FOR DEMONSTRATION`

> `SITE` = `https://credit-squad.vercel.app` (or `https://credit-squad-v2.vercel.app`).

**State: sessions not yet held.** Filled in after the five sessions from the observation sheets (by the facilitator, or by the controller from the sheets with the facilitator checking). Kit: `docs/product/usability/` (consent note, facilitator script, observation sheet, session log).

| | |
|---|---|
| Session dates | |
| Sessions held | 0 of 5 (4 analysts, 1 credit officer) |
| Build commit on the hosted site | |
| Address | `SITE` |
| Agents | off (no model key), unless the owner turned them on (Task 17) |
| Book | innovation book, reloaded fresh before each session, renamed clients |

## Triage rules

- **Severity:** blocker (could not finish, or was misled about a figure or a decision); major (finished only with help, or a wrong belief corrected later); minor (slowed); cosmetic (wording or look, no effect on the task). The note-taker proposes; triage sets it.
- **Observed, not interpreted:** "What happened" says what the participant did and said. Causes and fixes go in "Proposed fix".
- **Every blocker and major is fixed before v2 is called done**, each in its own commit (`fix(p5): …`) with a test. Where a rule is involved (own clients only, the router cannot decide, what a return gathers), the test is an API test, not only a screen test (`docs/lessons/a-second-may-act-rule-drifts-from-the-engine.md`).
- **After each fix:** a v2-only redeploy with `scripts/hosted/deploy-v2.sh`; re-run `pnpm e2e:smoke` and the read-only journeys against the hosted v2; repeat the frozen-site after-check after the last redeploy. The two frozen sites are never touched.
- **Minors and cosmetics:** the owner decides (fix now, backlog, or not changing).
- **v2 is called done** only when no blocker or major is open **and** the owner has read this file.
- **Lessons:** each new lesson is also written to `docs/lessons/` (one file per lesson, summary on the first line).

## Findings

| ID | Session(s) | Task | What happened (observed, not interpreted) | Severity | Seen by (n of 5) | Proposed fix | Decision | Fix commit | Re-checked |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

## Blockers and majors (fixed before v2 is done)

- None yet.

## Minors (owner decides)

- None yet.

## Not changing (with reason)

- None yet.

## Lessons

- None yet.

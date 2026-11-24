# Archived recordings: clients renamed on 22 November 2026

**Not replayed.** These are the recorded model answers (claude-opus-5-5, recorded 21 November 2026) for the eight
innovation clients the owner renamed on 22 November (`docs/product/name-check-2026-11-22.md`). They are kept here,
under the codes they were recorded with, as the record of what the model answered. Nothing reads them in a replay.

Why they cannot replay: the renamed clients' documents print the new names, so every document hash, file name and
record key changed. The figures did not change (see `docs/owner-signoff-rename-2026-11-23.md`).

The eight were re-recorded under their new codes on 23 November 2026 with the owner's go-ahead (`evals/recordings/`),
so `--mode recorded` replays them again from those. Before that it skipped them by name.

| Recorded as | Now | Recordings |
|---|---|---|
| dataflake | datamarrow | 16 |
| quillon-ai | tarnavi-ai | 7 |
| lumora-health | calvere-health | 0 (no model call: its October package is late) |
| halcyon-grid | tavernel-grid | 8 |
| tessaract-labs | vantrell-labs | 8 |
| corvane-analytics | meridew-analytics | 14 |
| tidewell-medical | brackmere-medical | 8 |
| stripple-tech | cindrel-tech | 4 |

Layout is the same as `evals/recordings/` (`<agent>/<code>/<period>/...`). The wording of these answers is still used
as a corpus of honest model text by `backend/tests/guardrails/test_structure.py`.

"The latest record" must be decided by a database sequence, never by a creation timestamp.

- **What happened:** `current_fact` picked the newest fact by `created_at`, whose default was `now()`. In PostgreSQL `now()` is the transaction's start time, so every fact written in one transaction tied, and the tie was broken by a random id. A probe that wrote two facts for one line in one transaction got the earlier one back in 20 of 40 lookups.
- **Why it hid:** the seeded book and the evaluation rarely store two usable facts for one line in the same transaction, so every suite passed.
- **Rule:** facts carry `seq` (an identity column); every "latest" or "in order" query on facts orders by it. `created_at` now defaults to `clock_timestamp()` and is for display only.
- **How to apply:** before ordering any table by `created_at` to pick a winner, ask whether two rows can be written in one transaction. If yes, give the table a sequence.
- Found 2026-11-17 while building recalculation on correction; fixed in migration `0002`.

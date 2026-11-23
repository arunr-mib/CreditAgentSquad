A fresh git worktree has neither the generated synthetic PDFs nor `.env`, so tests and seeds there fail or quietly use the main databases.

Why: `synthetic/out/documents/` and `synthetic/books/innovation/out/documents/` are git-ignored (generated), and so is `.env`. On 20 November 2026 the Phase 4 worktree failed `test_covenants_carry_fact_ids_clause_and_work_item` because the agreement PDF was missing, which looked like a code regression. Separately, `config.py` reads `.env` relative to the current directory, so a command run from `backend/` fell back to the default database URL, which points at the main checkout's database.

How to apply: after `git worktree add`, copy or regenerate the synthetic documents (`uv run python -m synthetic.generate`, or copy `synthetic/out/documents` from the main checkout), write the worktree's own `.env` with its own `DATABASE_URL` and `TEST_DATABASE_URL`, and run every command from the worktree root.

Also: Alembic runs only from `backend/` (its `alembic.ini` lives there), where the worktree's `.env` is not read, so export `DATABASE_URL` (and pass `-x url=...`) before migrating from a worktree. On 20 November 2026 one migrate run reached the main database this way; it was already at head, so nothing changed.

Since 23 November 2026 `seed_book` (and `frontend/e2e/seed_repair.py`, before it writes users) raises `FileNotFoundError` when a file the truth lists is not under the book's root, naming the generate command. Before that the seed skipped missing files and exited 0; in a fresh cloud container the repair seed loaded borrowers with no documents and repair journeys 3, 4 and 5 failed, which looked like product faults. `seed_borrower` called directly (as `test_monthly_cycles.py` does) is not checked.

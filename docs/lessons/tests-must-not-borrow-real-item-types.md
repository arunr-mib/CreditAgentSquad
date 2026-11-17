A test that needs "some work item" must use a type reserved for tests, never a real one, because real types gain decision hooks later.

Confirmed 2026-11-17, three times in one day: tests in `test_workflow.py` and `test_routes.py` used `terms.approval_needed`, then `review.commentary_approval`, then `spread.does_not_foot` as a generic example. Each broke when that type gained a hook that (correctly) refuses an item with nothing real behind it.

Rule: generic workflow tests use item types starting with `test.` (for example `test.second_person`, `test.blocking_item`). A test that uses a real type must build the real thing behind it.

Applies to: every test that creates a WorkItem directly.

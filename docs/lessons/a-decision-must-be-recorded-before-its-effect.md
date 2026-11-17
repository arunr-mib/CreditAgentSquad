Record a person's decision on a work item before running what the decision causes, in one unit of work.

- **What happened (2026-11-17, found by the worker fixing workflow gaps):** `decide_work_item` ran the decision's hook first and marked the item decided afterwards. A hook that re-raised the same question (the statements still do not foot) was de-duplicated onto the item that was about to be closed, so the new question vanished and the stage was released with figures that did not foot.
- **Rule:** mark the item decided first, then run the hook, inside one savepoint so a refused hook undoes the decision. Anything the hook raises then finds no open item to merge into and stands on its own.
- **How to apply:** when a handler can raise an item of the same type and key as the one being handled, test that case explicitly (`backend/tests/domain/test_cycle_gaps.py`).

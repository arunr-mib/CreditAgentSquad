Number matching rules each need a positive and a negative test, because every fix to one trap has opened another.

Inherited from CreditScout. Known traps: the 1.00 in "1.25 to 1.00" must not pass as a figure unless 1.25 is a known ratio; a fix for that once produced a phantom 900000 from "2,400,000 to 1,900,000"; a figure in unbalanced parentheses must not vanish; "(1.25x)" is a positive ratio, "(1,200)" is negative; a scale suffix counts only when attached to the number ("12 months" is not 12m); dates, years, quarter labels, section numbers and version numbers are not figures.

Found here 2026-11-17 by the Terms and Covenant agents: a known ratio that ends a sentence or a phrase ("to exceed 2.00 to 1.00." or "2.00 to 1.00, measured ...") kept its trailing 1.00 as a figure, because the "N to 1" rule refused any full stop or comma after the 1.00. Agreement clauses usually end that way, so text restating the limit was withheld. Fixed in `_N_TO_ONE` (a full stop or comma is refused only when a digit follows it), with tests for both directions. The Covenant Agent's `clause_figures` (`backend/app/agents/covenant_tools.py`) also sets such punctuation apart before reading a clause; keep the two in step.

Confirmed here 2026-11-17 (found by the Terms Agent's tests): "shall not exceed 2.00 to 1.00." ends with a full stop and "2.00 to 1.00, tested quarterly" continues with a comma; both must drop the "to 1.00". Only a comma or full stop followed by a digit means the number continues ("to 1,900,000", "to 1.5").

Rule: every normalisation or stripping rule ships with a test for what it must refuse and a test for what it must still allow.

Applies to: `backend/app/guardrails/numbers.py`.

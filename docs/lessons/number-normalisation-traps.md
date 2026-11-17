Number matching rules each need a positive and a negative test, because every fix to one trap has opened another.

Inherited from CreditScout. Known traps: the 1.00 in "1.25 to 1.00" must not pass as a figure unless 1.25 is a known ratio; a fix for that once produced a phantom 900000 from "2,400,000 to 1,900,000"; a figure in unbalanced parentheses must not vanish; "(1.25x)" is a positive ratio, "(1,200)" is negative; a scale suffix counts only when attached to the number ("12 months" is not 12m); dates, years, quarter labels, section numbers and version numbers are not figures.

Rule: every normalisation or stripping rule ships with a test for what it must refuse and a test for what it must still allow.

Applies to: `backend/app/guardrails/numbers.py`.

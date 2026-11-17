Whoever chooses the scope defines the truth, so code, not the model, must choose the evidence an answer is checked against.

Inherited from CreditScout (2026-10 and 2026-11). Every outcome miss in the live evaluation came from the model passing wrong tool inputs (a cap of 500,000 instead of the stated 620,000; figures from the wrong quarter). Three of four misses in an earlier run were fixed by having code add the documents behind the calculator's inputs to the evidence set.

Rule: tools take borrower, facility, period and cycle from the run's scope and overwrite whatever the model sent. Calculators take line keys and read facts themselves; they never accept amounts typed by the model. Verification evidence is gathered by code.

Applies to: `backend/app/agents/` tool gateway and every tool.

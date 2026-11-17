Whoever chooses the scope defines the truth, so code, not the model, must choose the evidence an answer is checked against.

Inherited from CreditScout (2026-10 and 2026-11). Every outcome miss in the live evaluation came from the model passing wrong tool inputs (a cap of 500,000 instead of the stated 620,000; figures from the wrong quarter). Three of four misses in an earlier run were fixed by having code add the documents behind the calculator's inputs to the evidence set.

Rule: tools take borrower, facility, period and cycle from the run's scope and overwrite whatever the model sent. Calculators take line keys and read facts themselves; they never accept amounts typed by the model. Verification evidence is gathered by code.

Found here 2026-11-17 by the independent reviewer: the same mistake one level down. The Spreading Agent reported the row label for each figure, and code checked that label against the template. A reader could report a fragment ("net of current portion") that reads as no other line, swap long-term debt with other liabilities, and turn a leverage breach into a pass with nothing raised. The model had chosen the evidence its mapping was checked against. Fix: code reads the row's label from the page (`guardrails/quotes.py::row_label`); the reader's label is only used to find the row. The same was done for certificate rows, and a column header must now name exactly one period.

How to apply: for every check, ask "who supplied the thing this is compared with?" If the answer is the model, the check proves nothing. This includes labels, column headers, units phrases, page numbers and quotes.

Applies to: `backend/app/agents/` tool gateway and every tool; every extraction reader.

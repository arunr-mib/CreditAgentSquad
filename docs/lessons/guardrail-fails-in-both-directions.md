A number guardrail can fail by abstaining on everything, and that failure is invisible in a "zero false results" metric.

Inherited from CreditScout (2026-10). A guardrail that accepted only calculated numbers forced an abstain on every well-formed explanation, because good explanations quote figures from the agreement ("requires 1.25x"). The safety metric read perfect while the product did nothing.

Rule: figures quoted from a cited source are valid. Compare numbers after normalisation, never as text. Always report the abstain rate beside the safety rate, and keep a guardrail on-versus-off comparison.

Applies to: `backend/app/guardrails/`, evaluation scorecards.

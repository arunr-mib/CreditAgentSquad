"""Structured errors returned (never raised) by the calculation core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# Error codes used across the package.
MISSING_INPUT = "missing_input"
NON_POSITIVE_DENOMINATOR = "non_positive_denominator"
UNKNOWN_KEY = "unknown_key"
UNKNOWN_LINE = "unknown_line"
UNKNOWN_OP = "unknown_op"
UNKNOWN_DEFINITION = "unknown_definition"
CIRCULAR_DEFINITION = "circular_definition"
DUPLICATE_COMPONENT = "duplicate_component"
FLOAT_NOT_ALLOWED = "float_not_allowed"
INVALID_NODE = "invalid_node"
INVALID_VALUE = "invalid_value"
INVALID_PERIOD = "invalid_period"
INVALID_PERIOD_MODE = "invalid_period_mode"
NOT_FISCAL_YEAR_END = "not_fiscal_year_end"
NEGATIVE_CAP = "negative_cap"
INVALID_ROUNDING = "invalid_rounding"
NO_TERMS_IN_FORCE = "no_terms_in_force"
AMBIGUOUS_TERMS = "ambiguous_terms"
INVALID_TERMS = "invalid_terms"
MISSING_PARAMETER = "missing_parameter"
DOES_NOT_FOOT = "does_not_foot"
DOES_NOT_BALANCE = "does_not_balance"
DOES_NOT_TIE = "does_not_tie"
CASH_ROLL_MISMATCH = "cash_roll_mismatch"
ABSENT_NOT_VERIFIED = "absent_not_verified"
COMPUTED_LINE_SUPPLIED = "computed_line_supplied"
NEGATIVE_AMOUNT = "negative_amount"
DUPLICATE_ROW = "duplicate_row"


@dataclass(frozen=True)
class CalcError:
    """One refusal. `key`, `period_end` and `months` name the line and period when there is one."""

    code: str
    message: str
    key: str | None = None
    period_end: date | None = None
    months: int | None = None
    detail: dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "key": self.key,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "months": self.months,
            "detail": {k: (str(v) if not isinstance(v, (str, int, bool, type(None), list, dict)) else v)
                       for k, v in self.detail.items()},
        }

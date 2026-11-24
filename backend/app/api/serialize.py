"""Turn database rows into plain JSON for the workspace. Decimals are sent as strings so no
figure is ever rounded by a browser."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect


def plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f") if value == value.to_integral() else format(value, "f").rstrip("0").rstrip(".")
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


def row(obj: Any, *, exclude: tuple[str, ...] = (), only: tuple[str, ...] | None = None) -> dict[str, Any]:
    """All column values of a model instance as JSON-ready values."""
    out = {}
    for attr in inspect(obj).mapper.column_attrs:
        name = attr.key
        if name in exclude or (only is not None and name not in only):
            continue
        out[name] = plain(getattr(obj, name))
    return out

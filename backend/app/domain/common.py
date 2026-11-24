"""Column helpers shared by the domain models."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

__all__ = [
    "Any", "Date", "DateTime", "Decimal", "ForeignKey", "JSONB", "Mapped", "Numeric", "String", "Text",
    "UUID", "date", "datetime", "fk", "json_col", "mapped_column", "money", "uuid",
]


def fk(target: str, *, nullable: bool = False, index: bool = True):
    return mapped_column(UUID(as_uuid=True), ForeignKey(target), nullable=nullable, index=index)


def money(*, nullable: bool = True):
    return mapped_column(Numeric(24, 6), nullable=nullable)


def json_col(*, nullable: bool = False, default=None):
    return mapped_column(JSONB, nullable=nullable, default=default)

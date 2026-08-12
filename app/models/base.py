import uuid
import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared base class for all models."""
    pass


class TimestampMixin:
    """Mixin for created_at — reuse on any table that needs it."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def uuid_pk():
    """Helper for a standard UUID primary key column."""
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


# ---- Shared Enums ----
# Enums enforce valid values at the DB level (no typos like "avaliable")

class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    RENTED = "rented"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class BookingStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentType(str, enum.Enum):
    RENTAL = "rental"
    DEPOSIT = "deposit"
    FEE = "fee"
    REFUND = "refund"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


class IncidentType(str, enum.Enum):
    BREAKDOWN = "breakdown"
    DAMAGE_DISPUTE = "damage_dispute"
    LATE_RETURN = "late_return"
    OTHER = "other"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class MessageChannel(str, enum.Enum):
    EMAIL = "email"
    CHAT = "chat"
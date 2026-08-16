"""
OpsLens — SQLAlchemy Models
============================
All tables for the campervan rental operations investigator.

Multi-tenancy: every table carries tenant_id, scoping all data to one
rental company. Booking is the hub table — contract, payments, and
incidents all trace back to it.
"""

import uuid
import enum
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    String, Text, Integer, Numeric, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at to any table that inherits it."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def uuid_pk():
    """Standard UUID primary key, used on every table."""
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


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


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    depots: Mapped[List["Depot"]] = relationship(back_populates="tenant")
    customers: Mapped[List["Customer"]] = relationship(back_populates="tenant")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="tenant")


# ============================================================
# Depot — pickup/dropoff locations
# ============================================================

class Depot(Base, TimestampMixin):
    __tablename__ = "depots"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="depots")


# ============================================================
# Customer
# ============================================================

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    __table_args__ = (
        # email only needs to be unique WITHIN a tenant, not globally
        UniqueConstraint("tenant_id", "email", name="uq_customer_tenant_email"),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    mobile_no: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False)
    passport_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    license_number: Mapped[str] = mapped_column(String(50), nullable=False)
    license_expiry: Mapped[date] = mapped_column(Date, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="customers")
    bookings: Mapped[List["Booking"]] = relationship(back_populates="customer")
    incidents: Mapped[List["Incident"]] = relationship(back_populates="customer")
    messages: Mapped[List["Message"]] = relationship(back_populates="customer")


# ============================================================
# Vehicle
# ============================================================

class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    depot_id: Mapped[str] = mapped_column(ForeignKey("depots.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)          # e.g. "Wanderer VW T6"
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        SAEnum(VehicleStatus, name="vehicle_status"), nullable=False,
        default=VehicleStatus.AVAILABLE, index=True
    )
    mileage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_maintenance_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="vehicles")
    depot: Mapped["Depot"] = relationship()
    bookings: Mapped[List["Booking"]] = relationship(back_populates="vehicle")


# ============================================================
# Booking — the hub table
# ============================================================

class Booking(Base, TimestampMixin):
    """Everything else (contract, payments, incidents) traces back to a booking."""
    __tablename__ = "bookings"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    pickup_depot_id: Mapped[str] = mapped_column(ForeignKey("depots.id"), nullable=False)
    return_depot_id: Mapped[str] = mapped_column(ForeignKey("depots.id"), nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status"), nullable=False,
        default=BookingStatus.UPCOMING, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # nullable — only filled in once the van is actually returned
    actual_return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    tenant: Mapped["Tenant"] = relationship()
    customer: Mapped["Customer"] = relationship(back_populates="bookings")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="bookings")
    # explicit foreign_keys needed: two FKs point at the same table (depots),
    # so SQLAlchemy can't infer which one each relationship should use
    pickup_depot: Mapped["Depot"] = relationship(
        foreign_keys="Booking.pickup_depot_id", overlaps="return_depot"
    )
    return_depot: Mapped["Depot"] = relationship(
        foreign_keys="Booking.return_depot_id", overlaps="pickup_depot"
    )

    # one-to-one: a booking has exactly one contract
    contract: Mapped[Optional["Contract"]] = relationship(back_populates="booking", uselist=False)
    payments: Mapped[List["Payment"]] = relationship(back_populates="booking")
    incidents: Mapped[List["Incident"]] = relationship(back_populates="booking")


# ============================================================
# Contract — one-to-one with booking, holds policy terms for RAG
# ============================================================

class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    # unique=True enforces the 1:1 relationship at the DB level
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), nullable=False, unique=True)

    mileage_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    damage_waiver_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    breakdown_response_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # Numeric, never Float, for money
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    terms_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship()
    booking: Mapped["Booking"] = relationship(back_populates="contract")


# ============================================================
# Payment
# ============================================================

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), nullable=False, index=True)

    type: Mapped[PaymentType] = mapped_column(SAEnum(PaymentType, name="payment_type"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"), nullable=False,
        default=PaymentStatus.PENDING, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship()
    booking: Mapped["Booking"] = relationship(back_populates="payments")


# ============================================================
# Incident — the trigger for investigations
# ============================================================

class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)

    type: Mapped[IncidentType] = mapped_column(
        SAEnum(IncidentType, name="incident_type"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus, name="incident_status"), nullable=False,
        default=IncidentStatus.OPEN, index=True
    )
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # filled in once resolved
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)  # staff user id/name

    tenant: Mapped["Tenant"] = relationship()
    booking: Mapped["Booking"] = relationship(back_populates="incidents")
    customer: Mapped["Customer"] = relationship(back_populates="incidents")


# ============================================================
# Message — raw customer communication, before classification
# ============================================================

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    # nullable — a customer might message before an incident/booking link is known
    booking_id: Mapped[Optional[str]] = mapped_column(ForeignKey("bookings.id"), nullable=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[MessageChannel] = mapped_column(
        SAEnum(MessageChannel, name="message_channel"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tenant: Mapped["Tenant"] = relationship()
    customer: Mapped["Customer"] = relationship(back_populates="messages")


# ============================================================
# AuditLog — tracks every agent/human action for observability
# ============================================================

class AuditLog(Base):
    """Records every step of an investigation: which agent/human did what,
    and when. This is what makes decisions traceable/auditable."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)

    actor: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "classifier_agent", "staff:jane"
    action: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. "classified_incident", "approved_refund"
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized extra context

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
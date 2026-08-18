
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from langchain_groq import ChatGroq

from app.config import settings
from app.models import Vehicle, VehicleStatus, Payment, PaymentStatus, Booking, Incident
from app.agents.state import InvestigationState

llm = ChatGroq(model="qwen/qwen3.6-27b", api_key=settings.GROQ_API_KEY, temperature=0)



# ============================================================
# Vehicle Agent
# ============================================================

class VehicleFindingsOutput(BaseModel):
    findings: str = Field(description="Plain-English summary: is a replacement vehicle available, and where")


def get_available_vehicles_near(db: Session, depot_id: str, exclude_vehicle_id: str):
    return (
        db.query(Vehicle)
        .filter(Vehicle.depot_id == depot_id)
        .filter(Vehicle.status == VehicleStatus.AVAILABLE)
        .filter(Vehicle.id != exclude_vehicle_id)
        .all()
    )


VEHICLE_PROMPT = """A customer has a {incident_type} issue and wants: {customer_intent}

Available replacement vehicles at the same depot:
{available_list}

Summarize in one or two sentences whether a suitable replacement is available.
"""


def make_vehicle_agent(db: Session):
    def vehicle_agent(state: InvestigationState) -> InvestigationState:
        booking = db.query(Booking).filter(Booking.id == state["booking_id"]).first()
        available = get_available_vehicles_near(db, booking.pickup_depot_id, booking.vehicle_id)
        available_list = ", ".join(v.name for v in available) if available else "None available"

        prompt = VEHICLE_PROMPT.format(
            incident_type=state["incident_type"],
            customer_intent=state["customer_intent"],
            available_list=available_list,
        )
        result: VehicleFindingsOutput = llm.with_structured_output(VehicleFindingsOutput).invoke(prompt)

        return {**state, "vehicle_findings": result.findings}

    return vehicle_agent


# ============================================================
# Payment Agent
# ============================================================

def get_payments_for_booking(db: Session, booking_id: str):
    return db.query(Payment).filter(Payment.booking_id == booking_id).all()


def make_payment_agent(db: Session):
    def payment_agent(state: InvestigationState) -> InvestigationState:
        payments = get_payments_for_booking(db, state["booking_id"])
        unpaid = [p for p in payments if p.status != PaymentStatus.PAID]

        if not payments:
            findings = "No payment records found for this booking."
        elif unpaid:
            findings = f"Customer has {len(unpaid)} unpaid/pending payment(s) - not in good standing."
        else:
            findings = "All payments (rental + deposit) are paid in full - customer in good standing."

        return {**state, "payment_findings": findings}

    return payment_agent


# ============================================================
# History / Risk Agent
# ============================================================

def count_prior_incidents(db: Session, customer_id: str, incident_type: str) -> int:
    return (
        db.query(func.count(Incident.id))
        .filter(Incident.customer_id == customer_id)
        .filter(Incident.type == incident_type)
        .scalar()
    )


def make_history_agent(db: Session):
    def history_agent(state: InvestigationState) -> InvestigationState:
        prior_count = count_prior_incidents(db, state["customer_id"], state["incident_type"])

        if prior_count == 0:
            findings = "First-time claim of this type from this customer - no prior pattern."
        elif prior_count <= 2:
            findings = f"Customer has {prior_count} prior claim(s) of this type - within normal range."
        else:
            findings = f"Customer has {prior_count} prior claims of this type - unusually high, flag for review."

        return {**state, "history_findings": findings}

    return history_agent

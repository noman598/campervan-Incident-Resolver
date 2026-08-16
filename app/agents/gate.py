
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq

from app.config import settings
from app.models import Contract
from app.agents.state import InvestigationState


# ---- Tool: plain DB query, no LLM involved ----
def get_contract_for_booking(db: Session, booking_id: str) -> Contract | None:
    return db.query(Contract).filter(Contract.booking_id == booking_id).first()


# ---- Structured output for this agent ----
class GateOutput(BaseModel):
    is_covered: bool
    contract_summary: str = Field(
        description="Plain-English summary of the relevant contract clause and why it does or doesn't cover this incident"
    )


llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0)
structured_llm = llm.with_structured_output(GateOutput)

GATE_PROMPT = """You are reviewing a campervan rental contract to determine
if a reported incident is covered.

Incident type: {incident_type}
Customer's request: {customer_intent}

Contract terms:
- Damage waiver included: {damage_waiver}
- Breakdown response SLA: {sla_hours} hours
- Mileage limit: {mileage_limit}
- Full terms: {terms_text}

Decide: is_covered should be true if the contract terms support helping
this customer. Give a short, plain-English contract_summary explaining
your reasoning.
"""


def make_gate_agent(db: Session):
    def gate_agent(state: InvestigationState) -> InvestigationState:
        contract = get_contract_for_booking(db, state["booking_id"])

        if contract is None:
            return {
                **state,
                "is_covered": False,
                "contract_summary": "No contract found for this booking.",
            }

        prompt = GATE_PROMPT.format(
            incident_type=state["incident_type"],
            customer_intent=state["customer_intent"],
            damage_waiver=contract.damage_waiver_included,
            sla_hours=contract.breakdown_response_hours,
            mileage_limit=contract.mileage_limit,
            terms_text=contract.terms_text or "N/A",
        )
        result: GateOutput = structured_llm.invoke(prompt)

        return {
            **state,
            "is_covered": result.is_covered,
            "contract_summary": result.contract_summary,
        }

    return gate_agent
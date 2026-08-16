
from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from app.config import settings
from app.agents.state import InvestigationState

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0)


class SynthesisOutput(BaseModel):
    recommended_action: Literal[
        "approve_replacement",
        "approve_refund",
        "approve_extension",
        "partial_credit",
        "deny",
        "escalate",
    ]
    reasoning: str = Field(description="Clear explanation of why this action is recommended, referencing the contract and findings")
    confidence: float = Field(description="0.0 to 1.0 confidence in this recommendation", ge=0.0, le=1.0)


structured_llm = llm.with_structured_output(SynthesisOutput)

SYNTHESIS_PROMPT = """You are making a final operations decision for a campervan rental incident.

Incident type: {incident_type}
Customer's request: {customer_intent}

Contract coverage: {is_covered}
Contract summary: {contract_summary}

{extra_findings}

Based on all the above, recommend ONE action:
- approve_replacement: send a replacement vehicle
- approve_refund: issue a monetary refund
- approve_extension: approve a rental extension
- partial_credit: partial refund/credit, not full
- deny: not covered or not justified
- escalate: needs human investigation before any action (e.g. suspicious pattern, ambiguous evidence)

Explain your reasoning clearly, and give a confidence score.
"""


def make_synthesis_agent():
    def synthesis_agent(state: InvestigationState) -> InvestigationState:
        if not state.get("is_covered", False):
            extra_findings = "(Not covered by contract - no further checks were run.)"
        else:
            extra_findings = (
                f"Vehicle findings: {state.get('vehicle_findings', 'N/A')}\n"
                f"Payment findings: {state.get('payment_findings', 'N/A')}\n"
                f"History findings: {state.get('history_findings', 'N/A')}"
            )

        prompt = SYNTHESIS_PROMPT.format(
            incident_type=state["incident_type"],
            customer_intent=state["customer_intent"],
            is_covered=state.get("is_covered", False),
            contract_summary=state.get("contract_summary", "N/A"),
            extra_findings=extra_findings,
        )
        result: SynthesisOutput = structured_llm.invoke(prompt)

        return {
            **state,
            "recommended_action": result.recommended_action,
            "reasoning": result.reasoning,
            "confidence": result.confidence,
        }

    return synthesis_agent
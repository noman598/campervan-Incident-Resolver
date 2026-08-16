"""
Classifier Agent
================
Entry point of the investigation graph. Reads the raw customer message
and outputs a structured (incident_type, customer_intent) — never free text.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from app.config import settings
from app.agents.state import InvestigationState


class ClassifierOutput(BaseModel):
    incident_type: Literal["breakdown", "damage_dispute", "late_return", "other"]
    customer_intent: str = Field(
        description="One short sentence summarizing what the customer wants"
    )


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.GROQ_API_KEY,
    temperature=0,   # deterministic — we want consistent classification, not creativity
)

# .with_structured_output() forces the LLM's response to match ClassifierOutput's
# schema — LangChain handles the tool-calling/parsing machinery for us
structured_llm = llm.with_structured_output(ClassifierOutput)

CLASSIFIER_PROMPT = """You are an operations assistant for a campervan rental company.
Read the customer's message and classify it.

incident_type must be exactly one of:
- "breakdown": vehicle mechanical/electrical failure, won't start, stranded
- "damage_dispute": customer disputing a damage charge or deposit deduction
- "late_return": customer requesting an extension or reporting a late return
- "other": anything that doesn't clearly fit the above

Customer message:
{message}
"""


def classify_incident(state: InvestigationState) -> InvestigationState:
    """LangGraph node: reads state['raw_message'], writes incident_type + customer_intent."""
    prompt = CLASSIFIER_PROMPT.format(message=state["raw_message"])
    result: ClassifierOutput = structured_llm.invoke(prompt)

    return {
        **state,
        "incident_type": result.incident_type,
        "customer_intent": result.customer_intent,
    }


# test_state = {"raw_message": "The generator we rented isn't working and we need a replacement tomorrow."}
# result = classify_incident(test_state)
# print(result)
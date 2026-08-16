"""
Investigation Runner
=======================
The actual entry point: given a raw customer message + booking/customer
ids, runs the full LangGraph investigation and returns the final state.
This is what an API endpoint (or a test script) calls.
"""

from sqlalchemy.orm import Session

from app.agents.graph import build_investigation_graph
from app.agents.state import InvestigationState


def run_investigation(db: Session, tenant_id: str, booking_id: str, customer_id: str, raw_message: str) -> InvestigationState:
    graph = build_investigation_graph(db)

    initial_state: InvestigationState = {
        "tenant_id": tenant_id,
        "booking_id": booking_id,
        "customer_id": customer_id,
        "raw_message": raw_message,
    }

    final_state = graph.invoke(initial_state)
    return final_state


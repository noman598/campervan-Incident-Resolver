"""
Investigation Graph
=====================
This is where LangGraph actually gets used. Wires together every agent
as a node, with conditional edges implementing the "gate" short-circuit
and the parallel fan-out you designed.

Graph shape:

    classifier -> gate -> (conditional)
                            |-- not covered --> synthesis
                            |-- covered -----> parallel_checks -> synthesis
"""

from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from app.agents.state import InvestigationState
from app.agents.classifier import classify_incident
from app.agents.gate import make_gate_agent
from app.agents.parallel_agents import make_vehicle_agent, make_payment_agent, make_history_agent
from app.agents.synthesis import make_synthesis_agent


def route_after_gate(state: InvestigationState) -> str:
    """Conditional edge function: inspects state, returns the name of the
    next node. This implements the 'not covered -> skip parallel checks'
    branch from your architecture diagram."""
    if state.get("is_covered", False):
        return "parallel_checks"
    return "synthesis"


def run_parallel_checks(db: Session):
    """A single node that internally runs all 3 parallel agents.

    Note: LangGraph does support true parallel branches (multiple edges
    from one node, converging at a join point). Running them sequentially
    inside one node is simpler to debug for a first version since each
    agent is independent - this is still correct, just not concurrently
    executed. Swap to true parallel edges later if latency matters.
    """
    vehicle_agent = make_vehicle_agent(db)
    payment_agent = make_payment_agent(db)
    history_agent = make_history_agent(db)

    def node(state: InvestigationState) -> InvestigationState:
        state = vehicle_agent(state)
        state = payment_agent(state)
        state = history_agent(state)
        return state

    return node


def build_investigation_graph(db: Session):
    """Builds and compiles the full investigation graph, wired to a
    specific DB session (injected via the factory pattern, same as
    individual agents)."""

    graph = StateGraph(InvestigationState)

    graph.add_node("classifier", classify_incident)
    graph.add_node("gate", make_gate_agent(db))
    graph.add_node("parallel_checks", run_parallel_checks(db))
    graph.add_node("synthesis", make_synthesis_agent())

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "gate")

    graph.add_conditional_edges(
        "gate",
        route_after_gate,
        {
            "parallel_checks": "parallel_checks",
            "synthesis": "synthesis",
        },
    )

    graph.add_edge("parallel_checks", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()
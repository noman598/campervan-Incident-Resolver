from typing import TypedDict, Optional


class InvestigationState(TypedDict, total=False):
    # ---- Identifiers (looked up from the incoming message) ----
    tenant_id: str
    booking_id: str
    customer_id: str
    incident_id: Optional[str]     # filled in once the Incident row is created

    # ---- Raw input ----
    raw_message: str

    # ---- Classifier Agent output ----
    incident_type: str             # "breakdown" | "damage_dispute" | "late_return" | "other"
    customer_intent: str           # e.g. "wants replacement", "disputing deduction"

    # ---- Gate Agent (Contract) output ----
    is_covered: bool
    contract_summary: str          # what the relevant clause says, in plain text

    # ---- Parallel agents' outputs ----
    vehicle_findings: str
    payment_findings: str
    history_findings: str

    # ---- Synthesis Agent output ----
    recommended_action: str        # e.g. "approve_replacement", "deny", "partial_refund"
    reasoning: str
    confidence: float
"""Quick manual test — not a formal pytest yet, just to verify the
pipeline runs end-to-end against real seeded data."""

from app.database import SessionLocal
from app.models import Incident, Booking
from app.agents.runner import run_investigation

db = SessionLocal()

# grab a real seeded incident to test against
incident = db.query(Incident).filter(Incident.type == "breakdown").first()

result = run_investigation(
    db=db,
    tenant_id=str(incident.tenant_id),
    booking_id=str(incident.booking_id),
    customer_id=str(incident.customer_id),
    raw_message=incident.description,
)

print("Incident type:", result["incident_type"])
print("Covered:", result["is_covered"])
print("Recommended action:", result["recommended_action"])
print("Reasoning:", result["reasoning"])
print("Confidence:", result["confidence"])

db.close()
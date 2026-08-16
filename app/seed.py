"""
OpsLens — Synthetic Data Generator
====================================
Populates the database with a realistic, internally-consistent dataset
for one tenant ("Wanderer Vans"): depots, customers, vehicles, bookings,
contracts, payments, and a realistic subset of incidents + messages.

Run:
    python -m app.seed
"""

import random
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from app.database import SessionLocal
from app.models import (
    Tenant, Depot, Customer, Vehicle, Booking, Contract, Payment,
    Incident, Message,
    VehicleStatus, BookingStatus, PaymentType, PaymentStatus,
    IncidentType, IncidentStatus, MessageChannel,
)

fake = Faker()
random.seed(42)   # reproducible dataset across runs
Faker.seed(42)

# ---- Tunable volumes ----
N_DEPOTS = 5
N_CUSTOMERS = 50
N_VEHICLES = 30
N_BOOKINGS = 150
INCIDENT_RATE = 0.25          # ~25% of eligible bookings get an incident
BREAKDOWN_SHARE = 0.4
DAMAGE_DISPUTE_SHARE = 0.35
LATE_RETURN_SHARE = 0.25

VAN_MODELS = [
    "VW California", "Mercedes Marco Polo", "Ford Transit Custom Camper",
    "Fiat Ducato Camper", "Toyota Hiace Camper", "VW Grand California",
]

BREAKDOWN_MESSAGES = [
    "The van broke down on the highway, engine won't start. We need a replacement urgently.",
    "Our campervan's battery died overnight, we're stranded at the campsite.",
    "The fridge and electrics stopped working mid trip, is this covered?",
    "Engine warning light came on and the van is losing power.",
]

DAMAGE_DISPUTE_MESSAGES = [
    "We were charged for a scratch we didn't cause, please review our deposit deduction.",
    "Why was $250 deducted from our deposit? The van was fine when we returned it.",
    "Disputing the damage charge, the dent was already there at pickup.",
]

LATE_RETURN_MESSAGES = [
    "Can we extend our rental by 2 more days?",
    "We're running a day late returning the van, is that alright?",
    "Requesting a 3 day extension on our current booking.",
]


def random_date_within(days_back=180, days_fwd=60):
    start = date.today() - timedelta(days=days_back)
    end = date.today() + timedelta(days=days_fwd)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def seed():
    db = SessionLocal()
    try:
        print("Seeding tenant...")
        tenant = Tenant(name="Wanderer Vans")
        db.add(tenant)
        db.flush()  # get tenant.id without full commit

        print(f"Seeding {N_DEPOTS} depots...")
        depots = []
        for _ in range(N_DEPOTS):
            depot = Depot(
                tenant_id=tenant.id,
                name=f"{fake.city()} Depot",
                address=fake.street_address(),
                city=fake.city(),
            )
            db.add(depot)
            depots.append(depot)
        db.flush()

        print(f"Seeding {N_CUSTOMERS} customers...")
        customers = []
        for _ in range(N_CUSTOMERS):
            customer = Customer(
                tenant_id=tenant.id,
                name=fake.name(),
                mobile_no=fake.phone_number()[:20],
                email=fake.unique.email(),
                passport_id=fake.bothify(text="??######"),
                license_number=fake.bothify(text="DL#######"),
                license_expiry=date.today() + timedelta(days=random.randint(30, 1500)),
            )
            db.add(customer)
            customers.append(customer)
        db.flush()

        print(f"Seeding {N_VEHICLES} vehicles...")
        vehicles = []
        for _ in range(N_VEHICLES):
            vehicle = Vehicle(
                tenant_id=tenant.id,
                depot_id=random.choice(depots).id,
                name=random.choice(VAN_MODELS),
                plate_number=fake.bothify(text="???-####").upper(),
                status=VehicleStatus.AVAILABLE,
                mileage=random.randint(5000, 120000),
                year=random.randint(2018, 2025),
                last_maintenance_date=date.today() - timedelta(days=random.randint(5, 200)),
            )
            db.add(vehicle)
            vehicles.append(vehicle)
        db.flush()

        print(f"Seeding {N_BOOKINGS} bookings (+ contracts + payments)...")
        bookings = []
        for _ in range(N_BOOKINGS):
            start = random_date_within()
            duration = random.randint(3, 14)
            end = start + timedelta(days=duration)
            customer = random.choice(customers)
            vehicle = random.choice(vehicles)
            depot = random.choice(depots)

            is_past = end < date.today()
            status = (
                BookingStatus.COMPLETED if is_past
                else BookingStatus.ACTIVE if start <= date.today() <= end
                else BookingStatus.UPCOMING
            )

            booking = Booking(
                tenant_id=tenant.id,
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                pickup_depot_id=depot.id,
                return_depot_id=depot.id,
                status=status,
                start_date=start,
                end_date=end,
                actual_return_date=end if status == BookingStatus.COMPLETED else None,
            )
            db.add(booking)
            db.flush()

            damage_waiver = random.random() < 0.6  # 60% opted into waiver
            contract = Contract(
                tenant_id=tenant.id,
                booking_id=booking.id,
                mileage_limit=random.choice([200, 300, 500, 1000]),
                damage_waiver_included=damage_waiver,
                breakdown_response_hours=random.choice([12, 24, 48]),
                deposit_amount=random.choice([200, 300, 500]),
                terms_text=(
                    f"This rental agreement covers a {duration}-day rental. "
                    f"Mileage limit applies. Damage waiver is "
                    f"{'included' if damage_waiver else 'not included'}, "
                    f"meaning the renter is "
                    f"{'not liable' if damage_waiver else 'liable'} for minor damage. "
                    f"Breakdown assistance guaranteed within the response window stated."
                ),
            )
            db.add(contract)

            rental_payment = Payment(
                tenant_id=tenant.id,
                booking_id=booking.id,
                type=PaymentType.RENTAL,
                status=PaymentStatus.PAID,
                amount=duration * random.choice([80, 95, 110, 130]),
                paid_at=datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            )
            deposit_payment = Payment(
                tenant_id=tenant.id,
                booking_id=booking.id,
                type=PaymentType.DEPOSIT,
                status=PaymentStatus.PAID,
                amount=contract.deposit_amount,
                paid_at=datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
            )
            db.add_all([rental_payment, deposit_payment])

            bookings.append((booking, contract))

        db.flush()

        print("Seeding incidents + messages (realistic subset)...")
        eligible = [b for b, c in bookings]  # any booking can have an incident
        n_incidents = int(len(eligible) * INCIDENT_RATE)
        incident_bookings = random.sample(eligible, n_incidents)

        for booking in incident_bookings:
            roll = random.random()
            if roll < BREAKDOWN_SHARE:
                itype = IncidentType.BREAKDOWN
                text = random.choice(BREAKDOWN_MESSAGES)
            elif roll < BREAKDOWN_SHARE + DAMAGE_DISPUTE_SHARE:
                itype = IncidentType.DAMAGE_DISPUTE
                text = random.choice(DAMAGE_DISPUTE_MESSAGES)
            else:
                itype = IncidentType.LATE_RETURN
                text = random.choice(LATE_RETURN_MESSAGES)

            reported_at = datetime.combine(
                booking.start_date + timedelta(days=random.randint(1, max(1, (booking.end_date - booking.start_date).days))),
                datetime.min.time(), tzinfo=timezone.utc
            )

            message = Message(
                tenant_id=tenant.id,
                customer_id=booking.customer_id,
                booking_id=booking.id,
                raw_text=text,
                channel=random.choice([MessageChannel.EMAIL, MessageChannel.CHAT]),
                received_at=reported_at,
            )
            db.add(message)

            incident = Incident(
                tenant_id=tenant.id,
                booking_id=booking.id,
                customer_id=booking.customer_id,
                type=itype,
                description=text,
                status=IncidentStatus.OPEN,
                reported_at=reported_at,
            )
            db.add(incident)

        db.commit()
        print("\nSeed complete.")
        print(f"  Tenant:    1 (Wanderer Vans, id={tenant.id})")
        print(f"  Depots:    {N_DEPOTS}")
        print(f"  Customers: {N_CUSTOMERS}")
        print(f"  Vehicles:  {N_VEHICLES}")
        print(f"  Bookings:  {N_BOOKINGS} (+ {N_BOOKINGS} contracts, {N_BOOKINGS*2} payments)")
        print(f"  Incidents: {n_incidents} (+ {n_incidents} messages)")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
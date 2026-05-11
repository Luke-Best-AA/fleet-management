"""Seed the database with initial data: an admin user, locations, categories."""

import sys

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.deletion_request import DeletionRequest  # noqa: F401
from app.models.location import Location
from app.models.maintenance import MaintenanceCategory, MaintenanceRecord  # noqa: F401
from app.models.mileage import MileageRecord  # noqa: F401
from app.models.retirement_request import RetirementRequest  # noqa: F401
from app.models.user import User
from app.models.vehicle import Vehicle
from app.security.password import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Locations
        if not db.query(Location).first():
            locations = [
                Location(name="London Depot", code="LON", region="South East", city="London", postcode="SW1A 1AA"),
                Location(
                    name="Manchester Depot", code="MAN", region="North West", city="Manchester", postcode="M1 1AA"
                ),
                Location(
                    name="Birmingham Depot", code="BHM", region="West Midlands", city="Birmingham", postcode="B1 1AA"
                ),
            ]
            db.add_all(locations)
            db.flush()
            print(f"Created {len(locations)} locations")

        # Admin user
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@fleet.local",
                password_hash=hash_password("admin123!"),
                role="admin",
                first_name="System",
                last_name="Admin",
                employee_number="EMP001",
            )
            db.add(admin)
            db.flush()
            print("Created admin user (username: admin, password: admin123!)")

        # Standard user
        if not db.query(User).filter(User.username == "driver1").first():
            loc = db.query(Location).filter(Location.code == "LON").first()
            driver = User(
                username="driver1",
                email="driver1@fleet.local",
                password_hash=hash_password("driver123!"),
                role="standard",
                first_name="John",
                last_name="Driver",
                employee_number="EMP002",
                location_id=loc.id if loc else None,
            )
            db.add(driver)
            db.flush()
            print("Created standard user (username: driver1, password: driver123!)")

        # Maintenance categories
        if not db.query(MaintenanceCategory).first():
            categories = [
                MaintenanceCategory(name="Oil Change", description="Engine oil replacement"),
                MaintenanceCategory(name="Tyre Replacement", description="Replace worn tyres"),
                MaintenanceCategory(name="Brake Service", description="Brake pad/disc replacement"),
                MaintenanceCategory(name="MOT", description="Annual MOT inspection"),
                MaintenanceCategory(name="Other", description="Other maintenance", requires_notes=True),
            ]
            db.add_all(categories)
            db.flush()
            print(f"Created {len(categories)} maintenance categories")

        # Sample vehicle
        if not db.query(Vehicle).first():
            loc = db.query(Location).filter(Location.code == "LON").first()
            driver = db.query(User).filter(User.username == "driver1").first()
            vehicle = Vehicle(
                registration_number="AB12 CDE",
                fleet_reference="FLT-001",
                vehicle_type="roadside_van",
                make="Ford",
                model="Transit",
                year=2022,
                current_mileage=15000,
                location_id=loc.id if loc else 1,
                primary_driver_user_id=driver.id if driver else None,
            )
            db.add(vehicle)
            db.flush()
            print("Created sample vehicle (AB12 CDE)")

        db.commit()
        print("Seed complete.")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()

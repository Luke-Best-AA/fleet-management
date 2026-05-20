"""Seed the database with realistic demo data for examiner review.

Truncates ALL tables on every run and re-creates a rich dataset including
historical audit-logs, page-visits, mileage, and maintenance records that
produce attractive charts on the admin dashboard.
"""

# ruff: noqa: S311 – random is fine for seed/demo data, not cryptographic

import random
from datetime import UTC, date, datetime, timedelta

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.deletion_request import DeletionRequest
from app.models.location import Location
from app.models.maintenance import MaintenanceCategory, MaintenanceRecord
from app.models.mileage import MileageRecord
from app.models.page_visit import PageVisit
from app.models.retirement_request import RetirementRequest
from app.models.user import User
from app.models.vehicle import Vehicle
from app.security.password import hash_password

random.seed(42)  # reproducible data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TODAY = date.today()
NOW = datetime.now(tz=UTC)


def _dt(d: date, hour: int = 9, minute: int = 0) -> datetime:
    """Turn a date into a timezone-aware datetime."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=UTC)


def _rand_time(d: date) -> datetime:
    """Random business-hours datetime on a given date."""
    hour = random.choices(range(24), weights=_HOURLY_WEIGHTS, k=1)[0]
    minute = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=UTC)


# Weighted hourly distribution – peaks at 09-11 and 14-16 for nice chart shape
_HOURLY_WEIGHTS = [
    1,
    0,
    0,
    0,
    0,
    1,
    3,
    8,
    15,
    22,
    20,
    18,  # 00-11
    12,
    14,
    19,
    18,
    14,
    8,
    5,
    3,
    2,
    1,
    1,
    1,  # 12-23
]

# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------
LOCATIONS = [
    {"name": "London Depot", "code": "LON", "region": "South East", "city": "London", "postcode": "SW1A 1AA"},
    {"name": "Manchester Depot", "code": "MAN", "region": "North West", "city": "Manchester", "postcode": "M1 1AA"},
    {"name": "Birmingham Depot", "code": "BHM", "region": "West Midlands", "city": "Birmingham", "postcode": "B1 1AA"},
    {"name": "Edinburgh Depot", "code": "EDI", "region": "Scotland", "city": "Edinburgh", "postcode": "EH1 1YZ"},
    {"name": "Bristol Depot", "code": "BRS", "region": "South West", "city": "Bristol", "postcode": "BS1 1AA"},
]

CATEGORIES = [
    {"name": "Oil Change", "description": "Engine oil and filter replacement"},
    {"name": "Tyre Replacement", "description": "Replace worn or damaged tyres"},
    {"name": "Brake Service", "description": "Brake pad and disc replacement"},
    {"name": "MOT", "description": "Annual MOT inspection"},
    {"name": "Battery Replacement", "description": "Replace vehicle battery"},
    {"name": "Other", "description": "Other maintenance work", "requires_notes": True},
]

USERS = [
    # Admins
    {
        "username": "admin",
        "email": "admin@fleet.local",
        "password": "admin123!",
        "role": "admin",
        "first_name": "System",
        "last_name": "Admin",
        "employee_number": "EMP001",
        "location_idx": 0,
    },
    {
        "username": "sjones",
        "email": "sjones@fleet.local",
        "password": "admin123!",
        "role": "admin",
        "first_name": "Sarah",
        "last_name": "Jones",
        "employee_number": "EMP002",
        "location_idx": 1,
    },
    # Standard drivers
    {
        "username": "jdriver",
        "email": "jdriver@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "John",
        "last_name": "Driver",
        "employee_number": "EMP003",
        "location_idx": 0,
    },
    {
        "username": "esmith",
        "email": "esmith@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Emma",
        "last_name": "Smith",
        "employee_number": "EMP004",
        "location_idx": 0,
    },
    {
        "username": "mwilson",
        "email": "mwilson@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Michael",
        "last_name": "Wilson",
        "employee_number": "EMP005",
        "location_idx": 1,
    },
    {
        "username": "lbrown",
        "email": "lbrown@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Laura",
        "last_name": "Brown",
        "employee_number": "EMP006",
        "location_idx": 1,
    },
    {
        "username": "dtaylor",
        "email": "dtaylor@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "David",
        "last_name": "Taylor",
        "employee_number": "EMP007",
        "location_idx": 2,
    },
    {
        "username": "cwhite",
        "email": "cwhite@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Claire",
        "last_name": "White",
        "employee_number": "EMP008",
        "location_idx": 2,
    },
    {
        "username": "rscott",
        "email": "rscott@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Robert",
        "last_name": "Scott",
        "employee_number": "EMP009",
        "location_idx": 3,
    },
    {
        "username": "ahall",
        "email": "ahall@fleet.local",
        "password": "driver123!",
        "role": "standard",
        "first_name": "Amy",
        "last_name": "Hall",
        "employee_number": "EMP010",
        "location_idx": 4,
    },
]

VEHICLES = [
    # London
    {
        "reg": "AB12 CDE",
        "ref": "FLT-001",
        "type": "roadside_van",
        "make": "Ford",
        "model": "Transit",
        "year": 2022,
        "mileage": 45200,
        "loc_idx": 0,
        "driver_idx": 2,
    },
    {
        "reg": "CD34 FGH",
        "ref": "FLT-002",
        "type": "flat_loader_lorry",
        "make": "Mercedes",
        "model": "Atego",
        "year": 2021,
        "mileage": 62100,
        "loc_idx": 0,
        "driver_idx": 3,
    },
    {
        "reg": "EF56 IJK",
        "ref": "FLT-003",
        "type": "patrol_van",
        "make": "Vauxhall",
        "model": "Vivaro",
        "year": 2023,
        "mileage": 18400,
        "loc_idx": 0,
        "driver_idx": None,
    },
    # Manchester
    {
        "reg": "GH78 LMN",
        "ref": "FLT-004",
        "type": "roadside_van",
        "make": "Ford",
        "model": "Transit Custom",
        "year": 2022,
        "mileage": 51800,
        "loc_idx": 1,
        "driver_idx": 4,
    },
    {
        "reg": "IJ90 OPQ",
        "ref": "FLT-005",
        "type": "roadside_van",
        "make": "VW",
        "model": "Crafter",
        "year": 2020,
        "mileage": 78500,
        "loc_idx": 1,
        "driver_idx": 5,
    },
    # Birmingham
    {
        "reg": "KL12 RST",
        "ref": "FLT-006",
        "type": "flat_loader_lorry",
        "make": "DAF",
        "model": "LF",
        "year": 2021,
        "mileage": 55300,
        "loc_idx": 2,
        "driver_idx": 6,
    },
    {
        "reg": "MN34 UVW",
        "ref": "FLT-007",
        "type": "patrol_van",
        "make": "Peugeot",
        "model": "Expert",
        "year": 2023,
        "mileage": 12700,
        "loc_idx": 2,
        "driver_idx": 7,
    },
    # Edinburgh
    {
        "reg": "OP56 XYZ",
        "ref": "FLT-008",
        "type": "roadside_van",
        "make": "Ford",
        "model": "Transit",
        "year": 2019,
        "mileage": 98200,
        "loc_idx": 3,
        "driver_idx": 8,
    },
    # Bristol
    {
        "reg": "QR78 ABC",
        "ref": "FLT-009",
        "type": "roadside_van",
        "make": "Renault",
        "model": "Master",
        "year": 2022,
        "mileage": 37600,
        "loc_idx": 4,
        "driver_idx": 9,
    },
    # Retired vehicle
    {
        "reg": "ST90 DEF",
        "ref": "FLT-010",
        "type": "roadside_van",
        "make": "Ford",
        "model": "Transit",
        "year": 2016,
        "mileage": 142000,
        "loc_idx": 0,
        "driver_idx": None,
        "status": "retired",
        "retirement_reason": "High mileage – beyond economical repair",
    },
]

PAGES = [
    "/dashboard",
    "/vehicles",
    "/vehicles/1",
    "/vehicles/2",
    "/vehicles/3",
    "/mileage",
    "/mileage/log",
    "/maintenance",
    "/maintenance/create",
    "/admin/locations",
    "/admin/users",
    "/admin/categories",
    "/admin/audit-log",
    "/admin/page-visits",
    "/requests/retirement",
    "/requests/deletion",
    "/auth/profile",
]
# Page weights – dashboard and vehicles visited most
_PAGE_WEIGHTS = [25, 18, 8, 6, 5, 14, 10, 12, 6, 4, 3, 2, 5, 3, 4, 3, 6]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------
def seed():  # noqa: C901
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ---- Truncate all tables (order matters for FK constraints) ----
        print("Truncating tables …")
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

        # ---- Locations ----
        locations = []
        for data in LOCATIONS:
            loc = Location(**data)
            db.add(loc)
            locations.append(loc)
        db.flush()
        print(f"  Created {len(locations)} locations")

        # ---- Maintenance categories ----
        categories = []
        for data in CATEGORIES:
            cat = MaintenanceCategory(**data)
            db.add(cat)
            categories.append(cat)
        db.flush()
        print(f"  Created {len(categories)} maintenance categories")

        # ---- Users ----
        users = []
        for data in USERS:
            u = User(
                username=data["username"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                employee_number=data["employee_number"],
                location_id=locations[data["location_idx"]].id,
            )
            db.add(u)
            users.append(u)
        db.flush()
        admin_user = users[0]
        admin2 = users[1]
        drivers = [u for u in users if u.role == "standard"]
        print(f"  Created {len(users)} users ({len(drivers)} drivers, 2 admins)")

        # ---- Vehicles ----
        vehicles = []
        for data in VEHICLES:
            v = Vehicle(
                registration_number=data["reg"],
                fleet_reference=data["ref"],
                vehicle_type=data["type"],
                make=data["make"],
                model=data["model"],
                year=data["year"],
                current_mileage=data["mileage"],
                location_id=locations[data["loc_idx"]].id,
                primary_driver_user_id=(users[data["driver_idx"]].id if data.get("driver_idx") is not None else None),
                status=data.get("status", "active"),
                retirement_reason=data.get("retirement_reason"),
            )
            db.add(v)
            vehicles.append(v)
        db.flush()
        active_vehicles = [v for v in vehicles if v.status == "active"]
        print(
            f"  Created {len(vehicles)} vehicles"
            f" ({len(active_vehicles)} active,"
            f" {len(vehicles) - len(active_vehicles)} retired)"
        )

        # ---- Mileage records (6 months of weekly readings) ----
        mileage_count = 0
        for v in active_vehicles:
            driver = next(
                (u for u in users if v.primary_driver_user_id and u.id == v.primary_driver_user_id),
                random.choice(drivers),
            )
            base_mileage = max(v.current_mileage - 12000, 1000)
            step = (v.current_mileage - base_mileage) / 26
            current = base_mileage
            for week_offset in range(26, 0, -1):
                record_date = TODAY - timedelta(weeks=week_offset)
                current += step + random.randint(-80, 80)
                current = int(min(current, v.current_mileage))
                db.add(
                    MileageRecord(
                        vehicle_id=v.id,
                        recorded_by_user_id=driver.id,
                        reading_value=current,
                        recorded_at=_dt(record_date, random.randint(7, 17)),
                    )
                )
                mileage_count += 1
            # Final reading = current mileage
            db.add(
                MileageRecord(
                    vehicle_id=v.id,
                    recorded_by_user_id=driver.id,
                    reading_value=v.current_mileage,
                    recorded_at=_dt(TODAY - timedelta(days=random.randint(0, 2)), 10),
                )
            )
            mileage_count += 1
        db.flush()
        print(f"  Created {mileage_count} mileage records")

        # ---- Maintenance records (12 months of history) ----
        maint_count = 0
        cost_ranges = {
            "Oil Change": (80, 160),
            "Tyre Replacement": (200, 600),
            "Brake Service": (150, 400),
            "MOT": (40, 60),
            "Battery Replacement": (100, 220),
            "Other": (50, 500),
        }
        for v in vehicles:
            driver = next(
                (u for u in users if v.primary_driver_user_id and u.id == v.primary_driver_user_id),
                random.choice(drivers),
            )
            num_records = random.randint(3, 8)
            for _ in range(num_records):
                cat = random.choice(categories)
                days_ago = random.randint(5, 365)
                m_date = TODAY - timedelta(days=days_ago)
                mileage_then = max(v.current_mileage - (days_ago * random.randint(30, 80)), 1000)
                cost_lo, cost_hi = cost_ranges.get(cat.name, (50, 300))
                notes = None
                if cat.requires_notes:
                    notes = random.choice(
                        [
                            "Windscreen wiper replacement",
                            "Replaced wing mirror",
                            "Fixed interior light",
                            "Air conditioning regas",
                            "Replaced fuel filter",
                        ]
                    )
                db.add(
                    MaintenanceRecord(
                        vehicle_id=v.id,
                        category_id=cat.id,
                        logged_by_user_id=driver.id,
                        maintenance_date=m_date,
                        mileage_at_time=mileage_then,
                        cost=round(random.uniform(cost_lo, cost_hi), 2),
                        notes=notes,
                    )
                )
                maint_count += 1
        db.flush()
        print(f"  Created {maint_count} maintenance records")

        # ---- Retirement requests ----
        retired_v = next(v for v in vehicles if v.status == "retired")
        db.add(
            RetirementRequest(
                vehicle_id=retired_v.id,
                requested_by_user_id=admin_user.id,
                reason="Vehicle has exceeded 140,000 miles and repair costs are no longer viable.",
                status="approved",
                reviewed_by_user_id=admin2.id,
                review_notes="Approved – replacement vehicle ordered.",
                requested_at=_dt(TODAY - timedelta(days=45)),
                reviewed_at=_dt(TODAY - timedelta(days=43)),
            )
        )
        db.add(
            RetirementRequest(
                vehicle_id=vehicles[4].id,
                requested_by_user_id=drivers[2].id,
                reason="Engine warning light recurring, workshop recommends retirement.",
                status="pending",
                requested_at=_dt(TODAY - timedelta(days=3)),
            )
        )
        db.add(
            RetirementRequest(
                vehicle_id=vehicles[7].id,
                requested_by_user_id=drivers[6].id,
                reason="Gearbox failure – repair quote exceeds vehicle value.",
                status="pending",
                requested_at=_dt(TODAY - timedelta(days=1)),
            )
        )
        db.flush()
        print("  Created 3 retirement requests (1 approved, 2 pending)")

        # ---- Deletion requests ----
        db.add(
            DeletionRequest(
                target_type="mileage_record",
                target_id=3,
                requested_by_user_id=drivers[0].id,
                reason="Entered mileage for wrong vehicle by mistake.",
                status="pending",
                requested_at=_dt(TODAY - timedelta(days=2)),
            )
        )
        db.add(
            DeletionRequest(
                target_type="maintenance_record",
                target_id=5,
                requested_by_user_id=drivers[1].id,
                reason="Duplicate maintenance entry.",
                status="approved",
                reviewed_by_user_id=admin_user.id,
                review_notes="Confirmed duplicate – removed.",
                requested_at=_dt(TODAY - timedelta(days=10)),
                reviewed_at=_dt(TODAY - timedelta(days=9)),
            )
        )
        db.flush()
        print("  Created 2 deletion requests (1 approved, 1 pending)")

        # ---- Audit logs (3 months of history) ----
        audit_actions = [
            ("create", "vehicle", "Created vehicle {reg}"),
            ("update", "vehicle", "Updated vehicle {reg}"),
            ("create", "user", "Created user {name}"),
            ("update", "user", "Updated user {name}"),
            ("delete", "location", "Soft-deleted location"),
            ("create", "location", "Created location {loc}"),
            ("update", "location", "Updated location {loc}"),
            ("create", "category", "Created maintenance category"),
            ("approve", "retirement_request", "Approved retirement request"),
            ("reject", "retirement_request", "Rejected retirement request"),
            ("approve", "deletion_request", "Approved deletion request"),
            ("reject", "deletion_request", "Rejected deletion request"),
            ("unretire", "vehicle", "Reinstated vehicle {reg}"),
        ]
        audit_count = 0
        for days_ago in range(90, 0, -1):
            d = TODAY - timedelta(days=days_ago)
            if random.random() < 0.25:
                continue
            num_events = random.randint(1, 5)
            for _ in range(num_events):
                action, target_type, detail_tpl = random.choice(audit_actions)
                actor = random.choice([admin_user, admin2])
                detail = detail_tpl.format(
                    reg=random.choice(vehicles).registration_number,
                    name=random.choice(users).full_name,
                    loc=random.choice(locations).name,
                )
                db.add(
                    AuditLog(
                        action=action,
                        target_type=target_type,
                        target_id=random.randint(1, 10),
                        target_label=detail.split(" ")[-1] if len(detail.split()) > 2 else None,
                        details=detail,
                        user_id=actor.id,
                        created_at=_rand_time(d),
                    )
                )
                audit_count += 1
        db.flush()
        print(f"  Created {audit_count} audit log entries")

        # ---- Page visits (90 days – produces great charts) ----
        visit_count = 0
        all_user_ids = [u.id for u in users]
        for days_ago in range(90, 0, -1):
            d = TODAY - timedelta(days=days_ago)
            weekday = d.weekday()
            if weekday >= 5:
                base_visits = random.randint(5, 15)
            else:
                base_visits = random.randint(25, 60)
            # Gradual upward trend (busier recently)
            trend_multiplier = 0.7 + (0.6 * (90 - days_ago) / 90)
            num_visits = int(base_visits * trend_multiplier)
            for _ in range(num_visits):
                page = random.choices(PAGES, weights=_PAGE_WEIGHTS, k=1)[0]
                user_id = random.choice(all_user_ids)
                db.add(
                    PageVisit(
                        user_id=user_id,
                        path=page,
                        method="GET",
                        visited_at=_rand_time(d),
                    )
                )
                visit_count += 1
        # Today – burst of activity
        for _ in range(random.randint(30, 50)):
            page = random.choices(PAGES, weights=_PAGE_WEIGHTS, k=1)[0]
            user_id = random.choice(all_user_ids)
            db.add(
                PageVisit(
                    user_id=user_id,
                    path=page,
                    method="GET",
                    visited_at=_rand_time(TODAY),
                )
            )
            visit_count += 1
        db.flush()
        print(f"  Created {visit_count} page visit records")

        db.commit()
        print("\nSeed complete!")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

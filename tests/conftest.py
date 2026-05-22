import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.deletion_request import DeletionRequest  # noqa: F401
from app.models.location import Location
from app.models.maintenance import MaintenanceCategory, MaintenanceRecord  # noqa: F401
from app.models.mileage import MileageRecord  # noqa: F401
from app.models.page_visit import PageVisit  # noqa: F401
from app.models.retirement_request import RetirementRequest  # noqa: F401
from app.models.user import User
from app.models.vehicle import Vehicle
from app.security.password import hash_password

# Use in-memory SQLite with StaticPool for test isolation
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clear_lockouts():
    """Clear Redis login attempt counters between tests."""
    yield
    from app.services import session as session_service

    for username in ["testadmin", "testdriver", "admin@test.com", "driver@test.com"]:
        try:
            session_service.clear_login_attempts(username)
        except Exception:  # noqa: S110
            pass


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def location(db):
    loc = Location(name="Test Depot", code="TST", city="Testville")
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@pytest.fixture
def admin_user(db):
    user = User(
        username="testadmin",
        email="admin@test.com",
        password_hash=hash_password("password123"),
        role="admin",
        first_name="Test",
        last_name="Admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def standard_user(db, location):
    user = User(
        username="testdriver",
        email="driver@test.com",
        password_hash=hash_password("password123"),
        role="standard",
        first_name="Test",
        last_name="Driver",
        location_id=location.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def vehicle(db, location, standard_user):
    v = Vehicle(
        registration_number="XX11 YYY",
        fleet_reference="FLT-TEST-001",
        vehicle_type="roadside_van",
        make="Ford",
        model="Transit",
        year=2023,
        current_mileage=10000,
        location_id=location.id,
        primary_driver_user_id=standard_user.id,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@pytest.fixture
def category(db):
    cat = MaintenanceCategory(name="Test Category", requires_notes=False)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture
def category_with_notes(db):
    cat = MaintenanceCategory(name="Notes Required", requires_notes=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def login_user(client, username="testadmin", password="password123"):
    """Helper to log in and get the session cookie."""

    # Create session directly for testing
    from app.security.csrf import generate_csrf_token

    # Use the test client's login flow
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password, "csrf_token": generate_csrf_token()},
        follow_redirects=False,
    )
    if "session_id" in response.cookies:
        client.cookies.set("session_id", response.cookies["session_id"])
    return response

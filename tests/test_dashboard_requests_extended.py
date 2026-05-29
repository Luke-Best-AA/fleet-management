"""Tests for dashboard and request route edge cases."""

from datetime import date

from app.models.maintenance import MaintenanceRecord
from app.security.csrf import generate_csrf_token


class _Base:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])


class TestDashboard(_Base):
    def test_dashboard_unauthenticated(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302

    def test_admin_dashboard(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_standard_dashboard(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/dashboard")
        assert resp.status_code == 200


class TestRequestCSRF(_Base):
    def test_retirement_create_invalid_csrf(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.post(
            "/requests/retirement/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reason": "Too old",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_deletion_create_invalid_csrf(self, client, db, standard_user, vehicle, category):
        rec = MaintenanceRecord(
            vehicle_id=vehicle.id,
            category_id=category.id,
            notes="Test",
            mileage_at_time=10000,
            logged_by_user_id=standard_user.id,
            maintenance_date=date.today(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testdriver")
        resp = client.post(
            "/requests/deletion/create",
            data={
                "target_type": "maintenance",
                "target_id": str(rec.id),
                "reason": "Wrong entry",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_retirement_review_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        # Even with invalid ID, CSRF should be caught first
        resp = client.post(
            "/requests/retirement/99999/review",
            data={
                "action": "approve",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_deletion_review_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/requests/deletion/99999/review",
            data={
                "action": "approve",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestRequestCreatePages(_Base):
    def test_deletion_create_page_standard(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/requests/deletion/create")
        assert resp.status_code == 200

    def test_retirement_create_unauthenticated(self, client):
        resp = client.get("/requests/retirement/create", follow_redirects=False)
        assert resp.status_code == 302

    def test_deletion_create_unauthenticated(self, client):
        resp = client.get("/requests/deletion/create", follow_redirects=False)
        assert resp.status_code == 302

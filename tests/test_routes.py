"""Tests for route access control."""
import pytest
from app.security.csrf import generate_csrf_token


class TestRoleRestrictions:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_admin_can_access_admin_pages(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/locations")
        assert resp.status_code == 200

    def test_standard_cannot_access_admin_pages(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/locations")
        assert resp.status_code == 403

    def test_standard_cannot_create_vehicle(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/vehicles/create")
        assert resp.status_code == 403

    def test_admin_can_create_vehicle(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.get("/vehicles/create")
        assert resp.status_code == 200

    def test_standard_cannot_edit_mileage(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/mileage/999/edit")
        assert resp.status_code == 403

    def test_standard_cannot_delete_maintenance(self, client, standard_user):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/maintenance/999/delete",
            data={"csrf_token": token},
        )
        assert resp.status_code == 403

    def test_dashboard_shows_for_standard(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "My Assigned Vehicles" in resp.text

    def test_dashboard_shows_for_admin(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Total Vehicles" in resp.text


class TestValidationRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_register_password_mismatch(self, client):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/register",
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "password123",
                "password_confirm": "different123",
                "first_name": "Test",
                "last_name": "User",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "do not match" in resp.text

    def test_register_short_password(self, client):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/register",
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "short",
                "password_confirm": "short",
                "first_name": "Test",
                "last_name": "User",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "8 characters" in resp.text

    def test_vehicle_create_validation(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/vehicles/create",
            data={
                "registration_number": "",
                "fleet_reference": "",
                "vehicle_type": "invalid",
                "make": "",
                "model": "",
                "year": "0",
                "current_mileage": "0",
                "location_id": str(location.id),
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "required" in resp.text.lower() or "must be" in resp.text.lower()

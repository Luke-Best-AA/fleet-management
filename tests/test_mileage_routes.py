"""Tests for mileage routes."""
import pytest
from app.security.csrf import generate_csrf_token
from app.services import mileage as mileage_service


class TestMileageListRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_mileage_list_admin(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/mileage")
        assert resp.status_code == 200

    def test_mileage_list_standard(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/mileage")
        assert resp.status_code == 200

    def test_mileage_list_unauthenticated(self, client):
        resp = client.get("/mileage", follow_redirects=False)
        assert resp.status_code == 302


class TestMileageCreateRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_create_page(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/mileage/create")
        assert resp.status_code == 200

    def test_create_mileage_standard_user(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/mileage/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reading_value": "15000",
                "is_admin_override": "",
                "override_reason": "",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_create_mileage_lower_than_current_fails(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/mileage/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reading_value": "5000",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "at least" in resp.text.lower()

    def test_create_mileage_admin_override(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/mileage/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reading_value": "5000",
                "is_admin_override": "true",
                "override_reason": "Odometer replacement",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestMileageEditRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_edit_page_admin(self, client, admin_user, vehicle, db):
        rec = mileage_service.create_record(
            db, vehicle.id, admin_user.id, 15000,
            user_role="admin", user_id=admin_user.id,
        )
        self._login(client, "testadmin")
        resp = client.get(f"/mileage/{rec.id}/edit")
        assert resp.status_code == 200

    def test_edit_page_standard_forbidden(self, client, standard_user, vehicle, db):
        rec = mileage_service.create_record(
            db, vehicle.id, standard_user.id, 15000,
            user_role="standard", user_id=standard_user.id,
        )
        self._login(client, "testdriver")
        resp = client.get(f"/mileage/{rec.id}/edit")
        assert resp.status_code == 403

    def test_edit_mileage_admin(self, client, admin_user, vehicle, db):
        rec = mileage_service.create_record(
            db, vehicle.id, admin_user.id, 15000,
            user_role="admin", user_id=admin_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/mileage/{rec.id}/edit",
            data={
                "reading_value": "18000",
                "is_admin_override": "",
                "override_reason": "",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestMileageDeleteRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_delete_admin(self, client, admin_user, vehicle, db):
        rec = mileage_service.create_record(
            db, vehicle.id, admin_user.id, 15000,
            user_role="admin", user_id=admin_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/mileage/{rec.id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_standard_forbidden(self, client, standard_user, vehicle, db):
        rec = mileage_service.create_record(
            db, vehicle.id, standard_user.id, 15000,
            user_role="standard", user_id=standard_user.id,
        )
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            f"/mileage/{rec.id}/delete",
            data={"csrf_token": token},
        )
        assert resp.status_code == 403

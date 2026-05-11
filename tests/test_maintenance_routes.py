"""Tests for maintenance routes."""
import pytest
from datetime import date

from app.security.csrf import generate_csrf_token
from app.services import maintenance as maint_service


class TestMaintenanceListRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_list_admin(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/maintenance")
        assert resp.status_code == 200

    def test_list_standard(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/maintenance")
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client):
        resp = client.get("/maintenance", follow_redirects=False)
        assert resp.status_code == 302


class TestMaintenanceCreateRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_create_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/maintenance/create")
        assert resp.status_code == 200

    def test_create_record_admin(self, client, admin_user, vehicle, category):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/maintenance/create",
            data={
                "vehicle_id": str(vehicle.id),
                "category_id": str(category.id),
                "maintenance_date": str(date.today()),
                "mileage_at_time": "10000",
                "notes": "Routine check",
                "cost": "50.00",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_create_record_standard_user(self, client, standard_user, vehicle, category):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/maintenance/create",
            data={
                "vehicle_id": str(vehicle.id),
                "category_id": str(category.id),
                "maintenance_date": str(date.today()),
                "mileage_at_time": "10000",
                "notes": "",
                "cost": "",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_create_retired_vehicle_fails(self, client, admin_user, vehicle, category, db):
        vehicle.status = "retired"
        db.commit()
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/maintenance/create",
            data={
                "vehicle_id": str(vehicle.id),
                "category_id": str(category.id),
                "maintenance_date": str(date.today()),
                "mileage_at_time": "10000",
                "notes": "",
                "cost": "",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "retired" in resp.text.lower()


class TestMaintenanceEditRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_edit_page_admin(self, client, admin_user, vehicle, category, db):
        rec = maint_service.create_record(
            db, vehicle.id, category.id, admin_user.id,
            date.today(), 10000, user_role="admin",
        )
        self._login(client, "testadmin")
        resp = client.get(f"/maintenance/{rec.id}/edit")
        assert resp.status_code == 200

    def test_edit_page_standard_forbidden(self, client, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db, vehicle.id, category.id, standard_user.id,
            date.today(), 10000, user_role="standard", user_vehicle_id=standard_user.id,
        )
        self._login(client, "testdriver")
        resp = client.get(f"/maintenance/{rec.id}/edit")
        assert resp.status_code == 403

    def test_edit_record_admin(self, client, admin_user, vehicle, category, db):
        rec = maint_service.create_record(
            db, vehicle.id, category.id, admin_user.id,
            date.today(), 10000, user_role="admin",
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/maintenance/{rec.id}/edit",
            data={
                "category_id": str(category.id),
                "maintenance_date": str(date.today()),
                "mileage_at_time": "12000",
                "notes": "Updated notes",
                "cost": "75.00",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestMaintenanceDeleteRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_delete_admin(self, client, admin_user, vehicle, category, db):
        rec = maint_service.create_record(
            db, vehicle.id, category.id, admin_user.id,
            date.today(), 10000, user_role="admin",
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/maintenance/{rec.id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_standard_forbidden(self, client, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db, vehicle.id, category.id, standard_user.id,
            date.today(), 10000, user_role="standard", user_vehicle_id=standard_user.id,
        )
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            f"/maintenance/{rec.id}/delete",
            data={"csrf_token": token},
        )
        assert resp.status_code == 403

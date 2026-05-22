"""Tests for vehicle routes."""

import jinja2
import pytest

from app.security.csrf import generate_csrf_token
from app.services import vehicle as vehicle_service
from tests.conftest import login_user


class TestVehicleRoutes:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_vehicle_list_admin(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        resp = client.get("/vehicles")
        assert resp.status_code == 200
        assert "XX11 YYY" in resp.text

    def test_vehicle_list_standard_user(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/vehicles")
        assert resp.status_code == 200

    def test_vehicle_list_unauthenticated_redirects(self, client):
        resp = client.get("/vehicles", follow_redirects=False)
        assert resp.status_code == 302

    def test_vehicle_detail_admin(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        resp = client.get(f"/vehicles/{vehicle.id}")
        assert resp.status_code == 200
        assert "XX11 YYY" in resp.text

    def test_vehicle_detail_standard_user_assigned(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get(f"/vehicles/{vehicle.id}")
        assert resp.status_code == 200

    def test_vehicle_detail_standard_user_unassigned(self, client, db, standard_user, location):
        from app.services import vehicle as vehicle_service

        other_v = vehicle_service.create_vehicle(
            db,
            "AB12 CDE",
            "FLT-OTHER",
            "patrol_van",
            "Ford",
            "Transit",
            2023,
            location.id,
        )
        self._login(client, "testdriver")
        resp = client.get(f"/vehicles/{other_v.id}")
        assert resp.status_code == 403


class TestVehicleCreate:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_create_page_admin(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.get("/vehicles/create")
        assert resp.status_code == 200

    def test_create_page_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/vehicles/create")
        assert resp.status_code == 403

    def test_create_vehicle_success(self, client, admin_user, location, db):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/vehicles/create",
            data={
                "registration_number": "AB12 CDE",
                "fleet_reference": "FLT-NEW-001",
                "vehicle_type": "roadside_van",
                "make": "Ford",
                "model": "Transit",
                "year": "2023",
                "current_mileage": "0",
                "location_id": str(location.id),
                "primary_driver_user_id": "",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_create_vehicle_validation_error(self, client, admin_user, location):
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

    def test_create_vehicle_duplicate_registration(self, client, admin_user, vehicle, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/vehicles/create",
            data={
                "registration_number": "XX11 YYY",
                "fleet_reference": "FLT-DUP",
                "vehicle_type": "roadside_van",
                "make": "Ford",
                "model": "Transit",
                "year": "2023",
                "current_mileage": "0",
                "location_id": str(location.id),
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "already in use" in resp.text.lower()


class TestVehicleEdit:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_edit_page_admin(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        resp = client.get(f"/vehicles/{vehicle.id}/edit")
        assert resp.status_code == 200

    def test_edit_page_standard_forbidden(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get(f"/vehicles/{vehicle.id}/edit")
        assert resp.status_code == 403

    def test_edit_retired_vehicle_redirects(self, client, admin_user, vehicle, db):
        vehicle.status = "retired"
        db.commit()
        self._login(client, "testadmin")
        resp = client.get(f"/vehicles/{vehicle.id}/edit", follow_redirects=False)
        assert resp.status_code == 302

    def test_edit_vehicle_success(self, client, admin_user, vehicle, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/vehicles/{vehicle.id}/edit",
            data={
                "registration_number": "XX11 YYY",
                "fleet_reference": "FLT-TEST-001",
                "vehicle_type": "patrol_van",
                "make": "Vauxhall",
                "model": "Vivaro",
                "year": "2024",
                "location_id": str(location.id),
                "primary_driver_user_id": "",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestVehicleDelete:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_delete_vehicle_admin(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/vehicles/{vehicle.id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_vehicle_standard_forbidden(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            f"/vehicles/{vehicle.id}/delete",
            data={"csrf_token": token},
        )
        assert resp.status_code == 403


# --- Coverage tests merged from test_vehicles_coverage.py ---


class TestVehicleCreatePageCoverage:
    def test_create_page(self, client, db, admin_user, location):
        login_user(client, "testadmin", "password123")
        resp = client.get("/vehicles/create")
        assert resp.status_code == 200


class TestVehicleCreatePostCoverage:
    def test_csrf_failure(self, client, db, admin_user, location):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/vehicles/create",
            data={"csrf_token": "bad", "registration_number": "AB12 CDE"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text

    def test_validation_error(self, client, db, admin_user, location):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/vehicles/create",
            data={
                "csrf_token": generate_csrf_token(),
                "registration_number": "",
                "fleet_reference": "",
                "vehicle_type": "",
                "make": "",
                "model": "",
                "year": "",
                "location_id": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_success(self, client, db, admin_user, location, standard_user):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/vehicles/create",
            data={
                "csrf_token": generate_csrf_token(),
                "registration_number": "ZZ99 NEW",
                "fleet_reference": "FLT-NEW-001",
                "vehicle_type": "patrol_van",
                "make": "Ford",
                "model": "Transit",
                "year": "2024",
                "current_mileage": "0",
                "location_id": str(location.id),
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_duplicate_registration(self, client, db, admin_user, location, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/vehicles/create",
            data={
                "csrf_token": generate_csrf_token(),
                "registration_number": vehicle.registration_number,
                "fleet_reference": "FLT-DUP-001",
                "vehicle_type": "patrol_van",
                "make": "Ford",
                "model": "Transit",
                "year": "2024",
                "current_mileage": "0",
                "location_id": str(location.id),
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200


class TestVehicleDetailCoverage:
    def test_access_denied_wrong_user(self, client, db, admin_user, standard_user, location):
        from app.models.user import User
        from app.security.password import hash_password

        other_user = User(
            username="otherdriver",
            email="other@test.com",
            password_hash=hash_password("password123"),
            role="standard",
            first_name="Other",
            last_name="Driver",
            location_id=location.id,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        v = vehicle_service.create_vehicle(
            db,
            "AA11 BBB",
            "FLT-OTH-001",
            "patrol_van",
            "Ford",
            "Transit",
            2023,
            location.id,
            primary_driver_user_id=other_user.id,
        )
        login_user(client, "testdriver", "password123")
        resp = client.get(f"/vehicles/{v.id}")
        assert resp.status_code == 403


class TestVehicleEditPageCoverage:
    def test_retired_vehicle_redirected(self, client, db, admin_user, vehicle, location):
        vehicle_service.retire_vehicle(db, vehicle.id, "End of life")
        login_user(client, "testadmin", "password123")
        resp = client.get(f"/vehicles/{vehicle.id}/edit", follow_redirects=False)
        assert resp.status_code == 302

    def test_edit_page_success(self, client, db, admin_user, vehicle, location):
        login_user(client, "testadmin", "password123")
        resp = client.get(f"/vehicles/{vehicle.id}/edit")
        assert resp.status_code == 200


class TestVehicleEditPostCoverage:
    def test_csrf_failure(self, client, db, admin_user, vehicle, location):
        login_user(client, "testadmin", "password123")
        with pytest.raises(jinja2.exceptions.UndefinedError):
            client.post(
                f"/vehicles/{vehicle.id}/edit",
                data={"csrf_token": "bad"},
                follow_redirects=False,
            )

    def test_success(self, client, db, admin_user, vehicle, location):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/vehicles/{vehicle.id}/edit",
            data={
                "csrf_token": generate_csrf_token(),
                "registration_number": vehicle.registration_number,
                "fleet_reference": vehicle.fleet_reference,
                "vehicle_type": "patrol_van",
                "make": "Updated",
                "model": "Model",
                "year": "2024",
                "location_id": str(location.id),
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestVehicleDeletePostCoverage:
    def test_csrf_failure(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/vehicles/{vehicle.id}/delete",
            data={"csrf_token": "bad"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_success(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/vehicles/{vehicle.id}/delete",
            data={"csrf_token": generate_csrf_token()},
            follow_redirects=False,
        )
        assert resp.status_code == 303

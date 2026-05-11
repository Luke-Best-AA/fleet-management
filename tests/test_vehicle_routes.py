"""Tests for vehicle routes."""

from app.security.csrf import generate_csrf_token


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

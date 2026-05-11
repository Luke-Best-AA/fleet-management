"""Tests for retirement and deletion request routes."""

from datetime import date

from app.security.csrf import generate_csrf_token
from app.services import deletion as deletion_service
from app.services import maintenance as maint_service
from app.services import retirement as retirement_service


class _RequestTestBase:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])


class TestRetirementRequestRoutes(_RequestTestBase):
    def test_retirement_list_admin(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/requests/retirement")
        assert resp.status_code == 200

    def test_retirement_list_standard(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/requests/retirement")
        assert resp.status_code == 200

    def test_retirement_list_unauthenticated(self, client):
        resp = client.get("/requests/retirement", follow_redirects=False)
        assert resp.status_code == 302

    def test_retirement_create_page(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        resp = client.get("/requests/retirement/create")
        assert resp.status_code == 200

    def test_standard_user_creates_request(self, client, standard_user, vehicle):
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/requests/retirement/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reason": "Vehicle is too old and unreliable",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_admin_retires_directly(self, client, admin_user, vehicle):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/requests/retirement/create",
            data={
                "vehicle_id": str(vehicle.id),
                "reason": "Decommissioning this vehicle",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_retirement_detail_page(self, client, admin_user, vehicle, standard_user, db):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Too old",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        resp = client.get(f"/requests/retirement/{req.id}")
        assert resp.status_code == 200

    def test_approve_retirement(self, client, admin_user, vehicle, standard_user, db):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Old vehicle",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={
                "action": "approve",
                "review_notes": "Approved",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_reject_retirement(self, client, admin_user, vehicle, standard_user, db):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Want to retire",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={
                "action": "reject",
                "review_notes": "Still usable",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_review_standard_forbidden(self, client, standard_user, vehicle, db):
        req = retirement_service.create_request(
            db,
            vehicle.id,
            standard_user.id,
            "Retire",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={
                "action": "approve",
                "review_notes": "",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 403


class TestDeletionRequestRoutes(_RequestTestBase):
    def test_deletion_list_admin(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/requests/deletion")
        assert resp.status_code == 200

    def test_deletion_list_standard(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/requests/deletion")
        assert resp.status_code == 200

    def test_deletion_list_unauthenticated(self, client):
        resp = client.get("/requests/deletion", follow_redirects=False)
        assert resp.status_code == 302

    def test_deletion_create_page(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/requests/deletion/create")
        assert resp.status_code == 200

    def test_create_deletion_request(self, client, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            "/requests/deletion/create",
            data={
                "target_type": "maintenance_record",
                "target_id": str(rec.id),
                "reason": "Wrong entry",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_deletion_detail_page(self, client, admin_user, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        resp = client.get(f"/requests/deletion/{req.id}")
        assert resp.status_code == 200

    def test_approve_deletion(self, client, admin_user, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={
                "action": "approve",
                "review_notes": "Approved",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_reject_deletion(self, client, admin_user, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={
                "action": "reject",
                "review_notes": "Keep it",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_review_standard_forbidden(self, client, standard_user, vehicle, category, db):
        rec = maint_service.create_record(
            db,
            vehicle.id,
            category.id,
            standard_user.id,
            date.today(),
            10000,
            user_role="standard",
            user_vehicle_id=standard_user.id,
        )
        req = deletion_service.create_request(
            db,
            "maintenance_record",
            rec.id,
            standard_user.id,
            "Delete",
            user_role="standard",
            user_id=standard_user.id,
        )
        self._login(client, "testdriver")
        token = generate_csrf_token()
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={
                "action": "approve",
                "review_notes": "",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 403

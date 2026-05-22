"""Tests for retirement and deletion request routes."""

from datetime import date

from app.models.mileage import MileageRecord
from app.security.csrf import generate_csrf_token
from app.services import deletion as deletion_service
from app.services import maintenance as maint_service
from app.services import retirement as retirement_service
from tests.conftest import login_user


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


# --- Coverage tests merged from test_requests_coverage.py ---


class TestRetirementCreatePageCoverage:
    def test_admin_sees_all_vehicles(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.get("/requests/retirement/create")
        assert resp.status_code == 200

    def test_standard_user_sees_own_vehicles(self, client, db, admin_user, standard_user, vehicle):
        login_user(client, "testdriver", "password123")
        resp = client.get("/requests/retirement/create")
        assert resp.status_code == 200


class TestRetirementCreatePostCoverage:
    def test_csrf_failure(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/requests/retirement/create",
            data={"csrf_token": "bad", "vehicle_id": str(vehicle.id), "reason": "Old"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_validation_error(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/requests/retirement/create",
            data={"csrf_token": generate_csrf_token(), "vehicle_id": "", "reason": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_admin_direct_retire(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/requests/retirement/create",
            data={
                "csrf_token": generate_csrf_token(),
                "vehicle_id": str(vehicle.id),
                "reason": "End of life",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/vehicles" in resp.headers.get("location", "")

    def test_standard_user_creates_request(self, client, db, admin_user, standard_user, vehicle):
        login_user(client, "testdriver", "password123")
        resp = client.post(
            "/requests/retirement/create",
            data={
                "csrf_token": generate_csrf_token(),
                "vehicle_id": str(vehicle.id),
                "reason": "Too many breakdowns",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/requests/retirement" in resp.headers.get("location", "")


class TestRetirementReviewCoverage:
    def _create_request(self, db, vehicle, user):
        return retirement_service.create_request(
            db,
            vehicle_id=vehicle.id,
            requested_by_user_id=user.id,
            reason="Needs review",
            user_role="standard",
            user_id=user.id,
        )

    def test_non_admin_forbidden(self, client, db, admin_user, standard_user, vehicle):
        req = self._create_request(db, vehicle, standard_user)
        login_user(client, "testdriver", "password123")
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={"csrf_token": generate_csrf_token(), "action": "approve"},
            follow_redirects=False,
        )
        assert resp.status_code == 403

    def test_csrf_failure(self, client, db, admin_user, standard_user, vehicle):
        req = self._create_request(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={"csrf_token": "bad", "action": "approve"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_approve(self, client, db, admin_user, standard_user, vehicle):
        req = self._create_request(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={
                "csrf_token": generate_csrf_token(),
                "action": "approve",
                "review_notes": "Approved ok",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_reject(self, client, db, admin_user, standard_user, vehicle):
        req = self._create_request(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/retirement/{req.id}/review",
            data={
                "csrf_token": generate_csrf_token(),
                "action": "reject",
                "review_notes": "Not yet",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestRetirementReviewPageCoverage:
    def test_detail_page(self, client, db, admin_user, standard_user, vehicle):
        req = retirement_service.create_request(
            db,
            vehicle_id=vehicle.id,
            requested_by_user_id=standard_user.id,
            reason="Check",
            user_role="standard",
            user_id=standard_user.id,
        )
        login_user(client, "testadmin", "password123")
        resp = client.get(f"/requests/retirement/{req.id}")
        assert resp.status_code == 200


class TestDeletionCreatePostCoverage:
    def _make_mileage(self, db, vehicle, user):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            recorded_by_user_id=user.id,
            reading_value=20000,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    def test_csrf_failure(self, client, db, admin_user, vehicle):
        rec = self._make_mileage(db, vehicle, admin_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/requests/deletion/create",
            data={
                "csrf_token": "bad",
                "target_type": "mileage_record",
                "target_id": str(rec.id),
                "reason": "Wrong",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_validation_error(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.post(
            "/requests/deletion/create",
            data={
                "csrf_token": generate_csrf_token(),
                "target_type": "",
                "target_id": "",
                "reason": "",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_success(self, client, db, admin_user, standard_user, vehicle):
        rec = self._make_mileage(db, vehicle, standard_user)
        login_user(client, "testdriver", "password123")
        resp = client.post(
            "/requests/deletion/create",
            data={
                "csrf_token": generate_csrf_token(),
                "target_type": "mileage_record",
                "target_id": str(rec.id),
                "reason": "Wrong entry",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestDeletionReviewCoverage:
    def _setup_deletion(self, db, vehicle, user):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            recorded_by_user_id=user.id,
            reading_value=20000,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return deletion_service.create_request(
            db,
            target_type="mileage_record",
            target_id=rec.id,
            requested_by_user_id=user.id,
            reason="Wrong",
            user_role=user.role,
            user_id=user.id,
        )

    def test_non_admin_forbidden(self, client, db, admin_user, standard_user, vehicle):
        req = self._setup_deletion(db, vehicle, standard_user)
        login_user(client, "testdriver", "password123")
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={"csrf_token": generate_csrf_token(), "action": "approve"},
            follow_redirects=False,
        )
        assert resp.status_code == 403

    def test_csrf_failure(self, client, db, admin_user, standard_user, vehicle):
        req = self._setup_deletion(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={"csrf_token": "bad", "action": "approve"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_approve(self, client, db, admin_user, standard_user, vehicle):
        req = self._setup_deletion(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={
                "csrf_token": generate_csrf_token(),
                "action": "approve",
                "review_notes": "OK",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_reject(self, client, db, admin_user, standard_user, vehicle):
        req = self._setup_deletion(db, vehicle, standard_user)
        login_user(client, "testadmin", "password123")
        resp = client.post(
            f"/requests/deletion/{req.id}/review",
            data={
                "csrf_token": generate_csrf_token(),
                "action": "reject",
                "review_notes": "No",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestDeletionDetailPageCoverage:
    def test_detail(self, client, db, admin_user, standard_user, vehicle):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            recorded_by_user_id=standard_user.id,
            reading_value=20000,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        req = deletion_service.create_request(
            db,
            target_type="mileage_record",
            target_id=rec.id,
            requested_by_user_id=standard_user.id,
            reason="Mistake",
            user_role="standard",
            user_id=standard_user.id,
        )
        login_user(client, "testadmin", "password123")
        resp = client.get(f"/requests/deletion/{req.id}")
        assert resp.status_code == 200


class TestDeletionCreatePageCoverage:
    def test_admin_create_page(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.get("/requests/deletion/create")
        assert resp.status_code == 200

    def test_standard_user_create_page(self, client, db, admin_user, standard_user, vehicle):
        login_user(client, "testdriver", "password123")
        resp = client.get("/requests/deletion/create")
        assert resp.status_code == 200

    def test_with_return_to(self, client, db, admin_user, vehicle):
        login_user(client, "testadmin", "password123")
        resp = client.get(f"/requests/deletion/create?return_to=vehicles&return_id={vehicle.id}")
        assert resp.status_code == 200

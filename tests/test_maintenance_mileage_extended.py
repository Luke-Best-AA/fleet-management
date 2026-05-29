"""Extended tests for maintenance and mileage routes — detail, CSRF, error paths."""

from datetime import date

from app.models.maintenance import MaintenanceRecord
from app.models.mileage import MileageRecord
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


class TestMaintenanceDetail(_Base):
    def test_detail_page_admin(self, client, db, admin_user, vehicle, category):
        rec = MaintenanceRecord(
            vehicle_id=vehicle.id,
            category_id=category.id,
            notes="Oil change",
            mileage_at_time=10000,
            logged_by_user_id=admin_user.id,
            maintenance_date=date.today(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.get(f"/maintenance/{rec.id}")
        assert resp.status_code == 200

    def test_detail_not_found(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/maintenance/99999")
        assert resp.status_code == 404


class TestMaintenanceCreateErrors(_Base):
    def test_create_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/maintenance/create",
            data={
                "vehicle_id": "1",
                "category_id": "1",
                "notes": "Test",
                "mileage_at_time": "10000",
                "csrf_token": "bad",
            },
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text


class TestMaintenanceEditErrors(_Base):
    def test_edit_invalid_csrf(self, client, db, admin_user, vehicle, category):
        rec = MaintenanceRecord(
            vehicle_id=vehicle.id,
            category_id=category.id,
            notes="Test",
            mileage_at_time=10000,
            logged_by_user_id=admin_user.id,
            maintenance_date=date.today(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.post(
            f"/maintenance/{rec.id}/edit",
            data={
                "category_id": str(category.id),
                "notes": "Updated",
                "mileage_at_time": "11000",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_invalid_csrf(self, client, db, admin_user, vehicle, category):
        rec = MaintenanceRecord(
            vehicle_id=vehicle.id,
            category_id=category.id,
            notes="Test",
            mileage_at_time=10000,
            logged_by_user_id=admin_user.id,
            maintenance_date=date.today(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.post(
            f"/maintenance/{rec.id}/delete",
            data={"csrf_token": "bad"},
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestMileageDetail(_Base):
    def test_detail_page_admin(self, client, db, admin_user, vehicle):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            reading_value=12000,
            recorded_by_user_id=admin_user.id,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.get(f"/mileage/{rec.id}")
        assert resp.status_code == 200

    def test_detail_not_found(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/mileage/99999")
        assert resp.status_code == 404


class TestMileageCreateErrors(_Base):
    def test_create_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/mileage/create",
            data={
                "vehicle_id": "1",
                "reading_value": "15000",
                "csrf_token": "bad",
            },
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text


class TestMileageEditErrors(_Base):
    def test_edit_invalid_csrf(self, client, db, admin_user, vehicle):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            reading_value=12000,
            recorded_by_user_id=admin_user.id,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.post(
            f"/mileage/{rec.id}/edit",
            data={
                "reading_value": "13000",
                "csrf_token": "bad",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_invalid_csrf(self, client, db, admin_user, vehicle):
        rec = MileageRecord(
            vehicle_id=vehicle.id,
            reading_value=12000,
            recorded_by_user_id=admin_user.id,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        self._login(client, "testadmin")
        resp = client.post(
            f"/mileage/{rec.id}/delete",
            data={"csrf_token": "bad"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

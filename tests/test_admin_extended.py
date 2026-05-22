"""Extended tests for admin routes — categories, users, audit log, page visits."""

from app.models.user import User
from app.security.csrf import generate_csrf_token
from app.security.password import hash_password


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


class TestCategoryEditRoutes(_Base):
    def test_category_edit_page(self, client, admin_user, category):
        self._login(client, "testadmin")
        resp = client.get(f"/admin/categories/{category.id}/edit")
        assert resp.status_code == 200
        assert "Test Category" in resp.text

    def test_category_edit_success(self, client, admin_user, category):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/categories/{category.id}/edit",
            data={
                "name": "Updated Category",
                "description": "Desc",
                "requires_notes": "true",
                "is_active": "true",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_category_edit_duplicate_name(self, client, db, admin_user, category):
        from app.models.maintenance import MaintenanceCategory

        other = MaintenanceCategory(name="Other Cat", requires_notes=False)
        db.add(other)
        db.commit()
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/categories/{category.id}/edit",
            data={
                "name": "Other Cat",
                "description": "",
                "is_active": "true",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200  # Re-renders with error

    def test_category_delete(self, client, admin_user, category):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/categories/{category.id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestUserAdminExtended(_Base):
    def test_user_detail_page(self, client, admin_user, standard_user):
        self._login(client, "testadmin")
        resp = client.get(f"/admin/users/{standard_user.id}")
        assert resp.status_code == 200
        assert "testdriver" in resp.text

    def test_user_detail_not_found(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/users/99999")
        assert resp.status_code == 404

    def test_user_edit_page(self, client, admin_user, standard_user):
        self._login(client, "testadmin")
        resp = client.get(f"/admin/users/{standard_user.id}/edit")
        assert resp.status_code == 200
        assert "testdriver" in resp.text

    def test_user_edit_success(self, client, db, admin_user, location):
        target = User(
            username="editme",
            email="editme@test.com",
            password_hash=hash_password("password123"),
            role="standard",
            first_name="Edit",
            last_name="Me",
            location_id=location.id,
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/users/{target.id}/edit",
            data={
                "first_name": "Updated",
                "last_name": "User",
                "email": "updated@test.com",
                "employee_number": "EMP099",
                "location_id": str(location.id),
                "is_active": "true",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_user_edit_duplicate_email(self, client, db, admin_user, standard_user, location):
        other = User(
            username="other",
            email="other@test.com",
            password_hash=hash_password("password123"),
            role="standard",
            first_name="Other",
            last_name="User",
            location_id=location.id,
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/users/{other.id}/edit",
            data={
                "first_name": "Other",
                "last_name": "User",
                "email": "driver@test.com",  # same as standard_user
                "employee_number": "",
                "location_id": str(location.id),
                "is_active": "true",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200  # Re-renders with error

    def test_user_list_with_role_filter(self, client, admin_user, standard_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/users?role=standard")
        assert resp.status_code == 200


class TestAuditLogRoutes(_Base):
    def test_audit_log_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/audit-log")
        assert resp.status_code == 200
        assert "Audit" in resp.text

    def test_audit_log_pagination(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/audit-log?page=2")
        assert resp.status_code == 200

    def test_audit_log_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/audit-log")
        assert resp.status_code == 403


class TestPageVisitRoutes(_Base):
    def test_page_visits_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/page-visits")
        assert resp.status_code == 200

    def test_page_visits_with_filters(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/page-visits?days=30&page=1")
        assert resp.status_code == 200

    def test_page_visits_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/page-visits")
        assert resp.status_code == 403

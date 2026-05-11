"""Tests for admin routes (locations, categories, users)."""

from app.security.csrf import generate_csrf_token


class _AdminTestBase:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])


class TestLocationAdminRoutes(_AdminTestBase):
    def test_location_list(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.get("/admin/locations")
        assert resp.status_code == 200
        assert "Test Depot" in resp.text

    def test_location_list_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/locations")
        assert resp.status_code == 403

    def test_location_create_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/locations/create")
        assert resp.status_code == 200

    def test_location_create_success(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/admin/locations/create",
            data={
                "name": "New Depot",
                "code": "NEW",
                "region": "North",
                "address_line_1": "123 Street",
                "address_line_2": "",
                "city": "London",
                "postcode": "SW1A 1AA",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_location_create_duplicate_name(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/admin/locations/create",
            data={
                "name": "Test Depot",
                "code": "DUP",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "already in use" in resp.text.lower()

    def test_location_edit_page(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.get(f"/admin/locations/{location.id}/edit")
        assert resp.status_code == 200

    def test_location_edit_success(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/locations/{location.id}/edit",
            data={
                "name": "Renamed Depot",
                "code": "TST",
                "region": "",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "postcode": "",
                "is_active": "true",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_location_delete(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            f"/admin/locations/{location.id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303


class TestCategoryAdminRoutes(_AdminTestBase):
    def test_category_list(self, client, admin_user, category):
        self._login(client, "testadmin")
        resp = client.get("/admin/categories")
        assert resp.status_code == 200
        assert "Test Category" in resp.text

    def test_category_list_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/categories")
        assert resp.status_code == 403

    def test_category_create_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/categories/create")
        assert resp.status_code == 200

    def test_category_create_success(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/admin/categories/create",
            data={
                "name": "Oil Change",
                "description": "Regular oil change",
                "requires_notes": "false",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_category_create_duplicate(self, client, admin_user, category):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/admin/categories/create",
            data={
                "name": "Test Category",
                "description": "",
                "requires_notes": "false",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "already in use" in resp.text.lower()


class TestUserAdminRoutes(_AdminTestBase):
    def test_user_list(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/users")
        assert resp.status_code == 200

    def test_user_list_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.get("/admin/users")
        assert resp.status_code == 403

    def test_user_create_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/admin/users/create")
        assert resp.status_code == 200

    def test_user_create_success(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/admin/users/create",
            data={
                "username": "newdriver",
                "email": "newdriver@test.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "Driver",
                "role": "standard",
                "employee_number": "",
                "location_id": str(location.id),
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

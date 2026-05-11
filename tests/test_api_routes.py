"""Tests for API routes (inline AJAX endpoints)."""

from app.security.csrf import generate_csrf_token


class TestDriverAPI:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_create_driver_admin(self, client, admin_user, location):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/api/drivers",
            json={
                "username": "apidriver",
                "email": "apidriver@test.com",
                "password": "password123",
                "first_name": "API",
                "last_name": "Driver",
                "role": "standard",
                "employee_number": "",
                "location_id": location.id,
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "label" in data
        assert "API Driver" in data["label"]

    def test_create_driver_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.post(
            "/api/drivers",
            json={
                "username": "newdriver",
                "email": "new@test.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "Driver",
                "csrf_token": generate_csrf_token(),
            },
        )
        assert resp.status_code == 403

    def test_create_driver_duplicate_username(self, client, admin_user, standard_user, location):
        self._login(client, "testadmin")
        resp = client.post(
            "/api/drivers",
            json={
                "username": "testdriver",
                "email": "another@test.com",
                "password": "password123",
                "first_name": "Dup",
                "last_name": "User",
                "role": "standard",
                "location_id": location.id,
                "csrf_token": generate_csrf_token(),
            },
        )
        assert resp.status_code == 422

    def test_create_driver_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/api/drivers",
            json={
                "username": "badcsrf",
                "email": "bad@test.com",
                "password": "password123",
                "first_name": "Bad",
                "last_name": "CSRF",
                "csrf_token": "invalid",
            },
        )
        assert resp.status_code == 400


class TestLocationAPI:
    def _login(self, client, username, password="password123"):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={"username": username, "password": password, "csrf_token": token},
            follow_redirects=False,
        )
        if "session_id" in resp.cookies:
            client.cookies.set("session_id", resp.cookies["session_id"])

    def test_create_location_admin(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/api/locations",
            json={
                "name": "API Depot",
                "code": "API",
                "region": "",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "postcode": "",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "API Depot" in data["label"]

    def test_create_location_standard_forbidden(self, client, standard_user):
        self._login(client, "testdriver")
        resp = client.post(
            "/api/locations",
            json={
                "name": "Forbidden Depot",
                "code": "FBD",
                "csrf_token": generate_csrf_token(),
            },
        )
        assert resp.status_code == 403

    def test_create_location_duplicate_name(self, client, admin_user, location):
        self._login(client, "testadmin")
        resp = client.post(
            "/api/locations",
            json={
                "name": "Test Depot",
                "code": "DUP",
                "csrf_token": generate_csrf_token(),
            },
        )
        assert resp.status_code == 422

    def test_create_location_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/api/locations",
            json={
                "name": "CSRF Depot",
                "code": "CSR",
                "csrf_token": "invalid",
            },
        )
        assert resp.status_code == 400

"""Extended tests for auth routes — profile, password change, login edge cases."""

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


class TestLoginEdgeCases(_Base):
    def test_login_page_redirects_when_authenticated(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/auth/login", follow_redirects=False)
        assert resp.status_code == 302

    def test_login_with_next_param(self, client):
        resp = client.get("/auth/login?next=/vehicles")
        assert resp.status_code == 200
        assert "/vehicles" in resp.text

    def test_login_with_password_changed_param(self, client):
        resp = client.get("/auth/login?password_changed=1")
        assert resp.status_code == 200
        assert "Password changed" in resp.text

    def test_login_redirects_to_next(self, client, admin_user):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={
                "username": "testadmin",
                "password": "password123",
                "csrf_token": token,
                "next": "/vehicles",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/vehicles"

    def test_login_blocks_open_redirect(self, client, admin_user):
        token = generate_csrf_token()
        resp = client.post(
            "/auth/login",
            data={
                "username": "testadmin",
                "password": "password123",
                "csrf_token": token,
                "next": "https://evil.com",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"

    def test_login_invalid_csrf(self, client, admin_user):
        resp = client.post(
            "/auth/login",
            data={
                "username": "testadmin",
                "password": "password123",
                "csrf_token": "invalid",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text


class TestProfileRoutes(_Base):
    def test_profile_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/auth/profile")
        assert resp.status_code == 200
        assert "testadmin" in resp.text or "Test" in resp.text

    def test_profile_unauthenticated(self, client):
        resp = client.get("/auth/profile", follow_redirects=False)
        assert resp.status_code == 302

    def test_profile_edit_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/auth/profile/edit")
        assert resp.status_code == 200

    def test_profile_edit_success(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/auth/profile/edit",
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@test.com",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_profile_edit_missing_fields(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/auth/profile/edit",
            data={
                "first_name": "",
                "last_name": "",
                "email": "",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "required" in resp.text.lower()

    def test_profile_edit_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/auth/profile/edit",
            data={
                "first_name": "A",
                "last_name": "B",
                "email": "a@b.com",
                "csrf_token": "bad",
            },
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text

    def test_profile_edit_unauthenticated(self, client):
        resp = client.get("/auth/profile/edit", follow_redirects=False)
        assert resp.status_code == 302


class TestChangePasswordRoutes(_Base):
    def test_change_password_page(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/auth/change-password")
        assert resp.status_code == 200

    def test_change_password_unauthenticated(self, client):
        resp = client.get("/auth/change-password", follow_redirects=False)
        assert resp.status_code == 302

    def test_change_password_success(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "password123",
                "new_password": "newpassword456",
                "new_password_confirm": "newpassword456",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "password_changed" in resp.headers["location"]

    def test_change_password_wrong_current(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
                "new_password_confirm": "newpassword456",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200
        assert "incorrect" in resp.text.lower() or "Current password" in resp.text

    def test_change_password_mismatch(self, client, admin_user):
        self._login(client, "testadmin")
        token = generate_csrf_token()
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "password123",
                "new_password": "newpassword456",
                "new_password_confirm": "differentpassword",
                "csrf_token": token,
            },
        )
        assert resp.status_code == 200

    def test_change_password_invalid_csrf(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "password123",
                "new_password": "newpassword456",
                "new_password_confirm": "newpassword456",
                "csrf_token": "bad",
            },
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text


class TestRegisterEdgeCases(_Base):
    def test_register_redirects_when_authenticated(self, client, admin_user):
        self._login(client, "testadmin")
        resp = client.get("/auth/register", follow_redirects=False)
        assert resp.status_code == 302

    def test_register_invalid_csrf(self, client):
        resp = client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password": "password123",
                "password_confirm": "password123",
                "first_name": "New",
                "last_name": "User",
                "csrf_token": "invalid",
            },
        )
        assert resp.status_code == 200
        assert "Invalid request" in resp.text

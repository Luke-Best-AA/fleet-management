"""Tests for authentication flows and session behaviour."""

from app.security.csrf import generate_csrf_token
from app.security.password import hash_password, verify_password
from app.services.session import (
    clear_login_attempts,
    create_session,
    destroy_session,
    get_session,
    invalidate_user_sessions,
    is_locked_out,
    record_failed_login,
    redis_client,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt generates unique salts


class TestCSRF:
    def test_generate_and_validate(self):
        from app.security.csrf import validate_csrf_token

        token = generate_csrf_token()
        assert validate_csrf_token(token)

    def test_invalid_token(self):
        from app.security.csrf import validate_csrf_token

        assert not validate_csrf_token("")
        assert not validate_csrf_token("invalid")
        assert not validate_csrf_token("a:b:c")


class TestSession:
    def setup_method(self):
        # Clean up test keys
        for key in redis_client.scan_iter("session:test_*"):
            redis_client.delete(key)
        for key in redis_client.scan_iter("user_session:999*"):
            redis_client.delete(key)

    def test_create_and_get(self):
        sid = create_session(99901, {"username": "test", "role": "admin", "first_name": "T"})
        data = get_session(sid)
        assert data is not None
        assert data["username"] == "test"
        assert data["role"] == "admin"

    def test_destroy(self):
        sid = create_session(99902, {"username": "test2", "role": "standard", "first_name": "T"})
        destroy_session(sid)
        assert get_session(sid) is None

    def test_single_session_per_user(self):
        sid1 = create_session(99903, {"username": "u", "role": "standard", "first_name": "U"})
        sid2 = create_session(99903, {"username": "u", "role": "standard", "first_name": "U"})
        assert get_session(sid1) is None  # Old session invalidated
        assert get_session(sid2) is not None

    def test_invalidate_user_sessions(self):
        sid = create_session(99904, {"username": "u2", "role": "admin", "first_name": "U"})
        invalidate_user_sessions(99904)
        assert get_session(sid) is None


class TestLockout:
    def setup_method(self):
        clear_login_attempts("locktest")

    def test_not_locked_initially(self):
        assert not is_locked_out("locktest")

    def test_lockout_after_max_attempts(self):
        for _ in range(5):
            record_failed_login("locktest")
        assert is_locked_out("locktest")

    def test_clear_attempts(self):
        for _ in range(5):
            record_failed_login("locktest")
        clear_login_attempts("locktest")
        assert not is_locked_out("locktest")


class TestAuthRoutes:
    def test_login_page_loads(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "Login" in response.text

    def test_register_page_loads(self, client):
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert "Create Account" in response.text

    def test_register_and_login(self, client):
        token = generate_csrf_token()
        response = client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password": "password123",
                "password_confirm": "password123",
                "first_name": "New",
                "last_name": "User",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "session_id" in response.cookies

    def test_login_with_valid_credentials(self, client, admin_user):
        token = generate_csrf_token()
        response = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "password123", "csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "session_id" in response.cookies

    def test_login_with_invalid_credentials(self, client, admin_user):
        token = generate_csrf_token()
        response = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "wrongpassword", "csrf_token": token},
        )
        assert response.status_code == 200
        assert "Invalid username or password" in response.text

    def test_logout(self, client, admin_user):
        # Login first
        token = generate_csrf_token()
        login_resp = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "password123", "csrf_token": token},
            follow_redirects=False,
        )
        client.cookies.set("session_id", login_resp.cookies.get("session_id"))

        # Logout
        token2 = generate_csrf_token()
        response = client.post(
            "/auth/logout",
            data={"csrf_token": token2},
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_register_duplicate_username(self, client, admin_user):
        token = generate_csrf_token()
        response = client.post(
            "/auth/register",
            data={
                "username": "testadmin",
                "email": "other@test.com",
                "password": "password123",
                "password_confirm": "password123",
                "first_name": "Dup",
                "last_name": "User",
                "csrf_token": token,
            },
        )
        assert response.status_code == 200
        assert "already taken" in response.text.lower() or "already" in response.text.lower()

    def test_unauthenticated_redirect(self, client):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302

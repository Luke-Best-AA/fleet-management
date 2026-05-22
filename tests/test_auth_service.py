"""Tests for app.services.auth service."""

import pytest

from app.exceptions import AuthenticationError, LockedOutError
from app.models.user import User
from app.security.password import hash_password
from app.services import auth as auth_service
from app.services import session as session_service


@pytest.fixture(autouse=True)
def _clear_lockout():
    """Clear any lockout state before and after each test."""
    for username in ("testadmin", "inactive", "nonexistent"):
        session_service.clear_login_attempts(username)
    yield
    for username in ("testadmin", "inactive", "nonexistent"):
        session_service.clear_login_attempts(username)


class TestAuthenticate:
    def test_valid_credentials(self, db, admin_user):
        user = auth_service.authenticate(db, "testadmin", "password123")
        assert user.id == admin_user.id

    def test_invalid_username(self, db, admin_user):
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            auth_service.authenticate(db, "nonexistent", "password123")

    def test_invalid_password(self, db, admin_user):
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            auth_service.authenticate(db, "testadmin", "wrongpassword")

    def test_inactive_user(self, db):
        user = User(
            username="inactive",
            email="inactive@test.com",
            password_hash=hash_password("password123"),
            role="standard",
            first_name="In",
            last_name="Active",
            is_active=False,
        )
        db.add(user)
        db.commit()
        with pytest.raises(AuthenticationError, match="deactivated"):
            auth_service.authenticate(db, "inactive", "password123")

    def test_lockout_after_max_attempts(self, db, admin_user):
        for _ in range(5):
            try:
                auth_service.authenticate(db, "testadmin", "wrong")
            except AuthenticationError:
                pass
        with pytest.raises(LockedOutError, match="locked"):
            auth_service.authenticate(db, "testadmin", "password123")


class TestLogin:
    def test_returns_session_and_user(self, db, admin_user):
        session_id, user = auth_service.login(db, "testadmin", "password123")
        assert session_id is not None
        assert user.id == admin_user.id

    def test_session_has_data(self, db, admin_user):
        session_id, _ = auth_service.login(db, "testadmin", "password123")
        data = session_service.get_session(session_id)
        assert data is not None
        assert data["username"] == "testadmin"


class TestLogout:
    def test_destroys_session(self, db, admin_user):
        session_id, _ = auth_service.login(db, "testadmin", "password123")
        auth_service.logout(session_id)
        assert session_service.get_session(session_id) is None


class TestChangePassword:
    def test_changes_password(self, db, admin_user):
        auth_service.change_password(db, admin_user.id, "password123", "newpassword456")
        # Old password should fail
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(db, "testadmin", "password123")
        # New password should work
        user = auth_service.authenticate(db, "testadmin", "newpassword456")
        assert user.id == admin_user.id

    def test_wrong_current_password(self, db, admin_user):
        with pytest.raises(AuthenticationError, match="Current password is incorrect"):
            auth_service.change_password(db, admin_user.id, "wrongcurrent", "newpassword456")

    def test_invalidates_sessions(self, db, admin_user):
        session_id, _ = auth_service.login(db, "testadmin", "password123")
        auth_service.change_password(db, admin_user.id, "password123", "newpassword456")
        assert session_service.get_session(session_id) is None

    def test_nonexistent_user(self, db):
        with pytest.raises(AuthenticationError, match="User not found"):
            auth_service.change_password(db, 99999, "old", "new")

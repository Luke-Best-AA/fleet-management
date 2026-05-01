"""Tests for user service layer."""
import pytest

from app.exceptions import (
    AuthorisationError,
    ConflictError,
    NotFoundError,
)
from app.services import user as user_service


class TestGetUserById:
    def test_returns_user(self, db, admin_user):
        result = user_service.get_user_by_id(db, admin_user.id)
        assert result.username == "testadmin"

    def test_raises_not_found(self, db):
        with pytest.raises(NotFoundError, match="User not found"):
            user_service.get_user_by_id(db, 9999)


class TestGetAllUsers:
    def test_returns_all(self, db, admin_user, standard_user):
        users = user_service.get_all_users(db)
        assert len(users) == 2

    def test_ordered_by_username(self, db, admin_user, standard_user):
        users = user_service.get_all_users(db)
        assert users[0].username == "testadmin"
        assert users[1].username == "testdriver"


class TestGetStandardUsers:
    def test_returns_standard_only(self, db, admin_user, standard_user):
        users = user_service.get_standard_users(db)
        assert len(users) == 1
        assert users[0].role == "standard"

    def test_active_only_default(self, db, standard_user):
        standard_user.is_active = False
        db.commit()
        users = user_service.get_standard_users(db)
        assert len(users) == 0

    def test_include_inactive(self, db, standard_user):
        standard_user.is_active = False
        db.commit()
        users = user_service.get_standard_users(db, active_only=False)
        assert len(users) == 1


class TestCreateUser:
    def test_create_standard_user(self, db):
        user = user_service.create_user(
            db, username="newuser", email="new@test.com",
            password="password123", first_name="New", last_name="User",
        )
        assert user.id is not None
        assert user.role == "standard"
        assert user.is_active is True

    def test_create_admin_by_admin(self, db):
        user = user_service.create_user(
            db, username="newadmin", email="newadmin@test.com",
            password="password123", first_name="New", last_name="Admin",
            role="admin", requesting_user_role="admin",
        )
        assert user.role == "admin"

    def test_create_admin_by_standard_fails(self, db):
        with pytest.raises(AuthorisationError):
            user_service.create_user(
                db, username="sneaky", email="sneaky@test.com",
                password="password123", first_name="S", last_name="A",
                role="admin", requesting_user_role="standard",
            )

    def test_duplicate_username_fails(self, db, admin_user):
        with pytest.raises(ConflictError, match="Username already taken"):
            user_service.create_user(
                db, username="testadmin", email="other@test.com",
                password="password123", first_name="D", last_name="U",
            )

    def test_duplicate_email_fails(self, db, admin_user):
        with pytest.raises(ConflictError, match="Email already in use"):
            user_service.create_user(
                db, username="newuser", email="admin@test.com",
                password="password123", first_name="D", last_name="U",
            )

    def test_duplicate_employee_number_fails(self, db):
        user_service.create_user(
            db, username="user1", email="u1@test.com",
            password="password123", first_name="U", last_name="1",
            employee_number="EMP001",
        )
        with pytest.raises(ConflictError, match="Employee number"):
            user_service.create_user(
                db, username="user2", email="u2@test.com",
                password="password123", first_name="U", last_name="2",
                employee_number="EMP001",
            )

    def test_empty_employee_number_ok(self, db):
        user = user_service.create_user(
            db, username="nonum", email="nonum@test.com",
            password="password123", first_name="N", last_name="N",
            employee_number="",
        )
        assert user.employee_number is None

    def test_create_with_location(self, db, location):
        user = user_service.create_user(
            db, username="located", email="loc@test.com",
            password="password123", first_name="L", last_name="U",
            location_id=location.id,
        )
        assert user.location_id == location.id

    def test_password_is_hashed(self, db):
        user = user_service.create_user(
            db, username="hashtest", email="hash@test.com",
            password="password123", first_name="H", last_name="T",
        )
        assert user.password_hash != "password123"
        assert user.password_hash.startswith("$2b$")


class TestUpdateUser:
    def test_update_name(self, db, standard_user):
        updated = user_service.update_user(
            db, standard_user.id,
            first_name="Updated", last_name="Name",
            email="driver@test.com",
        )
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"

    def test_update_email(self, db, standard_user):
        updated = user_service.update_user(
            db, standard_user.id,
            first_name="Test", last_name="Driver",
            email="newemail@test.com",
        )
        assert updated.email == "newemail@test.com"

    def test_update_duplicate_email_fails(self, db, admin_user, standard_user):
        with pytest.raises(ConflictError, match="Email already in use"):
            user_service.update_user(
                db, standard_user.id,
                first_name="Test", last_name="Driver",
                email="admin@test.com",
            )

    def test_update_same_email_ok(self, db, standard_user):
        updated = user_service.update_user(
            db, standard_user.id,
            first_name="Test", last_name="Driver",
            email="driver@test.com",
        )
        assert updated.email == "driver@test.com"

    def test_update_duplicate_employee_number_fails(self, db, admin_user, standard_user):
        admin_user.employee_number = "EMP001"
        db.commit()
        with pytest.raises(ConflictError, match="Employee number"):
            user_service.update_user(
                db, standard_user.id,
                first_name="Test", last_name="Driver",
                email="driver@test.com",
                employee_number="EMP001",
            )

    def test_update_is_active(self, db, standard_user):
        updated = user_service.update_user(
            db, standard_user.id,
            first_name="Test", last_name="Driver",
            email="driver@test.com", is_active=False,
        )
        assert updated.is_active is False

    def test_update_nonexistent_raises(self, db):
        with pytest.raises(NotFoundError):
            user_service.update_user(
                db, 9999,
                first_name="X", last_name="X",
                email="x@test.com",
            )

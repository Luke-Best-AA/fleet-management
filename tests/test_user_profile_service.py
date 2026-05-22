"""Tests for app.services.user — update_profile."""

import pytest

from app.exceptions import ConflictError, NotFoundError
from app.services import user as user_service


class TestUpdateProfile:
    def test_update_profile_success(self, db, admin_user):
        updated = user_service.update_profile(db, admin_user.id, "NewFirst", "NewLast", "newemail@test.com")
        assert updated.first_name == "NewFirst"
        assert updated.last_name == "NewLast"
        assert updated.email == "newemail@test.com"

    def test_duplicate_email_fails(self, db, admin_user, standard_user):
        with pytest.raises(ConflictError, match="Email already in use"):
            user_service.update_profile(db, admin_user.id, "Test", "Admin", "driver@test.com")

    def test_same_email_ok(self, db, admin_user):
        updated = user_service.update_profile(db, admin_user.id, "Test", "Admin", "admin@test.com")
        assert updated.email == "admin@test.com"

    def test_nonexistent_user_raises(self, db):
        with pytest.raises(NotFoundError):
            user_service.update_profile(db, 99999, "A", "B", "c@d.com")

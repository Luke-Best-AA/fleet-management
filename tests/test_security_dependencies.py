"""Tests for app/security/dependencies.py — 100% coverage target."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.security.dependencies import get_current_user, require_admin, require_auth, verify_csrf


class TestGetCurrentUser:
    def test_returns_user_when_set(self):
        request = MagicMock()
        request.state.user = {"id": 1, "role": "admin"}
        assert get_current_user(request) == {"id": 1, "role": "admin"}

    def test_returns_none_when_no_user(self):
        request = MagicMock()
        request.state.user = None
        assert get_current_user(request) is None


class TestRequireAuth:
    def test_returns_user_when_authenticated(self):
        request = MagicMock()
        request.state.user = {"id": 1, "role": "standard"}
        assert require_auth(request) == {"id": 1, "role": "standard"}

    def test_returns_none_when_not_authenticated(self):
        request = MagicMock()
        request.state.user = None
        assert require_auth(request) is None


class TestRequireAdmin:
    def test_returns_user_when_admin(self):
        request = MagicMock()
        request.state.user = {"id": 1, "role": "admin"}
        assert require_admin(request) == {"id": 1, "role": "admin"}

    def test_returns_none_when_standard_user(self):
        request = MagicMock()
        request.state.user = {"id": 1, "role": "standard"}
        assert require_admin(request) is None

    def test_returns_none_when_not_authenticated(self):
        request = MagicMock()
        request.state.user = None
        assert require_admin(request) is None


class TestVerifyCsrf:
    def test_returns_true_for_valid_token(self):
        from app.security.csrf import generate_csrf_token

        token = generate_csrf_token()
        request = MagicMock()
        form = MagicMock()
        form.get.return_value = token
        request.form = AsyncMock(return_value=form)
        result = asyncio.get_event_loop().run_until_complete(verify_csrf(request))
        assert result is True

    def test_returns_false_for_invalid_token(self):
        request = MagicMock()
        form = MagicMock()
        form.get.return_value = "bad-token"
        request.form = AsyncMock(return_value=form)
        result = asyncio.get_event_loop().run_until_complete(verify_csrf(request))
        assert result is False

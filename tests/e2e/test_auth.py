"""End-to-end tests for authentication flows using Playwright."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


class TestLogin:
    def test_login_page_loads(self, page, base_url):
        page.goto(f"{base_url}/auth/login")
        expect(page).to_have_title(re.compile("Login"))
        expect(page.locator("h3")).to_have_text("Login")

    def test_unauthenticated_redirects_to_login(self, page, base_url):
        page.goto(f"{base_url}/dashboard")
        expect(page).to_have_url(re.compile("/auth/login"))

    def test_login_with_valid_admin(self, page, base_url, admin_creds):
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', admin_creds["username"])
        page.fill('input[name="password"]', admin_creds["password"])
        page.click('button[type="submit"]')
        expect(page).to_have_url(re.compile("/dashboard"))

    def test_login_with_valid_driver(self, page, base_url, driver_creds):
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', driver_creds["username"])
        page.fill('input[name="password"]', driver_creds["password"])
        page.click('button[type="submit"]')
        expect(page).to_have_url(re.compile("/dashboard"))

    def test_login_with_wrong_password(self, page, base_url):
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')
        expect(page.locator(".alert-danger")).to_be_visible()

    def test_login_with_nonexistent_user(self, page, base_url):
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', "nobody")
        page.fill('input[name="password"]', "password")
        page.click('button[type="submit"]')
        expect(page.locator(".alert-danger")).to_be_visible()


class TestLogout:
    def test_logout_redirects_to_login(self, page, base_url, admin_creds):
        # Log in first
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', admin_creds["username"])
        page.fill('input[name="password"]', admin_creds["password"])
        page.click('button[type="submit"]')
        expect(page).to_have_url(re.compile("/dashboard"))

        # Log out
        page.goto(f"{base_url}/auth/logout")
        expect(page).to_have_url(re.compile("/auth/login"))

    def test_cannot_access_dashboard_after_logout(self, page, base_url, admin_creds):
        # Log in
        page.goto(f"{base_url}/auth/login")
        page.fill('input[name="username"]', admin_creds["username"])
        page.fill('input[name="password"]', admin_creds["password"])
        page.click('button[type="submit"]')
        expect(page).to_have_url(re.compile("/dashboard"))

        # Log out
        page.goto(f"{base_url}/auth/logout")

        # Try to access dashboard
        page.goto(f"{base_url}/dashboard")
        expect(page).to_have_url(re.compile("/auth/login"))

"""End-to-end tests for navigation and page access using Playwright."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _login(page, base_url, username, password):
    page.goto(f"{base_url}/auth/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(re.compile("/dashboard"))


class TestAdminNavigation:
    def test_dashboard_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        expect(page.locator("h2, h3, h1").first).to_be_visible()

    def test_vehicles_page_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        page.goto(f"{base_url}/vehicles")
        expect(page).to_have_url(re.compile("/vehicles"))

    def test_mileage_page_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        page.goto(f"{base_url}/mileage")
        expect(page).to_have_url(re.compile("/mileage"))

    def test_maintenance_page_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        page.goto(f"{base_url}/maintenance")
        expect(page).to_have_url(re.compile("/maintenance"))

    def test_admin_locations_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        page.goto(f"{base_url}/admin/locations")
        expect(page).to_have_url(re.compile("/admin/locations"))

    def test_admin_users_loads(self, page, base_url, admin_creds):
        _login(page, base_url, **admin_creds)
        page.goto(f"{base_url}/admin/users")
        expect(page).to_have_url(re.compile("/admin/users"))


class TestDriverNavigation:
    def test_dashboard_loads(self, page, base_url, driver_creds):
        _login(page, base_url, **driver_creds)
        expect(page.locator("h2, h3, h1").first).to_be_visible()

    def test_vehicles_page_loads(self, page, base_url, driver_creds):
        _login(page, base_url, **driver_creds)
        page.goto(f"{base_url}/vehicles")
        expect(page).to_have_url(re.compile("/vehicles"))

    def test_driver_cannot_access_admin(self, page, base_url, driver_creds):
        _login(page, base_url, **driver_creds)
        page.goto(f"{base_url}/admin/locations")
        expect(page.locator("text=403, text=Forbidden, text=not authorised").first).to_be_visible()

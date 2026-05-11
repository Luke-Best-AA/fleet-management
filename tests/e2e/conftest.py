"""Playwright E2E test configuration.

Starts the Fleet Management app in a subprocess with a test SQLite database
and connects to the running Redis instance for session management.
"""

import os
import socket
import subprocess
import sys
import time

import pytest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def app_server():
    """Start the app on a random port for the E2E test session."""
    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///./test_e2e.db",
        "REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "SECRET_KEY": "e2e-test-secret-key",
        "SECURE_COOKIES": "false",
    }

    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base_url = f"http://127.0.0.1:{port}"

    # Wait for app to be ready
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("App did not start in time")

    yield base_url

    proc.terminate()
    proc.wait(timeout=5)

    # Clean up test database
    if os.path.exists("test_e2e.db"):
        os.remove("test_e2e.db")


@pytest.fixture(scope="session")
def seed_data(app_server):
    """Seed the E2E database with test data via the seed script."""
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///./test_e2e.db",
    }
    subprocess.run(
        [sys.executable, "seed.py"],
        env=env,
        check=True,
        capture_output=True,
    )
    return {
        "admin": {"username": "admin", "password": "admin123!"},
        "driver": {"username": "driver1", "password": "driver123!"},
    }


@pytest.fixture(scope="session")
def base_url(app_server):
    return app_server


@pytest.fixture
def admin_creds(seed_data):
    return seed_data["admin"]


@pytest.fixture
def driver_creds(seed_data):
    return seed_data["driver"]

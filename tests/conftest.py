import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

import jsonschema
import pytest
import requests
import uvicorn
from jsonschema import Draft7Validator

from app.auth import create_expired_token
from app.main import app

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def load_schema(schema_name: str) -> Dict[str, Any]:
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"
    if schema_name not in _SCHEMA_CACHE:
        schema_path = SCHEMAS_DIR / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE[schema_name] = json.load(f)
    return _SCHEMA_CACHE[schema_name]


def validate_payload(instance: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        error_msgs = "\n".join([f"- At {list(e.path)}: {e.message}" for e in errors])
        raise AssertionError(f"Schema validation failed for '{schema_name}':\n{error_msgs}")


def assert_latency(response: requests.Response, max_ms: float = 300.0) -> None:
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert (
        elapsed_ms < max_ms
    ), f"Response latency {elapsed_ms:.2f}ms exceeded limit of {max_ms}ms for {response.request.method} {response.url}"


# -----------------------------------------------------------------------------
# Server Management Fixture (Auto-start / connect)
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def fastapi_server():
    """Verify that the FastAPI server is running on http://127.0.0.1:8000,

    or start it in a background thread for the duration of the test session.
    """
    server_url = "http://127.0.0.1:8000/api/v1/test/reset"
    started_local = False
    server = None

    # Check if a server is already responsive
    try:
        res = requests.post(server_url, timeout=1)
        if res.status_code == 200:
            yield
            return
    except Exception:
        pass

    # Server not active; start in background thread
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_local = True

    # Wait for server readiness
    start_time = time.time()
    while time.time() - start_time < 10.0:
        try:
            res = requests.post(server_url, timeout=1)
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("FastAPI server failed to start within 10 seconds")

    yield

    if started_local and server is not None:
        server.should_exit = True
        thread.join(timeout=2)


# -----------------------------------------------------------------------------
# Base URL & HTTP Session Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_url() -> str:
    return "http://127.0.0.1:8000/api/v1"


@pytest.fixture(scope="session")
def api_session():
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture
def reset_db(base_url: str, api_session: requests.Session):
    """Reset the database to initial seed state before running a test."""
    res = api_session.post(f"{base_url}/test/reset", timeout=2)
    assert res.status_code == 200, f"Failed to reset database: {res.text}"
    return res.json()


# -----------------------------------------------------------------------------
# Auth Fixtures (Admin, Employee, Expired, Tampered, Malformed)
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def admin_token(base_url: str, api_session: requests.Session) -> str:
    res = api_session.post(
        f"{base_url}/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
        timeout=2,
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def employee_token(base_url: str, api_session: requests.Session) -> str:
    res = api_session.post(
        f"{base_url}/auth/login",
        json={"username": "emp01", "password": "EmpPass123!"},
        timeout=2,
    )
    assert res.status_code == 200, f"Employee login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def employee_headers(employee_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {employee_token}"}


@pytest.fixture(scope="session")
def expired_token() -> str:
    """Generate a real PyJWT token with an expiration timestamp in the past."""
    return create_expired_token({"sub": "emp01", "role": "employee", "employee_id": "EMP-1001"})


@pytest.fixture(scope="session")
def expired_headers(expired_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {expired_token}"}


@pytest.fixture(scope="session")
def tampered_token(admin_token: str) -> str:
    """Tamper with the signature portion of a valid JWT token."""
    parts = admin_token.split(".")
    if len(parts) == 3:
        # Corrupt the signature by appending characters
        tampered_sig = parts[2][:-4] + "fake"
        return f"{parts[0]}.{parts[1]}.{tampered_sig}"
    return admin_token + "tampered"


@pytest.fixture(scope="session")
def tampered_headers(tampered_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {tampered_token}"}


@pytest.fixture(scope="session")
def malformed_headers() -> Dict[str, str]:
    return {"Authorization": "InvalidScheme abcdef12345"}

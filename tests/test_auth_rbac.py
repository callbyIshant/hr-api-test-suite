import pytest
import requests

from tests.conftest import assert_latency, validate_payload


@pytest.mark.auth
@pytest.mark.latency
def test_login_admin_success(base_url: str, api_session: requests.Session):
    payload = {"username": "admin", "password": "AdminPass123!"}
    res = api_session.post(f"{base_url}/auth/login", json=payload)
    assert_latency(res)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["expires_in"] == 3600


@pytest.mark.auth
@pytest.mark.latency
def test_login_employee_success(base_url: str, api_session: requests.Session):
    payload = {"username": "emp01", "password": "EmpPass123!"}
    res = api_session.post(f"{base_url}/auth/login", json=payload)
    assert_latency(res)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "employee"
    assert data["expires_in"] == 3600


@pytest.mark.auth
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize(
    "creds",
    [
        {"username": "admin", "password": "WrongPassword!"},
        {"username": "emp01", "password": "BadPassword123"},
        {"username": "nonexistent_user", "password": "AdminPass123!"},
        {"username": "", "password": ""},
    ],
)
def test_login_invalid_credentials_401(base_url: str, api_session: requests.Session, creds: dict):
    res = api_session.post(f"{base_url}/auth/login", json=creds)
    assert_latency(res)
    assert res.status_code == 401
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.auth
@pytest.mark.schema
@pytest.mark.latency
def test_missing_auth_header_401(base_url: str, api_session: requests.Session):
    res = api_session.get(f"{base_url}/employees")
    assert_latency(res)
    assert res.status_code == 401
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.auth
@pytest.mark.schema
@pytest.mark.latency
def test_malformed_auth_header_401(base_url: str, api_session: requests.Session, malformed_headers: dict):
    res = api_session.get(f"{base_url}/employees", headers=malformed_headers)
    assert_latency(res)
    assert res.status_code == 401
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.auth
@pytest.mark.schema
@pytest.mark.latency
def test_expired_jwt_token_401(base_url: str, api_session: requests.Session, expired_headers: dict):
    res = api_session.get(f"{base_url}/employees", headers=expired_headers)
    assert_latency(res)
    assert res.status_code == 401
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "TOKEN_EXPIRED"


@pytest.mark.auth
@pytest.mark.schema
@pytest.mark.latency
def test_tampered_jwt_token_401(base_url: str, api_session: requests.Session, tampered_headers: dict):
    res = api_session.get(f"{base_url}/employees", headers=tampered_headers)
    assert_latency(res)
    assert res.status_code == 401
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "INVALID_TOKEN"


# -----------------------------------------------------------------------------
# RBAC Matrix Tests (admin vs employee vs unauthenticated)
# -----------------------------------------------------------------------------


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_post_employees(base_url: str, api_session: requests.Session, employee_headers: dict):
    # Employee attempting POST /employees -> 403 Forbidden
    payload = {
        "full_name": "Rogue Employee",
        "email": "rogue@company.com",
        "department": "Engineering",
        "salary": 50000.0,
    }
    res = api_session.post(f"{base_url}/employees", headers=employee_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 403
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "FORBIDDEN"


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_get_employees_list(base_url: str, api_session: requests.Session, employee_headers: dict, admin_headers: dict):
    # Both Admin and Employee can read list
    res_emp = api_session.get(f"{base_url}/employees", headers=employee_headers)
    assert_latency(res_emp)
    assert res_emp.status_code == 200

    res_admin = api_session.get(f"{base_url}/employees", headers=admin_headers)
    assert_latency(res_admin)
    assert res_admin.status_code == 200


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_get_employee_detail_own_vs_other(
    base_url: str,
    api_session: requests.Session,
    employee_headers: dict,
    admin_headers: dict,
    reset_db,
):
    # Setup: Admin creates EMP-1002
    create_res = api_session.post(
        f"{base_url}/employees",
        headers=admin_headers,
        json={
            "full_name": "Bob Smith",
            "email": "bob.smith@company.com",
            "department": "HR",
            "salary": 65000.0,
        },
    )
    assert create_res.status_code == 201

    # Employee accesses own profile (EMP-1001) -> 200 OK
    res_own = api_session.get(f"{base_url}/employees/EMP-1001", headers=employee_headers)
    assert_latency(res_own)
    assert res_own.status_code == 200

    # Employee accesses another employee's profile (EMP-1002) -> 403 Forbidden
    res_other = api_session.get(f"{base_url}/employees/EMP-1002", headers=employee_headers)
    assert_latency(res_other)
    assert res_other.status_code == 403
    validate_payload(res_other.json(), "error_schema")
    assert res_other.json()["error_code"] == "FORBIDDEN"

    # Admin accesses other employee's profile (EMP-1002) -> 200 OK
    res_admin = api_session.get(f"{base_url}/employees/EMP-1002", headers=admin_headers)
    assert_latency(res_admin)
    assert res_admin.status_code == 200


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_put_employees(base_url: str, api_session: requests.Session, employee_headers: dict):
    # Employee attempting PUT /employees/{id} -> 403 Forbidden
    payload = {
        "full_name": "Updated Name",
        "email": "emp01@company.com",
        "department": "Engineering",
        "salary": 80000.0,
    }
    res = api_session.put(f"{base_url}/employees/EMP-1001", headers=employee_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 403
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "FORBIDDEN"


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_delete_employees(base_url: str, api_session: requests.Session, employee_headers: dict):
    # Employee attempting DELETE /employees/{id} -> 403 Forbidden
    res = api_session.delete(f"{base_url}/employees/EMP-1001", headers=employee_headers)
    assert_latency(res)
    assert res.status_code == 403
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "FORBIDDEN"


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_post_attendance_own_vs_other(
    base_url: str,
    api_session: requests.Session,
    employee_headers: dict,
    admin_headers: dict,
    reset_db,
):
    # Admin creates EMP-1002
    api_session.post(
        f"{base_url}/employees",
        headers=admin_headers,
        json={
            "full_name": "Bob Smith",
            "email": "bob@company.com",
            "department": "Operations",
            "salary": 60000.0,
        },
    )

    # Employee logs attendance for self (EMP-1001) -> 201 Created
    res_own = api_session.post(
        f"{base_url}/attendance",
        headers=employee_headers,
        json={"employee_id": "EMP-1001", "date": "2026-11-15", "work_hours": 8.0, "status": "Present"},
    )
    assert_latency(res_own)
    assert res_own.status_code == 201

    # Employee logs attendance for another (EMP-1002) -> 403 Forbidden
    res_other = api_session.post(
        f"{base_url}/attendance",
        headers=employee_headers,
        json={"employee_id": "EMP-1002", "date": "2026-11-15", "work_hours": 8.0, "status": "Present"},
    )
    assert_latency(res_other)
    assert res_other.status_code == 403
    validate_payload(res_other.json(), "error_schema")
    assert res_other.json()["error_code"] == "FORBIDDEN"


@pytest.mark.rbac
@pytest.mark.schema
@pytest.mark.latency
def test_rbac_get_attendance_own_vs_other(
    base_url: str,
    api_session: requests.Session,
    employee_headers: dict,
    admin_headers: dict,
    reset_db,
):
    # Admin creates EMP-1002
    api_session.post(
        f"{base_url}/employees",
        headers=admin_headers,
        json={
            "full_name": "Bob Smith",
            "email": "bob@company.com",
            "department": "Operations",
            "salary": 60000.0,
        },
    )

    # Employee reads own attendance -> 200 OK
    res_own = api_session.get(f"{base_url}/attendance/EMP-1001", headers=employee_headers)
    assert_latency(res_own)
    assert res_own.status_code == 200

    # Employee reads other employee's attendance -> 403 Forbidden
    res_other = api_session.get(f"{base_url}/attendance/EMP-1002", headers=employee_headers)
    assert_latency(res_other)
    assert res_other.status_code == 403
    validate_payload(res_other.json(), "error_schema")
    assert res_other.json()["error_code"] == "FORBIDDEN"

    # Admin reads other employee's attendance -> 200 OK
    res_admin = api_session.get(f"{base_url}/attendance/EMP-1002", headers=admin_headers)
    assert_latency(res_admin)
    assert res_admin.status_code == 200


@pytest.mark.rbac
@pytest.mark.latency
def test_rbac_post_test_reset_unauthenticated(base_url: str, api_session: requests.Session):
    # POST /test/reset is a public test utility, no token needed -> 200 OK
    res = api_session.post(f"{base_url}/test/reset")
    assert_latency(res)
    assert res.status_code == 200
    assert "reset" in res.json()["message"].lower()

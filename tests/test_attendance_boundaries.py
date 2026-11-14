import pytest
import requests

from tests.conftest import assert_latency, validate_payload


# -----------------------------------------------------------------------------
# Attendance Work Hours Boundary Tests (< 0.5, > 16.0)
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("hours", [-5.0, -0.1, 0.0, 0.2, 0.49])
def test_attendance_hours_worked_boundary_low_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    hours: float,
):
    # Testing both hours_worked and work_hours field alias
    payload = {
        "employee_id": "EMP-1001",
        "date": "2026-11-16",
        "hours_worked": hours,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("hours", [16.01, 18.0, 24.0, 25.0, 100.0])
def test_attendance_hours_worked_boundary_high_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    hours: float,
):
    payload = {
        "employee_id": "EMP-1001",
        "date": "2026-11-16",
        "work_hours": hours,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# Bad Employee ID Pattern Tests
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize(
    "bad_emp_id",
    [
        "1001",
        "EMP-",
        "EMP-ABC",
        "emp-1001",
        "INVALID_ID",
        "EMP",
        "EMP-1001-EXTRA",
        "",
    ],
)
def test_attendance_bad_emp_pattern_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_emp_id: str,
):
    payload = {
        "employee_id": bad_emp_id,
        "date": "2026-11-17",
        "work_hours": 8.0,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# Department Enum Boundary Tests
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize(
    "bad_dept",
    [
        "IT",
        "Sales",
        "Marketing",
        "Legal",
        "engineering",  # wrong case
        "HR ",          # trailing space
        "Unknown",
        "",
    ],
)
def test_employee_invalid_department_enum_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_dept: str,
):
    payload = {
        "full_name": "Valid Name",
        "email": "valid.dept@company.com",
        "department": bad_dept,
        "salary": 50000.0,
    }
    res = api_session.post(f"{base_url}/employees", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# Salary Boundary Tests (< 30000 or > 500000)
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("bad_salary", [-10000.0, 0.0, 15000.0, 29999.99])
def test_employee_salary_boundary_low_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_salary: float,
):
    payload = {
        "full_name": "Low Earner",
        "email": "low.earner@company.com",
        "department": "Engineering",
        "salary": bad_salary,
    }
    res = api_session.post(f"{base_url}/employees", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("bad_salary", [500000.01, 550000.0, 1000000.0])
def test_employee_salary_boundary_high_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_salary: float,
):
    payload = {
        "full_name": "High Earner",
        "email": "high.earner@company.com",
        "department": "Operations",
        "salary": bad_salary,
    }
    res = api_session.post(f"{base_url}/employees", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# Name & Date Boundary Tests
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("bad_name", ["", "A", "A" * 81])
def test_employee_name_boundary_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_name: str,
):
    payload = {
        "full_name": bad_name,
        "email": "name.test@company.com",
        "department": "HR",
        "salary": 60000.0,
    }
    res = api_session.post(f"{base_url}/employees", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("bad_date", ["2026/11/14", "14-11-2026", "2026-1-1", "invalid-date", ""])
def test_attendance_date_format_boundary_422(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    bad_date: str,
):
    payload = {
        "employee_id": "EMP-1001",
        "date": bad_date,
        "work_hours": 8.0,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 422
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# Duplicate Check-In (409) & Valid Boundaries (201)
# -----------------------------------------------------------------------------


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
def test_attendance_duplicate_checkin_409(
    base_url: str,
    api_session: requests.Session,
    employee_headers: dict,
    reset_db,
):
    checkin_payload = {
        "employee_id": "EMP-1001",
        "date": "2026-11-20",
        "work_hours": 8.0,
        "status": "Present",
    }
    # First check-in -> 201 Created
    res1 = api_session.post(f"{base_url}/attendance", headers=employee_headers, json=checkin_payload)
    assert_latency(res1)
    assert res1.status_code == 201
    validate_payload(res1.json(), "attendance_schema")

    # Second check-in on identical date -> 409 Conflict
    res2 = api_session.post(f"{base_url}/attendance", headers=employee_headers, json=checkin_payload)
    assert_latency(res2)
    assert res2.status_code == 409
    validate_payload(res2.json(), "error_schema")
    assert res2.json()["error_code"] == "CONFLICT"


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
def test_attendance_nonexistent_employee_404(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
):
    payload = {
        "employee_id": "EMP-9999",
        "date": "2026-11-21",
        "work_hours": 8.0,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 404
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "NOT_FOUND"


@pytest.mark.boundary
@pytest.mark.schema
@pytest.mark.latency
@pytest.mark.parametrize("hours", [0.5, 8.0, 16.0])
def test_attendance_valid_boundary_values_201(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    hours: float,
    reset_db,
):
    date_str = f"2026-11-{(int(hours) + 10):02d}"
    payload = {
        "employee_id": "EMP-1001",
        "date": date_str,
        "hours_worked": hours,
        "status": "Present",
    }
    res = api_session.post(f"{base_url}/attendance", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 201
    validate_payload(res.json(), "attendance_schema")
    assert res.json()["work_hours"] == hours

import pytest
import requests

from tests.conftest import assert_latency, validate_payload


# -----------------------------------------------------------------------------
# Dedicated Schema Negative Checks (Draft-07 Strictness)
# -----------------------------------------------------------------------------


@pytest.mark.schema
def test_employee_schema_negative_extra_properties():
    valid_payload = {
        "employee_id": "EMP-1001",
        "full_name": "Alice Johnson",
        "email": "emp01@company.com",
        "department": "Engineering",
        "salary": 75000.0,
        "is_active": True,
        "created_at": "2026-11-14T09:00:00Z",
    }
    # Baseline passes
    validate_payload(valid_payload, "employee_schema")

    # Extra property must raise AssertionError
    invalid_payload = valid_payload.copy()
    invalid_payload["unexpected_bonus"] = 5000
    with pytest.raises(AssertionError) as exc_info:
        validate_payload(invalid_payload, "employee_schema")
    assert "unexpected_bonus" in str(exc_info.value)


@pytest.mark.schema
@pytest.mark.parametrize(
    "missing_key",
    ["employee_id", "full_name", "email", "department", "salary", "is_active", "created_at"],
)
def test_employee_schema_negative_missing_fields(missing_key: str):
    valid_payload = {
        "employee_id": "EMP-1001",
        "full_name": "Alice Johnson",
        "email": "emp01@company.com",
        "department": "Engineering",
        "salary": 75000.0,
        "is_active": True,
        "created_at": "2026-11-14T09:00:00Z",
    }
    invalid_payload = valid_payload.copy()
    del invalid_payload[missing_key]
    with pytest.raises(AssertionError) as exc_info:
        validate_payload(invalid_payload, "employee_schema")
    assert f"'{missing_key}' is a required property" in str(exc_info.value)


@pytest.mark.schema
@pytest.mark.parametrize(
    "field, bad_val",
    [
        ("salary", "seventy-five thousand"),
        ("is_active", "yes"),
        ("email", "not-an-email"),
        ("department", "NonExistentDept"),
        ("employee_id", 1001),
    ],
)
def test_employee_schema_negative_types(field: str, bad_val):
    valid_payload = {
        "employee_id": "EMP-1001",
        "full_name": "Alice Johnson",
        "email": "emp01@company.com",
        "department": "Engineering",
        "salary": 75000.0,
        "is_active": True,
        "created_at": "2026-11-14T09:00:00Z",
    }
    invalid_payload = valid_payload.copy()
    invalid_payload[field] = bad_val
    with pytest.raises(AssertionError):
        validate_payload(invalid_payload, "employee_schema")


@pytest.mark.schema
def test_attendance_schema_negative_extra_properties():
    valid_payload = {
        "attendance_id": "ATT-1001",
        "employee_id": "EMP-1001",
        "date": "2026-11-14",
        "work_hours": 8.0,
        "status": "Present",
        "created_at": "2026-11-14T09:00:00Z",
    }
    # Baseline passes
    validate_payload(valid_payload, "attendance_schema")

    # Extra property must raise AssertionError
    invalid_payload = valid_payload.copy()
    invalid_payload["supervisor_notes"] = "All good"
    with pytest.raises(AssertionError) as exc_info:
        validate_payload(invalid_payload, "attendance_schema")
    assert "supervisor_notes" in str(exc_info.value)


@pytest.mark.schema
@pytest.mark.parametrize(
    "missing_key",
    ["attendance_id", "employee_id", "date", "work_hours", "status", "created_at"],
)
def test_attendance_schema_negative_missing_fields(missing_key: str):
    valid_payload = {
        "attendance_id": "ATT-1001",
        "employee_id": "EMP-1001",
        "date": "2026-11-14",
        "work_hours": 8.0,
        "status": "Present",
        "created_at": "2026-11-14T09:00:00Z",
    }
    invalid_payload = valid_payload.copy()
    del invalid_payload[missing_key]
    with pytest.raises(AssertionError) as exc_info:
        validate_payload(invalid_payload, "attendance_schema")
    assert f"'{missing_key}' is a required property" in str(exc_info.value)


@pytest.mark.schema
def test_error_schema_negative_extra_properties():
    valid_error = {
        "error_code": "FORBIDDEN",
        "message": "Access denied",
        "details": None,
    }
    validate_payload(valid_error, "error_schema")

    invalid_error = valid_error.copy()
    invalid_error["internal_trace"] = "Traceback line 42"
    with pytest.raises(AssertionError) as exc_info:
        validate_payload(invalid_error, "error_schema")
    assert "internal_trace" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Latency Benchmark: 20 Sequential Requests with p95 < 300ms
# -----------------------------------------------------------------------------


@pytest.mark.latency
@pytest.mark.schema
def test_p95_latency_benchmark_20_sequential_requests(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    employee_headers: dict,
    reset_db,
):
    latencies = []

    # Sequence of 20 distinct requests hitting various endpoints
    requests_plan = [
        ("POST", f"{base_url}/test/reset", {}, None),
        ("GET", f"{base_url}/employees", admin_headers, None),
        ("GET", f"{base_url}/employees/EMP-1001", admin_headers, None),
        ("GET", f"{base_url}/employees/EMP-1001", employee_headers, None),
        ("GET", f"{base_url}/attendance/EMP-1001", admin_headers, None),
        ("GET", f"{base_url}/attendance/EMP-1001", employee_headers, None),
        ("POST", f"{base_url}/auth/login", {}, {"username": "admin", "password": "AdminPass123!"}),
        ("POST", f"{base_url}/auth/login", {}, {"username": "emp01", "password": "EmpPass123!"}),
        ("GET", f"{base_url}/employees", employee_headers, None),
        ("GET", f"{base_url}/employees/EMP-1001", employee_headers, None),
        ("POST", f"{base_url}/attendance", employee_headers, {"employee_id": "EMP-1001", "date": "2026-11-28", "work_hours": 8.0, "status": "Present"}),
        ("GET", f"{base_url}/attendance/EMP-1001", employee_headers, None),
        ("GET", f"{base_url}/employees", admin_headers, None),
        ("POST", f"{base_url}/employees", admin_headers, {"full_name": "Seq Test", "email": "seq@company.com", "department": "HR", "salary": 55000.0}),
        ("GET", f"{base_url}/employees", employee_headers, None),
        ("GET", f"{base_url}/attendance/EMP-1001", admin_headers, None),
        ("POST", f"{base_url}/auth/login", {}, {"username": "admin", "password": "AdminPass123!"}),
        ("GET", f"{base_url}/employees/EMP-1001", admin_headers, None),
        ("GET", f"{base_url}/attendance/EMP-1001", employee_headers, None),
        ("POST", f"{base_url}/test/reset", {}, None),
    ]

    assert len(requests_plan) == 20, f"Expected exactly 20 requests in plan, got {len(requests_plan)}"

    for idx, (method, url, headers, body) in enumerate(requests_plan, 1):
        if method == "GET":
            res = api_session.get(url, headers=headers)
        elif method == "POST":
            res = api_session.post(url, headers=headers, json=body)
        else:
            raise ValueError(f"Unsupported method {method}")

        elapsed_ms = res.elapsed.total_seconds() * 1000
        latencies.append(elapsed_ms)

        # Invariant 3: Response latency is strictly under 300ms
        assert res.status_code in (200, 201), f"Request {idx} failed with {res.status_code}: {res.text}"
        assert elapsed_ms < 300.0, f"Request {idx} ({method} {url}) exceeded 300ms limit: {elapsed_ms:.2f}ms"

    # Calculate p95 latency
    sorted_latencies = sorted(latencies)
    # 95th percentile index for 20 items: index 19 (the 19th or 20th item)
    p95_index = int(0.95 * len(latencies))
    p95_latency = sorted_latencies[min(p95_index, len(latencies) - 1)]

    min_lat = min(latencies)
    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)

    print(f"\n--- Latency Benchmark (20 Sequential Requests) ---")
    print(f"Min: {min_lat:.2f}ms | Avg: {avg_lat:.2f}ms | Max: {max_lat:.2f}ms | p95: {p95_latency:.2f}ms")

    assert p95_latency < 300.0, f"p95 latency {p95_latency:.2f}ms exceeded limit of 300ms"

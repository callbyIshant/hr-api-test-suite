import pytest
import requests

from tests.conftest import assert_latency, validate_payload


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_employee_full_crud_lifecycle(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    reset_db,
):
    # 1. CREATE employee (POST /employees)
    new_employee_payload = {
        "full_name": "Priya Sharma",
        "email": "priya.sharma@company.com",
        "department": "Engineering",
        "salary": 95000.0,
    }
    create_res = api_session.post(
        f"{base_url}/employees",
        headers=admin_headers,
        json=new_employee_payload,
    )
    assert_latency(create_res)
    assert create_res.status_code == 201
    created_data = create_res.json()
    validate_payload(created_data, "employee_schema")
    emp_id = created_data["employee_id"]
    assert emp_id.startswith("EMP-")
    assert created_data["full_name"] == new_employee_payload["full_name"]
    assert created_data["email"] == new_employee_payload["email"]
    assert created_data["department"] == new_employee_payload["department"]
    assert created_data["salary"] == new_employee_payload["salary"]
    assert created_data["is_active"] is True
    assert "created_at" in created_data

    # 2. READ employee (GET /employees/{emp_id})
    get_res = api_session.get(f"{base_url}/employees/{emp_id}", headers=admin_headers)
    assert_latency(get_res)
    assert get_res.status_code == 200
    validate_payload(get_res.json(), "employee_schema")
    assert get_res.json()["employee_id"] == emp_id

    # 3. LIST employees (GET /employees)
    list_res = api_session.get(f"{base_url}/employees", headers=admin_headers)
    assert_latency(list_res)
    assert list_res.status_code == 200
    employees_list = list_res.json()
    assert isinstance(employees_list, list)
    assert len(employees_list) >= 2  # Seed EMP-1001 + newly created emp_id
    for emp in employees_list:
        validate_payload(emp, "employee_schema")
    assert any(e["employee_id"] == emp_id for e in employees_list)

    # 4. UPDATE employee (PUT /employees/{emp_id})
    update_payload = {
        "full_name": "Priya Sharma-Patel",
        "email": "priya.patel@company.com",
        "department": "Operations",
        "salary": 110000.0,
    }
    put_res = api_session.put(
        f"{base_url}/employees/{emp_id}",
        headers=admin_headers,
        json=update_payload,
    )
    assert_latency(put_res)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    validate_payload(updated_data, "employee_schema")
    assert updated_data["full_name"] == update_payload["full_name"]
    assert updated_data["email"] == update_payload["email"]
    assert updated_data["department"] == update_payload["department"]
    assert updated_data["salary"] == update_payload["salary"]

    # 5. DELETE employee (DELETE /employees/{emp_id})
    del_res = api_session.delete(f"{base_url}/employees/{emp_id}", headers=admin_headers)
    assert_latency(del_res)
    assert del_res.status_code == 204
    assert del_res.text == ""

    # 6. VERIFY DELETION (GET /employees/{emp_id} -> 404)
    verify_res = api_session.get(f"{base_url}/employees/{emp_id}", headers=admin_headers)
    assert_latency(verify_res)
    assert verify_res.status_code == 404
    validate_payload(verify_res.json(), "error_schema")
    assert verify_res.json()["error_code"] == "NOT_FOUND"


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_create_employee_duplicate_email_409(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    reset_db,
):
    # Attempt to create with existing seeded email emp01@company.com
    payload = {
        "full_name": "Duplicate Candidate",
        "email": "emp01@company.com",
        "department": "Finance",
        "salary": 70000.0,
    }
    res = api_session.post(f"{base_url}/employees", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 409
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "CONFLICT"


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_update_employee_duplicate_email_409(
    base_url: str,
    api_session: requests.Session,
    admin_headers: dict,
    reset_db,
):
    # Create EMP-1002
    res_create = api_session.post(
        f"{base_url}/employees",
        headers=admin_headers,
        json={
            "full_name": "Bob Jones",
            "email": "bob.jones@company.com",
            "department": "HR",
            "salary": 60000.0,
        },
    )
    assert res_create.status_code == 201
    emp_id = res_create.json()["employee_id"]

    # Attempt to update EMP-1002 with EMP-1001's email (emp01@company.com)
    update_payload = {
        "full_name": "Bob Jones",
        "email": "emp01@company.com",
        "department": "HR",
        "salary": 60000.0,
    }
    res_put = api_session.put(f"{base_url}/employees/{emp_id}", headers=admin_headers, json=update_payload)
    assert_latency(res_put)
    assert res_put.status_code == 409
    validate_payload(res_put.json(), "error_schema")
    assert res_put.json()["error_code"] == "CONFLICT"


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_get_nonexistent_employee_404(base_url: str, api_session: requests.Session, admin_headers: dict):
    res = api_session.get(f"{base_url}/employees/EMP-9999", headers=admin_headers)
    assert_latency(res)
    assert res.status_code == 404
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "NOT_FOUND"


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_update_nonexistent_employee_404(base_url: str, api_session: requests.Session, admin_headers: dict):
    payload = {
        "full_name": "Ghost",
        "email": "ghost@company.com",
        "department": "Engineering",
        "salary": 50000.0,
    }
    res = api_session.put(f"{base_url}/employees/EMP-9999", headers=admin_headers, json=payload)
    assert_latency(res)
    assert res.status_code == 404
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "NOT_FOUND"


@pytest.mark.crud
@pytest.mark.schema
@pytest.mark.latency
def test_delete_nonexistent_employee_404(base_url: str, api_session: requests.Session, admin_headers: dict):
    res = api_session.delete(f"{base_url}/employees/EMP-9999", headers=admin_headers)
    assert_latency(res)
    assert res.status_code == 404
    validate_payload(res.json(), "error_schema")
    assert res.json()["error_code"] == "NOT_FOUND"

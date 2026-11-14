#!/usr/bin/env python3
"""Programmatically builds the Postman Collection v2.1 and local environment files

by reading the JSON schemas from schemas/*.json and generating deterministic tests.
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT_DIR / "schemas"
POSTMAN_DIR = ROOT_DIR / "postman"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_test_script(
    expected_status: int,
    schema: dict = None,
    custom_script: str = "",
    schema_is_array: bool = False,
) -> list:
    """Builds the Postman JavaScript test script lines enforcing:

    1. Status code assertion
    2. Response latency < 300ms
    3. JSON Schema compliance
    4. Optional custom logic (e.g. saving environment variables)
    """
    lines = [
        f'pm.test("Status code is {expected_status}", function () {{',
        f"    pm.response.to.have.status({expected_status});",
        "});",
        "",
        'pm.test("Response time is strictly below 300ms", function () {',
        "    pm.expect(pm.response.responseTime).to.be.below(300);",
        "});",
    ]

    if schema is not None:
        if schema_is_array:
            array_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "array",
                "items": schema,
            }
            schema_json_str = json.dumps(array_schema)
        else:
            schema_json_str = json.dumps(schema)

        lines.extend(
            [
                "",
                'pm.test("Response adheres to JSON Schema", function () {',
                f"    var schema = {schema_json_str};",
                "    pm.response.to.have.jsonSchema(schema);",
                "});",
            ]
        )

    if custom_script:
        lines.extend(["", custom_script])

    return lines


def make_request_item(
    name: str,
    method: str,
    url_path: str,
    headers: list,
    body: dict = None,
    expected_status: int = 200,
    schema: dict = None,
    custom_script: str = "",
    schema_is_array: bool = False,
) -> dict:
    test_lines = make_test_script(
        expected_status=expected_status,
        schema=schema,
        custom_script=custom_script,
        schema_is_array=schema_is_array,
    )

    path_segments = [seg for seg in url_path.strip("/").split("/") if seg]

    item = {
        "name": name,
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": test_lines,
                },
            }
        ],
        "request": {
            "method": method,
            "header": [
                {"key": k, "value": v, "type": "text"} for k, v in headers
            ],
            "url": {
                "raw": f"{{{{base_url}}}}/{url_path.lstrip('/')}",
                "host": ["{{base_url}}"],
                "path": path_segments,
            },
        },
        "response": [],
    }

    if body is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
        item["request"]["header"].append(
            {"key": "Content-Type", "value": "application/json", "type": "text"}
        )

    return item


def build_collection():
    employee_schema = load_json(SCHEMAS_DIR / "employee_schema.json")
    attendance_schema = load_json(SCHEMAS_DIR / "attendance_schema.json")
    error_schema = load_json(SCHEMAS_DIR / "error_schema.json")

    login_response_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "LoginResponse",
        "type": "object",
        "required": ["access_token", "token_type", "role", "expires_in"],
        "properties": {
            "access_token": {"type": "string"},
            "token_type": {"type": "string"},
            "role": {"type": "string"},
            "expires_in": {"type": "number"},
        },
        "additionalProperties": False,
    }

    reset_response_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ResetResponse",
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {"type": "string"},
        },
        "additionalProperties": False,
    }

    # -------------------------------------------------------------------------
    # Folder 1: 00_Setup & Auth
    # -------------------------------------------------------------------------
    folder_setup_auth = {
        "name": "00_Setup & Auth",
        "item": [
            make_request_item(
                name="01 - Reset In-Memory Store",
                method="POST",
                url_path="test/reset",
                headers=[],
                expected_status=200,
                schema=reset_response_schema,
            ),
            make_request_item(
                name="02 - Admin Login",
                method="POST",
                url_path="auth/login",
                headers=[],
                body={"username": "admin", "password": "AdminPass123!"},
                expected_status=200,
                schema=login_response_schema,
                custom_script="var jsonData = pm.response.json();\npm.environment.set('admin_token', jsonData.access_token);",
            ),
            make_request_item(
                name="03 - Employee Login",
                method="POST",
                url_path="auth/login",
                headers=[],
                body={"username": "emp01", "password": "EmpPass123!"},
                expected_status=200,
                schema=login_response_schema,
                custom_script="var jsonData = pm.response.json();\npm.environment.set('employee_token', jsonData.access_token);",
            ),
        ],
    }

    # -------------------------------------------------------------------------
    # Folder 2: 01_RBAC & Auth Negative Checks
    # -------------------------------------------------------------------------
    folder_rbac_negative = {
        "name": "01_RBAC & Auth Negative Checks",
        "item": [
            make_request_item(
                name="01 - Missing Token Rejection",
                method="GET",
                url_path="employees",
                headers=[],
                expected_status=401,
                schema=error_schema,
            ),
            make_request_item(
                name="02 - Bad / Tampered Token Rejection",
                method="GET",
                url_path="employees",
                headers=[("Authorization", "Bearer invalid.signature.token")],
                expected_status=401,
                schema=error_schema,
            ),
            make_request_item(
                name="03 - Employee Creating User Forbidden",
                method="POST",
                url_path="employees",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                body={
                    "full_name": "Unauthorized Add",
                    "email": "unauthorized.add@company.com",
                    "department": "HR",
                    "salary": 50000.0,
                },
                expected_status=403,
                schema=error_schema,
            ),
            make_request_item(
                name="04 - Employee Deleting User Forbidden",
                method="DELETE",
                url_path="employees/EMP-1001",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                expected_status=403,
                schema=error_schema,
            ),
        ],
    }

    # -------------------------------------------------------------------------
    # Folder 3: 02_Employee CRUD
    # -------------------------------------------------------------------------
    folder_crud = {
        "name": "02_Employee CRUD",
        "item": [
            make_request_item(
                name="01 - Admin Create Employee",
                method="POST",
                url_path="employees",
                headers=[("Authorization", "Bearer {{admin_token}}")],
                body={
                    "full_name": "Priya Sharma",
                    "email": "priya.newman@company.com",
                    "department": "Engineering",
                    "salary": 95000.0,
                },
                expected_status=201,
                schema=employee_schema,
                custom_script="var jsonData = pm.response.json();\npm.environment.set('created_employee_id', jsonData.employee_id);",
            ),
            make_request_item(
                name="02 - Admin Get Created Employee",
                method="GET",
                url_path="employees/{{created_employee_id}}",
                headers=[("Authorization", "Bearer {{admin_token}}")],
                expected_status=200,
                schema=employee_schema,
            ),
            make_request_item(
                name="03 - Admin Update Created Employee",
                method="PUT",
                url_path="employees/{{created_employee_id}}",
                headers=[("Authorization", "Bearer {{admin_token}}")],
                body={
                    "full_name": "Priya Sharma-Patel",
                    "email": "priya.patel.newman@company.com",
                    "department": "Operations",
                    "salary": 105000.0,
                },
                expected_status=200,
                schema=employee_schema,
            ),
            make_request_item(
                name="04 - Admin Delete Created Employee",
                method="DELETE",
                url_path="employees/{{created_employee_id}}",
                headers=[("Authorization", "Bearer {{admin_token}}")],
                expected_status=204,
                schema=None,  # 204 No Content
            ),
            make_request_item(
                name="05 - Verify Deleted Employee 404",
                method="GET",
                url_path="employees/{{created_employee_id}}",
                headers=[("Authorization", "Bearer {{admin_token}}")],
                expected_status=404,
                schema=error_schema,
            ),
        ],
    }

    # -------------------------------------------------------------------------
    # Folder 4: 03_Attendance & Boundaries
    # -------------------------------------------------------------------------
    folder_attendance = {
        "name": "03_Attendance & Boundaries",
        "item": [
            make_request_item(
                name="01 - Valid Check-In as Employee",
                method="POST",
                url_path="attendance",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                body={
                    "employee_id": "EMP-1001",
                    "date": "2026-11-20",
                    "work_hours": 8.0,
                    "status": "Present",
                },
                expected_status=201,
                schema=attendance_schema,
            ),
            make_request_item(
                name="02 - Duplicate Check-In Conflict",
                method="POST",
                url_path="attendance",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                body={
                    "employee_id": "EMP-1001",
                    "date": "2026-11-20",
                    "work_hours": 8.0,
                    "status": "Remote",
                },
                expected_status=409,
                schema=error_schema,
            ),
            make_request_item(
                name="03 - Negative Hours Validation Error",
                method="POST",
                url_path="attendance",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                body={
                    "employee_id": "EMP-1001",
                    "date": "2026-11-21",
                    "work_hours": -1.0,
                    "status": "Present",
                },
                expected_status=422,
                schema=error_schema,
            ),
            make_request_item(
                name="04 - Excessive Hours Validation Error",
                method="POST",
                url_path="attendance",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                body={
                    "employee_id": "EMP-1001",
                    "date": "2026-11-21",
                    "work_hours": 24.0,
                    "status": "Present",
                },
                expected_status=422,
                schema=error_schema,
            ),
            make_request_item(
                name="05 - Get Attendance List for Employee",
                method="GET",
                url_path="attendance/EMP-1001",
                headers=[("Authorization", "Bearer {{employee_token}}")],
                expected_status=200,
                schema=attendance_schema,
                schema_is_array=True,
            ),
        ],
    }

    collection = {
        "info": {
            "_postman_id": "hr-attendance-api-suite-v1",
            "name": "HR & Attendance REST API Automated Contract Suite",
            "description": "Automated contract, RBAC, CRUD, and boundary test suite for HR & Attendance API.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            folder_setup_auth,
            folder_rbac_negative,
            folder_crud,
            folder_attendance,
        ],
    }

    env_data = {
        "id": "hr-attendance-local-env",
        "name": "HR Attendance Local Environment",
        "values": [
            {
                "key": "base_url",
                "value": "http://127.0.0.1:8000/api/v1",
                "enabled": True,
            },
            {
                "key": "admin_token",
                "value": "",
                "enabled": True,
            },
            {
                "key": "employee_token",
                "value": "",
                "enabled": True,
            },
            {
                "key": "created_employee_id",
                "value": "",
                "enabled": True,
            },
        ],
        "_postman_variable_scope": "environment",
    }

    POSTMAN_DIR.mkdir(parents=True, exist_ok=True)

    collection_path = POSTMAN_DIR / "hr_attendance_collection.json"
    with open(collection_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)
    print(f"Collection generated at: {collection_path}")

    env_path = POSTMAN_DIR / "local_env.json"
    with open(env_path, "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=2)
    print(f"Environment generated at: {env_path}")


if __name__ == "__main__":
    build_collection()

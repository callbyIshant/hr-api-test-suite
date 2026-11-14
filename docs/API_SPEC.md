# HR & Attendance REST API Specification (v1)

Base URL: `http://127.0.0.1:8000/api/v1`

## 1. Authentication & Roles
- `POST /auth/login`
  - Request: `{"username": "string", "password": "string"}`
  - Seeded Users:
    - Admin: `username="admin"`, `password="AdminPass123!"` (role: `"admin"`)
    - Employee: `username="emp01"`, `password="EmpPass123!"` (role: `"employee"`, employee_id: `"EMP-1001"`)
  - Response `200 OK`: `{"access_token": "string", "token_type": "bearer", "role": "admin|employee", "expires_in": 3600}`
  - Response `401 Unauthorized`: Invalid credentials.

## 2. RBAC Matrix
| Endpoint | Method | `admin` | `employee` | Unauthenticated |
|---|---|---|---|---|
| `/test/reset` | POST | 200 | 200 | 200 (Local test utility) |
| `/employees` | POST | 201 | 403 | 401 |
| `/employees` | GET | 200 | 200 | 401 |
| `/employees/{emp_id}` | GET | 200 | 200 (own) / 403 (other) | 401 |
| `/employees/{emp_id}` | PUT | 200 | 403 | 401 |
| `/employees/{emp_id}` | DELETE | 204 | 403 | 401 |
| `/attendance` | POST | 201 | 201 (own) / 403 (other) | 401 |
| `/attendance/{emp_id}` | GET | 200 | 200 (own) / 403 (other) | 401 |

## 3. Data Models & Boundary Constraints
### Employee Create/Update (`POST /employees`, `PUT /employees/{emp_id}`)
- `full_name`: string, required, minLength: 2, maxLength: 80
- `email`: string (valid email format), required
- `department`: enum `["Engineering", "HR", "Finance", "Operations"]`, required
- `salary`: number, required, minimum: 30000, maximum: 500000

### Employee Response (`200 OK` / `201 Created`)
```json
{
  "employee_id": "EMP-1002",
  "full_name": "Priya Sharma",
  "email": "priya@company.com",
  "department": "Engineering",
  "salary": 95000.0,
  "is_active": true,
  "created_at": "2026-11-14T10:00:00Z"
}
```

### Attendance Create (`POST /attendance`)
- `employee_id`: string, required, pattern: `^EMP-\d+$` (e.g. `"EMP-1001"`)
- `date`: string (ISO `YYYY-MM-DD` format), required
- `work_hours` (or `hours_worked`): number, required, minimum: 0.5, maximum: 16.0
- `status`: enum `["Present", "Absent", "Half-Day", "Remote"]`, required

### Attendance Response (`200 OK` / `201 Created`)
```json
{
  "attendance_id": "ATT-1001",
  "employee_id": "EMP-1001",
  "date": "2026-11-14",
  "work_hours": 8.0,
  "status": "Present",
  "created_at": "2026-11-14T09:00:00Z"
}
```

### Attendance List Response (`200 OK` for `GET /attendance/{emp_id}`)
Array of Attendance Response objects:
```json
[
  {
    "attendance_id": "ATT-1001",
    "employee_id": "EMP-1001",
    "date": "2026-11-14",
    "work_hours": 8.0,
    "status": "Present",
    "created_at": "2026-11-14T09:00:00Z"
  }
]
```

## 4. Standard Error Response
All endpoints return a uniform JSON error payload on errors (`400`, `401`, `403`, `404`, `409`, `422`, `500`):

```json
{
  "error_code": "STRING_ERROR_CODE",
  "message": "Human-readable error description",
  "details": null
}
```

- `error_code`: Machine-readable error code (e.g. `"UNAUTHORIZED"`, `"FORBIDDEN"`, `"NOT_FOUND"`, `"CONFLICT"`, `"VALIDATION_ERROR"`, `"INTERNAL_SERVER_ERROR"`).
- `message`: Clear summary of the error.
- `details`: Additional contextual data (such as field-level validation errors for `422`), or `null`.

## 5. Test Reset Utility
- `POST /test/reset`
  - Unauthenticated access allowed (test isolation utility).
  - Resets employee table to initial seed:
    - `EMP-1001`: `full_name="Alice Johnson"`, `email="emp01@company.com"`, `department="Engineering"`, `salary=75000.0`, `is_active=true`
  - Resets attendance table to initial seed:
    - `ATT-1001`: `employee_id="EMP-1001"`, `date="2026-11-14"`, `work_hours=8.0`, `status="Present"`
  - Response `200 OK`: `{"message": "Database reset to initial seed state successfully"}`

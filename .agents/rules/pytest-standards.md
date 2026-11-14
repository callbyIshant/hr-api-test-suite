---
trigger: glob
globs: "tests/**/*.py, schemas/**/*.json, pytest.ini"
description: "Enforce pytest fixtures, jsonschema validation, RBAC negative tests, and latency assertions."
---
# Pytest & JSON Schema Standards

1. **Schema Validation Helper:**
   - Store all JSON schemas as standalone `.json` files in `schemas/` using Draft-07 (`"http://json-schema.org/draft-07/schema#"`).
   - Set `"additionalProperties": false` on all response object schemas so undocumented API fields immediately fail the test.
   - Load schemas via a shared `validate_payload(instance, schema_name)` helper in `tests/conftest.py` using `jsonschema.validate(instance=..., schema=...)`.

2. **Fixtures & Auth (`tests/conftest.py`):**
   - Provide session-scoped fixtures: `base_url`, `api_session`, `admin_headers`, `employee_headers`, `expired_headers`, and `malformed_headers`.
   - Include a fixture `reset_db` (autouse per module or function where needed) that hits `POST /api/v1/test/reset` so CRUD tests are completely isolated and idempotent.

3. **Boundary & Negative Coverage:**
   - Use `@pytest.mark.parametrize` for boundary payloads (empty strings, strings > 100 chars, negative work hours, > 24 work hours, invalid ISO dates, missing required fields, wrong data types).
   - Explicitly distinguish **401 Unauthorized** (missing token, expired JWT, tampered signature, `Bearer ` prefix missing) from **403 Forbidden** (valid `employee` JWT attempting `admin`-only endpoints like `POST /api/v1/employees` or `DELETE /api/v1/employees/{id}`).
   - Assert FastAPI/REST validation failures return **422 Unprocessable Entity** (or **400 Bad Request** per spec) and conform to `schemas/error_schema.json`.
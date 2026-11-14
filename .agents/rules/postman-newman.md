---
trigger: glob
globs: "postman/**/*.json, scripts/**/*.sh"
description: "Rules for generating valid Postman v2.1 collections and Newman CLI execution scripts."
---
# Postman v2.1 & Newman CLI Standards

1. **Valid Postman v2.1 Schema:**
   - Always use `"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"`.
   - Never truncate JSON with `// ... existing code`. Write complete, valid JSON or use a Python generator script to build `postman/hr_attendance_collection.json` cleanly without syntax errors.

2. **Collection Execution Order (Deterministic Workflow):**
   - Folder 1: `00_Setup & Auth` (`POST /api/v1/test/reset`, `POST /api/v1/auth/login` as Admin -> saves `admin_token`, `POST /api/v1/auth/login` as Employee -> saves `employee_token`).
   - Folder 2: `01_RBAC & Auth Negative Checks` (401 no token, 401 bad token, 403 employee creating/deleting user).
   - Folder 3: `02_Employee CRUD` (Create -> Get -> Update -> Delete, chaining `created_employee_id` environment variable).
   - Folder 4: `03_Attendance & Boundaries` (Valid check-in, duplicate check-in 409, negative hours 422, >24 hours 422).

3. **Mandatory Postman Test Scripts (`pm.test`):**
   - Every request MUST include:
     - Status code assertion (`pm.response.to.have.status(...)`)
     - Latency assertion (`pm.expect(pm.response.responseTime).to.be.below(300)`)
     - JSON Schema validation (`pm.response.to.have.jsonSchema(schema)`)
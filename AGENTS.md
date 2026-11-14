# Project Mission: HR & Attendance REST API Automated Test Suite & Schema Validator

## Stack & Versions
- **Target API:** FastAPI (in-memory SQLite/dict store for deterministic zero-dependency test runs, running on `http://127.0.0.1:8000`)
- **Test Framework:** Python 3.11+, `pytest`, `requests`, `jsonschema` (Draft7Validator)
- **CLI Contract Runner:** Postman Collection v2.1 + `newman` CLI (`newman-reporter-htmlextra`)

## Anti-Hallucination Invariants (STRICT)
1. **Single Source of Truth:** All endpoints, payloads, status codes, and RBAC roles MUST strictly match @docs/API_SPEC.md. Never invent endpoints, query parameters, or response fields not listed in `@docs/API_SPEC.md`.
2. **Real HTTP Calls in Suite:** `tests/` must use `requests.Session()` hitting `BASE_URL` (`http://127.0.0.1:8000`), NOT FastAPI's internal `TestClient`, so the exact same live server is tested by both `pytest` and `newman` and real network socket latency (`response.elapsed`) is measured.
3. **Latency Assertion:** Every functional test and Postman request must assert response latency is strictly under 300ms (`response.elapsed.total_seconds() * 1000 < 300`).
4. **Verification Before Completion:** Never claim a task is complete without running the relevant terminal command (`pytest` or `newman run`) and reading the full output.
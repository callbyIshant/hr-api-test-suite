from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import (
    AppException,
    create_access_token,
    get_current_user,
)
from app.models import (
    AttendanceCreate,
    AttendanceResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    TokenData,
)

# -----------------------------------------------------------------------------
# Seeded Credentials & In-Memory Data Store
# -----------------------------------------------------------------------------

SEEDED_USERS = {
    "admin": {
        "password": "AdminPass123!",
        "role": "admin",
        "employee_id": None,
    },
    "emp01": {
        "password": "EmpPass123!",
        "role": "employee",
        "employee_id": "EMP-1001",
    },
}


class InMemoryStore:
    def __init__(self):
        self.employees: Dict[str, Dict[str, Any]] = {}
        self.attendance: List[Dict[str, Any]] = []
        self.employee_seq: int = 1002
        self.attendance_seq: int = 1002
        self.reset()

    def reset(self):
        self.employees = {
            "EMP-1001": {
                "employee_id": "EMP-1001",
                "full_name": "Alice Johnson",
                "email": "emp01@company.com",
                "department": "Engineering",
                "salary": 75000.0,
                "is_active": True,
                "created_at": "2026-11-14T09:00:00Z",
            }
        }
        self.attendance = [
            {
                "attendance_id": "ATT-1001",
                "employee_id": "EMP-1001",
                "date": "2026-11-14",
                "work_hours": 8.0,
                "status": "Present",
                "created_at": "2026-11-14T09:00:00Z",
            }
        ]
        self.employee_seq = 1002
        self.attendance_seq = 1002


db = InMemoryStore()

# -----------------------------------------------------------------------------
# FastAPI App & Router
# -----------------------------------------------------------------------------

app = FastAPI(
    title="HR & Attendance REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

api_router = APIRouter(prefix="/api/v1")

# -----------------------------------------------------------------------------
# Standardized Error Handlers
# -----------------------------------------------------------------------------

HTTP_STATUS_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
}


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Normalize Pydantic validation errors
    formatted_errors = []
    for err in exc.errors():
        formatted_errors.append(
            {
                "field": ".".join(str(loc) for loc in err.get("loc", []) if loc != "body"),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": formatted_errors,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_code = HTTP_STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "details": None,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
        },
    )


# -----------------------------------------------------------------------------
# RBAC Dependencies
# -----------------------------------------------------------------------------


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "admin":
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message="Admin privileges required to perform this action",
            details=None,
        )
    return current_user


# -----------------------------------------------------------------------------
# Authentication Endpoints
# -----------------------------------------------------------------------------


@api_router.post(
    "/auth/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def login(credentials: LoginRequest):
    user = SEEDED_USERS.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message="Invalid username or password",
            details=None,
        )

    token_payload = {
        "sub": credentials.username,
        "role": user["role"],
        "employee_id": user["employee_id"],
    }
    access_token = create_access_token(token_payload)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"],
        expires_in=3600,
    )


# -----------------------------------------------------------------------------
# Test Utility Endpoints
# -----------------------------------------------------------------------------


@api_router.post("/test/reset", status_code=status.HTTP_200_OK)
async def test_reset():
    """Reset the in-memory data store to initial seed state. Public test utility."""
    db.reset()
    return {"message": "Database reset to initial seed state successfully"}


# -----------------------------------------------------------------------------
# Employee Endpoints
# -----------------------------------------------------------------------------


@api_router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_employee(
    employee_in: EmployeeCreate,
    current_user: TokenData = Depends(require_admin),
):
    # Check if email is already taken
    for emp in db.employees.values():
        if emp["email"].lower() == employee_in.email.lower():
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                error_code="CONFLICT",
                message=f"Employee with email '{employee_in.email}' already exists",
                details=None,
            )

    emp_id = f"EMP-{db.employee_seq}"
    db.employee_seq += 1
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_employee = {
        "employee_id": emp_id,
        "full_name": employee_in.full_name,
        "email": employee_in.email,
        "department": employee_in.department.value,
        "salary": float(employee_in.salary),
        "is_active": True,
        "created_at": now_iso,
    }
    db.employees[emp_id] = new_employee
    return EmployeeResponse(**new_employee)


@api_router.get(
    "/employees",
    response_model=List[EmployeeResponse],
    responses={
        401: {"model": ErrorResponse},
    },
)
async def list_employees(current_user: TokenData = Depends(get_current_user)):
    return [EmployeeResponse(**emp) for emp in db.employees.values()]


@api_router.get(
    "/employees/{emp_id}",
    response_model=EmployeeResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_employee(
    emp_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    # RBAC: admin can view all; employee can only view own profile
    if current_user.role != "admin" and current_user.employee_id != emp_id:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message="Forbidden: You cannot access other employee profiles",
            details=None,
        )

    emp = db.employees.get(emp_id)
    if not emp:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"Employee with ID '{emp_id}' not found",
            details=None,
        )

    return EmployeeResponse(**emp)


@api_router.put(
    "/employees/{emp_id}",
    response_model=EmployeeResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def update_employee(
    emp_id: str,
    employee_in: EmployeeUpdate,
    current_user: TokenData = Depends(require_admin),
):
    emp = db.employees.get(emp_id)
    if not emp:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"Employee with ID '{emp_id}' not found",
            details=None,
        )

    # Check for email conflict with another employee
    for other_id, other_emp in db.employees.items():
        if other_id != emp_id and other_emp["email"].lower() == employee_in.email.lower():
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                error_code="CONFLICT",
                message=f"Employee with email '{employee_in.email}' already exists",
                details=None,
            )

    emp["full_name"] = employee_in.full_name
    emp["email"] = employee_in.email
    emp["department"] = employee_in.department.value
    emp["salary"] = float(employee_in.salary)

    return EmployeeResponse(**emp)


@api_router.delete(
    "/employees/{emp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def delete_employee(
    emp_id: str,
    current_user: TokenData = Depends(require_admin),
):
    if emp_id not in db.employees:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"Employee with ID '{emp_id}' not found",
            details=None,
        )

    del db.employees[emp_id]
    # Remove attendance records for the deleted employee
    db.attendance = [att for att in db.attendance if att["employee_id"] != emp_id]
    return None


# -----------------------------------------------------------------------------
# Attendance Endpoints
# -----------------------------------------------------------------------------


@api_router.post(
    "/attendance",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def record_attendance(
    attendance_in: AttendanceCreate,
    current_user: TokenData = Depends(get_current_user),
):
    # RBAC: employee can only record attendance for self; admin can record for anyone
    if current_user.role != "admin" and current_user.employee_id != attendance_in.employee_id:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message="Forbidden: Employees can only record attendance for themselves",
            details=None,
        )

    # Check employee exists
    if attendance_in.employee_id not in db.employees:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"Employee with ID '{attendance_in.employee_id}' not found",
            details=None,
        )

    # Check duplicate check-in for the same date
    for record in db.attendance:
        if (
            record["employee_id"] == attendance_in.employee_id
            and record["date"] == attendance_in.date
        ):
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                error_code="CONFLICT",
                message=(
                    f"Attendance record already exists for employee "
                    f"'{attendance_in.employee_id}' on date '{attendance_in.date}'"
                ),
                details=None,
            )

    att_id = f"ATT-{db.attendance_seq}"
    db.attendance_seq += 1
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_attendance = {
        "attendance_id": att_id,
        "employee_id": attendance_in.employee_id,
        "date": attendance_in.date,
        "work_hours": float(attendance_in.work_hours),
        "status": attendance_in.status.value,
        "created_at": now_iso,
    }
    db.attendance.append(new_attendance)
    return AttendanceResponse(**new_attendance)


@api_router.get(
    "/attendance/{emp_id}",
    response_model=List[AttendanceResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_employee_attendance(
    emp_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    # RBAC: admin can view all; employee can only view own attendance
    if current_user.role != "admin" and current_user.employee_id != emp_id:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message="Forbidden: You cannot view attendance for other employees",
            details=None,
        )

    if emp_id not in db.employees:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"Employee with ID '{emp_id}' not found",
            details=None,
        )

    records = [
        AttendanceResponse(**att)
        for att in db.attendance
        if att["employee_id"] == emp_id
    ]
    return records


# Register the v1 API router
app.include_router(api_router)

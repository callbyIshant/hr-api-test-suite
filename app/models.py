from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class DepartmentEnum(str, Enum):
    ENGINEERING = "Engineering"
    HR = "HR"
    FINANCE = "Finance"
    OPERATIONS = "Operations"


class AttendanceStatusEnum(str, Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    HALF_DAY = "Half-Day"
    REMOTE = "Remote"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int = 3600


class TokenData(BaseModel):
    username: str
    role: str
    employee_id: Optional[str] = None


class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=80, description="Full name of the employee")
    email: EmailStr = Field(..., description="Valid company email address")
    department: DepartmentEnum = Field(..., description="Department department enum")
    salary: float = Field(..., ge=30000.0, le=500000.0, description="Salary between 30000 and 500000")


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    employee_id: str
    is_active: bool = True
    created_at: str


class AttendanceCreate(BaseModel):
    employee_id: str = Field(..., description="Employee ID e.g. EMP-1001")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    work_hours: float = Field(..., ge=0.0, le=24.0, description="Work hours between 0.0 and 24.0")
    status: AttendanceStatusEnum = Field(..., description="Attendance status")


class AttendanceResponse(BaseModel):
    attendance_id: str
    employee_id: str
    date: str
    work_hours: float
    status: str
    created_at: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Any] = None

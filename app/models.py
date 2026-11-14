from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


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
    department: DepartmentEnum = Field(..., description="Department enum")
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
    employee_id: str = Field(..., pattern=r"^EMP-\d+$", description="Employee ID e.g. EMP-1001")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    work_hours: Optional[float] = Field(None, ge=0.5, le=16.0, description="Work hours between 0.5 and 16.0")
    hours_worked: Optional[float] = Field(None, ge=0.5, le=16.0, description="Alias for work_hours between 0.5 and 16.0")
    status: AttendanceStatusEnum = Field(default=AttendanceStatusEnum.PRESENT, description="Attendance status")

    @model_validator(mode="before")
    @classmethod
    def resolve_hours(cls, data: Any) -> Any:
        if isinstance(data, dict):
            hw = data.get("hours_worked")
            wh = data.get("work_hours")
            if hw is not None and wh is None:
                data["work_hours"] = hw
            elif wh is not None and hw is None:
                data["hours_worked"] = wh
            elif hw is None and wh is None:
                raise ValueError("work_hours or hours_worked is required")
        return data


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

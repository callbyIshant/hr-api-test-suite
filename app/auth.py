import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Header

from app.models import TokenData

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret-jwt-key-for-qa-project-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Any] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_expired_token(data: dict) -> str:
    """Helper to generate an already-expired token for testing."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    # Expired 10 minutes ago
    expire = now - timedelta(minutes=10)
    issued_at = now - timedelta(minutes=70)
    to_encode.update({"iat": issued_at, "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AppException(
            status_code=401,
            error_code="TOKEN_EXPIRED",
            message="Token has expired",
            details=None,
        )
    except jwt.PyJWTError:
        raise AppException(
            status_code=401,
            error_code="INVALID_TOKEN",
            message="Could not validate credentials",
            details=None,
        )


def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    if not authorization:
        raise AppException(
            status_code=401,
            error_code="UNAUTHORIZED",
            message="Authorization header is required",
            details=None,
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppException(
            status_code=401,
            error_code="UNAUTHORIZED",
            message="Invalid authentication scheme. Expected 'Bearer <token>'",
            details=None,
        )

    token = parts[1]
    payload = decode_access_token(token)
    username: Optional[str] = payload.get("sub") or payload.get("username")
    role: Optional[str] = payload.get("role")
    employee_id: Optional[str] = payload.get("employee_id")

    if not username or not role:
        raise AppException(
            status_code=401,
            error_code="INVALID_TOKEN",
            message="Token payload is missing required claims (username/role)",
            details=None,
        )

    return TokenData(username=username, role=role, employee_id=employee_id)

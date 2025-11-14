"""
Security utilities for authentication and authorization.

Implements JWT token generation, OAuth2, password hashing, and API key validation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token

    Returns:
        Dict[str, Any]: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get current user from JWT token.

    Args:
        token: JWT token from request

    Returns:
        Dict[str, Any]: User data

    Raises:
        HTTPException: If token is invalid
    """
    payload = decode_access_token(token)

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Fetch user from database
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, text

    async with AsyncSessionLocal() as session:
        # Check if user exists and is active
        # Note: Replace with actual User model when available
        result = await session.execute(
            text("SELECT id, email, is_active FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user_row = result.fetchone()

        if user_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user_row.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        return {
            "user_id": user_row.id,
            "email": user_row.email,
            **payload
        }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Dict[str, Any]: Active user data

    Raises:
        HTTPException: If user is inactive
    """
    if current_user.get("disabled", False):
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


async def validate_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Validate API key from request header.

    Args:
        api_key: API key from header

    Returns:
        str: Valid API key

    Raises:
        HTTPException: If API key is invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
        )

    # Validate API key against database
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, text
    from datetime import datetime

    async with AsyncSessionLocal() as session:
        # Check if API key exists, is active, and not expired
        # Note: Replace with actual ApiKey model when available
        result = await session.execute(
            text("""
                SELECT id, tenant_id, is_active, expires_at 
                FROM api_keys 
                WHERE key_hash = :key_hash
            """),
            {"key_hash": api_key}  # In production, hash the key before lookup
        )
        key_row = result.fetchone()

        if key_row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )

        if not key_row.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key is inactive",
            )

        if key_row.expires_at and key_row.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key has expired",
            )

        return api_key


def get_tenant_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Extract tenant ID from current user for multi-tenancy.

    Args:
        current_user: Current authenticated user

    Returns:
        str: Tenant ID

    Raises:
        HTTPException: If tenant ID not found
    """
    tenant_id = current_user.get("tenant_id")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID not found in user context",
        )

    return tenant_id

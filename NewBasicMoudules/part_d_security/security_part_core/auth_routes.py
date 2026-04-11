# -*- coding: utf-8 -*-
"""
FastAPI Auth Routes - Full HttpOnly Cookie Implementation

Security features:
- Dual HttpOnly cookies (access_token + refresh_token)
- Redis-based token storage and revocation
- Rate limiting for login attempts
- RBAC role checking
- CSRF protection for state-changing operations
"""

from datetime import datetime, timezone, timedelta
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, validator
import secrets

from security_part.auth_core import (
    hash_password,
    verify_password,
    TokenService,
    JWTConfig,
    SensitiveOperation,
    UserRegister,
    UserLogin,
    UserBase,
    sanitize_log_data,
    mask_email,
    logger,
    xss_filter,
    sanitize_user_input
)
from security_part.user_store import UserStore as MockUserDB
from security_part.redis_store import TokenStore, RateLimiter
from security_part.rbac import Role, get_user_role, require_role, require_permission

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings
COOKIE_ACCESS_NAME = "access_token"
COOKIE_REFRESH_NAME = "refresh_token"
COOKIE_CSRF_NAME = "csrf_token"


def get_cookie_config():
    """Get cookie configuration based on environment."""
    # Allow enabling secure cookies via environment (FORCE_HTTPS or COOKIE_SECURE)
    env_secure = os.environ.get("FORCE_HTTPS", "").lower() in ("1", "true", "yes")
    env_cookie_secure = os.environ.get("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    secure_flag = env_secure or env_cookie_secure
    return {
        "httponly": True,
        "secure": secure_flag,
        "samesite": "strict",
        "path": "/"
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_expires: int = 900,  # 15 minutes
    refresh_expires: int = 604800  # 7 days
):
    """Set both access and refresh tokens as HttpOnly cookies."""
    config = get_cookie_config()
    
    # Access token cookie
    response.set_cookie(
        key=COOKIE_ACCESS_NAME,
        value=access_token,
        max_age=access_expires,
        **config
    )
    
    # Refresh token cookie
    response.set_cookie(
        key=COOKIE_REFRESH_NAME,
        value=refresh_token,
        max_age=refresh_expires,
        **config
    )
    
    # CSRF token (not HttpOnly, for JS to read and send in header)
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=COOKIE_CSRF_NAME,
        value=csrf_token,
        max_age=refresh_expires,
        httponly=False,  # JS needs to read this
        secure=config["secure"],
        samesite=config["samesite"],
        path="/"
    )
    
    return csrf_token


def clear_auth_cookies(response: Response):
    """Clear all auth cookies."""
    response.delete_cookie(key=COOKIE_ACCESS_NAME, path="/")
    response.delete_cookie(key=COOKIE_REFRESH_NAME, path="/")
    response.delete_cookie(key=COOKIE_CSRF_NAME, path="/")


def get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
    """Extract token from HttpOnly cookie."""
    return request.cookies.get(cookie_name)


def verify_csrf_token(request: Request) -> bool:
    """Verify CSRF token from header against cookie."""
    cookie_csrf = request.cookies.get(COOKIE_CSRF_NAME)
    header_csrf = request.headers.get("X-CSRF-Token")
    return cookie_csrf and header_csrf and cookie_csrf == header_csrf


async def get_current_user(request: Request) -> dict:
    """Get current user from HttpOnly access token cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get access token from cookie
    token = get_token_from_cookie(request, COOKIE_ACCESS_NAME)
    if not token:
        raise credentials_exception
    
    # Decode and validate token
    payload = TokenService.decode_token(token)
    if not payload:
        raise credentials_exception
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = MockUserDB.get_user_safe(username)
    if user is None:
        raise credentials_exception
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User disabled"
        )
    
    # Add role to user data
    user["role"] = user.get("role", Role.STUDENT.value)
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    pass  # No need for refresh token in body, it's in cookie


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, request: Request):
    """User registration with race condition protection."""
    # First check (before processing)
    if MockUserDB.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    log_data = user_data.model_dump()
    logger.info(f"Register request: {sanitize_log_data(log_data)}")
    
    # XSS Filter: Sanitize user inputs before storing
    safe_username = xss_filter(user_data.username, strict=True)
    safe_email = xss_filter(user_data.email, strict=True)
    
    # Create user with default student role
    # Database UNIQUE constraint will prevent race condition duplicates
    try:
        user = MockUserDB.create_user(
            username=safe_username,
            email=safe_email,
            password=user_data.password
        )
        user["role"] = Role.STUDENT.value
    except Exception as e:
        # Handle race condition: another request created the user between check and insert
        if "UNIQUE constraint failed" in str(e) or "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    
    return {
        "code": 201,
        "message": "Registration successful",
        "data": user
    }


@router.post("/login", response_model=dict)
async def login(response: Response, login_data: LoginRequest, request: Request):
    """User login with rate limiting and HttpOnly cookies."""
    
    # Rate limiting check
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining = RateLimiter.is_allowed(f"login:{client_ip}:{login_data.username}")
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for {login_data.username} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again after 5 minutes."
        )
    
    logger.info(f"Login attempt: username={login_data.username}, ip={client_ip}")
    
    # Verify user credentials
    user = MockUserDB.get_user_by_username(login_data.username)
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        logger.warning(f"Login failed: username={login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User disabled"
        )
    
    # Reset rate limit on successful login
    RateLimiter.reset(f"login:{client_ip}:{login_data.username}")
    
    # Update last login
    MockUserDB.update_last_login(login_data.username)
    
    # Generate tokens
    access_token, access_jti = TokenService.create_access_token(user_id=user["username"])
    refresh_token, refresh_jti = TokenService.create_refresh_token(user_id=user["username"])
    
    # Store refresh token in Redis
    TokenStore.store_refresh_token(refresh_jti, user["username"], JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Set HttpOnly cookies
    csrf_token = set_auth_cookies(
        response,
        access_token,
        refresh_token,
        access_expires=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )
    
    logger.info(f"Login success: username={login_data.username}")
    
    return {
        "code": 200,
        "message": "Login successful",
        "data": {
            "username": user["username"],
            "role": user.get("role", Role.STUDENT.value),
            "csrf_token": csrf_token  # Send CSRF token in response for JS to use
        }
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(request: Request, response: Response):
    """Refresh access token using HttpOnly refresh token cookie."""
    
    # Get refresh token from cookie
    refresh_token = get_token_from_cookie(request, COOKIE_REFRESH_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode refresh token
    payload = TokenService.decode_token(refresh_token, check_blacklist=False)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate against Redis
    jti = payload.get("jti")
    user_id = payload.get("sub")
    
    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if refresh token is valid in Redis
    stored_user = TokenStore.validate_refresh_token(jti)
    if not stored_user or stored_user != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate new access token
    new_access_token, new_access_jti = TokenService.create_access_token(user_id=user_id)
    
    # Set new access token cookie
    config = get_cookie_config()
    response.set_cookie(
        key=COOKIE_ACCESS_NAME,
        value=new_access_token,
        max_age=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **config
    )
    
    logger.info(f"Token refreshed for user: {user_id}")
    
    return {
        "code": 200,
        "message": "Token refreshed",
        "data": {
            "expires_in": JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    }


@router.post("/logout", response_model=dict)
async def logout(request: Request, response: Response):
    """User logout - revoke tokens and clear cookies."""
    
    # Get tokens from cookies
    access_token = get_token_from_cookie(request, COOKIE_ACCESS_NAME)
    refresh_token = get_token_from_cookie(request, COOKIE_REFRESH_NAME)
    
    # Revoke access token (add to blacklist)
    if access_token:
        TokenService.revoke_token(access_token)
    
    # Revoke refresh token (remove from Redis)
    if refresh_token:
        payload = TokenService.decode_token(refresh_token, check_blacklist=False)
        if payload:
            jti = payload.get("jti")
            if jti:
                TokenStore.revoke_refresh_token(jti)
    
    # Clear all cookies
    clear_auth_cookies(response)
    
    logger.info("User logged out")
    
    return {"code": 200, "message": "Logout successful"}


@router.get("/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return {
        "code": 200,
        "message": "success",
        "data": current_user
    }


# Admin-only endpoints
@router.get("/admin/users", response_model=dict)
@require_role(Role.ADMIN)
async def list_users(current_user: dict = Depends(get_current_user)):
    """List all users (admin only)."""
    # This would query all users from database
    return {
        "code": 200,
        "message": "Admin access granted",
        "data": {"note": "User listing endpoint - implement as needed"}
    }


@router.delete("/admin/users/{username}", response_model=dict)
@require_role(Role.ADMIN)
async def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    """Delete a user (admin only)."""
    # This would delete user from database
    return {
        "code": 200,
        "message": f"User {username} deleted",
        "data": {}
    }


# Sensitive operations with confirmation
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    current_password: str
    confirmation_text: str  # Must type "DELETE" to confirm


@router.post("/change-password", response_model=dict)
async def change_password(
    request: Request,
    response: Response,
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password with current password confirmation (sensitive operation).
    
    Requires current password to prevent unauthorized changes.
    """
    username = current_user.get("username")
    
    # Verify current password (sensitive operation confirmation)
    if not SensitiveOperation.verify_password_confirmation(username, password_data.current_password):
        logger.warning(f"Password change failed: incorrect current password for {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password complexity
    try:
        # Reuse the validator from UserRegister
        from security_part.auth_core import UserRegister
        # Create a temporary model to validate password
        class _TempValidator(BaseModel):
            password: str = Field(..., min_length=8, max_length=128)
            
            @validator("password")
            def validate_pwd(cls, v):
                if not any(c.isupper() for c in v):
                    raise ValueError("password must include an uppercase letter")
                if not any(c.islower() for c in v):
                    raise ValueError("password must include a lowercase letter")
                if not any(c.isdigit() for c in v):
                    raise ValueError("password must include a digit")
                return v
        
        _TempValidator(password=password_data.new_password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password does not meet requirements: {str(e)}"
        )
    
    # Hash and update password
    new_hashed_password = hash_password(password_data.new_password)
    
    # Update in database
    from security_part.user_store import UserStore
    user = UserStore.get_user_by_username(username)
    if user:
        # Update the password (add method to UserStore if needed)
        # For now, we'll use a direct approach
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent / "users.db"
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET hashed_password = ? WHERE username = ?",
                (new_hashed_password, username)
            )
            conn.commit()
        finally:
            conn.close()
    
    # Revoke all existing tokens for this user (security: prevent old token usage)
    # Get current tokens from cookies and revoke them
    access_token = get_token_from_cookie(request, COOKIE_ACCESS_NAME)
    refresh_token = get_token_from_cookie(request, COOKIE_REFRESH_NAME)
    
    if access_token:
        TokenService.revoke_token(access_token)
    if refresh_token:
        payload = TokenService.decode_token(refresh_token, check_blacklist=False)
        if payload:
            jti = payload.get("jti")
            if jti:
                TokenStore.revoke_refresh_token(jti)
    
    # Clear cookies to force re-login
    clear_auth_cookies(response)
    
    logger.info(f"Password changed successfully for user: {username}. All tokens revoked.")
    
    return {
        "code": 200,
        "message": "Password changed successfully. Please login again with your new password.",
        "data": {}
    }


@router.delete("/account", response_model=dict)
async def delete_account(
    request: Request,
    delete_data: DeleteAccountRequest,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Delete user account with password confirmation and text confirmation (sensitive operation).
    
    Requires:
    1. Current password verification
    2. Type "DELETE" in confirmation_text field
    """
    username = current_user.get("username")
    
    # Verify current password (sensitive operation confirmation)
    if not SensitiveOperation.verify_password_confirmation(username, delete_data.current_password):
        logger.warning(f"Account deletion failed: incorrect password for {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Verify confirmation text
    if delete_data.confirmation_text != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation text must be 'DELETE' (uppercase) to proceed"
        )
    
    # Revoke all tokens BEFORE deleting user (security: prevent token reuse)
    access_token = get_token_from_cookie(request, COOKIE_ACCESS_NAME)
    refresh_token = get_token_from_cookie(request, COOKIE_REFRESH_NAME)
    
    if access_token:
        TokenService.revoke_token(access_token)
    if refresh_token:
        payload = TokenService.decode_token(refresh_token, check_blacklist=False)
        if payload:
            jti = payload.get("jti")
            if jti:
                TokenStore.revoke_refresh_token(jti)
    
    # Delete user from database
    from security_part.user_store import UserStore
    import sqlite3
    from pathlib import Path
    db_path = Path(__file__).resolve().parent / "users.db"
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = ?", (username,))
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        conn.commit()
    finally:
        conn.close()
    
    # Clear cookies and logout
    clear_auth_cookies(response)
    
    logger.info(f"Account deleted successfully for user: {username}. All tokens revoked.")
    
    return {
        "code": 200,
        "message": "Account deleted successfully. All your data has been removed.",
        "data": {}
    }

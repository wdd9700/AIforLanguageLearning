# -*- coding: utf-8 -*-
"""
FastAPI Auth Routes
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

import secrets

from security_part.auth_core import (
    hash_password,
    verify_password,
    TokenService,
    JWTConfig,
    SensitiveOperation,
    UserRegister,
    UserLogin,
    TokenResponse,
    UserBase,
    sanitize_log_data,
    mask_email,
    logger
)
from security_part.user_store import UserStore as MockUserDB

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Use `UserStore` (SQLite) as the persistent backing store for users.
# The class is aliased to `MockUserDB` so the rest of the routes keep working.


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
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
    
    return user


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, request: Request):
    """User registration"""
    if MockUserDB.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    log_data = user_data.model_dump()
    logger.info(f"Register request: {sanitize_log_data(log_data)}")
    
    user = MockUserDB.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password
    )
    
    return {
        "code": 201,
        "message": "Registration successful",
        "data": user
    }


@router.post("/login", response_model=dict)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """User login"""
    logger.info(f"Login attempt: username={form_data.username}")

    user = MockUserDB.get_user_by_username(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        logger.warning(f"Login failed: username={form_data.username}")
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

    MockUserDB.update_last_login(form_data.username)

    access_token = TokenService.create_access_token(user_id=user["username"])
    refresh_token = TokenService.create_refresh_token(user_id=user["username"])

    # Set refresh token as HttpOnly cookie and set a non-HttpOnly CSRF cookie
    try:
        max_age = JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    except Exception:
        max_age = 7 * 24 * 3600

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="Strict",
        max_age=max_age,
        secure=False,
        path="/"
    )
    csrf_value = secrets.token_urlsafe(16)
    response.set_cookie(
        key="csrf_token",
        value=csrf_value,
        httponly=False,
        samesite="Strict",
        max_age=max_age,
        secure=False,
        path="/"
    )

    logger.info(f"Login success: username={form_data.username}")

    # Return access token in JSON; refresh token is stored as cookie (frontend should not store the refresh token)
    return {
        "code": 200,
        "message": "Login successful",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 30 * 60
        }
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(request: Request):
    """Refresh access token.

    Preferred flow: use HttpOnly cookie `refresh_token` + CSRF protection (header `X-CSRF-Token` matching cookie `csrf_token`).
    Fallback: accept JSON body {"refresh_token": "..."} for API clients.
    """
    refresh_token_value = None

    # Try cookie-based flow first
    cookie_refresh = request.cookies.get("refresh_token")
    if cookie_refresh:
        # require double-submit CSRF token
        header_csrf = request.headers.get("x-csrf-token")
        cookie_csrf = request.cookies.get("csrf_token")
        if not cookie_csrf or not header_csrf or header_csrf != cookie_csrf:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid")
        refresh_token_value = cookie_refresh
    else:
        # fallback to JSON body
        try:
            body = await request.json()
            refresh_token_value = body.get("refresh_token")
        except Exception:
            refresh_token_value = None

    if not refresh_token_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing refresh token")

    new_access_token = TokenService.refresh_access_token(refresh_token_value)

    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "code": 200,
        "message": "Token refreshed",
        "data": {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 30 * 60
        }
    }


@router.post("/logout", response_model=dict)
async def logout(request: Request, response: Response):
    """User logout. Supports Authorization header or refresh cookie. Clears cookies on success."""
    auth_header = request.headers.get("authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    cookie_refresh = request.cookies.get("refresh_token")

    revoked = False
    if token:
        revoked = TokenService.revoke_token(token)
    elif cookie_refresh:
        revoked = TokenService.revoke_token(cookie_refresh)

    if revoked:
        # clear cookies
        response.delete_cookie("refresh_token", path="/")
        response.delete_cookie("csrf_token", path="/")
        return {"code": 200, "message": "Logout successful"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid token"
    )


@router.get("/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "code": 200,
        "message": "success",
        "data": current_user
    }

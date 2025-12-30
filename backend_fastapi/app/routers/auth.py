from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginUser(BaseModel):
    username: str
    role: str = "admin"


class LoginData(BaseModel):
    accessToken: str
    user: LoginUser


class LoginResponse(BaseModel):
    success: bool
    data: LoginData | None = None
    error: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    # P0：前端目前用于演示/本地开发会默认 admin/admin 自动登录。
    username = (req.username or "").strip()
    password = (req.password or "").strip()

    if not username or not password:
        return LoginResponse(success=False, error="Missing credentials")

    # 最小可用：仅接受 admin/admin（可后续替换为标准 Bearer Token / fastapi-users）。
    if username != "admin" or password != "admin":
        return LoginResponse(success=False, error="Invalid username or password")

    token = f"dev-token-{int(time.time())}"
    return LoginResponse(
        success=True,
        data=LoginData(accessToken=token, user=LoginUser(username=username, role="admin")),
    )

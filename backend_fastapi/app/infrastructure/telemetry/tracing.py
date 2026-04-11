"""分布式追踪与 TraceID 生成"""

from __future__ import annotations

import contextvars
import uuid
from typing import Any

from fastapi import Request

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_trace_id() -> str:
    """获取当前上下文中的 trace_id"""
    return _trace_id_var.get()


def get_request_id() -> str:
    """获取当前上下文中的 request_id"""
    return _request_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前上下文中的 trace_id"""
    _trace_id_var.set(trace_id)


def set_request_id(request_id: str) -> None:
    """设置当前上下文中的 request_id"""
    _request_id_var.set(request_id)


def generate_trace_id() -> str:
    """生成新的 trace_id"""
    return uuid.uuid4().hex


def generate_request_id() -> str:
    """生成新的 request_id"""
    return uuid.uuid4().hex[:16]


class TraceMiddleware:
    """TraceID 中间件"""

    async def process_request(self, request: Request) -> dict[str, Any]:
        trace_id = request.headers.get("X-Trace-Id") or generate_trace_id()
        request_id = request.headers.get("X-Request-Id") or generate_request_id()
        set_trace_id(trace_id)
        set_request_id(request_id)
        return {"trace_id": trace_id, "request_id": request_id}

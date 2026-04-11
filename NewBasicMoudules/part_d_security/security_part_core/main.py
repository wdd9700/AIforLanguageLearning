# -*- coding: utf-8 -*-
"""
AI Foreign Language System - Security Auth Demo
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from jinja2 import FileSystemLoader, Environment
import uvicorn
import os

from security_part.auth_routes import router as auth_router, get_current_user
from security_part.rbac import Role

BASE_DIR = Path(__file__).resolve().parent


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (disable dangerous features)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in HTTPS mode)
        if os.environ.get("FORCE_HTTPS") or os.environ.get("COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


app = FastAPI(
    title="AI Foreign Language System - Auth Demo",
    description="Demo: integrate bcrypt + JWT authentication module with HttpOnly cookies",
    version="2.0.0",
    docs_url=None,  # Disable /docs (Swagger UI)
    redoc_url=None,  # Disable /redoc (ReDoc)
    openapi_url=None,  # Disable /openapi.json
)

# Security headers middleware (must be first)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware - required for cookie-based auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8001", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates"), encoding="utf-8"),
    auto_reload=True,
    cache_size=0
)


class CustomTemplates:
    def __init__(self, env):
        self.env = env

    def TemplateResponse(self, name, context):
        from starlette.templating import _TemplateResponse
        from starlette.datastructures import Headers
        template = self.env.get_template(name)
        headers = Headers(raw=[(b"content-type", b"text/html; charset=utf-8")])
        return _TemplateResponse(
            template=template,
            context=context,
            headers=headers
        )


templates = CustomTemplates(jinja_env)

app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Home page - redirect to login if not authenticated."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    """Registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


# Protected admin routes - require authentication
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{path:path}", response_class=HTMLResponse)
async def admin_page(request: Request, path: str = ""):
    """Admin pages - require admin authentication."""
    try:
        # Check if user is logged in and is admin
        user = await get_current_user(request)
        if user.get("role") != Role.ADMIN.value:
            # Return 404 instead of 403 to hide admin page existence
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse("Not Found", status_code=404)
        return templates.TemplateResponse("admin.html", {"request": request, "user": user})
    except Exception:
        # Not authenticated - return 404 to hide page existence
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Not Found", status_code=404)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for load balancer and monitoring.
    
    Returns:
        dict: Standard API response with health status.
    """
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "healthy",
            "service": "AI Auth Demo Service v2.0"
        }
    }


if __name__ == "__main__":
    print("=" * 60)
    print("AI Foreign Language System - Auth Demo v2.0")
    print("=" * 60)
    print("")
    print("Features:")
    print("   - Dual HttpOnly Cookie Authentication")
    print("   - Redis Token Storage")
    print("   - Rate Limiting (5 attempts per 5 minutes)")
    print("   - RBAC Role-based Access Control")
    print("   - CSRF Protection")
    print("")
    print("Endpoints:")
    scheme = "https" if os.environ.get("SSL_CERTFILE") and os.environ.get("SSL_KEYFILE") else "http"
    host = "localhost:8001"
    print(f"   - Home: {scheme}://{host}")
    print(f"   - Login: {scheme}://{host}/login")
    print(f"   - Register: {scheme}://{host}/register")
    print("=" * 60)

    certfile = os.environ.get("SSL_CERTFILE")
    keyfile = os.environ.get("SSL_KEYFILE")
    if certfile and keyfile:
        print("Starting with HTTPS (ssl_certfile && ssl_keyfile provided)")
        uvicorn.run(app, host="0.0.0.0", port=8001, ssl_certfile=certfile, ssl_keyfile=keyfile)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001)

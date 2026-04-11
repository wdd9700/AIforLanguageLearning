# -*- coding: utf-8 -*-
"""Role-Based Access Control (RBAC) implementation.

Provides role definitions and permission decorators for FastAPI routes.
"""

from functools import wraps
from fastapi import HTTPException, status, Request
from typing import List, Optional, Callable
from enum import Enum


class Role(str, Enum):
    """User roles in the system."""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# Role hierarchy (higher = more permissions)
ROLE_HIERARCHY = {
    Role.STUDENT: 1,
    Role.TEACHER: 2,
    Role.ADMIN: 3
}

# Default permissions for each role
ROLE_PERMISSIONS = {
    Role.STUDENT: [
        "read:own_profile",
        "update:own_profile",
        "read:own_courses",
        "submit:homework",
    ],
    Role.TEACHER: [
        "read:own_profile",
        "update:own_profile",
        "read:own_courses",
        "create:course",
        "update:own_course",
        "delete:own_course",
        "grade:homework",
        "read:student_data",  # Only for their own students
    ],
    Role.ADMIN: [
        "*",  # All permissions
    ]
}


def get_user_role(user: dict) -> Optional[Role]:
    """Extract role from user data."""
    role_str = user.get("role", "student")
    try:
        return Role(role_str)
    except ValueError:
        return Role.STUDENT  # Default to student


def has_permission(user: dict, required_permission: str) -> bool:
    """Check if user has a specific permission."""
    role = get_user_role(user)
    
    # Admin has all permissions
    if role == Role.ADMIN:
        return True
    
    permissions = ROLE_PERMISSIONS.get(role, [])
    return required_permission in permissions or "*" in permissions


def has_role(user: dict, required_role: Role) -> bool:
    """Check if user has at least the required role level."""
    user_role = get_user_role(user)
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def require_role(required_role: Role):
    """Decorator to require a minimum role for a route.
    
    Usage:
        @app.get("/admin-only")
        @require_role(Role.ADMIN)
        async def admin_endpoint(current_user: dict = Depends(get_current_user)):
            return {"message": "Admin access granted"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            if not current_user:
                # Try to find in args (FastAPI injects dependencies)
                for arg in args:
                    if isinstance(arg, dict) and "username" in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_role(current_user, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {required_role.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(required_permission: str):
    """Decorator to require a specific permission for a route.
    
    Usage:
        @app.get("/courses")
        @require_permission("read:own_courses")
        async def list_courses(current_user: dict = Depends(get_current_user)):
            return {"courses": []}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                for arg in args:
                    if isinstance(arg, dict) and "username" in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_permission(current_user, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_owner_or_admin(resource_owner_id: str, current_user: dict):
    """Check if current user is the resource owner or admin."""
    user_role = get_user_role(current_user)
    user_id = str(current_user.get("id", ""))
    
    if user_role == Role.ADMIN:
        return True
    
    if user_id == str(resource_owner_id):
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only access your own resources"
    )


# FastAPI dependency for role checking
def check_role(required_role: Role):
    """FastAPI dependency for role checking.
    
    Usage:
        @app.get("/teacher-only")
        async def teacher_endpoint(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(check_role(Role.TEACHER))
        ):
            return {"message": "Teacher access granted"}
    """
    def _check(current_user: dict) -> None:
        if not has_role(current_user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
    return _check

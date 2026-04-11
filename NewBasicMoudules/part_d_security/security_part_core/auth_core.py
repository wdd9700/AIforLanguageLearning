# -*- coding: utf-8 -*-

"""Auth core module (ASCII-only)

Provides basic password hashing (PBKDF2), JWT token helpers and small
utility functions used by the example auth routes.

This simplified module is intended for local testing. It exposes the
same API surface expected by the auth routes in this project.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
from typing import Optional, Dict, Any
import secrets
import hashlib
import logging
import binascii
import html
import re

from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, validator

# bcrypt for password hashing (with automatic salt)
import bcrypt


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_core")


class JWTConfig:
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token (15 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    _secret_key: str = ""
    _key_created_at: Optional[datetime] = None
    KEY_ROTATION_DAYS: int = 30

    @classmethod
    def get_secret_key(cls) -> str:
        """Get JWT secret key from environment, file, or generate new one.
        
        Priority: environment var `JWT_SECRET_KEY` -> persisted file `.jwt_secret` -> in-memory (generate and persist)
        
        Returns:
            str: The secret key for JWT signing.
        """
        # Priority: environment var `JWT_SECRET_KEY` -> persisted file `.jwt_secret` -> in-memory (generate and persist)
        now = datetime.now(timezone.utc)
        env_key = os.environ.get("JWT_SECRET_KEY")
        if env_key:
            return env_key

        secret_file = Path(__file__).resolve().parent / ".jwt_secret"

        # If file exists, read it and check rotation based on file mtime
        try:
            if secret_file.exists():
                key_text = secret_file.read_text(encoding="utf-8").strip()
                if key_text:
                    try:
                        mtime = datetime.fromtimestamp(secret_file.stat().st_mtime, timezone.utc)
                        if (now - mtime).days >= cls.KEY_ROTATION_DAYS:
                            # rotate and persist
                            new_key = secrets.token_urlsafe(32)
                            secret_file.write_text(new_key, encoding="utf-8")
                            logger.info("Rotated JWT secret key (file)")
                            return new_key
                        return key_text
                    except Exception:
                        return key_text
        except Exception:
            logger.warning("Failed to read persisted JWT secret; falling back to memory")

        # fallback to in-memory key with rotation semantics
        if cls._secret_key and cls._key_created_at and (now - cls._key_created_at).days < cls.KEY_ROTATION_DAYS:
            return cls._secret_key

        # generate new key and attempt to persist
        new_key = secrets.token_urlsafe(32)
        try:
            secret_file.write_text(new_key, encoding="utf-8")
            logger.info("Initialized JWT secret key (persisted to file)")
        except Exception:
            logger.warning("Could not persist JWT secret to file, using in-memory key")

        cls._secret_key = new_key
        cls._key_created_at = now
        return cls._secret_key


def hash_password(password: str) -> str:
    """Hash password using bcrypt with automatic salt.
    
    bcrypt automatically generates a random salt and embeds it in the hash.
    The salt is part of the returned hash string, so no separate storage needed.
    """
    # bcrypt requires bytes input
    password_bytes = password.encode('utf-8')
    # bcrypt.gensalt() automatically generates a random salt
    # The work factor (rounds) is included in the salt
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a bcrypt hashed password.
    
    bcrypt automatically extracts the salt from the hash and uses it for verification.
    """
    try:
        if not isinstance(hashed_password, str):
            return False
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool = True
    created_at: datetime


# Reserved usernames that cannot be registered (security protection)
RESERVED_USERNAMES = {
    "null", "undefined", "none", "nan",
    "admin", "root", "system", "guest", "user", "test",
    "administrator", "superuser", "owner", "master",
    "api", "www", "mail", "ftp", "localhost", "127.0.0.1",
    "support", "help", "info", "contact", "service",
    "postgres", "mysql", "redis", "mongo", "database",
    "github", "gitlab", "docker", "kubernetes", "k8s"
}


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @validator("username")
    def username_reserved_check(cls, v):
        """Prevent registration of reserved/system usernames."""
        if v.lower() in RESERVED_USERNAMES:
            raise ValueError(f"username '{v}' is reserved and cannot be used")
        # Also check for common SQL injection patterns in username
        dangerous_patterns = ["'", "\"", ";", "--", "/*", "*/", "=", " or ", " and "]
        for pattern in dangerous_patterns:
            if pattern in v.lower():
                raise ValueError(f"username contains invalid characters")
        return v

    @validator("password")
    def password_complexity(cls, v):
        """Password complexity: uppercase, lowercase, digit required.
        Special characters are NOT required (to prevent SQL injection issues)."""
        if not any(c.isupper() for c in v):
            raise ValueError("password must include an uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("password must include a lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must include a digit")
        # Note: Special character requirement removed to prevent SQL injection risks
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenService:
    """Token service with Redis-backed revocation checking."""

    @classmethod
    def create_access_token(cls, user_id: str, expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
        """Create access token. Returns (token, jti)."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        jti = secrets.token_urlsafe(16)
        # Use numeric timestamps for exp/iat to avoid type inconsistencies
        payload = {"sub": user_id, "exp": int(expire.timestamp()), "iat": int(now.timestamp()), "type": "access", "jti": jti}
        token = jwt.encode(payload, JWTConfig.get_secret_key(), algorithm=JWTConfig.ALGORITHM)
        return token, jti

    @classmethod
    def create_refresh_token(cls, user_id: str, expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
        """Create refresh token. Returns (token, jti)."""
        if expires_delta is None:
            expires_delta = timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        jti = secrets.token_urlsafe(16)
        payload = {"sub": user_id, "exp": int(expire.timestamp()), "iat": int(now.timestamp()), "type": "refresh", "jti": jti}
        token = jwt.encode(payload, JWTConfig.get_secret_key(), algorithm=JWTConfig.ALGORITHM)
        return token, jti

    @classmethod
    def decode_token(cls, token: str, check_blacklist: bool = True) -> Optional[Dict[str, Any]]:
        """Decode and validate token."""
        from security_part.redis_store import TokenStore
        try:
            payload = jwt.decode(token, JWTConfig.get_secret_key(), algorithms=[JWTConfig.ALGORITHM])
            jti = payload.get("jti")
            if jti and check_blacklist:
                if TokenStore.is_blacklisted(jti):
                    logger.warning(f"Token blacklisted: {jti}")
                    return None
            return payload
        except JWTError as e:
            logger.warning(f"Token decode error: {e}")
            return None

    @classmethod
    def revoke_token(cls, token: str) -> bool:
        """Revoke a token by adding to blacklist."""
        from security_part.redis_store import TokenStore
        try:
            payload = jwt.decode(token, JWTConfig.get_secret_key(), algorithms=[JWTConfig.ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                # exp may be numeric timestamp; ensure it's a float timestamp
                try:
                    expiry_ts = float(exp)
                except Exception:
                    # If it's something else, skip blacklist
                    return False
                expires_in = int(expiry_ts - datetime.now(timezone.utc).timestamp())
                if expires_in > 0:
                    TokenStore.blacklist_token(jti, expires_in)
                    return True
        except JWTError:
            pass
        return False

    @classmethod
    def get_token_jti(cls, token: str) -> Optional[str]:
        """Extract JTI from token without full validation."""
        try:
            payload = jwt.decode(token, JWTConfig.get_secret_key(), algorithms=[JWTConfig.ALGORITHM])
            return payload.get("jti")
        except JWTError:
            return None


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    sensitive_fields = {"password", "passwd", "pwd", "secret", "token", "api_key", "authorization"}
    sanitized = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    return sanitized


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


# ==================== XSS Protection ====================

# Dangerous HTML tags that should be removed
DANGEROUS_HTML_TAGS = {
    'script', 'iframe', 'object', 'embed', 'form', 'input', 'textarea',
    'button', 'select', 'option', 'link', 'style', 'meta', 'base',
    'frame', 'frameset', 'applet', 'marquee', 'blink'
}

# Dangerous attributes that should be removed
DANGEROUS_ATTRIBUTES = {
    'onerror', 'onload', 'onclick', 'onmouseover', 'onmouseout',
    'onmousedown', 'onmouseup', 'onmousemove', 'onkeydown', 'onkeyup',
    'onkeypress', 'onfocus', 'onblur', 'onchange', 'onsubmit', 'onreset',
    'onselect', 'onabort', 'onunload', 'onbeforeunload', 'onresize',
    'onscroll', 'ondblclick', 'oncontextmenu', 'javascript:', 'data:',
    'vbscript:', 'mocha:', 'livescript:'
}

# Dangerous URL schemes
DANGEROUS_SCHEMES = {'javascript:', 'data:', 'vbscript:', 'mocha:', 'livescript:'}


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS.
    
    Converts: < > & " ' to HTML entities
    """
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text, quote=True)


def sanitize_html(text: str) -> str:
    """Remove dangerous HTML tags and attributes.
    
    This is a basic sanitizer - for production use consider bleach library.
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Remove dangerous tags
    for tag in DANGEROUS_HTML_TAGS:
        # Remove opening tags
        text = re.sub(rf'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
        # Remove closing tags
        text = re.sub(rf'</{tag}>', '', text, flags=re.IGNORECASE)
    
    # Remove dangerous attributes (event handlers and dangerous schemes)
    for attr in DANGEROUS_ATTRIBUTES:
        # Match attribute="value" or attribute='value' with any content
        text = re.sub(rf'\s{attr}=["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        # Also match attribute without quotes (value until space or >)
        text = re.sub(rf'\s{attr}=[^\s>]+', '', text, flags=re.IGNORECASE)
    
    # Remove dangerous URL schemes
    for scheme in DANGEROUS_SCHEMES:
        text = re.sub(rf'{scheme}[^\s"\'>]*', '', text, flags=re.IGNORECASE)
    
    return text


def xss_filter(text: str, strict: bool = True) -> str:
    """Complete XSS filtering: sanitize + escape.
    
    Args:
        text: Input text to filter
        strict: If True, escape all HTML; if False, only remove dangerous tags
        
    Returns:
        Safe text string
    """
    if not isinstance(text, str):
        text = str(text)
    
    # First sanitize dangerous HTML
    text = sanitize_html(text)
    
    if strict:
        # Escape all remaining HTML
        text = escape_html(text)
    
    return text


def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all string values in user input dict.
    
    Recursively processes nested dicts and lists.
    """
    if isinstance(data, dict):
        return {k: sanitize_user_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_user_input(item) for item in data]
    elif isinstance(data, str):
        return xss_filter(data, strict=True)
    else:
        return data


class SensitiveOperation:
    """Sensitive operation confirmation system.
    
    Requires users to confirm sensitive actions (password change, account deletion)
    by providing current password again.
    """
    _pending_confirmations: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def require_confirmation(cls, user_id: str, operation_type: str, operation_data: Dict[str, Any], expires_minutes: int = 10) -> str:
        """Create a confirmation token for sensitive operation.
        
        Args:
            user_id: The user requesting the operation
            operation_type: Type of operation (e.g., 'change_password', 'delete_account')
            operation_data: Additional data for the operation
            expires_minutes: Token validity period
            
        Returns:
            Confirmation token to be sent to user
        """
        token = secrets.token_urlsafe(32)
        expire_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        cls._pending_confirmations[token] = {
            "user_id": user_id, 
            "operation_type": operation_type, 
            "operation_data": operation_data, 
            "expire_at": expire_at
        }
        return token

    @classmethod
    def confirm_operation(cls, token: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Confirm a sensitive operation with token.
        
        Args:
            token: The confirmation token
            user_id: The user confirming the operation
            
        Returns:
            Operation data if confirmed, None otherwise
        """
        op = cls._pending_confirmations.get(token)
        if not op or op.get("user_id") != user_id:
            return None
        if datetime.now(timezone.utc) > op.get("expire_at"):
            del cls._pending_confirmations[token]
            return None
        data = op.get("operation_data")
        del cls._pending_confirmations[token]
        return {"operation_type": op.get("operation_type"), "operation_data": data}

    @classmethod
    def verify_password_confirmation(cls, user_id: str, password: str) -> bool:
        """Verify user's current password for sensitive operation confirmation.
        
        This is the recommended approach: require user to re-enter current password
        instead of using a separate confirmation token.
        
        Args:
            user_id: The username/user_id
            password: The current password provided by user
            
        Returns:
            True if password matches, False otherwise
        """
        from security_part.user_store import UserStore
        user = UserStore.get_user_by_username(user_id)
        if not user:
            return False
        return verify_password(password, user.get("hashed_password", ""))


if __name__ == "__main__":
    # simple self-test
    pw = "TestPassword123"
    h = hash_password(pw)
    print("hash:", h)
    print("verify:", verify_password(pw, h))

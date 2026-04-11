# -*- coding: utf-8 -*-
"""Redis-based token storage and rate limiting.

This module provides:
- Refresh token storage in Redis
- Login attempt rate limiting
- Token blacklisting for logout
"""

import json
import redis
from datetime import datetime, timezone
from typing import Optional
import os

# Redis connection settings
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)


class RedisStore:
    """Redis client wrapper for token management and rate limiting."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance
    
    @property
    def client(self):
        """Get or create Redis client with fallback to memory store."""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # Test connection
                self._client.ping()
            except redis.ConnectionError as e:
                # Fallback to memory store if Redis is not available
                print(f"Warning: Redis not available ({e}), using memory fallback")
                self._client = MemoryFallbackStore()
        return self._client


class MemoryFallbackStore:
    """In-memory fallback when Redis is not available."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    def setex(self, key, seconds, value):
        self._data[key] = value
        self._expiry[key] = datetime.now(timezone.utc).timestamp() + seconds
    
    def get(self, key):
        if key in self._expiry:
            if datetime.now(timezone.utc).timestamp() > self._expiry[key]:
                self.delete(key)
                return None
        return self._data.get(key)
    
    def delete(self, key):
        self._data.pop(key, None)
        self._expiry.pop(key, None)
    
    def exists(self, key):
        return 1 if self.get(key) is not None else 0
    
    def ping(self):
        return True
    
    def incr(self, key):
        current = int(self._data.get(key, 0))
        self._data[key] = current + 1
        return current + 1
    
    def expire(self, key, seconds):
        if key in self._data:
            self._expiry[key] = datetime.now(timezone.utc).timestamp() + seconds
            return 1
        return 0


class TokenStore:
    """Token storage using Redis."""
    
    PREFIX_REFRESH = "refresh_token:"
    PREFIX_BLACKLIST = "blacklist:"
    
    @classmethod
    def store_refresh_token(cls, jti: str, user_id: str, expires_in_days: int = 7) -> bool:
        """Store refresh token JTI in Redis."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_REFRESH}{jti}"
            data = json.dumps({"user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()})
            r.setex(key, expires_in_days * 24 * 3600, data)
            return True
        except Exception as e:
            print(f"Error storing refresh token: {e}")
            return False
    
    @classmethod
    def validate_refresh_token(cls, jti: str) -> Optional[str]:
        """Validate refresh token and return user_id if valid."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_REFRESH}{jti}"
            data = r.get(key)
            if data:
                return json.loads(data).get("user_id")
            return None
        except Exception as e:
            print(f"Error validating refresh token: {e}")
            return None
    
    @classmethod
    def revoke_refresh_token(cls, jti: str) -> bool:
        """Revoke a refresh token."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_REFRESH}{jti}"
            r.delete(key)
            return True
        except Exception as e:
            print(f"Error revoking refresh token: {e}")
            return False
    
    @classmethod
    def blacklist_token(cls, jti: str, expires_in_seconds: int) -> bool:
        """Add a token JTI to blacklist."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_BLACKLIST}{jti}"
            r.setex(key, expires_in_seconds, "revoked")
            return True
        except Exception as e:
            print(f"Error blacklisting token: {e}")
            return False
    
    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_BLACKLIST}{jti}"
            return r.exists(key) > 0
        except Exception as e:
            print(f"Error checking blacklist: {e}")
            return False


class RateLimiter:
    """Rate limiting for login attempts."""
    
    PREFIX_LOGIN = "login_attempts:"
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 300  # 5 minutes
    
    @classmethod
    def is_allowed(cls, identifier: str) -> tuple[bool, int]:
        """Check if login attempt is allowed.
        
        Returns: (is_allowed, remaining_attempts)
        """
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_LOGIN}{identifier}"
            
            current = r.get(key)
            if current is None:
                # First attempt
                r.setex(key, cls.WINDOW_SECONDS, "1")
                return True, cls.MAX_ATTEMPTS - 1
            
            attempts = int(current)
            if attempts >= cls.MAX_ATTEMPTS:
                return False, 0
            
            # Increment attempt count
            r.incr(key)
            return True, cls.MAX_ATTEMPTS - attempts - 1
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            # Allow on error (fail open for availability)
            return True, cls.MAX_ATTEMPTS
    
    @classmethod
    def reset(cls, identifier: str) -> bool:
        """Reset rate limit for an identifier (e.g., after successful login)."""
        try:
            r = RedisStore().client
            key = f"{cls.PREFIX_LOGIN}{identifier}"
            r.delete(key)
            return True
        except Exception as e:
            print(f"Error resetting rate limit: {e}")
            return False


# Initialize Redis connection on module load
_redis_store = RedisStore()

"""
Failed-login tracking and account lockout.

Brute-force defence: count failed logins per email per rolling window.
After N failures in the window, lock the account for a cool-down period.

Stored in Redis so it's automatic-expiry and shared across replicas.
Falls back to in-memory storage if Redis isn't reachable, which is
acceptable for development.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

# Policy
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60       # rolling window
LOCKOUT_SECONDS = 30 * 60      # how long an account is locked

_KEY_PREFIX = "login_fail:"
_LOCKOUT_PREFIX = "login_lock:"


class _InMemoryFallback:
    """Used when Redis is unavailable — single-process only."""

    def __init__(self):
        self._store: dict[str, list[float]] = {}
        self._locks: dict[str, float] = {}

    def record_failure(self, email: str) -> int:
        now = time.time()
        history = [t for t in self._store.get(email, []) if t > now - WINDOW_SECONDS]
        history.append(now)
        self._store[email] = history
        return len(history)

    def is_locked(self, email: str) -> bool:
        until = self._locks.get(email)
        if until and until > time.time():
            return True
        if until:
            self._locks.pop(email, None)
        return False

    def lock(self, email: str) -> None:
        self._locks[email] = time.time() + LOCKOUT_SECONDS

    def clear(self, email: str) -> None:
        self._store.pop(email, None)
        self._locks.pop(email, None)


class FailedLoginTracker:
    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self._fallback = _InMemoryFallback()
        try:
            self._redis = redis_client or redis.from_url(
                settings.redis_url, decode_responses=True
            )
            self._redis.ping()
            logger.info("FailedLoginTracker using Redis")
        except (redis.RedisError, OSError) as exc:
            logger.warning("Redis unavailable for login tracking (%s); using memory", exc)
            self._redis = None

    def _email_key(self, email: str) -> str:
        return f"{_KEY_PREFIX}{email.lower()}"

    def _lock_key(self, email: str) -> str:
        return f"{_LOCKOUT_PREFIX}{email.lower()}"

    def record_failure(self, email: str) -> int:
        """
        Record a failed attempt. Returns the current count in the window.
        Auto-locks the account when MAX_ATTEMPTS is reached.
        """
        if not self._redis:
            count = self._fallback.record_failure(email)
            if count >= MAX_ATTEMPTS:
                self._fallback.lock(email)
            return count
        try:
            key = self._email_key(email)
            now = int(time.time())
            pipe = self._redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
            pipe.zcard(key)
            pipe.expire(key, WINDOW_SECONDS)
            _, _, count, _ = pipe.execute()
            count = int(count)
            if count >= MAX_ATTEMPTS:
                self._redis.setex(self._lock_key(email), LOCKOUT_SECONDS, "1")
            return count
        except redis.RedisError:
            logger.warning("Redis failed during record_failure; using fallback")
            return self._fallback.record_failure(email)

    def is_locked(self, email: str) -> bool:
        if not self._redis:
            return self._fallback.is_locked(email)
        try:
            return bool(self._redis.exists(self._lock_key(email)))
        except redis.RedisError:
            return self._fallback.is_locked(email)

    def clear(self, email: str) -> None:
        """Call after a successful login."""
        if not self._redis:
            self._fallback.clear(email)
            return
        try:
            self._redis.delete(self._email_key(email), self._lock_key(email))
        except redis.RedisError:
            self._fallback.clear(email)


# Lazy singleton — instantiated on first use to allow test-time Redis mocking
_tracker: Optional[FailedLoginTracker] = None


def get_tracker() -> FailedLoginTracker:
    global _tracker
    if _tracker is None:
        _tracker = FailedLoginTracker()
    return _tracker

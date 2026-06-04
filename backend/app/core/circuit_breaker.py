"""
Circuit breaker for outbound API calls.

Pattern:

    closed → too many recent failures → open (reject fast for cooldown)
                                       ↓ after cooldown elapses
                                      half_open → next success closes it,
                                                  next failure re-opens

This protects the worker pool from spending its time on calls that
are guaranteed to fail (e.g. Companies House outage, API key revoked).
Once tripped, workers fail-fast and the scheduled poll backs off so
we don't drain our rate-limit budget on errors.

Thread/process-local. For multi-worker consistency a Redis-backed
breaker would be preferable; for our scale, per-worker is fine since
each worker independently observes the same upstream state.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

State = Literal["closed", "open", "half_open"]


class CircuitOpenError(RuntimeError):
    """Raised when the breaker rejects a call without attempting it."""


@dataclass
class CircuitBreaker:
    """
    Args:
        name             : identifier for logs/metrics
        failure_threshold: consecutive failures to trip from closed → open
        cooldown_seconds : how long to stay open before allowing a probe
        half_open_after  : alias kept for clarity; mirrors cooldown_seconds
    """
    name: str
    failure_threshold: int = 5
    cooldown_seconds: float = 60.0

    _state: State = field(default="closed", init=False)
    _failures: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def state(self) -> State:
        with self._lock:
            return self._maybe_transition_open_to_half_open_locked()

    def _maybe_transition_open_to_half_open_locked(self) -> State:
        if self._state == "open" and (time.monotonic() - self._opened_at) >= self.cooldown_seconds:
            self._state = "half_open"
        return self._state

    def allow(self) -> bool:
        """True when the next call should be attempted, False to fail-fast."""
        with self._lock:
            self._maybe_transition_open_to_half_open_locked()
            return self._state != "open"

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._state == "half_open" or self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = time.monotonic()

    def force_close(self) -> None:
        """Manual reset — for ops use."""
        with self._lock:
            self._state = "closed"
            self._failures = 0
            self._opened_at = 0.0

    def __call__(self, fn):
        """Decorator form: wraps a function with breaker logic."""
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not self.allow():
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is open — fail-fast until cooldown elapses"
                )
            try:
                result = fn(*args, **kwargs)
            except Exception:
                self.record_failure()
                raise
            self.record_success()
            return result

        return wrapper


# Process-wide singleton for Companies House. Workers import this and
# the same instance enforces fail-fast across all calls in that process.
companies_house_breaker = CircuitBreaker(
    name="companies_house",
    failure_threshold=5,
    cooldown_seconds=120.0,
)

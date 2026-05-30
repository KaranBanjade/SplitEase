import logging
import time
from uuid import UUID

import httpx
import pybreaker

from config import settings

logger = logging.getLogger(__name__)


class _AsyncCircuitBreaker:
    """Lightweight async circuit breaker (avoids pybreaker's tornado dependency)."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(self, fail_max: int = 3, reset_timeout: int = 30, name: str = ""):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._state = self.CLOSED
        self._fail_counter = 0
        self._opened_at: float | None = None

    @property
    def current_state(self) -> str:
        if self._state == self.OPEN:
            if self._opened_at and time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = self.HALF_OPEN
        return self._state

    async def call(self, coro_func, *args, **kwargs):
        if self.current_state == self.OPEN:
            raise pybreaker.CircuitBreakerError(self.name)
        try:
            result = await coro_func(*args, **kwargs)
            if self._state == self.HALF_OPEN:
                self._state = self.CLOSED
                self._fail_counter = 0
                logger.info("Circuit breaker '%s' recovered (closed)", self.name)
            return result
        except (httpx.ConnectError, httpx.TimeoutException):
            self._fail_counter += 1
            if self._fail_counter >= self.fail_max:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
                logger.warning("Circuit breaker '%s' opened", self.name)
            raise


_auth_breaker = _AsyncCircuitBreaker(fail_max=3, reset_timeout=30, name="expense→auth-service")


async def get_user(user_id: UUID) -> dict | None:
    """Fetch a single user from the auth service by UUID."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await _auth_breaker.call(
                client.get,
                f"{settings.AUTH_SERVICE_URL}/internal/users/{user_id}",
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except pybreaker.CircuitBreakerError:
            logger.warning(
                "Circuit breaker open — skipping auth lookup for user %s", user_id
            )
        except httpx.RequestError as exc:
            logger.warning("Auth service request failed for user %s: %s", user_id, exc)
    return None


async def get_user_by_email(email: str) -> dict | None:
    """Fetch a user from the auth service by email address."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await _auth_breaker.call(
                client.get,
                f"{settings.AUTH_SERVICE_URL}/internal/users/by-email/{email}",
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except pybreaker.CircuitBreakerError:
            logger.warning(
                "Circuit breaker open — skipping auth lookup for email %s", email
            )
        except httpx.RequestError as exc:
            logger.warning("Auth service request failed for email %s: %s", email, exc)
    return None


async def get_users_batch(user_ids: list[UUID]) -> dict[str, dict]:
    """
    Fetch multiple users concurrently.
    Returns {user_id_str: user_dict} for all successfully resolved users.
    """
    import asyncio

    results: dict[str, dict] = {}

    async def fetch_one(uid: UUID) -> None:
        user = await get_user(uid)
        if user:
            results[str(uid)] = user

    await asyncio.gather(*[fetch_one(uid) for uid in set(user_ids)])
    return results

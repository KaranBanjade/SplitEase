import asyncio
import logging
import time

import httpx
import pybreaker
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from config import settings

logger = logging.getLogger(__name__)

# Route table: path prefix → base URL of target service
# The "/api" portion is stripped before forwarding.
AUTH_PREFIX = "/api/auth"
EXPENSE_PREFIXES = (
    "/api/groups",
    "/api/expenses",
    "/api/settlements",
    "/api/recurring",
)

# Headers that must not be forwarded verbatim to upstream services
_HOP_BY_HOP = frozenset(
    [
        "host",
        "content-length",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "connection",
        "keep-alive",
        "proxy-authorization",
        "proxy-authenticate",
    ]
)

# Response headers we should NOT copy back to the client
_SKIP_RESPONSE_HEADERS = frozenset(
    ["content-encoding", "transfer-encoding", "content-length"]
)


# ---------------------------------------------------------------------------
# Async-native circuit breaker
# (pybreaker.call_async requires tornado; this avoids that dependency)
# ---------------------------------------------------------------------------
class AsyncCircuitBreaker:
    """
    Simple async circuit breaker.
    States: CLOSED → OPEN (after fail_max failures) → HALF-OPEN (after reset_timeout s)
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(self, fail_max: int = 3, reset_timeout: int = 30, name: str = ""):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.name = name
        self._state = self.CLOSED
        self._fail_counter = 0
        self._opened_at: float | None = None

    @property
    def current_state(self) -> str:
        if self._state == self.OPEN:
            # Check if reset_timeout has elapsed → move to HALF_OPEN
            if self._opened_at and time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = self.HALF_OPEN
        return self._state

    @property
    def fail_counter(self) -> int:
        return self._fail_counter

    async def call(self, coro_func, *args, **kwargs):
        state = self.current_state

        if state == self.OPEN:
            raise pybreaker.CircuitBreakerError(self.name)

        try:
            result = await coro_func(*args, **kwargs)
            # Success — reset on HALF_OPEN, keep counter on CLOSED
            if state == self.HALF_OPEN:
                logger.info("Circuit breaker '%s' closed (recovered)", self.name)
                self._state = self.CLOSED
                self._fail_counter = 0
            return result

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            self._fail_counter += 1
            if self._fail_counter >= self.fail_max:
                logger.warning(
                    "Circuit breaker '%s' opened after %d failures",
                    self.name, self._fail_counter,
                )
                self._state = self.OPEN
                self._opened_at = time.monotonic()
            raise


# ---------------------------------------------------------------------------
# Circuit breakers — one per upstream service
# fail_max=3: open after 3 consecutive connection failures
# reset_timeout=30: attempt recovery after 30 s (HALF-OPEN state)
# ---------------------------------------------------------------------------
auth_breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=30, name="auth-service")
expense_breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=30, name="expense-service")


def get_target_url(path: str) -> tuple[str | None, AsyncCircuitBreaker | None]:
    """
    Map an incoming /api/<service>/... path to the upstream service URL.
    Returns (url, breaker) or (None, None) when no upstream is found.
    """
    if path.startswith(AUTH_PREFIX):
        return settings.AUTH_SERVICE_URL + path[4:], auth_breaker  # strip '/api'

    for prefix in EXPENSE_PREFIXES:
        if path.startswith(prefix):
            return settings.EXPENSE_SERVICE_URL + path[4:], expense_breaker

    return None, None


async def proxy_request(request: Request) -> Response:
    """
    Forward *request* to the appropriate upstream service and return the
    upstream response verbatim.  Adds X-Forwarded-For and X-User-Id headers.
    Circuit breakers prevent cascading failures when an upstream is down.
    """
    target, breaker = get_target_url(request.url.path)
    if not target:
        return JSONResponse(status_code=404, content={"detail": "Route not found"})

    # Preserve the original query string
    if request.url.query:
        target = f"{target}?{request.url.query}"

    body = await request.body()

    # Build forwarded headers
    headers: dict[str, str] = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    if request.client:
        headers["X-Forwarded-For"] = request.client.host
        headers["X-Forwarded-Proto"] = request.url.scheme
    # Propagate the authenticated user-id so upstream services can trust it
    if hasattr(request.state, "user_id") and request.state.user_id:
        headers["X-User-Id"] = str(request.state.user_id)

    service_name = breaker.name if breaker else "unknown"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_resp = await breaker.call(
                client.request,
                method=request.method,
                url=target,
                headers=headers,
                content=body,
            )
    except pybreaker.CircuitBreakerError:
        logger.warning("Circuit breaker OPEN for %s — rejecting request", service_name)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Service temporarily unavailable (circuit open)",
                "service": service_name,
            },
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Upstream service unavailable"},
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"detail": "Upstream service timed out"},
        )
    except httpx.HTTPError as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Bad gateway: {exc}"},
        )

    # Strip hop-by-hop / encoding headers before returning to client
    response_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in _SKIP_RESPONSE_HEADERS
    }

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=response_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )

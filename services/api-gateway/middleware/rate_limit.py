"""
rate_limit.py
=============
Sliding-window rate limiter middleware.

Uses Redis sorted sets when available (set ``_shared_redis`` from main.py
after the Redis connection is established).  Falls back to an in-process
dict so the service still operates when Redis is unreachable.

Window:  60 seconds
Limit:   settings.RATE_LIMIT_PER_MINUTE requests per IP
"""
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis
from config import settings

# Module-level reference injected by main.py after the Redis pool is ready.
# Using a module-level var avoids needing to introspect the middleware stack.
_shared_redis: aioredis.Redis | None = None

# Paths that bypass rate limiting entirely
_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding-window rate limiter.

    Redis (preferred):   O(log N) via ZREMRANGEBYSCORE + ZADD + ZCARD pipeline
    In-memory fallback:  simple list of timestamps per IP key
    """

    def __init__(self, app):
        super().__init__(app)
        # Per-instance in-memory fallback store
        self._local_counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            path in _EXEMPT_PATHS
            or path.startswith("/docs")
            or path.startswith("/openapi")
            or path.startswith("/redoc")
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window = 60  # seconds

        allowed = await self._check_rate_limit(key, now, window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Limit is 100 per minute."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    async def _check_rate_limit(self, key: str, now: float, window: int) -> bool:
        """Return True if the request is within the rate limit."""
        redis = _shared_redis  # read module-level reference
        if redis is not None:
            try:
                pipe = redis.pipeline()
                # Remove timestamps outside the current window
                pipe.zremrangebyscore(key, 0, now - window)
                # Record this request (use float-as-string member for uniqueness)
                pipe.zadd(key, {f"{now:.6f}": now})
                # Count requests in the window
                pipe.zcard(key)
                # Auto-expire the key so Redis doesn't accumulate stale entries
                pipe.expire(key, window * 2)
                results = await pipe.execute()
                count: int = results[2]
                return count <= settings.RATE_LIMIT_PER_MINUTE
            except Exception:
                # Redis hiccup – fall through to in-memory
                pass

        # ── In-memory fallback ────────────────────────────────────────────────
        timestamps = self._local_counts.get(key, [])
        timestamps = [t for t in timestamps if now - t < window]
        timestamps.append(now)
        self._local_counts[key] = timestamps
        return len(timestamps) <= settings.RATE_LIMIT_PER_MINUTE

"""
main.py – API Gateway entry point
==================================
Starts FastAPI with:
  - CORS middleware
  - Auth middleware  (JWT validation, innermost)
  - Rate-limit middleware  (Redis sliding-window, outermost)
  - /api/dashboard aggregate endpoint
  - Catch-all proxy route that forwards to auth-service / expense-service
  - /health probe

Redis is optional: if unavailable the rate-limiter falls back to an
in-process dictionary.  The live Redis client is shared with the
RateLimitMiddleware instance via the module-level ``_shared_redis`` variable
in the rate_limit module.
"""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import redis.asyncio as aioredis

from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware import rate_limit as _rl_module  # to inject shared redis
from routers.aggregate import router as aggregate_router
from proxy import proxy_request, auth_breaker, expense_breaker, AsyncCircuitBreaker
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application lifespan: connect to Redis on start, close on shutdown
# ---------------------------------------------------------------------------
_redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis_client
    try:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
        )
        await _redis_client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        # Make the live client available to RateLimitMiddleware instances
        _rl_module._shared_redis = _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) – using in-memory rate limiting", exc)
        _redis_client = None

    yield  # ← application runs here

    if _redis_client:
        await _redis_client.aclose()
        logger.info("Redis connection closed")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SplitEase API Gateway",
    version="1.0.0",
    description="Single entry-point that routes requests to auth-service and expense-service.",
    lifespan=lifespan,
)

# CORS – allow all origins in development; tighten in production via env vars
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Starlette applies middleware in reverse registration order, so the
# last middleware added is the *outermost* wrapper.  We want:
#   client → RateLimit → Auth → router/proxy
# Auth is registered first (inner), RateLimit second (outer).
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(aggregate_router, prefix="/api")


# ---------------------------------------------------------------------------
# Catch-all proxy route – must be registered AFTER specific routes
# ---------------------------------------------------------------------------
@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def gateway(request: Request, path: str) -> Response:  # noqa: ARG001
    return await proxy_request(request)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
async def health():
    redis_ok = False
    if _redis_client:
        try:
            await _redis_client.ping()
            redis_ok = True
        except Exception:
            pass
    return {
        "status": "ok",
        "service": "api-gateway",
        "redis": redis_ok,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/breakers", tags=["ops"])
async def breaker_status():
    """Expose circuit breaker states — useful for the failure demo."""
    return {
        "auth-service": {
            "state": auth_breaker.current_state,
            "fail_counter": auth_breaker.fail_counter,
        },
        "expense-service": {
            "state": expense_breaker.current_state,
            "fail_counter": expense_breaker.fail_counter,
        },
    }

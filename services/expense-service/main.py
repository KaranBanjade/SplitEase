import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import engine, Base
from routers import groups, expenses, settlements, recurring

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB schema + tables
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS expenses_schema"))
        await conn.run_sync(Base.metadata.create_all)

    # Redis — used to publish events to the message queue
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — event publishing disabled", exc)
        app.state.redis = None

    yield

    if redis_client:
        await redis_client.aclose()
    await engine.dispose()


app = FastAPI(title="Expense Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
app.include_router(settlements.router, prefix="/settlements", tags=["settlements"])
app.include_router(recurring.router, prefix="/recurring", tags=["recurring"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "expense"}

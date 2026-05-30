import asyncio
import logging
from fastapi import APIRouter, Request, HTTPException
import httpx
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _safe_get(client: httpx.AsyncClient, url: str, headers: dict) -> dict | list | None:
    """
    Perform a GET request and return parsed JSON on HTTP 200, or None on any
    error (network, non-200, timeout, JSON decode failure).
    """
    try:
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Dashboard aggregate: request to %s failed: %s", url, exc)
    return None


@router.get("/dashboard")
async def dashboard(request: Request):
    """
    Aggregate endpoint that combines:
    - Current user profile (auth-service /me)
    - User's groups (expense-service /groups)
    - Per-group balance summary (expense-service /groups/{id}/balances)

    All upstream requests are fired concurrently.  Partial failures are
    tolerated — missing data is returned as null / empty lists.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")

    forward_headers = {"Authorization": auth_header}
    # Also propagate authenticated user-id set by auth middleware
    if hasattr(request.state, "user_id") and request.state.user_id:
        forward_headers["X-User-Id"] = str(request.state.user_id)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # ── Phase 1: fetch user profile and groups in parallel ──────────────
        user_data, groups_data = await asyncio.gather(
            _safe_get(client, f"{settings.AUTH_SERVICE_URL}/me", forward_headers),
            _safe_get(client, f"{settings.EXPENSE_SERVICE_URL}/groups", forward_headers),
        )

        user: dict | None = user_data if isinstance(user_data, dict) else None
        groups: list = groups_data if isinstance(groups_data, list) else []

        # ── Phase 2: fetch balances for up to 5 groups in parallel ──────────
        top_groups = groups[:5]
        balance_tasks = [
            _safe_get(
                client,
                f"{settings.EXPENSE_SERVICE_URL}/groups/{g['id']}/balances",
                forward_headers,
            )
            for g in top_groups
            if isinstance(g, dict) and "id" in g
        ]
        balance_results = await asyncio.gather(*balance_tasks)

    # ── Aggregate balance totals ─────────────────────────────────────────────
    user_id = str(user.get("id", "")) if user else ""
    total_owed_to_you = 0.0   # others owe the current user
    total_you_owe = 0.0        # current user owes others

    for balance_list in balance_results:
        if not isinstance(balance_list, list):
            continue
        for entry in balance_list:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("user_id", "")) == user_id:
                amt = float(entry.get("amount", 0))
                if amt > 0:
                    total_owed_to_you += amt
                elif amt < 0:
                    total_you_owe += abs(amt)

    return {
        "user": user,
        "groups": top_groups,
        "summary": {
            "total_owed_to_you": round(total_owed_to_you, 2),
            "total_you_owe": round(total_you_owe, 2),
            "net_balance": round(total_owed_to_you - total_you_owe, 2),
        },
    }

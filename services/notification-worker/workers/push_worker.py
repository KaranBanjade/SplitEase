"""
push_worker.py
==============
Weekly job that sends Web Push notifications reminding users about overdue
settlements.

Push subscriptions are stored in the database table:
  auth_schema.push_subscriptions(user_id, endpoint, p256dh, auth_key)

VAPID keys must be set via environment variables:
  VAPID_PRIVATE_KEY  – base64url-encoded private key
  VAPID_PUBLIC_KEY   – base64url-encoded public key
  VAPID_CLAIMS_EMAIL – mailto: address embedded in the VAPID JWT claims

The pywebpush library handles VAPID signing + AESGCM payload encryption.
"""
import asyncio
import json
import logging
from typing import Any

from pywebpush import webpush, WebPushException
from sqlalchemy import text

from ..database import AsyncSessionLocal
from ..config import settings

logger = logging.getLogger(__name__)


# ─── low-level push helper ──────────────────────────────────────────────────

def _send_web_push(
    subscription_info: dict[str, Any],
    title: str,
    body: str,
    url: str,
) -> None:
    """
    Synchronous helper – called via ``asyncio.to_thread`` so it does not
    block the event loop.

    ``subscription_info`` must have the shape expected by pywebpush:
      {
        "endpoint": "https://...",
        "keys": {"p256dh": "...", "auth": "..."}
      }
    """
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
            "icon": "/icons/icon-192.png",
        }
    )

    webpush(
        subscription_info=subscription_info,
        data=payload,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={
            "sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}",
        },
    )


async def send_push_to_user(
    user_id: str,
    title: str,
    body: str,
    url: str = "",
) -> int:
    """
    Send a push notification to all devices registered for *user_id*.
    Returns the number of successfully delivered notifications.
    """
    if not settings.VAPID_PRIVATE_KEY:
        logger.debug("VAPID keys not configured – push skipped for user %s", user_id)
        return 0

    target_url = url or settings.APP_URL
    delivered = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT endpoint, p256dh, auth_key
                FROM auth_schema.push_subscriptions
                WHERE user_id = :user_id
                  AND is_active = true
                """
            ),
            {"user_id": user_id},
        )
        subscriptions = result.fetchall()

    if not subscriptions:
        logger.debug("No push subscriptions for user %s", user_id)
        return 0

    stale_endpoints: list[str] = []

    for endpoint, p256dh, auth_key in subscriptions:
        sub_info = {
            "endpoint": endpoint,
            "keys": {"p256dh": p256dh, "auth": auth_key},
        }
        try:
            await asyncio.to_thread(_send_web_push, sub_info, title, body, target_url)
            delivered += 1
        except WebPushException as exc:
            # HTTP 410 Gone means the subscription was unregistered by the browser
            if exc.response is not None and exc.response.status_code == 410:
                logger.info(
                    "Push subscription expired for user %s (endpoint: %.60s…)",
                    user_id,
                    endpoint,
                )
                stale_endpoints.append(endpoint)
            else:
                logger.warning(
                    "Push failed for user %s: %s", user_id, exc
                )
        except Exception as exc:
            logger.warning("Push failed for user %s: %s", user_id, exc)

    # ── Remove stale subscriptions ──────────────────────────────────────────
    if stale_endpoints:
        async with AsyncSessionLocal() as db:
            for ep in stale_endpoints:
                await db.execute(
                    text(
                        """
                        UPDATE auth_schema.push_subscriptions
                        SET is_active = false,
                            updated_at = NOW()
                        WHERE endpoint = :ep
                        """
                    ),
                    {"ep": ep},
                )
            await db.commit()

    return delivered


# ─── weekly job ─────────────────────────────────────────────────────────────

async def send_settlement_reminders() -> None:
    """
    Weekly job: push a reminder to every user who has an unsettled debt older
    than 7 days.  Notification includes total amount owed so users act fast.
    """
    if not settings.VAPID_PRIVATE_KEY:
        logger.info("VAPID keys not configured – skipping push reminders")
        return

    logger.info("Starting weekly settlement push reminders")
    notified = skipped = failed = 0

    async with AsyncSessionLocal() as db:
        # Users with overdue unsettled balances (created > 7 days ago)
        result = await db.execute(
            text(
                """
                SELECT
                    es.user_id,
                    g.currency,
                    SUM(es.owed_amount) AS total_owed,
                    COUNT(DISTINCT e.id) AS expense_count
                FROM expenses_schema.expense_splits es
                JOIN expenses_schema.expenses e  ON es.expense_id = e.id
                JOIN expenses_schema.groups   g  ON e.group_id    = g.id
                WHERE es.settled_at IS NULL
                  AND es.owed_amount > 0
                  AND e.created_at < NOW() - INTERVAL '7 days'
                GROUP BY es.user_id, g.currency
                HAVING SUM(es.owed_amount) > 0.009
                ORDER BY total_owed DESC
                """
            )
        )
        rows = result.fetchall()

    if not rows:
        logger.info("No overdue settlements – push job complete")
        return

    logger.info(
        "Sending settlement reminders to %d user-currency combination(s)",
        len(rows),
    )

    for user_id, currency, total_owed, expense_count in rows:
        try:
            amount_str = f"{currency} {float(total_owed):.2f}"
            exp_word = "expense" if expense_count == 1 else "expenses"
            delivered = await send_push_to_user(
                user_id=str(user_id),
                title="You have unsettled expenses",
                body=(
                    f"You owe {amount_str} across "
                    f"{expense_count} {exp_word}. Tap to settle up!"
                ),
                url=f"{settings.APP_URL}/settlements",
            )
            if delivered > 0:
                notified += 1
            else:
                skipped += 1
        except Exception as exc:
            failed += 1
            logger.error(
                "Failed to send reminder to user %s: %s", user_id, exc, exc_info=True
            )

    logger.info(
        "Settlement reminders done: %d notified, %d skipped (no subscription), %d failed",
        notified,
        skipped,
        failed,
    )

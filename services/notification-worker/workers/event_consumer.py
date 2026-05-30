"""
event_consumer.py
=================
Consumes events from the Redis Stream ``splitease:events`` published by
expense-service.  Runs as a long-lived asyncio Task alongside APScheduler.

Supported event types
---------------------
* ``expense.created`` – sends a push notification to every group member
  (except the creator) so they see the new expense immediately.
"""
import asyncio
import logging

import redis.asyncio as aioredis
from sqlalchemy import text

from ..database import AsyncSessionLocal
from ..config import settings
from .push_worker import send_push_to_user

logger = logging.getLogger(__name__)

STREAM_KEY = "splitease:events"
CONSUMER_GROUP = "splitease-notifications"
CONSUMER_NAME = "worker-1"


async def consume_events() -> None:
    """
    Main consumer loop.  Blocks with XREADGROUP (5 s timeout) so it yields
    the event loop regularly and responds promptly to CancelledError.
    """
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Create the consumer group if it doesn't exist yet.
    # mkstream=True also creates the stream key if Redis has never seen it.
    try:
        await client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(
            "Consumer group '%s' created on stream '%s'", CONSUMER_GROUP, STREAM_KEY
        )
    except Exception as exc:
        if "BUSYGROUP" in str(exc):
            logger.info("Consumer group '%s' already exists — resuming", CONSUMER_GROUP)
        else:
            logger.warning("xgroup_create warning: %s", exc)

    logger.info("Event consumer started, listening on stream '%s'", STREAM_KEY)

    try:
        while True:
            try:
                # ">" means: give me only NEW messages not yet delivered to any consumer
                messages = await client.xreadgroup(
                    CONSUMER_GROUP,
                    CONSUMER_NAME,
                    {STREAM_KEY: ">"},
                    count=10,
                    block=5000,  # block up to 5 s, then loop (allows clean cancellation)
                )
                if not messages:
                    continue

                for _stream, entries in messages:
                    for message_id, fields in entries:
                        await _handle_message(client, message_id, fields)

            except asyncio.CancelledError:
                raise  # propagate so the outer try/finally runs
            except Exception as exc:
                logger.error("Event consumer error: %s", exc, exc_info=True)
                await asyncio.sleep(5)  # back off before retrying

    finally:
        await client.aclose()
        logger.info("Event consumer stopped")


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------

async def _handle_message(
    client: aioredis.Redis, message_id: str, fields: dict
) -> None:
    event_type = fields.get("type")
    try:
        if event_type == "expense.created":
            await _handle_expense_created(fields)
        else:
            logger.debug("Unknown event type '%s' — skipping", event_type)
    except Exception as exc:
        logger.error(
            "Error handling message %s (type=%s): %s", message_id, event_type, exc,
            exc_info=True,
        )
    finally:
        # Always ACK — even on error — so the message doesn't requeue forever
        await client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)


# ---------------------------------------------------------------------------
# Handler: expense.created
# ---------------------------------------------------------------------------

async def _handle_expense_created(fields: dict) -> None:
    expense_id = fields.get("expense_id", "?")
    group_id = fields.get("group_id")
    created_by = fields.get("created_by")
    description = fields.get("description", "A new expense")
    amount = fields.get("amount", "0")

    logger.info(
        "expense.created event: expense=%s group=%s created_by=%s",
        expense_id, group_id, created_by,
    )

    if not group_id:
        logger.warning("expense.created event missing group_id — skipping")
        return

    # Fetch group members from the expenses DB schema
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT user_id FROM expenses_schema.group_members "
                "WHERE group_id = :gid"
            ),
            {"gid": group_id},
        )
        member_ids = [str(row[0]) for row in result.fetchall()]

    if not member_ids:
        logger.debug("No members found for group %s", group_id)
        return

    notified = 0
    for member_id in member_ids:
        if member_id == created_by:
            continue  # don't notify the person who created the expense
        try:
            delivered = await send_push_to_user(
                user_id=member_id,
                title="New expense added",
                body=f"{description} — {amount}",
                url=f"{settings.APP_URL}/groups/{group_id}",
            )
            notified += delivered
        except Exception as exc:
            logger.warning("Push failed for member %s: %s", member_id, exc)

    logger.info(
        "expense.created: notified %d member(s) for expense %s",
        notified, expense_id,
    )

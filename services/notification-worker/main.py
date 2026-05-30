"""
main.py – Notification Worker entry point
=========================================
Starts two concurrent async components:

  1. APScheduler (AsyncIOScheduler) with three cron jobs:
       • Daily   09:00 UTC  – process_recurring_expenses
       • Weekly  Mon 08:00  – send_weekly_digests  (email)
       • Weekly  Mon 09:00  – send_settlement_reminders (push)

  2. Redis Stream consumer (event_consumer.consume_events):
       • Listens on stream ``splitease:events``
       • Reacts to ``expense.created`` by sending immediate push notifications

Run with:
  python -m notification_worker   (package mode, from services/ directory)
  python -m main                  (direct module, from this directory)
"""
import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .workers.recurring_worker import process_recurring_expenses
from .workers.email_worker import send_weekly_digests
from .workers.push_worker import send_settlement_reminders
from .workers.event_consumer import consume_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # ── Job 1: Process recurring expenses daily at 09:00 UTC ────────────────
    scheduler.add_job(
        process_recurring_expenses,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="recurring_expenses",
        name="Process recurring expenses",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1-hour late start
    )

    # ── Job 2: Weekly digest emails every Monday at 08:00 UTC ───────────────
    scheduler.add_job(
        send_weekly_digests,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="UTC"),
        id="weekly_email_digest",
        name="Send weekly balance digest emails",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # ── Job 3: Weekly push reminders every Monday at 09:00 UTC ──────────────
    scheduler.add_job(
        send_settlement_reminders,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="UTC"),
        id="weekly_push_reminders",
        name="Send settlement push reminders",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    return scheduler


async def main() -> None:
    logger.info("Notification worker starting…")

    scheduler = _build_scheduler()
    scheduler.start()

    logger.info("Scheduler started with %d job(s):", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  • [%s] next run: %s", job.name, job.next_run_time)

    # ── Redis Stream consumer ────────────────────────────────────────────────
    consumer_task = asyncio.create_task(consume_events(), name="event-consumer")
    logger.info("Redis Stream consumer started")

    # ── Graceful shutdown ────────────────────────────────────────────────────
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(sig):
        logger.info("Received signal %s – shutting down", sig.name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    # ── Keep alive ───────────────────────────────────────────────────────────
    try:
        await stop_event.wait()
    finally:
        logger.info("Cancelling event consumer…")
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        logger.info("Stopping scheduler…")
        scheduler.shutdown(wait=True)
        logger.info("Notification worker stopped")


if __name__ == "__main__":
    asyncio.run(main())

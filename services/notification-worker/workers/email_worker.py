"""
email_worker.py
===============
Weekly job that sends balance-digest emails to all users who have outstanding
balances in any of their groups.

Each email lists:
  - How much the user owes to each creditor  (direction = "owe")
  - How much each debtor owes the user       (direction = "owed")

User display-names are resolved via the auth-service's internal endpoint.
Emails are sent via the ``emails`` library over SMTP/TLS.
"""
import asyncio
import logging
from typing import Any

import emails
from emails.template import JinjaTemplate
from sqlalchemy import text

from ..database import AsyncSessionLocal
from ..config import settings
import httpx

logger = logging.getLogger(__name__)

# ─── HTML template ──────────────────────────────────────────────────────────

_DIGEST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SplitEase Weekly Summary</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    padding: 32px 16px;
  }
  .container {
    max-width: 600px;
    margin: 0 auto;
    background: #1e293b;
    border-radius: 12px;
    padding: 32px;
    border: 1px solid #334155;
  }
  .logo {
    font-size: 24px;
    font-weight: 700;
    color: #818cf8;
    margin-bottom: 24px;
  }
  .greeting { font-size: 16px; margin-bottom: 20px; color: #cbd5e1; }
  .section-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 12px;
  }
  .debt-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #0f172a;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 3px solid transparent;
  }
  .debt-row.owe   { border-color: #f87171; }
  .debt-row.owed  { border-color: #4ade80; }
  .debt-label { font-size: 14px; color: #e2e8f0; }
  .debt-label .name { font-weight: 600; }
  .debt-amount { font-size: 16px; font-weight: 700; }
  .owe  .debt-amount { color: #f87171; }
  .owed .debt-amount { color: #4ade80; }
  .settled {
    background: #0f172a;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    color: #4ade80;
    font-size: 16px;
  }
  .cta-wrapper { margin-top: 28px; text-align: center; }
  .cta {
    display: inline-block;
    background: #6366f1;
    color: #ffffff;
    padding: 12px 28px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 15px;
  }
  .footer {
    margin-top: 24px;
    font-size: 12px;
    color: #475569;
    text-align: center;
  }
</style>
</head>
<body>
<div class="container">
  <div class="logo">SplitEase</div>

  <p class="greeting">Hi {{ user_name }},<br>
  Here's your weekly expense summary.</p>

  {% if debts %}
  <p class="section-title">Outstanding Balances</p>

  {% for debt in debts %}
  <div class="debt-row {{ debt.direction }}">
    <div class="debt-label">
      {% if debt.direction == 'owe' %}
        You owe <span class="name">{{ debt.other_name }}</span>
        {% if debt.group_name %} &nbsp;<span style="color:#64748b;font-size:12px">({{ debt.group_name }})</span>{% endif %}
      {% else %}
        <span class="name">{{ debt.other_name }}</span> owes you
        {% if debt.group_name %} &nbsp;<span style="color:#64748b;font-size:12px">({{ debt.group_name }})</span>{% endif %}
      {% endif %}
    </div>
    <div class="debt-amount">{{ debt.currency }} {{ "%.2f"|format(debt.amount) }}</div>
  </div>
  {% endfor %}

  {% else %}
  <div class="settled">You are all settled up!</div>
  {% endif %}

  <div class="cta-wrapper">
    <a href="{{ app_url }}" class="cta">Open SplitEase</a>
  </div>

  <p class="footer">
    You are receiving this because you have an account on SplitEase.<br>
    To manage notification preferences, visit your account settings.
  </p>
</div>
</body>
</html>
"""

_DIGEST_TEMPLATE = JinjaTemplate(_DIGEST_HTML)


# ─── helpers ────────────────────────────────────────────────────────────────

async def _resolve_user_names(
    client: httpx.AsyncClient,
    user_ids: set[str],
) -> dict[str, str]:
    """
    Batch-resolve display names from the auth-service.
    Falls back to "Unknown" on any error.
    """
    names: dict[str, str] = {}
    tasks = {
        uid: client.get(
            f"{settings.AUTH_SERVICE_URL}/internal/users/{uid}",
            timeout=3.0,
        )
        for uid in user_ids
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for uid, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            names[uid] = "Unknown"
            continue
        if result.status_code == 200:
            names[uid] = result.json().get("name", "Unknown")
        else:
            names[uid] = "Unknown"
    return names


def _send_email(
    to_address: str,
    render_context: dict[str, Any],
) -> None:
    """
    Synchronous send via the ``emails`` library.
    Called from an async context via ``asyncio.to_thread``.
    """
    message = emails.Message(
        subject="SplitEase – Your Weekly Balance Summary",
        html=_DIGEST_TEMPLATE,
        mail_from=(settings.FROM_EMAIL, "SplitEase"),
    )
    smtp_params: dict = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
    }
    # Only add auth/TLS when credentials are provided (omit for Mailhog)
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        smtp_params["user"] = settings.SMTP_USER
        smtp_params["password"] = settings.SMTP_PASSWORD
        smtp_params["tls"] = True

    response = message.send(
        to=to_address,
        render=render_context,
        smtp=smtp_params,
    )
    return response


# ─── main job ───────────────────────────────────────────────────────────────

async def send_weekly_digests() -> None:
    """
    Weekly job: query all users with unsettled balances and email each one
    a personalised digest.
    """
    if not settings.SMTP_HOST:
        logger.info("SMTP_HOST not configured – skipping weekly digest emails")
        return

    logger.info("Starting weekly digest email job")
    sent = failed = skipped = 0

    async with AsyncSessionLocal() as db:
        # All users who are members of at least one group
        users_result = await db.execute(
            text(
                """
                SELECT DISTINCT u.id, u.email, u.name
                FROM auth_schema.users u
                JOIN expenses_schema.group_members gm ON u.id = gm.user_id
                WHERE u.is_active = true
                ORDER BY u.email
                """
            )
        )
        users = users_result.fetchall()

    if not users:
        logger.info("No active users found – digest job complete")
        return

    logger.info("Checking balances for %d user(s)", len(users))

    async with httpx.AsyncClient() as http_client:
        for user_id, email, user_name in users:
            try:
                async with AsyncSessionLocal() as db:
                    # Net balance per (debtor, creditor, group, currency)
                    debts_result = await db.execute(
                        text(
                            """
                            SELECT
                                es.user_id          AS debtor_id,
                                e.paid_by           AS creditor_id,
                                g.id                AS group_id,
                                g.name              AS group_name,
                                g.currency          AS currency,
                                SUM(es.owed_amount) AS total_owed
                            FROM expenses_schema.expense_splits es
                            JOIN expenses_schema.expenses  e ON es.expense_id = e.id
                            JOIN expenses_schema.groups    g ON e.group_id    = g.id
                            JOIN expenses_schema.group_members gm
                                 ON g.id = gm.group_id AND gm.user_id = :user_id
                            WHERE es.settled_at IS NULL
                              AND es.owed_amount > 0
                              AND (es.user_id = :user_id OR e.paid_by = :user_id)
                            GROUP BY es.user_id, e.paid_by, g.id, g.name, g.currency
                            HAVING SUM(es.owed_amount) > 0.009
                            ORDER BY total_owed DESC
                            """
                        ),
                        {"user_id": user_id},
                    )
                    raw_debts = debts_result.fetchall()

                if not raw_debts:
                    skipped += 1
                    continue  # nothing to report

                # Collect all user IDs that need name resolution
                peer_ids: set[str] = set()
                for row in raw_debts:
                    peer_ids.add(str(row[0]))  # debtor
                    peer_ids.add(str(row[1]))  # creditor
                peer_ids.discard(str(user_id))  # we already have this user's name

                user_names = await _resolve_user_names(http_client, peer_ids)
                user_names[str(user_id)] = user_name or "you"

                debts: list[dict] = []
                for debtor_id, creditor_id, _gid, group_name, currency, total_owed in raw_debts:
                    if str(debtor_id) == str(user_id):
                        debts.append(
                            {
                                "direction": "owe",
                                "other_name": user_names.get(str(creditor_id), "Unknown"),
                                "amount": float(total_owed),
                                "currency": currency,
                                "group_name": group_name,
                            }
                        )
                    else:
                        debts.append(
                            {
                                "direction": "owed",
                                "other_name": user_names.get(str(debtor_id), "Unknown"),
                                "amount": float(total_owed),
                                "currency": currency,
                                "group_name": group_name,
                            }
                        )

                render_ctx = {
                    "user_name": user_name or email,
                    "debts": debts,
                    "app_url": settings.APP_URL,
                }

                result = await asyncio.to_thread(_send_email, email, render_ctx)
                logger.info("Digest sent to %s (status %s)", email, result.status_code)
                sent += 1

            except Exception as exc:
                failed += 1
                logger.error("Failed to send digest to %s: %s", email, exc, exc_info=True)

    logger.info(
        "Weekly digest done: %d sent, %d skipped (no balance), %d failed",
        sent,
        skipped,
        failed,
    )

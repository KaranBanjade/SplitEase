import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template
from config import settings

logger = logging.getLogger(__name__)

PASSWORD_RESET_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset your SplitEase password</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding: 40px 0;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
          <tr>
            <td style="background-color: #4f46e5; padding: 30px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 28px;">SplitEase</h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="color: #1f2937; margin-top: 0;">Reset your password</h2>
              <p style="color: #6b7280; font-size: 16px; line-height: 1.6;">
                Hi {{ name }},
              </p>
              <p style="color: #6b7280; font-size: 16px; line-height: 1.6;">
                We received a request to reset your password for your SplitEase account.
                Click the button below to set a new password. This link will expire in 1 hour.
              </p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{{ reset_url }}"
                   style="background-color: #4f46e5; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold; display: inline-block;">
                  Reset Password
                </a>
              </div>
              <p style="color: #9ca3af; font-size: 14px; line-height: 1.6;">
                If you didn't request a password reset, you can safely ignore this email.
                Your password won't change until you click the link above and create a new one.
              </p>
              <p style="color: #9ca3af; font-size: 14px; line-height: 1.6;">
                Or copy and paste this URL into your browser:<br>
                <a href="{{ reset_url }}" style="color: #4f46e5; word-break: break-all;">{{ reset_url }}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
              <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                &copy; 2024 SplitEase. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

PASSWORD_RESET_TEXT = """
Hi {{ name }},

We received a request to reset your password for your SplitEase account.

Click the link below to set a new password (expires in 1 hour):
{{ reset_url }}

If you didn't request a password reset, you can safely ignore this email.

-- SplitEase Team
"""


def send_password_reset_email(to_email: str, name: str, reset_token: str) -> bool:
    """
    Send a password reset email via SMTP.
    Returns True on success, False on failure.
    Works with authenticated SMTP (production) and unauthenticated relays like Mailhog (dev).
    """
    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP_HOST not configured; skipping email send for %s", to_email
        )
        return False

    reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"

    html_body = Template(PASSWORD_RESET_HTML).render(name=name, reset_url=reset_url)
    text_body = Template(PASSWORD_RESET_TEXT).render(name=name, reset_url=reset_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your SplitEase password"
    msg["From"] = f"SplitEase <{settings.FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            # Only use TLS + auth when credentials are provided (skip for Mailhog)
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
        logger.info("Password reset email sent to %s", to_email)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send password reset email to %s: %s", to_email, exc)
        return False

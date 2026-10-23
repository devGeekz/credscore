"""password-reset email delivery.

smtp unset (dev/test) -> the link is logged so a human can still finish the
flow. smtp set -> plain smtplib with starttls on 587 / implicit ssl on 465.
"""

import logging
import smtplib
import ssl

from app.config import settings

logger = logging.getLogger("credscore.mailer")


def send_password_reset_email(to: str, link: str) -> None:
    subject = "Reset your CredScore password"
    body = (
        "Someone asked to reset your CredScore password.\n\n"
        f"Use this link within one hour: {link}\n\n"
        "If this wasn't you, ignore this message and your password stays unchanged."
    )
    message = f"From: {settings.smtp_from}\nTo: {to}\nSubject: {subject}\n\n{body}"

    if not settings.smtp_host:
        logger.info("smtp not configured - password reset link for %s: %s", to, link)
        return

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(
                settings.smtp_host, 465, context=ssl.create_default_context(), timeout=15
            ) as server:
                _login_and_send(server, to, message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                _login_and_send(server, to, message)
    except Exception:
        logger.exception("failed to send password reset email to %s", to)


def _login_and_send(server: smtplib.SMTP, to: str, message: str) -> None:
    if settings.smtp_user:
        server.login(settings.smtp_user, settings.smtp_password)
    server.sendmail(settings.smtp_from, [to], message)

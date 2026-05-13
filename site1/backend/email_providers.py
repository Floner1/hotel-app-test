"""Email provider wrapper.

Single seam between the application and the underlying send mechanism.
Today this is Django's SMTP backend over Gmail; swapping to another provider
later only requires editing this module.

Notes:
- Synchronous send. Exceptions propagate to the caller (EmailService),
  which is responsible for logging the failure into email_queue.
- Returns the Message-ID header when EmailMessage.message() exposes it,
  otherwise None.
"""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_email(
    *,
    to: Sequence[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[Sequence[str]] = None,
    headers: Optional[dict] = None,
) -> Optional[str]:
    """Send a multi-part (text + HTML) email.

    Returns the Message-ID string from the constructed MIME message, or None
    if it can't be read. Raises on failure — caller logs it.
    """
    if not to:
        raise ValueError("send_email: recipient list is empty")

    sender = from_email or settings.DEFAULT_FROM_EMAIL
    plain = text_body or strip_tags(html_body)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=sender,
        to=list(to),
        reply_to=list(reply_to) if reply_to else None,
        headers=headers or None,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)

    try:
        return msg.message().get('Message-ID')
    except Exception:
        return None

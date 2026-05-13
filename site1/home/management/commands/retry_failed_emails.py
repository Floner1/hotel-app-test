"""Manual retry pass for failed entries in email_queue.

Usage:
    python manage.py retry_failed_emails          # retry + cleanup retention
    python manage.py retry_failed_emails --no-cleanup
    python manage.py retry_failed_emails --limit 50
    python manage.py retry_failed_emails --cleanup-only

This is NOT a queue worker. The architecture is synchronous-inline sending;
this command exists only so a human can re-attempt previously-failed sends.
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from backend.email_providers import send_email
from data.repos.repositories import EmailRepository


class Command(BaseCommand):
    help = "Retry failed email_queue rows and prune entries older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=50,
            help='Maximum number of failed rows to retry in this run (default 50).'
        )
        parser.add_argument(
            '--no-cleanup', action='store_true',
            help='Skip the retention-window cleanup pass.'
        )
        parser.add_argument(
            '--cleanup-only', action='store_true',
            help='Only run the retention cleanup pass; do not retry.'
        )

    def handle(self, *args, **opts):
        limit = opts['limit']
        cleanup_only = opts['cleanup_only']
        skip_cleanup = opts['no_cleanup']

        retried = sent = failed = 0
        if not cleanup_only:
            rows = list(EmailRepository.get_failed(limit=limit))
            self.stdout.write(f'Retrying {len(rows)} failed email(s)...')

            for row in rows:
                retried += 1
                # We don't have the original context here, so re-send a minimal
                # plain-text body using the stored subject. Operator can also
                # delete a bad row to drop it entirely.
                try:
                    text = (
                        f'(Retry of email_queue #{row.id})\n\n'
                        f'Type: {row.email_type}\n'
                        f'Original subject: {row.subject}\n\n'
                        f'This is an automated retry. If the content is missing, '
                        f'please contact the sender.'
                    )
                    msg_id = send_email(
                        to=[row.to_email],
                        subject=row.subject,
                        html_body=f'<pre>{text}</pre>',
                        text_body=text,
                    )
                    EmailRepository.mark_retried_sent(row.id, provider_msg_id=msg_id)
                    sent += 1
                    self.stdout.write(self.style.SUCCESS(f'  #{row.id} retried -> {row.to_email}'))
                except Exception as exc:
                    EmailRepository.mark_retried_failed(row.id, error=exc)
                    failed += 1
                    self.stdout.write(self.style.WARNING(f'  #{row.id} still failed: {exc}'))

            self.stdout.write(
                f'Retry summary: attempted={retried} sent={sent} still_failed={failed}'
            )

        if not skip_cleanup:
            days = getattr(settings, 'EMAIL_QUEUE_RETENTION_DAYS', 90)
            removed = EmailRepository.delete_older_than(days=days)
            self.stdout.write(
                f'Retention cleanup: removed {removed} email_queue row(s) older than {days} days.'
            )

"""Views re-querying what the global context processor already supplies.

Separate from batch 5's four audited findings. `home.context_processors.text_overrides`
is registered globally in settings, so every `render(request, ...)` already receives
`hotel` and `hotel_name`. Nine view contexts fetched them again anyway, so the
context-processor dedup was undone at the view layer on most admin pages and on the
public register page.

These pin the query count against the hotel_info table per request. A value-only
assertion passes on the duplicated code and so proves nothing.
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import User


@pytest.fixture
def account_admin(db, client):
    """email_log sits behind login_required plus a staff/admin check.

    Local rather than shared: consolidating the six copies of this pattern across
    home/ is a known cleanup, deliberately out of scope for this batch.
    """
    admin = User.objects.create(
        username='ctxadmin', email='ctxadmin@example.com',
        password_hash='!unusable', role='admin',
        created_at=timezone.now(),
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


def hotel_queries(captured):
    """Only the SELECTs against hotel_info, ignoring auth/session traffic."""
    return [q['sql'] for q in captured.captured_queries if 'hotel_info' in q['sql']]


@pytest.mark.django_db
def test_register_page_reads_the_hotel_row_once(client, hotel):
    """GET /register/ is public. It used to pay 3 hotel_info SELECTs: one from the
    context processor plus the two the view added to its own context."""
    with CaptureQueriesContext(connection) as captured:
        response = client.get(reverse('register'))

    assert response.status_code == 200
    sql = hotel_queries(captured)
    assert len(sql) == 1, (
        f'/register/ issued {len(sql)} hotel_info queries, expected 1:\n'
        + '\n'.join(sql)
    )


@pytest.mark.django_db
def test_register_page_still_shows_the_hotel_name(client, hotel):
    """The view stopped passing hotel_name; the processor must still supply it.

    Guards the actual risk of the deletion: dropping the key without the
    processor covering it would blank the name rather than raise.
    """
    response = client.get(reverse('register'))

    assert response.context['hotel_name'] == 'Thien Tai Hotel'
    assert response.context['hotel']['hotel_name'] == 'Thien Tai Hotel'


@pytest.mark.django_db
def test_admin_email_log_reads_the_hotel_row_once(account_admin, hotel):
    """Representative of the six admin views that each added their own 'hotel'."""
    with CaptureQueriesContext(connection) as captured:
        response = account_admin.get(reverse('email_log'))

    assert response.status_code == 200
    sql = hotel_queries(captured)
    assert len(sql) == 1, (
        f'email_log issued {len(sql)} hotel_info queries, expected 1:\n'
        + '\n'.join(sql)
    )


@pytest.mark.django_db
def test_admin_email_log_still_receives_the_hotel(account_admin, hotel):
    response = account_admin.get(reverse('email_log'))

    assert response.context['hotel']['hotel_name'] == 'Thien Tai Hotel'

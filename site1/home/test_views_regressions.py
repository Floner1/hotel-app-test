"""Regressions in home/views.py.

Three separate bugs, one section each. They share a file because they share a
module; nothing else connects them.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.urls import reverse

from data.models import AuditLog, CustomerBookingInfo, User


# ── Bug 1: deleting an account with history ────────────────────────────
#
# audit_log.user_id is an FK to users(user_id) with no ON DELETE action, and
# every login writes a row. So user.delete() raises IntegrityError for anyone
# who has ever signed in, the generic handler swallows it, and the admin is
# told "An error occurred" with no idea why. Deactivation is what this repo
# already does everywhere else the append-only audit table holds an FK.


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_user(
        username='accountadmin',
        email='accountadmin@example.com',
        password='irrelevant-for-force-login',
        role='admin',
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


@pytest.fixture
def guest_with_history(db):
    """A customer who has logged in at least once, so audit_log holds a row
    pointing at them. That row is what makes the FK refuse the delete."""
    guest = User.objects.create_user(
        username='longtimeguest',
        email='longtimeguest@example.com',
        password='irrelevant',
        role='customer',
    )
    AuditLog.objects.create(
        user=guest,
        action_type='LOGIN',
        table_name='users',
        record_id=guest.user_id,
    )
    return guest


def test_removing_an_account_with_audit_history_deactivates_it(
    admin_client, guest_with_history
):
    """The account has to end up gone from the admin's list, and the row has to
    survive so audit_log keeps pointing at something."""
    admin_client.post(reverse('manage_accounts'), {
        'action': 'delete',
        'account_id': guest_with_history.user_id,
    })

    assert User.objects.filter(pk=guest_with_history.pk).exists(), (
        'the row was deleted out from under audit_log, orphaning its FK'
    )
    guest_with_history.refresh_from_db()
    assert guest_with_history.is_active is False, (
        'the account is still active, so nothing was done to it'
    )
    assert AuditLog.objects.filter(user=guest_with_history).exists(), (
        'the audit trail lost its actor'
    )


def test_removing_an_account_reports_what_actually_happened(
    admin_client, guest_with_history
):
    """The old message claimed a delete that never happened. The new one has to
    say deactivated, and must not be the generic error."""
    response = admin_client.post(reverse('manage_accounts'), {
        'action': 'delete',
        'account_id': guest_with_history.user_id,
    })

    text = ' '.join(m.message for m in get_messages(response.wsgi_request))
    assert 'error' not in text.lower(), f'admin saw a failure: {text!r}'
    assert 'deactivated' in text.lower(), (
        f'the message does not say what happened to the account: {text!r}'
    )


# ── Bug 2: 500 on a booking that already committed ─────────────────────
#
# ReservationService._parse_date accepts six formats. The view then re-parsed
# the raw POST strings with strict '%m/%d/%Y' to work out how many nights to
# show. An ISO date sails through the service, the booking is written, the
# audit row is written, and then strptime raises ValueError. It is not a
# ValidationError, so the generic handler catches it and the guest gets a 500
# for a reservation that exists and has already had its confirmation queued.

_CHECK_IN = date.today() + timedelta(days=30)


@pytest.fixture(autouse=True)
def _clear_ratelimit():
    """get_reservation is @ratelimit(key='ip', rate='10/m'), counted in the
    default cache, which is process-wide and outlives a single test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _no_outbound_mail():
    """A real .env with GMAIL_APP_PASSWORD flips EMAIL_BACKEND to SMTP, so an
    unpatched run would post actual mail from these bookings."""
    with patch('backend.services.services.EmailService.queue_booking_confirmation'):
        yield


@pytest.fixture
def bookable(hotel):
    """The least create_reservation needs to succeed: a priced room type and
    one physical room of that type."""
    from data.models import Room, RoomPrice
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    return Room.objects.create(
        hotel=hotel, room_code='401', floor_number=4, room_number=401,
        room_type='deluxe',
    )


@pytest.fixture
def guest_client(client, db):
    guest = User.objects.create_user(
        username='bookingguest',
        email='bookingguest@example.com',
        password='irrelevant-for-force-login',
        role='customer',
    )
    client.force_login(guest, backend='home.auth_backend.CustomUserBackend')
    client.guest = guest
    return client


def _post_booking(guest_client, checkin, checkout, **extra):
    payload = {
        'name': 'Booking Guest',
        'email': 'bookingguest@example.com',
        'phone': '123',
        'checkin_date': checkin,
        'checkout_date': checkout,
        'adults': '1',
        'children': '0',
        'room_type': 'deluxe',
    }
    payload.update(extra)
    return guest_client.post(reverse('reservation'), payload)


def test_iso_dates_do_not_500_a_booking_that_already_committed(
    guest_client, bookable
):
    """The service accepts ISO dates, so the row lands. The response has to
    match."""
    response = _post_booking(
        guest_client,
        _CHECK_IN.isoformat(),
        (_CHECK_IN + timedelta(days=2)).isoformat(),
    )

    assert CustomerBookingInfo.objects.filter(user=guest_client.guest).count() == 1, (
        'the booking never committed, so this test is not exercising the bug'
    )
    assert response.status_code == 200, (
        f'the booking committed but the guest was told it failed: '
        f'{response.status_code} {response.content!r}'
    )
    payload = json.loads(response.content)
    assert payload['status'] == 'success'
    assert payload['total_days'] == 2


def test_same_day_booking_still_reports_one_day(guest_client, bookable):
    """Check-in and check-out on the same date is zero nights and has always
    been shown, and charged, as one."""
    stay = _CHECK_IN.strftime('%m/%d/%Y')
    response = _post_booking(guest_client, stay, stay)

    assert response.status_code == 200, response.content
    assert json.loads(response.content)['total_days'] == 1

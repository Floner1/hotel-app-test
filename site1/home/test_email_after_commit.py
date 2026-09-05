"""The booking confirmation email must not go out inside the caller's
transaction.

create_reservation has always said it sends "AFTER the transaction commits",
and read on its own it does: the send sits below its own atomic() block. But
get_reservation wraps the whole call in a second atomic() so the milestone
count and the booking it gates land together, and that makes the inner block a
savepoint rather than a transaction. The send then runs with the outer
transaction still open and the select_for_update() lock on the guest's row
still held.

The send is synchronous SMTP (backend/email_providers.py) with EMAIL_TIMEOUT at
15 seconds, and queue_booking_confirmation posts twice, guest then admin. So a
slow or dead mail server holds a row lock for up to half a minute, and two
bookings by the same guest serialise behind it for a reason that has nothing to
do with the milestone check.

transaction=True on both tests because the point is what happens at a real
commit, and pytest-django's default wraps each test in a transaction that never
commits.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import connection, transaction
from django.urls import reverse

from backend.services.services import ReservationService
from data.models import User

_CHECK_IN = date.today() + timedelta(days=30)

RESERVATION = {
    'name': 'Test Guest',
    'email': 'guest@example.com',
    'checkin_date': _CHECK_IN.isoformat(),
    'checkout_date': (_CHECK_IN + timedelta(days=2)).isoformat(),
    'room_type': 'deluxe',
    'adults': 1,
    'children': 0,
}


@pytest.fixture
def bookable(hotel):
    """The minimum create_reservation needs to reach the confirmation send: a
    priced room type and one physical room of that type."""
    from data.models import Room, RoomPrice
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    return Room.objects.create(
        hotel=hotel, room_code='901', floor_number=9, room_number=901,
        room_type='deluxe',
    )


@pytest.fixture
def _mocked_send():
    """Stand in for the SMTP call and record whether a transaction was still
    open when it fired."""
    calls = {'count': 0, 'in_atomic_block': None}

    def _record(reservation_id):
        calls['count'] += 1
        calls['in_atomic_block'] = connection.in_atomic_block

    with patch(
        'backend.services.services.EmailService.queue_booking_confirmation',
        side_effect=_record,
    ):
        yield calls


@pytest.mark.django_db(transaction=True)
def test_create_reservation_defers_the_email_to_its_callers_commit(
    bookable, _mocked_send
):
    """Reproduces get_reservation's shape: a lock on the guest row, the booking
    written under it, both inside one atomic block. The send has to wait for
    that block, not for create_reservation's own."""
    guest = User.objects.create_user(
        username='deferguest', email='defer@example.com',
        password='irrelevant-for-this-test', role='customer',
    )

    with transaction.atomic():
        User.objects.select_for_update().filter(pk=guest.pk).first()
        ReservationService.create_reservation(dict(RESERVATION, user=guest))

        assert _mocked_send['count'] == 0, (
            'the confirmation email was sent while the caller still held the '
            'transaction, and with it the lock on the guest row'
        )

    assert _mocked_send['count'] == 1, (
        'the email never fired once the transaction committed'
    )


@pytest.mark.django_db(transaction=True)
def test_booking_through_the_view_mails_after_the_lock_is_released(
    client, bookable, _mocked_send
):
    """The same thing down the real path, so this cannot pass on a test-local
    reproduction of a caller that has since changed shape."""
    guest = User.objects.create_user(
        username='viewguest', email='viewguest@example.com',
        password='irrelevant-for-force-login', role='customer',
    )
    client.force_login(guest, backend='home.auth_backend.CustomUserBackend')

    response = client.post(reverse('reservation'), {
        'name': 'View Guest', 'email': 'viewguest@example.com', 'phone': '123',
        'checkin_date': _CHECK_IN.strftime('%m/%d/%Y'),
        'checkout_date': (_CHECK_IN + timedelta(days=2)).strftime('%m/%d/%Y'),
        'adults': '1', 'children': '0', 'room_type': 'deluxe',
    })

    assert response.json()['status'] == 'success', response.content
    assert _mocked_send['count'] == 1, 'the confirmation email never fired'
    assert _mocked_send['in_atomic_block'] is False, (
        'the email went out inside the atomic block that holds the milestone '
        'row lock, so a slow SMTP server blocks the lock for its whole timeout'
    )

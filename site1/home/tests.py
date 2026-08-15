import contextlib
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.urls import reverse
from data.models import User
from data.repos.repositories import EmailRepository, RoomRepository
from backend.services.services import ReservationService, RoomService

# Campaign body_html is rendered with |safe into the outgoing email, so it must
# be sanitized on the way IN, at save time. These tests assert on the value
# handed to the ORM rather than reading it back: the suite cannot build a test
# database (data.User is managed=False, so the users table never exists and
# django_admin_log's FK fails), and the value passed to .create()/.save() is
# exactly what would be written.

DIRTY = '<p>Spring rates</p><script>alert(1)</script><a href="javascript:alert(2)">x</a>'


@patch('data.repos.repositories.EmailCampaign.objects.create')
def test_create_campaign_sanitizes_body_html(mock_create):
    EmailRepository.create_campaign(name='Spring', subject='Rates', body_html=DIRTY)

    saved = mock_create.call_args.kwargs['body_html']
    assert '<script>' not in saved, f'script tag reached the DB: {saved!r}'
    assert 'javascript:' not in saved, f'javascript: URL reached the DB: {saved!r}'
    assert '<p>Spring rates</p>' in saved, f'safe markup was stripped: {saved!r}'


@patch('data.repos.repositories.EmailCampaign.objects.get')
def test_update_campaign_sanitizes_body_html(mock_get):
    camp = mock_get.return_value

    EmailRepository.update_campaign(1, body_html=DIRTY)

    assert '<script>' not in camp.body_html, f'script tag reached the DB: {camp.body_html!r}'
    assert 'javascript:' not in camp.body_html
    assert '<p>Spring rates</p>' in camp.body_html

@pytest.mark.django_db
def test_newsletter_signup_invalid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'invalid-email'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 400
    assert response.json()['status'] == 'error'

@pytest.mark.django_db
def test_newsletter_signup_valid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'test@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


# Regression cover for the availability bug: get_available_rooms_by_type used to
# filter on Room.reservation_status, which is a snapshot of the room's state
# right now, not over the requested range. A room reserved for December was
# therefore unbookable in January.

@pytest.mark.django_db
def test_future_booking_does_not_block_other_dates(room, active_assignment):
    room.reservation_status = 'reserved'
    room.save()

    free = RoomRepository.count_available_rooms_by_type(
        room.room_type, date(2027, 1, 5), date(2027, 1, 7)
    )

    assert free == 1, 'a room booked in December must still be bookable in January'


@pytest.mark.django_db
def test_overlapping_dates_are_excluded(room, active_assignment):
    free = RoomRepository.count_available_rooms_by_type(
        room.room_type, active_assignment.check_in, active_assignment.check_out
    )

    assert free == 0, 'a room with an active assignment over the range is not available'


# Room allocation used to run inside a bare `except Exception: logger.warning(...)`
# in create_reservation. The booking row is written before allocation is
# attempted, so a failed allocation left a committed booking with no room
# attached and still returned that booking to the caller as a success.

# Derived from today, not hardcoded: _validate_dates rejects a past check-in,
# which would raise before a booking is ever written and leave the assertions
# below passing for the wrong reason.
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
    """The minimum create_reservation needs to reach room allocation: a priced
    room type and one physical room of that type."""
    from data.models import Room, RoomPrice
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    return Room.objects.create(
        hotel=hotel,
        room_code='201',
        floor_number=2,
        room_number=201,
        room_type='deluxe',
    )


def _allocation_fails():
    """Replace allocate_room with the ValidationError it raises when it loses
    the race for the last room. Substituted rather than provoked naturally:
    create_reservation and allocate_room run the same availability query, so
    they only disagree under concurrency — which test_concurrency.py covers
    against real SQL Server."""
    return patch.object(
        RoomService,
        'allocate_room',
        side_effect=ValidationError('No available deluxe rooms.'),
    )


@pytest.mark.django_db(transaction=True)
def test_failed_allocation_raises_to_the_caller(bookable):
    with _allocation_fails() as allocate:
        with pytest.raises(ValidationError, match='No available deluxe rooms'):
            ReservationService.create_reservation(dict(RESERVATION))

    # Without this, any of create_reservation's ~8 earlier ValidationErrors
    # would satisfy the raises() above while never reaching the fixed line.
    assert allocate.called, 'never got as far as room allocation'


@pytest.mark.django_db(transaction=True)
def test_failed_allocation_leaves_no_booking_behind(bookable):
    from data.models import CustomerBookingInfo

    with _allocation_fails() as allocate:
        # Swallow here so this test asserts on the committed rows, not on the
        # exception; the raise itself is covered by the test above.
        with contextlib.suppress(ValidationError):
            ReservationService.create_reservation(dict(RESERVATION))

    assert allocate.called, 'never got as far as room allocation'
    assert CustomerBookingInfo.objects.count() == 0, (
        'a booking was committed even though no room could be allocated'
    )

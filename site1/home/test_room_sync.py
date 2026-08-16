"""RoomAssignment is the one arbiter of whether a room is occupied.

Two defects sat either side of that idea and neither respected it.

Bug 1: the room dashboard's manual status buttons wrote Room.reservation_status
and the render loop derived what it showed from any active RoomAssignment
covering today, in preference to that field. Clicking "Empty Clean" on a booked
room saved vacant/clean and reloaded showing "Occupied", with nothing to tell
staff why.

Bug 3: edit_reservation only re-ran allocation when status itself changed, and
allocate_room returned any existing active assignment without checking it still
described the booking. Moving a confirmed booking's dates left the assignment,
and therefore every availability check that reads it, on the old range.

The decision, taken with Peter before any of this was written: the assignment
wins. A manual write that the render would override is refused and says which
booking holds the room. No dashboard click ever tears a room off a live
booking.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import CustomerBookingInfo, Room, RoomAssignment, RoomPrice


@pytest.fixture
def staff_client(client, db):
    """A logged-in staff user, which both views under test require."""
    from data.models import User
    user = User.objects.create_user(
        username='roomtester',
        email='roomtester@example.com',
        password='irrelevant-for-force-login',
        role='staff',
    )
    client.force_login(user, backend='home.auth_backend.CustomUserBackend')
    return client


def _booking(hotel, check_in, check_out, status='confirmed', name='Test Guest'):
    now = timezone.now()
    return CustomerBookingInfo.objects.create(
        hotel=hotel, guest_name=name, room_type='deluxe', booking_date=now,
        check_in=check_in, check_out=check_out,
        booked_rate=Decimal('500000'), total_price=Decimal('1000000'),
        status=status, created_at=now, updated_at=now,
    )


@pytest.fixture
def occupied_today(hotel, room):
    """A booking whose active assignment covers today, so the dashboard renders
    the room as occupied whatever Room.reservation_status says."""
    booking = _booking(
        hotel, date.today() - timedelta(days=1), date.today() + timedelta(days=2),
        status='checked_in', name='In House',
    )
    assignment = RoomAssignment.objects.create(
        booking=booking, room=room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    # What RoomService.check_in_room would have left behind. Without this the
    # room keeps the model default of vacant/clean, and "was the refused write
    # saved?" becomes unanswerable: the attempted value and the starting value
    # are the same, so the assertions below would pass either way.
    room.reservation_status = 'occupied'
    room.save()
    return booking, assignment


# ── Bug 1: a manual write that the render would override gets refused ──


@pytest.mark.django_db
def test_manual_vacant_on_an_occupied_room_is_refused_not_swallowed(
    staff_client, room, occupied_today
):
    booking, _ = occupied_today

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'vacant'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, (
        f'expected a refusal, got {response.status_code}: {response.content!r}'
    )
    assert str(booking.booking_id) in response.json()['message'], (
        f'the refusal must name the booking holding the room: {response.json()!r}'
    )
    room.refresh_from_db()
    assert room.reservation_status == 'occupied', 'the refused write still landed'
    assert room.housekeeping_status == 'clean'


@pytest.mark.django_db
def test_manual_empty_dirty_on_an_occupied_room_is_refused(
    staff_client, room, occupied_today
):
    """Empty Dirty also claims the room is empty, so it loses the same way."""
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'empty_dirty'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, response.content
    room.refresh_from_db()
    assert room.housekeeping_status == 'clean', 'the refused write still landed'
    assert room.reservation_status == 'occupied'


@pytest.mark.django_db
def test_out_of_order_is_still_allowed_on_an_occupied_room(
    staff_client, room, occupied_today
):
    """Out of Order outranks the assignment in the same derivation, so it has
    to keep working. Otherwise the refusal above is a blanket lockout."""
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'out_of_order'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.housekeeping_status == 'out_of_order'


@pytest.mark.django_db
def test_manual_occupied_works_on_a_room_with_no_assignment(staff_client, room):
    """A walk-in with no booking row has nothing to conflict with, and this is
    the only way to record one."""
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.reservation_status == 'occupied'


@pytest.mark.django_db
def test_empty_dirty_works_on_a_room_with_no_assignment(staff_client, room):
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'empty_dirty'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.reservation_status == 'vacant'
    assert room.housekeeping_status == 'dirty'


@pytest.mark.django_db
def test_marking_a_future_booked_room_occupied_is_refused(staff_client, room, hotel):
    """A future assignment renders as Reserved, so Occupied would be overridden
    too. Same rule, different branch of the derivation."""
    booking = _booking(
        hotel, date.today() + timedelta(days=5), date.today() + timedelta(days=7),
    )
    RoomAssignment.objects.create(
        booking=booking, room=room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, response.content


# ── Bug 3: the assignment follows the booking ──────────────────────────


@pytest.fixture
def confirmed_with_assignment(hotel):
    """A confirmed booking holding an active assignment, plus a spare room of
    the same type so a re-allocation has somewhere to go."""
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    room_a = Room.objects.create(
        hotel=hotel, room_code='401', floor_number=4, room_number=401,
        room_type='deluxe',
    )
    Room.objects.create(
        hotel=hotel, room_code='402', floor_number=4, room_number=402,
        room_type='deluxe',
    )
    booking = _booking(hotel, date(2027, 3, 10), date(2027, 3, 12), name='Date Mover')
    assignment = RoomAssignment.objects.create(
        booking=booking, room=room_a, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    return booking, assignment


def _edit(staff_client, booking, **overrides):
    payload = {
        'name': booking.guest_name,
        'room_type': 'deluxe',
        'checkin_date': str(booking.check_in),
        'checkout_date': str(booking.check_out),
        'adults': 1,
        'status': 'confirmed',
    }
    payload.update(overrides)
    return staff_client.post(
        reverse('edit_reservation', args=[booking.booking_id]),
        data=json.dumps(payload),
        content_type='application/json',
    )


@pytest.mark.django_db
def test_editing_dates_without_touching_status_moves_the_assignment(
    staff_client, confirmed_with_assignment
):
    """The headline case. Status stays 'confirmed' throughout, which is exactly
    the path the old code never re-allocated on."""
    booking, _ = confirmed_with_assignment

    response = _edit(
        staff_client, booking,
        checkin_date='2027-03-20', checkout_date='2027-03-22',
    )

    assert response.status_code == 200, response.content
    booking.refresh_from_db()
    assert booking.status == 'confirmed', 'status must not have moved'

    active = RoomAssignment.objects.filter(booking=booking, status='active')
    assert active.count() == 1, (
        f'expected exactly one active assignment, got {active.count()}'
    )
    current = active.first()
    assert current.check_in == date(2027, 3, 20), (
        f'assignment left on the old dates: {current.check_in} to {current.check_out}'
    )
    assert current.check_out == date(2027, 3, 22)


@pytest.mark.django_db
def test_the_room_is_free_for_the_old_dates_after_the_move(
    staff_client, confirmed_with_assignment
):
    """The other side of the same coin: availability reads RoomAssignment, so a
    stale row keeps a room looking booked for dates nobody is staying."""
    booking, _ = confirmed_with_assignment

    _edit(staff_client, booking, checkin_date='2027-03-20', checkout_date='2027-03-22')

    from data.repos.repositories import RoomRepository
    free = RoomRepository.count_available_rooms_by_type(
        'deluxe', date(2027, 3, 10), date(2027, 3, 12)
    )
    assert free == 2, f'both rooms should be free for the vacated dates, got {free}'


@pytest.mark.django_db
def test_editing_the_room_type_moves_the_assignment(
    staff_client, confirmed_with_assignment, hotel
):
    booking, old_assignment = confirmed_with_assignment
    RoomPrice.objects.create(
        hotel=hotel, room_type='suite', price_per_night=Decimal('900000')
    )
    suite = Room.objects.create(
        hotel=hotel, room_code='501', floor_number=5, room_number=501,
        room_type='suite',
    )

    response = _edit(staff_client, booking, room_type='suite')

    assert response.status_code == 200, response.content
    current = RoomAssignment.objects.get(booking=booking, status='active')
    assert current.room_id == suite.room_id, (
        'the assignment is still pointing at the old room type'
    )


@pytest.mark.django_db
def test_edit_rolls_back_when_no_room_is_free_for_the_new_dates(hotel, staff_client):
    """allocate_room releases the stale assignment before it looks for a room,
    so a booking moved onto full dates must roll the whole save back. Otherwise
    the booking keeps the new dates and loses its room."""
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    only_room = Room.objects.create(
        hotel=hotel, room_code='601', floor_number=6, room_number=601,
        room_type='deluxe',
    )
    mover = _booking(hotel, date(2027, 3, 10), date(2027, 3, 12), name='Mover')
    RoomAssignment.objects.create(
        booking=mover, room=only_room, status='active',
        check_in=mover.check_in, check_out=mover.check_out,
    )
    blocker = _booking(hotel, date(2027, 3, 20), date(2027, 3, 22), name='Blocker')
    RoomAssignment.objects.create(
        booking=blocker, room=only_room, status='active',
        check_in=blocker.check_in, check_out=blocker.check_out,
    )

    response = _edit(
        staff_client, mover,
        checkin_date='2027-03-20', checkout_date='2027-03-22',
    )

    assert response.status_code == 400, response.content
    mover.refresh_from_db()
    assert mover.check_in == date(2027, 3, 10), 'the booking kept dates it has no room for'
    surviving = RoomAssignment.objects.get(booking=mover, status='active')
    assert surviving.check_in == date(2027, 3, 10), 'the booking lost its room'


@pytest.mark.django_db
def test_allocate_room_replaces_an_assignment_that_no_longer_matches(
    confirmed_with_assignment
):
    """Root-cause cover one level below the view. allocate_room returned any
    active assignment without checking it still described the booking, so even
    a later status transition could not repair a stale one."""
    from backend.services.services import RoomService

    booking, _ = confirmed_with_assignment
    booking.check_in = date(2027, 3, 20)
    booking.check_out = date(2027, 3, 22)
    booking.save()

    assignment = RoomService.allocate_room(booking)

    assert assignment.check_in == date(2027, 3, 20)
    assert assignment.check_out == date(2027, 3, 22)
    assert RoomAssignment.objects.filter(booking=booking, status='active').count() == 1


@pytest.mark.django_db
def test_allocate_room_still_returns_a_matching_assignment_unchanged(
    confirmed_with_assignment
):
    """The guard against double-allocation still has to hold, or every call
    would churn out a fresh assignment."""
    from backend.services.services import RoomService

    booking, original = confirmed_with_assignment

    assert RoomService.allocate_room(booking).pk == original.pk
    assert RoomAssignment.objects.filter(booking=booking).count() == 1

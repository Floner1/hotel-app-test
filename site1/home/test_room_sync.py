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
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
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


def _booking(hotel, check_in, check_out, status='confirmed', name='Test Guest',
             room_type='deluxe'):
    now = timezone.now()
    return CustomerBookingInfo.objects.create(
        hotel=hotel, guest_name=name, room_type=room_type, booking_date=now,
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
def test_occupied_on_an_out_of_order_room_is_refused_without_a_booking(
    staff_client, room
):
    """out_of_order outranks reservation_status, so Occupied loses here too,
    but there is no assignment to name in the refusal.

    Found by review: the refusal message reached for assignment.booking_id
    unconditionally, so this path raised AttributeError and returned a 500
    rather than a refusal.
    """
    room.housekeeping_status = 'out_of_order'
    room.save()

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, (
        f'expected a refusal, got {response.status_code}: {response.content!r}'
    )
    assert 'out of order' in response.json()['message'].lower(), (
        f'the refusal must say what actually blocked it: {response.json()!r}'
    )
    room.refresh_from_db()
    assert room.reservation_status != 'occupied'


@pytest.mark.django_db
def test_clearing_an_out_of_order_room_still_works(staff_client, room):
    """Empty Clean sets housekeeping back to clean in the same write, so the
    derivation agrees and the room can always be brought back into service."""
    room.housekeeping_status = 'out_of_order'
    room.save()

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'vacant'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.housekeeping_status == 'clean'


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


@pytest.fixture
def seeded_case_mismatch(hotel):
    """The casing the real database actually has.

    rooms.room_type and room_price.room_type hold the seeded title-case value,
    '1 Bed With Balcony'. _canonicalise_room_type lower-cases whatever it is
    given, so booking.room_type holds '1 bed with balcony'. Every fixture above
    uses all-lowercase 'deluxe', where the two happen to be identical, which is
    exactly why this went unnoticed.
    """
    RoomPrice.objects.create(
        hotel=hotel, room_type='1 Bed With Balcony',
        price_per_night=Decimal('1150000'),
    )
    room = Room.objects.create(
        hotel=hotel, room_code='701', floor_number=7, room_number=701,
        room_type='1 Bed With Balcony',
    )
    Room.objects.create(
        hotel=hotel, room_code='702', floor_number=7, room_number=702,
        room_type='1 Bed With Balcony',
    )
    booking = _booking(
        hotel, date(2027, 5, 10), date(2027, 5, 12), name='Case Mismatch',
        room_type='1 bed with balcony',
    )
    assignment = RoomAssignment.objects.create(
        booking=booking, room=room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    return booking, assignment


@pytest.mark.django_db
def test_allocate_room_keeps_an_assignment_that_differs_only_in_casing(
    seeded_case_mismatch
):
    """Comparing the two room_type values with == judged every real booking's
    assignment stale, so any status transition re-rolled the guest into a
    different room for no reason."""
    from backend.services.services import RoomService

    booking, original = seeded_case_mismatch

    assert RoomService.allocate_room(booking).pk == original.pk, (
        'the guest was moved to another room by a case difference'
    )
    assert RoomAssignment.objects.filter(booking=booking, status='active').count() == 1


@pytest.mark.django_db
def test_a_failed_reallocation_leaves_the_booking_holding_its_room(hotel):
    """allocate_room releases the stale assignment before it searches. If that
    release is not inside the same transaction as the search, a booking moved
    onto full dates loses the room it had and gains nothing.

    Called with no enclosing transaction, which is how the status-transition
    path in edit_reservation calls it.
    """
    from backend.services.services import RoomService

    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    only_room = Room.objects.create(
        hotel=hotel, room_code='801', floor_number=8, room_number=801,
        room_type='deluxe',
    )
    mover = _booking(hotel, date(2027, 7, 10), date(2027, 7, 12), name='Mover')
    held = RoomAssignment.objects.create(
        booking=mover, room=only_room, status='active',
        check_in=mover.check_in, check_out=mover.check_out,
    )
    blocker = _booking(hotel, date(2027, 7, 20), date(2027, 7, 22), name='Blocker')
    RoomAssignment.objects.create(
        booking=blocker, room=only_room, status='active',
        check_in=blocker.check_in, check_out=blocker.check_out,
    )

    mover.check_in = date(2027, 7, 20)
    mover.check_out = date(2027, 7, 22)
    mover.save()

    with pytest.raises(ValidationError):
        RoomService.allocate_room(mover)

    held.refresh_from_db()
    assert held.status == 'active', (
        'the room was released and never replaced, so the booking has none'
    )


@pytest.mark.django_db
def test_a_room_with_a_current_and_a_future_booking_is_judged_on_the_current_one(
    staff_client, room, hotel
):
    """A room can hold a stay in progress and a booking for next week at once.

    The render kept whichever assignment came last and the POST guard took an
    unordered .first(), so the two could judge the same room against different
    bookings. The future one is created first here, which is the order that
    made them disagree.
    """
    future = _booking(
        hotel, date.today() + timedelta(days=5), date.today() + timedelta(days=7),
        name='Next Week',
    )
    RoomAssignment.objects.create(
        booking=future, room=room, status='active',
        check_in=future.check_in, check_out=future.check_out,
    )
    current = _booking(
        hotel, date.today() - timedelta(days=1), date.today() + timedelta(days=2),
        status='checked_in', name='In House Now',
    )
    RoomAssignment.objects.create(
        booking=current, room=room, status='active',
        check_in=current.check_in, check_out=current.check_out,
    )

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'vacant'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, response.content
    assert str(current.booking_id) in response.json()['message'], (
        f'judged against the wrong booking: {response.json()!r}'
    )


@pytest.mark.django_db
def test_an_out_of_order_room_with_a_booking_blames_the_out_of_order(
    staff_client, room, occupied_today
):
    """out_of_order outranks the assignment in the derivation, so when both are
    present it is the thing actually blocking the write. Telling staff to go
    and change the booking sends them somewhere that will not help."""
    room.housekeeping_status = 'out_of_order'
    room.save()

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409, response.content
    assert 'out of order' in response.json()['message'].lower(), (
        f'blamed the booking for an out-of-order room: {response.json()!r}'
    )


@pytest.mark.django_db
def test_a_rejected_edit_reports_a_readable_message(hotel, staff_client):
    """str() on a Django ValidationError renders its message list, brackets and
    quotes included, so the guest-facing text arrived as ["No available ..."].
    """
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    only_room = Room.objects.create(
        hotel=hotel, room_code='901', floor_number=9, room_number=901,
        room_type='deluxe',
    )
    mover = _booking(hotel, date(2027, 8, 10), date(2027, 8, 12), name='Mover')
    RoomAssignment.objects.create(
        booking=mover, room=only_room, status='active',
        check_in=mover.check_in, check_out=mover.check_out,
    )
    blocker = _booking(hotel, date(2027, 8, 20), date(2027, 8, 22), name='Blocker')
    RoomAssignment.objects.create(
        booking=blocker, room=only_room, status='active',
        check_in=blocker.check_in, check_out=blocker.check_out,
    )

    response = _edit(
        staff_client, mover,
        checkin_date='2027-08-20', checkout_date='2027-08-22',
    )

    assert response.status_code == 400, response.content
    message = response.json()['message']
    assert not message.startswith('['), f'raw list repr reached the user: {message!r}'
    assert 'No available' in message


# ── Extending a stay must not re-roll a guest who is already in the room ──


@pytest.fixture
def checked_in_with_spare(hotel):
    """A guest physically in 501, plus a free room of the same type.

    The spare is what a re-roll has to move them into, and its existence is the
    whole point: with only one room of the type the pool search would fail on
    its own and hide the defect.
    """
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    in_room = Room.objects.create(
        hotel=hotel, room_code='501', floor_number=5, room_number=501,
        room_type='deluxe', reservation_status='occupied',
    )
    spare = Room.objects.create(
        hotel=hotel, room_code='502', floor_number=5, room_number=502,
        room_type='deluxe',
    )
    booking = _booking(
        hotel, date(2027, 9, 10), date(2027, 9, 12),
        status='checked_in', name='In House',
    )
    assignment = RoomAssignment.objects.create(
        booking=booking, room=in_room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    return booking, in_room, spare, assignment


@pytest.mark.django_db
def test_extending_a_checked_in_stay_keeps_the_guest_in_their_room(
    checked_in_with_spare
):
    """The guest is asleep in 501. Extending the booking cannot teleport them.

    random.choice is patched to hand back the room the guest is *not* in, so
    this cannot pass by luck. On the old code the picker decides and the guest
    lands in 502; on the fixed code the picker is never consulted, because the
    room they already hold is free for the longer range.
    """
    from backend.services.services import RoomService

    booking, in_room, spare, _ = checked_in_with_spare
    booking.check_out = date(2027, 9, 15)
    booking.save()

    with patch(
        'backend.services.services.random.choice',
        side_effect=lambda rooms: next(
            r for r in rooms if r.room_id == spare.room_id
        ),
    ):
        assignment = RoomService.allocate_room(booking)

    assert assignment.room_id == in_room.room_id, (
        'the guest was moved out of the room they are checked in to'
    )
    assert assignment.check_out == date(2027, 9, 15), (
        'the assignment did not take the extended dates'
    )
    in_room.refresh_from_db()
    assert in_room.reservation_status == 'occupied', (
        'the room still has a guest in it but was left marked reserved'
    )


@pytest.mark.django_db
def test_extending_a_checked_in_stay_is_refused_when_the_room_is_taken(
    hotel, checked_in_with_spare
):
    """Someone else holds 501 for the new range, but 502 is free, so the old
    code quietly moved the guest into it. Staff cannot move a checked-in guest
    as a side effect of a date click: refuse and say which room is the problem.
    """
    from backend.services.services import RoomService

    booking, in_room, spare, held = checked_in_with_spare
    blocker = _booking(hotel, date(2027, 9, 13), date(2027, 9, 16), name='Blocker')
    RoomAssignment.objects.create(
        booking=blocker, room=in_room, status='active',
        check_in=blocker.check_in, check_out=blocker.check_out,
    )

    booking.check_out = date(2027, 9, 15)
    booking.save()

    with pytest.raises(ValidationError) as err:
        RoomService.allocate_room(booking)

    assert in_room.room_code in '; '.join(err.value.messages), (
        f'the refusal must name the room the guest is in: {err.value.messages!r}'
    )
    assert not RoomAssignment.objects.filter(
        booking=booking, room=spare
    ).exists(), 'the guest was silently moved into the spare room'
    held.refresh_from_db()
    assert held.status == 'active', (
        'the refused edit still released the room the guest is sleeping in'
    )

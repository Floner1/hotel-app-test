"""Regressions from the 2026-09 master audit, High items 1 to 5.

One section per item. They share a file because they came out of one audit,
not because the bugs are related.
"""

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import CustomerBookingInfo, DiscountCode, RoomAssignment, RoomPrice, User
from data.repos.repositories import RoomRepository


def _login(client, role, username):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com',
        password='irrelevant-for-force-login', role=role,
    )
    client.force_login(user, backend='home.auth_backend.CustomUserBackend')
    return user


def _booking(hotel, *, user=None, room_type='deluxe', nights=2, days_out=10,
             rate='500000', status='pending'):
    now = timezone.now()
    check_in = timezone.localdate() + timedelta(days=days_out)
    return CustomerBookingInfo.objects.create(
        hotel=hotel, user=user, guest_name='Test Guest', email='guest@example.com',
        phone='0900000000', room_type=room_type, booking_date=now,
        check_in=check_in, check_out=check_in + timedelta(days=nights),
        booked_rate=Decimal(rate), total_price=Decimal(rate) * nights,
        status=status, created_at=now, updated_at=now,
    )


# ── Item 1: an edit that touches nothing priced must not reprice ──────────
#
# Bookings store room_type lowercased ('1 bed with balcony'), and the edit
# modal's options carry the room_price spelling ('1 Bed With Balcony'). The
# strict === matched nothing, so the browser preselected the first option and
# a phone-number fix saved a different room type. Separately, every save
# repriced from the list rate, wiping custom rates and discounts.


@pytest.mark.django_db
def test_editing_contact_details_keeps_a_custom_rate(client, hotel):
    _login(client, 'staff', 'desk1')
    RoomPrice.objects.create(
        hotel=hotel, room_type='1 Bed With Balcony', price_per_night=Decimal('1150000'),
    )
    booking = _booking(hotel, room_type='1 bed with balcony', rate='900000')

    response = client.post(
        reverse('edit_reservation', args=[booking.booking_id]),
        data=json.dumps({
            'name': booking.guest_name, 'email': booking.email, 'phone': '0911111111',
            'room_type': '1 Bed With Balcony',
            'checkin_date': booking.check_in.isoformat(),
            'checkout_date': booking.check_out.isoformat(),
            'adults': 1, 'children': 0, 'status': 'pending',
        }),
        content_type='application/json',
    )

    assert response.json()['status'] == 'success', response.json()
    booking.refresh_from_db()
    assert booking.phone == '0911111111'
    assert booking.room_type == '1 bed with balcony'
    assert booking.booked_rate == Decimal('900000')
    assert booking.total_price == Decimal('1800000')


@pytest.mark.django_db
def test_dashboard_matches_room_types_case_insensitively(client):
    """A pin on the rendered JS, because the comparison only runs in a browser.

    The live check for this one is opening the edit modal on a lowercased
    booking and reading the preselected option.
    """
    _login(client, 'staff', 'desk2')
    page = client.get(reverse('admin_reservations')).content.decode()

    # Edit modal preselect.
    assert 'booking.room_type.toLowerCase() === room.canonical.toLowerCase()' in page
    # Sidebar room-type filter, same mismatch against data-room-type.
    assert "(row.dataset.roomType || '').toLowerCase() === roomTypeFilter.toLowerCase()" in page


# ── Item 2: a same-day booking is charged one night, so it holds one ──────
#
# The overlap test was the half-open check_in < other.check_out AND
# check_out > other.check_in. A stay with check_in == check_out has zero
# length under it and overlapped nothing, from either side, while the service
# charged it a full night. Two guests could get the same room.


def _assign(hotel, room, check_in, check_out):
    return RoomAssignment.objects.create(
        booking=_booking(hotel), room=room, status='active',
        check_in=check_in, check_out=check_out,
    )


@pytest.mark.django_db
def test_existing_same_day_stay_blocks_that_night(hotel, room):
    d = timezone.localdate() + timedelta(days=10)
    _assign(hotel, room, d, d)

    assert RoomRepository.count_available_rooms_by_type('deluxe', d, d + timedelta(days=1)) == 0


@pytest.mark.django_db
def test_same_day_request_on_the_first_night_of_an_existing_stay(hotel, room):
    # Mid-stay was already caught. The first night is where check_in < check_out
    # compares d < d for the new request and lets it through.
    d = timezone.localdate() + timedelta(days=10)
    _assign(hotel, room, d, d + timedelta(days=2))

    assert RoomRepository.count_available_rooms_by_type('deluxe', d, d) == 0


@pytest.mark.django_db
def test_back_to_back_stays_still_fit(hotel, room):
    d = timezone.localdate() + timedelta(days=10)
    _assign(hotel, room, d, d)
    # The same-day stay's night is over by the next morning.
    assert RoomRepository.count_available_rooms_by_type(
        'deluxe', d + timedelta(days=1), d + timedelta(days=2)) == 1

    _assign(hotel, room, d + timedelta(days=3), d + timedelta(days=4))
    # Checking out on day 4 frees day 4 for a same-day stay.
    checkout_day = d + timedelta(days=4)
    assert RoomRepository.count_available_rooms_by_type('deluxe', checkout_day, checkout_day) == 1


@pytest.mark.django_db
def test_two_guests_cannot_book_the_same_room_for_a_same_day_stay(hotel, room):
    """The audit's scenario end to end: one room, a same-day booking, then an
    overnight booking starting the same day."""
    from django.core.exceptions import ValidationError
    from backend.services.services import ReservationService

    RoomPrice.objects.create(hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000'))
    d = timezone.localdate() + timedelta(days=10)
    form = {'name': 'Guest', 'email': 'a@example.com', 'room_type': 'deluxe', 'adults': 1}

    ReservationService.create_reservation({**form, 'checkin_date': d.isoformat(), 'checkout_date': d.isoformat()})

    with pytest.raises(ValidationError):
        ReservationService.create_reservation({
            **form, 'email': 'b@example.com',
            'checkin_date': d.isoformat(), 'checkout_date': (d + timedelta(days=1)).isoformat(),
        })


# ── Item 3: a booking staff type in is the guest's, not the staff member's ─
#
# get_reservation counted request.user's bookings to decide the loyalty
# milestone. From the dashboard that user is the staff member, and the Add
# Reservation modal has no way to answer milestone_check, so every third staff
# booking failed, wrote nothing, and failed again on retry. The bookings were
# also owned by the staff account.


def _reservation_form(check_in):
    return {
        'name': 'Walk In', 'phone': '0900000000', 'email': 'walkin@example.com',
        'checkin_date': check_in.strftime('%m/%d/%Y'),
        'checkout_date': (check_in + timedelta(days=1)).strftime('%m/%d/%Y'),
        'adults': 1, 'children': 0, 'room_type': 'deluxe',
    }


def _book(client, days_out=5):
    return client.post(
        reverse('reservation'),
        _reservation_form(timezone.localdate() + timedelta(days=days_out)),
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )


@pytest.fixture
def priced_room(hotel, room):
    RoomPrice.objects.create(hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000'))
    return room


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['staff', 'admin'])
def test_staff_third_booking_is_created_not_intercepted(client, hotel, priced_room, role):
    desk = _login(client, role, f'desk-{role}')
    _booking(hotel, user=desk, days_out=40)
    _booking(hotel, user=desk, days_out=50)

    response = _book(client)

    assert response.json()['status'] == 'success', response.json()


@pytest.mark.django_db
def test_staff_booking_belongs_to_the_guest_not_the_desk(client, hotel, priced_room):
    desk = _login(client, 'staff', 'desk7')

    booking_id = _book(client).json()['booking_id']

    booking = CustomerBookingInfo.objects.get(pk=booking_id)
    assert booking.user_id is None
    # Who assigned the room is still on record.
    assert RoomAssignment.objects.get(booking=booking).assigned_by_id == desk.pk


@pytest.mark.django_db
def test_customer_third_booking_still_offers_the_milestone(client, hotel, priced_room):
    guest = _login(client, 'customer', 'loyal1')
    _booking(hotel, user=guest, days_out=40)
    _booking(hotel, user=guest, days_out=50)

    response = _book(client)

    assert response.json()['status'] == 'milestone_check'
    assert CustomerBookingInfo.objects.filter(user=guest).count() == 2


# ── Item 4: the account form cannot say "admin", so it must not change one ─
#
# The edit form's account type select offers Customer or Staff and nothing
# else, and the view wrote role = 'staff' if is_staff else 'customer' onto any
# row. Saving an admin's row, including the only admin's own, demoted them,
# with no UI path back.


def _edit_account(client, user, is_staff):
    return client.post(reverse('manage_accounts'), {
        'action': 'edit', 'account_id': user.user_id, 'username': user.username,
        'email': user.email, 'password': '', 'is_staff': is_staff,
    })


@pytest.mark.django_db
@pytest.mark.parametrize('is_staff', ['true', 'false'])
def test_admin_saving_own_row_stays_admin(client, is_staff):
    admin = _login(client, 'admin', 'onlyadmin')

    _edit_account(client, admin, is_staff)

    admin.refresh_from_db()
    assert admin.role == 'admin'


@pytest.mark.django_db
def test_saving_another_admin_row_keeps_it_admin(client):
    _login(client, 'admin', 'admin1')
    other = User.objects.create_user(
        username='admin2', email='admin2@example.com', password='irrelevant', role='admin')

    _edit_account(client, other, 'true')

    other.refresh_from_db()
    assert other.role == 'admin'


@pytest.mark.django_db
def test_admin_can_still_change_a_staff_role(client):
    _login(client, 'admin', 'admin3')
    staff = User.objects.create_user(
        username='desk8', email='desk8@example.com', password='irrelevant', role='staff')

    _edit_account(client, staff, 'false')

    staff.refresh_from_db()
    assert staff.role == 'customer'


# ── Item 5: a booking delete is all or nothing ────────────────────────────
#
# delete_reservation removed the room assignment, then customer requests, then
# the booking, as three separate writes. discount_codes.redeemed_booking_id is
# a foreign key, so a booking that had redeemed a code refused to delete after
# its room assignment was already gone, and the room went back on sale.
#
# transaction=True because SQLite checks these foreign keys at commit, and the
# default test transaction never commits.


@pytest.fixture
def customer_requests_table(transactional_db):
    """The view deletes from customer_requests, which has no model, so the
    SQLite test schema does not have it."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('CREATE TABLE IF NOT EXISTS customer_requests '
                       '(request_id INTEGER PRIMARY KEY, booking_id INTEGER)')
    yield
    with connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS customer_requests')


def _assigned_booking(hotel, room):
    booking = _booking(hotel)
    RoomAssignment.objects.create(
        booking=booking, room=room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    return booking


@pytest.mark.django_db(transaction=True)
def test_deleting_a_booking_that_redeemed_a_code(client, hotel, room, customer_requests_table):
    _login(client, 'staff', 'desk9')
    booking = _assigned_booking(hotel, room)
    code = DiscountCode.objects.create(
        code='TT10-ABCDEF', email='guest@example.com', discount_percent=10,
        status='redeemed', redeemed_booking=booking,
    )

    response = client.post(reverse('delete_reservation', args=[booking.booking_id]))

    assert response.status_code == 200, response.content
    assert not CustomerBookingInfo.objects.filter(pk=booking.pk).exists()
    code.refresh_from_db()
    # Deleting the booking is not a refund of the code.
    assert code.status == 'redeemed'
    assert code.redeemed_booking_id is None


@pytest.mark.django_db(transaction=True)
def test_a_failed_delete_leaves_the_room_assignment(client, hotel, room, customer_requests_table):
    from unittest.mock import patch
    _login(client, 'staff', 'desk10')
    booking = _assigned_booking(hotel, room)

    with patch.object(CustomerBookingInfo, 'delete', side_effect=RuntimeError('boom')):
        response = client.post(reverse('delete_reservation', args=[booking.booking_id]))

    assert response.status_code == 500
    assert RoomAssignment.objects.filter(booking_id=booking.pk, status='active').exists()

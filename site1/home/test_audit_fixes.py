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

from data.models import CustomerBookingInfo, RoomPrice, User


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

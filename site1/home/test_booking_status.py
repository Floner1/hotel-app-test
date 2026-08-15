"""Booking-status validation must not drift between its definition sites.

The status value is gated in three independent places:
  1. CustomerBookingInfo.status  (the model field's choices)
  2. home.views.BOOKING_STATUSES (the explicit check in edit_reservation)
  3. chk_booking_status          (the CHECK constraint in schema.sql)

Nothing keeps them in sync automatically, and the file meant to keep the live DB
constraint aligned (migrations/alter_booking_status_constraint.sql) was deleted.
These tests fail the moment any of the three drifts from the others.

Note: schema.sql is the checked-in schema, not the live database. A green run
here proves the code and the checked-in schema agree; it says nothing about what
constraint is actually installed in production.
"""

import re
from pathlib import Path

import pytest
from django.db import IntegrityError
from django.urls import reverse

from data.models import CustomerBookingInfo
from data.models.hotel import BookingStatus
from home.views import BOOKING_STATUSES

SCHEMA_SQL = Path(__file__).resolve().parent.parent / 'schema.sql'


def _schema_statuses():
    """Pull the allowed values straight out of the CHECK constraint text."""
    match = re.search(
        r"CONSTRAINT\s+chk_booking_status\s+CHECK\s*\(\s*status\s+IN\s*\(([^)]*)\)",
        SCHEMA_SQL.read_text(encoding='utf-8'),
        re.IGNORECASE,
    )
    assert match, 'chk_booking_status constraint not found in schema.sql'
    return {value.strip().strip("'") for value in match.group(1).split(',')}


@pytest.fixture
def staff_client(client, db):
    """A logged-in staff user, which is what edit_reservation requires."""
    from data.models import User
    user = User.objects.create_user(
        username='statustester',
        email='statustester@example.com',
        password='irrelevant-for-force-login',
        role='staff',
    )
    client.force_login(user, backend='home.auth_backend.CustomUserBackend')
    return client


def test_model_field_declares_the_shared_choices():
    """The model field must carry choices, not be a bare CharField."""
    field = CustomerBookingInfo._meta.get_field('status')
    assert field.choices, 'CustomerBookingInfo.status has no choices= set'
    assert {value for value, _label in field.choices} == set(BookingStatus.values)


def test_views_constant_is_derived_from_the_model():
    assert BOOKING_STATUSES == set(BookingStatus.values)


def test_schema_check_constraint_matches_the_model():
    assert _schema_statuses() == set(BookingStatus.values)


@pytest.fixture
def deluxe_rate(hotel):
    """edit_reservation resolves a rate before it ever reaches booking.save(),
    so the room type needs a real room_price row to get that far."""
    from decimal import Decimal
    from data.models import RoomPrice
    return RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )


@pytest.mark.django_db
def test_db_constraint_rejection_returns_400_not_500(
    monkeypatch, staff_client, booking, deluxe_rate
):
    """A CHECK-constraint rejection must surface as a real 400, not be swallowed
    by the generic `except Exception` that returns an opaque 500."""

    def _boom(self, *args, **kwargs):
        raise IntegrityError('CHECK constraint failed: chk_booking_status')

    monkeypatch.setattr(CustomerBookingInfo, 'save', _boom)

    response = staff_client.post(
        reverse('edit_reservation', args=[booking.booking_id]),
        data={
            'name': 'Test Guest',
            'room_type': 'deluxe',
            'checkin_date': '2026-12-20',
            'checkout_date': '2026-12-22',
            'adults': 1,
            'status': 'confirmed',
        },
        content_type='application/json',
    )

    assert response.status_code == 400, (
        f'expected 400 from the constraint handler, got {response.status_code}: '
        f'{response.content!r}'
    )


@pytest.mark.django_db
def test_invalid_room_type_returns_400_not_500(staff_client, booking):
    """Regression guard for a ValidationError name-shadowing bug.

    edit_reservation used to re-import ValidationError inside the function. A
    function-local import binds the name for the WHOLE function, so the earlier
    `raise ValidationError('Invalid room type selected.')` raised
    UnboundLocalError instead — turning this 400 path into an opaque 500.
    """
    response = staff_client.post(
        reverse('edit_reservation', args=[booking.booking_id]),
        data={
            'name': 'Test Guest',
            'room_type': 'no-such-room-type',
            'checkin_date': '2026-12-20',
            'checkout_date': '2026-12-22',
            'adults': 1,
        },
        content_type='application/json',
    )

    assert response.status_code == 400, (
        f'expected 400, got {response.status_code}: {response.content!r}'
    )
    assert 'Invalid room type' in response.json()['message']

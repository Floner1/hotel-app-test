"""Test-suite setup for a legacy, hand-managed database.

Every model in data/ (and the SQL Server schema behind it) is managed = False,
so Django creates no tables for the sqlite test database configured in
settings.py. Flip managed on for the test session only.
"""

from datetime import date
from decimal import Decimal

import django
import pytest
from django.apps import apps
from django.utils import timezone


def pytest_configure():
    # Hook order between this conftest and the pytest-django plugin is not
    # guaranteed; django.setup() is a no-op if the plugin got there first.
    django.setup()
    for model in apps.get_models():
        model._meta.managed = True


@pytest.fixture(autouse=True)
def _reset_caches():
    """Two caches outlive individual tests and fail the same way: primed against
    an empty table by one test, they make later tests fail for reasons unrelated
    to what those tests assert. ReservationService._RATE_CACHE is a class
    attribute (an empty dict counts as populated); the chat prompt's room and
    service lists sit in the per-process default LocMemCache.
    """
    from django.core.cache import cache
    from backend.services.services import ReservationService
    ReservationService._RATE_CACHE = None
    cache.clear()
    yield
    ReservationService._RATE_CACHE = None
    cache.clear()


@pytest.fixture
def hotel(db):
    from data.models import Hotel
    return Hotel.objects.create(hotel_name='Thien Tai Hotel')


@pytest.fixture
def room(hotel):
    from data.models import Room
    return Room.objects.create(
        hotel=hotel,
        room_code='101',
        floor_number=1,
        room_number=101,
        room_type='deluxe',
    )


@pytest.fixture
def booking(hotel):
    """A December 2026 booking. Dates are fixed, not relative to today, so the
    January assertion in the regression test cannot drift."""
    from data.models import CustomerBookingInfo
    now = timezone.now()
    return CustomerBookingInfo.objects.create(
        hotel=hotel,
        guest_name='Test Guest',
        room_type='deluxe',
        booking_date=now,
        check_in=date(2026, 12, 20),
        check_out=date(2026, 12, 22),
        booked_rate=Decimal('500000'),
        total_price=Decimal('1000000'),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def active_assignment(booking, room):
    from data.models import RoomAssignment
    return RoomAssignment.objects.create(
        booking=booking,
        room=room,
        status='active',
        check_in=booking.check_in,
        check_out=booking.check_out,
    )

"""_ROOM_TYPE_ALIASES has to resolve to something the rest of the app knows.

The alias table exists to map old free-text room types onto a canonical value.
It mapped them onto invented snake_case keys (one_bed_balcony_room) instead,
and no table holds those. _load_room_rates keys the rate cache on
room_price.room_type, and the availability query filters rooms.room_type on
the same strings, so every alias hit resolved to a value that matched no rate
and no physical room. The fallback path could only ever fail.

The strings asserted on below are the ones the checked-in schema seeds.
"""

from decimal import Decimal

import pytest

from backend.services.services import ReservationService

# room_price rows straight out of 'tables v10 for hotel.sql'. Kept as a literal
# so a rename in the schema shows up here as a failure rather than as a booking
# form that quietly stops pricing one room type.
SEEDED_ROOM_TYPES = (
    ('1 Bed No Window', 650000),
    ('2 Bed No Window Room', 750000),
    ('1 Bed With Window', 850000),
    ('1 Bed With Balcony', 1150000),
    ('2 Bed & Balcony Condotel', 1550000),
)


@pytest.fixture
def seeded_rates(hotel):
    from data.models import RoomPrice
    for room_type, price in SEEDED_ROOM_TYPES:
        RoomPrice.objects.create(
            hotel=hotel, room_type=room_type, price_per_night=Decimal(price)
        )


# Every string here misses the direct room_price match, so it can only resolve
# through the alias table. Each one used to raise "No nightly rate configured".
@pytest.mark.django_db
@pytest.mark.parametrize('alias, expected', [
    ('1 bed balcony room', Decimal('1150000.00')),
    ('1-bed balcony room', Decimal('1150000.00')),
    ('one_bed_balcony_room', Decimal('1150000.00')),
    ('1 bed window room', Decimal('850000.00')),
    ('two bed no window', Decimal('750000.00')),
    ('condotel 2 bed and balcony', Decimal('1550000.00')),
    ('two_bed_condotel_balcony', Decimal('1550000.00')),
])
def test_alias_only_room_types_resolve_to_a_rate(seeded_rates, alias, expected):
    assert ReservationService._resolve_rate(alias) == expected


@pytest.mark.django_db
def test_alias_resolves_to_a_type_that_matches_real_rooms(seeded_rates, hotel):
    """A priced canonical value is not enough on its own. create_reservation
    feeds the same value into the availability query against the rooms table,
    so a booking would be rejected as sold out before it ever reached pricing.
    """
    from data.models import Room
    Room.objects.create(
        hotel=hotel, room_code='401', floor_number=4, room_number=401,
        room_type='1 Bed With Balcony',
    )

    canonical = ReservationService._canonicalise_room_type('1 bed balcony room')

    assert Room.objects.filter(room_type__iexact=canonical).exists(), (
        f'canonical {canonical!r} matches no physical room'
    )


@pytest.mark.django_db
def test_a_direct_room_price_match_still_wins(seeded_rates):
    """The direct branch runs first and must keep working untouched."""
    assert ReservationService._canonicalise_room_type('1 Bed With Balcony') == (
        '1 bed with balcony'
    )


@pytest.mark.django_db
def test_unknown_room_type_returns_none(seeded_rates):
    assert ReservationService._canonicalise_room_type('presidential suite') is None


@pytest.mark.django_db
def test_alias_pointing_at_a_missing_room_price_row_returns_none(hotel):
    """No room_price rows at all, so the alias target does not exist.

    The old code returned the canonical key regardless, and the caller got
    "No nightly rate configured for room type: ..." — an error naming the
    pricing table when the fault is in this map. None gives the caller
    "Invalid room type selected" instead, which points at the right place.
    """
    assert ReservationService._canonicalise_room_type('1 bed balcony room') is None

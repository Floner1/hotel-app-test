"""Discount codes are bound to the email they were issued to.

newsletter-discount-plan.md §2 decision 2 makes the binding the whole point of
the design: knowing a code is not enough, you also have to be booking with the
address it was sent to. §4 spells out the comparison. It was specified and
never written, so until now any code could be redeemed against any email.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from backend.services.services import ReservationService
from data.models import DiscountCode

_CHECK_IN = date.today() + timedelta(days=30)


@pytest.fixture
def issued_code(db):
    """An active 10% code issued to owner@example.com and nobody else."""
    return DiscountCode.objects.create(
        code='TT10-OWNER1',
        email='owner@example.com',
        discount_percent=10,
        status='active',
    )


@pytest.fixture
def bookable(hotel):
    """The minimum create_reservation needs to reach the discount block: a
    priced room type and one physical room of that type."""
    from data.models import Room, RoomPrice
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    return Room.objects.create(
        hotel=hotel, room_code='301', floor_number=3, room_number=301,
        room_type='deluxe',
    )


@pytest.fixture(autouse=True)
def _no_outbound_mail():
    """create_reservation queues a confirmation after the transaction commits.
    A real .env with GMAIL_APP_PASSWORD flips EMAIL_BACKEND to SMTP, so an
    unpatched run would post actual mail on its way through these assertions."""
    with patch(
        'backend.services.services.EmailService.queue_booking_confirmation'
    ), patch(
        'backend.services.services.EmailService.queue_welcome_discount'
    ):
        yield


def _reservation(email):
    return {
        'name': 'Test Guest',
        'email': email,
        'checkin_date': _CHECK_IN.isoformat(),
        'checkout_date': (_CHECK_IN + timedelta(days=2)).isoformat(),
        'room_type': 'deluxe',
        'adults': 1,
        'children': 0,
        'discount_code': 'TT10-OWNER1',
    }


# ── Bug 5: the code must match the email it was issued to ──────────────


@pytest.mark.django_db(transaction=True)
def test_create_reservation_rejects_a_code_issued_to_another_email(
    bookable, issued_code
):
    with pytest.raises(ValidationError, match="isn't valid for this email"):
        ReservationService.create_reservation(_reservation('thief@example.com'))

    issued_code.refresh_from_db()
    assert issued_code.status == 'active', 'the code was redeemed by the wrong email'


@pytest.mark.django_db(transaction=True)
def test_create_reservation_accepts_the_code_for_its_own_email(bookable, issued_code):
    """The other half of the pair, so the test above cannot pass by rejecting
    every code."""
    booking = ReservationService.create_reservation(_reservation('owner@example.com'))

    issued_code.refresh_from_db()
    assert issued_code.status == 'redeemed'
    # 500000 a night, two nights, less 10%.
    assert booking.total_price == Decimal('900000.00')


@pytest.mark.django_db
def test_validate_endpoint_rejects_a_code_issued_to_another_email(client, issued_code):
    response = client.post(
        reverse('validate_discount_code'),
        {'code': 'TT10-OWNER1', 'email': 'thief@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    payload = response.json()
    assert payload['valid'] is False, f'a stranger got a green light: {payload!r}'
    assert "isn't valid for this email" in payload['message']


@pytest.mark.django_db
def test_validate_endpoint_accepts_the_code_for_its_own_email(client, issued_code):
    response = client.post(
        reverse('validate_discount_code'),
        {'code': 'TT10-OWNER1', 'email': 'owner@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    payload = response.json()
    assert payload['valid'] is True, f'the rightful owner was refused: {payload!r}'
    assert payload['discount_percent'] == 10


@pytest.mark.django_db
def test_validate_endpoint_will_not_confirm_a_code_without_an_email(client, issued_code):
    """Fail closed. Without an email the binding cannot be checked, so the
    endpoint must not call the code valid — it would be promising a discount
    that create_reservation then refuses."""
    response = client.post(
        reverse('validate_discount_code'),
        {'code': 'TT10-OWNER1'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.json()['valid'] is False


# ── The validator must not confirm a guessed code exists ──


@pytest.mark.django_db
def test_validate_endpoint_gives_one_message_for_every_failure(client, issued_code):
    """Three distinguishable messages ("not found" / "already used" / "issued
    to a different email") let a caller confirm a guessed code exists and read
    its state without knowing the address it is bound to. Rate limiting and a
    32^6 code space make brute force impractical, but they do not stop someone
    checking a code they already hold.
    """
    def message(code, email):
        return client.post(
            reverse('validate_discount_code'),
            {'code': code, 'email': email},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        ).json()['message']

    not_found = message('TT10-NOSUCH', 'anyone@example.com')
    wrong_email = message('TT10-OWNER1', 'thief@example.com')

    issued_code.status = 'redeemed'
    issued_code.save()
    already_used = message('TT10-OWNER1', 'owner@example.com')

    assert not_found == wrong_email == already_used, (
        'the three failure modes are still distinguishable: '
        f'{not_found!r} / {wrong_email!r} / {already_used!r}'
    )

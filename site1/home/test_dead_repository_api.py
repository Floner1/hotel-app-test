"""These 11 repository methods had zero callers anywhere in the repo and were
deleted. `update_booking` and `delete_booking` were the dangerous pair: they look
like the live booking-mutation API, but real updates and deletes go through
home/views.py (update_reservation / delete_reservation), which also re-syncs room
assignments, writes the audit log, and clears child FK rows first. Calling the
repository versions instead would silently skip all of that.

If one of these names comes back, it is either dead weight again or a
reimplementation of a path that already exists somewhere better.
"""

import pytest

from data.repos.repositories import (
    DiscountRepository,
    EmailRepository,
    ReservationRepository,
)

DEAD_METHODS = [
    (ReservationRepository, 'email_exists'),
    (ReservationRepository, 'get_upcoming_bookings'),
    (ReservationRepository, 'get_bookings_by_date_range'),
    (ReservationRepository, 'search_bookings'),
    (ReservationRepository, 'get_booking_count'),
    (ReservationRepository, 'get_bookings_today'),
    (ReservationRepository, 'update_booking'),
    (ReservationRepository, 'delete_booking'),
    (EmailRepository, 'list_recent'),
    (EmailRepository, 'list_subscribers'),
    (DiscountRepository, 'issue_milestone_for_email'),
]


@pytest.mark.parametrize(
    'cls,name',
    DEAD_METHODS,
    ids=[f'{c.__name__}.{n}' for c, n in DEAD_METHODS],
)
def test_dead_repository_method_stays_deleted(cls, name):
    assert not hasattr(cls, name), (
        f'{cls.__name__}.{name} is back; it had zero callers and was removed'
    )

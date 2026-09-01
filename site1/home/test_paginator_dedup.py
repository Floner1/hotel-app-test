"""Characterization tests for the three paginated admin views.

admin_reservations, email_log and email_subscribers each carried the same
copy-pasted Paginator try/except ladder. Django's Paginator.get_page() *is*
that ladder, so each block collapses to one line. Nothing about behaviour is
supposed to move, so these tests are written to pass BEFORE the change as
well as after -- they are characterization tests, not red-green TDD.

The edges are the risk, not the happy path: a non-integer page, an
out-of-range page, and an absent page param are the three branches the old
code spelled out by hand. Each view also gets its per-page number pinned,
because that is the one thing that genuinely differs between the three sites
(200 for reservations, 25 for the two email views) and the easiest thing to
lose in a copy-paste collapse.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import CustomerBookingInfo, EmailQueue, EmailSubscriber, User


@pytest.fixture
def admin_ui_client(client, db):
    """All three views sit behind @login_required + is_staff_or_admin.

    Deliberately a local fixture: home/ already has several of these
    (test_room_maintenance.staff_client, tests.account_admin) and folding
    them into conftest.py is out of scope here.
    """
    admin = User.objects.create_user(
        username='pagetester',
        email='pagetester@example.com',
        password='irrelevant-for-force-login',
        role='admin',
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


@pytest.fixture
def thirty_emails(db):
    """30 rows over a 25-per-page view: 2 pages, second one short.

    A short last page is what makes "out of range returns the LAST page"
    distinguishable from "returns the first page".
    """
    now = timezone.now()
    EmailQueue.objects.bulk_create([
        EmailQueue(
            to_email=f'guest{i}@example.com',
            subject=f'Booking {i}',
            email_type='booking_confirmation',
            status='sent',
            created_at=now - timedelta(minutes=i),
        )
        for i in range(30)
    ])


@pytest.fixture
def thirty_subscribers(db):
    now = timezone.now()
    EmailSubscriber.objects.bulk_create([
        EmailSubscriber(
            email=f'sub{i}@example.com',
            status='subscribed',
            unsubscribe_token=f'token-{i:04d}',
            created_at=now - timedelta(minutes=i),
        )
        for i in range(30)
    ])


@pytest.fixture
def thirty_bookings(hotel):
    now = timezone.now()
    CustomerBookingInfo.objects.bulk_create([
        CustomerBookingInfo(
            hotel=hotel,
            guest_name=f'Guest {i}',
            room_type='deluxe',
            booking_date=now,
            check_in=date(2027, 3, 1),
            check_out=date(2027, 3, 3),
            booked_rate=Decimal('500000'),
            total_price=Decimal('1000000'),
            created_at=now,
            updated_at=now,
        )
        for i in range(30)
    ])


# -- email_log: all four edges, on a two-page dataset --


@pytest.mark.django_db
def test_email_log_valid_page_returns_that_page(admin_ui_client, thirty_emails):
    response = admin_ui_client.get(reverse('email_log'), {'page': 2})

    assert response.status_code == 200
    rows = response.context['rows']
    assert rows.number == 2
    assert len(rows.object_list) == 5


@pytest.mark.django_db
def test_email_log_non_integer_page_returns_page_one(admin_ui_client, thirty_emails):
    response = admin_ui_client.get(reverse('email_log'), {'page': 'notanumber'})

    assert response.status_code == 200, 'a junk page must not 404 or 500'
    rows = response.context['rows']
    assert rows.number == 1
    assert len(rows.object_list) == 25


@pytest.mark.django_db
def test_email_log_out_of_range_page_returns_the_last_page(admin_ui_client, thirty_emails):
    response = admin_ui_client.get(reverse('email_log'), {'page': 99999})

    assert response.status_code == 200, 'an out-of-range page must not 404'
    rows = response.context['rows']
    assert rows.number == rows.paginator.num_pages == 2, 'must land on the LAST page'
    assert len(rows.object_list) == 5, 'the last page must not be empty'


@pytest.mark.django_db
def test_email_log_absent_page_returns_page_one(admin_ui_client, thirty_emails):
    response = admin_ui_client.get(reverse('email_log'))

    assert response.status_code == 200
    rows = response.context['rows']
    assert rows.number == 1
    assert len(rows.object_list) == 25


@pytest.mark.django_db
def test_email_log_empty_page_param_returns_page_one(admin_ui_client, thirty_emails):
    """?page= with no value: int of an empty string is a ValueError, the same
    branch junk input takes."""
    response = admin_ui_client.get(reverse('email_log') + '?page=')

    assert response.status_code == 200
    assert response.context['rows'].number == 1


@pytest.mark.django_db
def test_email_log_page_zero_returns_the_last_page(admin_ui_client, thirty_emails):
    """page < 1 raises EmptyPage, not PageNotAnInteger, so it takes the
    out-of-range branch and lands on the last page. Odd, but it is what the
    hand-written ladder did and get_page does the same."""
    response = admin_ui_client.get(reverse('email_log'), {'page': 0})

    assert response.status_code == 200
    assert response.context['rows'].number == 2


@pytest.mark.django_db
def test_email_log_paginates_25_per_page(admin_ui_client, thirty_emails):
    response = admin_ui_client.get(reverse('email_log'))

    assert response.context['rows'].paginator.per_page == 25


# -- email_subscribers: same four edges --


@pytest.mark.django_db
def test_email_subscribers_valid_page_returns_that_page(admin_ui_client, thirty_subscribers):
    response = admin_ui_client.get(reverse('email_subscribers'), {'page': 2})

    assert response.status_code == 200
    rows = response.context['rows']
    assert rows.number == 2
    assert len(rows.object_list) == 5


@pytest.mark.django_db
def test_email_subscribers_non_integer_page_returns_page_one(admin_ui_client, thirty_subscribers):
    response = admin_ui_client.get(reverse('email_subscribers'), {'page': 'notanumber'})

    assert response.status_code == 200, 'a junk page must not 404 or 500'
    rows = response.context['rows']
    assert rows.number == 1
    assert len(rows.object_list) == 25


@pytest.mark.django_db
def test_email_subscribers_out_of_range_page_returns_the_last_page(admin_ui_client, thirty_subscribers):
    response = admin_ui_client.get(reverse('email_subscribers'), {'page': 99999})

    assert response.status_code == 200, 'an out-of-range page must not 404'
    rows = response.context['rows']
    assert rows.number == rows.paginator.num_pages == 2, 'must land on the LAST page'
    assert len(rows.object_list) == 5, 'the last page must not be empty'


@pytest.mark.django_db
def test_email_subscribers_absent_page_returns_page_one(admin_ui_client, thirty_subscribers):
    response = admin_ui_client.get(reverse('email_subscribers'))

    assert response.status_code == 200
    rows = response.context['rows']
    assert rows.number == 1
    assert len(rows.object_list) == 25
    assert rows.paginator.per_page == 25


# -- admin_reservations: 200 per page, so 30 rows is a single page --
#
# Not worth inserting 201 bookings to get a second page: the two email views
# above already pin "out of range lands on the LAST page, not the first".
# What matters here is that the branches still fire without a 404/500 and
# that this site kept its own per-page number of 200.


@pytest.mark.django_db
def test_admin_reservations_valid_page_returns_that_page(admin_ui_client, thirty_bookings):
    response = admin_ui_client.get(reverse('admin_reservations'), {'page': 1})

    assert response.status_code == 200
    reservations = response.context['reservations']
    assert reservations.number == 1
    assert len(reservations.object_list) == 30


@pytest.mark.django_db
def test_admin_reservations_non_integer_page_returns_page_one(admin_ui_client, thirty_bookings):
    response = admin_ui_client.get(reverse('admin_reservations'), {'page': 'notanumber'})

    assert response.status_code == 200, 'a junk page must not 404 or 500'
    assert response.context['reservations'].number == 1


@pytest.mark.django_db
def test_admin_reservations_out_of_range_page_returns_the_last_page(admin_ui_client, thirty_bookings):
    response = admin_ui_client.get(reverse('admin_reservations'), {'page': 99999})

    assert response.status_code == 200, 'an out-of-range page must not 404'
    reservations = response.context['reservations']
    assert reservations.number == reservations.paginator.num_pages
    assert len(reservations.object_list) == 30, 'the last page must not be empty'


@pytest.mark.django_db
def test_admin_reservations_absent_page_returns_page_one(admin_ui_client, thirty_bookings):
    response = admin_ui_client.get(reverse('admin_reservations'))

    assert response.status_code == 200
    assert response.context['reservations'].number == 1


@pytest.mark.django_db
def test_admin_reservations_keeps_its_own_200_per_page(admin_ui_client, thirty_bookings):
    """The one thing that really differs between the three call sites."""
    response = admin_ui_client.get(reverse('admin_reservations'))

    assert response.context['reservations'].paginator.per_page == 200


# -- The empty-table case, where num_pages is 1 and page 1 is legal but empty --


@pytest.mark.django_db
def test_out_of_range_on_an_empty_table_still_returns_page_one(admin_ui_client):
    response = admin_ui_client.get(reverse('email_log'), {'page': 99999})

    assert response.status_code == 200, 'an empty table must not 404'
    rows = response.context['rows']
    assert rows.number == 1
    assert len(rows.object_list) == 0

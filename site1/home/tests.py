import contextlib
import json
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from data.models import User
from data.repos.repositories import EmailRepository, RoomRepository
from backend.services.services import ReservationService, RoomService

# Campaign body_html is rendered with |safe into the outgoing email, so it must
# be sanitized on the way IN, at save time. These tests assert on the value
# handed to the ORM rather than reading it back: the suite cannot build a test
# database (data.User is managed=False, so the users table never exists and
# django_admin_log's FK fails), and the value passed to .create()/.save() is
# exactly what would be written.

DIRTY = '<p>Spring rates</p><script>alert(1)</script><a href="javascript:alert(2)">x</a>'


@patch('data.repos.repositories.EmailCampaign.objects.create')
def test_create_campaign_sanitizes_body_html(mock_create):
    EmailRepository.create_campaign(name='Spring', subject='Rates', body_html=DIRTY)

    saved = mock_create.call_args.kwargs['body_html']
    assert '<script>' not in saved, f'script tag reached the DB: {saved!r}'
    assert 'javascript:' not in saved, f'javascript: URL reached the DB: {saved!r}'
    assert '<p>Spring rates</p>' in saved, f'safe markup was stripped: {saved!r}'


@patch('data.repos.repositories.EmailCampaign.objects.get')
def test_update_campaign_sanitizes_body_html(mock_get):
    camp = mock_get.return_value

    EmailRepository.update_campaign(1, body_html=DIRTY)

    assert '<script>' not in camp.body_html, f'script tag reached the DB: {camp.body_html!r}'
    assert 'javascript:' not in camp.body_html
    assert '<p>Spring rates</p>' in camp.body_html

@pytest.mark.django_db
def test_newsletter_signup_invalid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'invalid-email'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 400
    assert response.json()['status'] == 'error'

@pytest.mark.django_db
def test_newsletter_signup_valid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'test@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


# Regression cover for the availability bug: get_available_rooms_by_type used to
# filter on Room.reservation_status, which is a snapshot of the room's state
# right now, not over the requested range. A room reserved for December was
# therefore unbookable in January.

@pytest.mark.django_db
def test_future_booking_does_not_block_other_dates(room, active_assignment):
    room.reservation_status = 'reserved'
    room.save()

    free = RoomRepository.count_available_rooms_by_type(
        room.room_type, date(2027, 1, 5), date(2027, 1, 7)
    )

    assert free == 1, 'a room booked in December must still be bookable in January'


@pytest.mark.django_db
def test_overlapping_dates_are_excluded(room, active_assignment):
    free = RoomRepository.count_available_rooms_by_type(
        room.room_type, active_assignment.check_in, active_assignment.check_out
    )

    assert free == 0, 'a room with an active assignment over the range is not available'


# Room allocation used to run inside a bare `except Exception: logger.warning(...)`
# in create_reservation. The booking row is written before allocation is
# attempted, so a failed allocation left a committed booking with no room
# attached and still returned that booking to the caller as a success.

# Derived from today, not hardcoded: _validate_dates rejects a past check-in,
# which would raise before a booking is ever written and leave the assertions
# below passing for the wrong reason.
_CHECK_IN = date.today() + timedelta(days=30)

RESERVATION = {
    'name': 'Test Guest',
    'email': 'guest@example.com',
    'checkin_date': _CHECK_IN.isoformat(),
    'checkout_date': (_CHECK_IN + timedelta(days=2)).isoformat(),
    'room_type': 'deluxe',
    'adults': 1,
    'children': 0,
}


@pytest.fixture
def bookable(hotel):
    """The minimum create_reservation needs to reach room allocation: a priced
    room type and one physical room of that type."""
    from data.models import Room, RoomPrice
    RoomPrice.objects.create(
        hotel=hotel, room_type='deluxe', price_per_night=Decimal('500000')
    )
    return Room.objects.create(
        hotel=hotel,
        room_code='201',
        floor_number=2,
        room_number=201,
        room_type='deluxe',
    )


def _allocation_fails():
    """Replace allocate_room with the ValidationError it raises when it loses
    the race for the last room. Substituted rather than provoked naturally:
    create_reservation and allocate_room run the same availability query, so
    they only disagree under concurrency — which test_concurrency.py covers
    against real SQL Server."""
    return patch.object(
        RoomService,
        'allocate_room',
        side_effect=ValidationError('No available deluxe rooms.'),
    )


@pytest.mark.django_db(transaction=True)
def test_failed_allocation_raises_to_the_caller(bookable):
    with _allocation_fails() as allocate:
        with pytest.raises(ValidationError, match='No available deluxe rooms'):
            ReservationService.create_reservation(dict(RESERVATION))

    # Without this, any of create_reservation's ~8 earlier ValidationErrors
    # would satisfy the raises() above while never reaching the fixed line.
    assert allocate.called, 'never got as far as room allocation'


@pytest.mark.django_db(transaction=True)
def test_failed_allocation_leaves_no_booking_behind(bookable):
    from data.models import CustomerBookingInfo

    with _allocation_fails() as allocate:
        # Swallow here so this test asserts on the committed rows, not on the
        # exception; the raise itself is covered by the test above.
        with contextlib.suppress(ValidationError):
            ReservationService.create_reservation(dict(RESERVATION))

    assert allocate.called, 'never got as far as room allocation'
    assert CustomerBookingInfo.objects.count() == 0, (
        'a booking was committed even though no room could be allocated'
    )


# ── Authentication and access control ──────────────────────────────────
# All four run without the database: data.User is managed = False, so the
# users table does not exist in the test database. They patch at the query
# boundary and assert on what the code does with the result.


def test_auth_backend_rejects_inactive_user_even_with_correct_password():
    """A deactivated account must not authenticate, right password or not.

    CustomUserBackend checks is_active AFTER the password check, so a broken
    ordering here would let a disabled account back in.
    """
    from home.auth_backend import CustomUserBackend

    user = MagicMock(is_active=False)
    user.check_password.return_value = True

    with patch('home.auth_backend.User.objects.get', return_value=user):
        result = CustomUserBackend().authenticate(
            None, username='bob', password='correct-password'
        )

    assert result is None, 'an inactive user was authenticated'


def test_auth_backend_accepts_active_user_with_correct_password():
    """The other half of the pair, so the test above cannot pass by rejecting
    everything."""
    from home.auth_backend import CustomUserBackend

    user = MagicMock(is_active=True)
    user.check_password.return_value = True

    with patch('home.auth_backend.User.objects.get', return_value=user):
        result = CustomUserBackend().authenticate(
            None, username='bob', password='correct-password'
        )

    assert result is user


def test_password_validators_reject_an_all_digit_password():
    """AUTH_PASSWORD_VALIDATORS must still include NumericPasswordValidator.

    Guards the settings entry, not the view. The view itself is covered by
    test_register_view_rejects_an_all_digit_password below.
    """
    with pytest.raises(ValidationError):
        validate_password('12345678')


def _clear_register_ratelimit():
    """register_view is @ratelimit(key='ip', rate='3/m'). django-ratelimit
    counts in the default cache, which is process-wide and outlives a test, so
    the third registration test in a run would get a 403 instead of the
    rejection it asserts on."""
    from django.core.cache import cache
    cache.clear()


@pytest.mark.django_db
def test_register_view_rejects_an_all_digit_password(client):
    """register_view must run the configured validators, not just a length check.

    '12345678' is eight characters, so the `len(password1) < 8` test passes it.
    Only NumericPasswordValidator and CommonPasswordValidator catch it, and
    they are inert unless the view actually calls validate_password.

    _send_verification_email is patched out because GMAIL_APP_PASSWORD in a
    real .env flips EMAIL_BACKEND to SMTP, and a regression here would
    otherwise post real mail on the way to failing.
    """
    _clear_register_ratelimit()
    with patch('home.views._send_verification_email') as send_mail:
        response = client.post(reverse('register'), {
            'username': 'digituser',
            'email': 'digits@example.com',
            'password1': '12345678',
            'password2': '12345678',
        })

    assert not User.objects.filter(username='digituser').exists(), (
        'an all-numeric password created an account'
    )
    assert not send_mail.called, 'reached the verification email despite a bad password'
    assert b'entirely numeric' in response.content, (
        f'no validator message rendered back to the form: {response.content[:400]!r}'
    )


@pytest.mark.django_db
def test_register_view_rejects_a_password_matching_the_username(client):
    """validate_password has to be given the user, or one of the four
    configured validators does nothing.

    UserAttributeSimilarityValidator returns immediately on a None user, so
    calling validate_password(password) alone still accepts a password
    identical to the username. The view passes an unsaved User for this.
    """
    _clear_register_ratelimit()
    with patch('home.views._send_verification_email') as send_mail:
        response = client.post(reverse('register'), {
            'username': 'sameassword',
            'email': 'same@example.com',
            'password1': 'sameassword',
            'password2': 'sameassword',
        })

    assert not User.objects.filter(username='sameassword').exists(), (
        'a password identical to the username created an account'
    )
    assert not send_mail.called
    assert b'too similar' in response.content, (
        f'no similarity message rendered back to the form: {response.content[:400]!r}'
    )


@pytest.fixture
def account_admin(db, client):
    """manage_accounts is staff/admin only, and creating a staff account needs
    admin specifically."""
    admin = User.objects.create_user(
        username='acctadmin', email='acctadmin@example.com',
        password='irrelevant-for-force-login', role='admin',
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


@pytest.mark.django_db
def test_manage_accounts_rejects_a_weak_password(account_admin):
    """Staff provisioning an account must clear the same bar as public signup.

    register_view has called validate_password since the length-check bug;
    manage_accounts went straight to set_password, so '12345678' sailed in.
    Eight characters passes a length check, and NumericPasswordValidator and
    CommonPasswordValidator both reject it, so it only lands if the view never
    runs the validators.
    """
    account_admin.post(reverse('manage_accounts'), {
        'action': 'create',
        'username': 'weakuser',
        'email': 'weak@example.com',
        'password': '12345678',
    })

    assert not User.objects.filter(username='weakuser').exists(), (
        'an all-numeric password created a staff-provisioned account'
    )


@pytest.mark.django_db
def test_manage_accounts_still_creates_an_account_with_a_good_password(account_admin):
    """So the test above cannot pass by rejecting everything."""
    account_admin.post(reverse('manage_accounts'), {
        'action': 'create',
        'username': 'sturdyuser',
        'email': 'sturdy@example.com',
        'password': 'chim-vac-sau-1954',
    })

    assert User.objects.filter(username='sturdyuser').exists(), (
        'a perfectly good password was refused'
    )


@pytest.mark.django_db
def test_manage_accounts_rejects_a_weak_password_on_edit(account_admin):
    """The edit branch sets passwords too. Validating only on create would move
    the same hole one button across the same screen."""
    target = User.objects.create_user(
        username='edittarget', email='edittarget@example.com',
        password='chim-vac-sau-1954', role='customer',
    )
    old_hash = target.password_hash

    account_admin.post(reverse('manage_accounts'), {
        'action': 'edit',
        'account_id': target.user_id,
        'username': 'edittarget',
        'email': 'edittarget@example.com',
        'password': '12345678',
    })

    target.refresh_from_db()
    assert target.password_hash == old_hash, 'an all-numeric password was accepted'


@pytest.mark.django_db
def test_milestone_count_is_taken_under_a_row_lock(client):
    """The count that grants the discount must not straddle a transaction.

    Asserted at the query boundary because sqlite accepts select_for_update()
    and never blocks on it; test_concurrency.py proves the blocking half
    against real SQL Server, the same split pytest.ini already documents for
    allocate_room. Without the lock, two bookings from one guest around their
    third both read the same count and both collect 10%.

    This guest has no bookings, so the provisional count is 1 and the request
    falls through the ask-the-guest branch into the locked one.
    """
    guest = User.objects.create_user(
        username='milestoneguest', email='milestone@example.com',
        password='irrelevant-for-force-login', role='customer',
    )
    client.force_login(guest, backend='home.auth_backend.CustomUserBackend')

    with patch('home.views.User.objects.select_for_update') as locked:
        client.post(reverse('reservation'), {
            'name': 'Milestone Guest', 'email': 'milestone@example.com',
            'phone': '123',
            'checkin_date': _CHECK_IN.strftime('%m/%d/%Y'),
            'checkout_date': (_CHECK_IN + timedelta(days=2)).strftime('%m/%d/%Y'),
            'adults': '1', 'children': '0', 'room_type': 'deluxe',
        })

    assert locked.called, 'the milestone count ran without locking the guest row'


def test_milestone_check_counts_bookings_by_authenticated_user_not_email():
    """Loyalty milestones must be counted against request.user.

    The email arrives in the POST body, so counting on it would let anyone
    claim someone else's every-third-booking discount by typing their
    address. The assertion is on the filter kwargs for that reason.
    """
    from home.views import get_reservation

    user = MagicMock(is_authenticated=True, is_staff=False)
    request = RequestFactory().post('/reservation/', {
        'name': 'Jane', 'phone': '123', 'email': 'jane@example.com',
        'checkin_date': '2026-08-01', 'checkout_date': '2026-08-02',
        'adults': '1', 'children': '0', 'room_type': 'standard',
        'milestone_decision': '',
    })
    request.user = user

    mock_qs = MagicMock()
    # The count runs through .exclude() to drop cancelled and rejected
    # bookings, so prime the end of that chain rather than the filter itself.
    mock_qs.exclude.return_value.count.return_value = 2  # (2+1) % 3 == 0
    with patch(
        'home.views.CustomerBookingInfo.objects.filter', return_value=mock_qs
    ) as mock_filter:
        response = get_reservation(request)

    assert json.loads(response.content)['status'] == 'milestone_check'
    mock_filter.assert_called_once_with(user=user)

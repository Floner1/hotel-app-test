"""Room maintenance issues: reporting one and resolving it.

`room_maintenance_logs` has been in the schema since v10 and the README has
described it as working the whole time, but nothing in the app read or wrote it.
This is the flow that makes the table real, scoped with Peter before any of it
was written:

  - the description is captured in the same click that marks a room Out of Order
  - resolving an issue does NOT bring the room back into service; staff still
    click Empty Clean or Empty Dirty, so `_display_status` keeps a single driver
  - the schema's 'in_progress' status stays unused, because nothing drives it
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import CustomerBookingInfo, Room, RoomAssignment
from data.models.hotel import RoomMaintenanceLog
from data.repos.repositories import RoomMaintenanceRepository


@pytest.fixture
def staff_user(db):
    from data.models import User
    return User.objects.create_user(
        username='roomtester',
        email='roomtester@example.com',
        password='irrelevant-for-force-login',
        role='staff',
    )


@pytest.fixture
def staff_client(client, staff_user):
    """A logged-in staff user, which the dashboard requires."""
    client.force_login(staff_user, backend='home.auth_backend.CustomUserBackend')
    return client


# ── The model ──


@pytest.mark.django_db
def test_log_maps_to_the_schema_table_and_defaults_to_open(room):
    log = RoomMaintenanceLog.objects.create(
        room=room, issue_description='Aircon leaking', created_at=timezone.now(),
    )

    assert RoomMaintenanceLog._meta.db_table == 'room_maintenance_logs'
    # original_attrs, not _meta.managed: conftest flips managed on for every
    # model so sqlite gets tables, so _meta.managed reads True during tests
    # whatever the class declared. This has to assert what the class declared.
    assert RoomMaintenanceLog._meta.original_attrs['managed'] is False
    assert log.status == 'open'
    assert log.resolved_at is None
    assert log.reported_by is None


# ── The repository ──


@pytest.mark.django_db
def test_report_creates_an_open_log_attributed_to_the_reporter(room, staff_user):
    log = RoomMaintenanceRepository.report(room, 'Aircon leaking', staff_user)

    assert log.status == 'open'
    assert log.room_id == room.room_id
    assert log.reported_by_id == staff_user.user_id
    assert log.created_at is not None, (
        'created_at must be written explicitly: Django names every field in the '
        'INSERT, so leaving it unset writes NULL straight past DEFAULT GETDATE()'
    )


@pytest.mark.django_db
def test_resolve_marks_resolved_and_stamps_the_time(room):
    log = RoomMaintenanceRepository.report(room, 'Door will not latch')

    resolved = RoomMaintenanceRepository.resolve(log.log_id)

    assert resolved.status == 'resolved'
    assert resolved.resolved_at is not None
    log.refresh_from_db()
    assert log.status == 'resolved', 'the change must be persisted, not just local'


@pytest.mark.django_db
def test_resolving_an_already_resolved_issue_returns_none(room):
    log = RoomMaintenanceRepository.report(room, 'Cracked window')
    RoomMaintenanceRepository.resolve(log.log_id)

    assert RoomMaintenanceRepository.resolve(log.log_id) is None


@pytest.mark.django_db
def test_open_by_room_groups_by_room_and_omits_resolved(room, hotel):
    other = Room.objects.create(
        hotel=hotel, room_code='102', floor_number=1, room_number=102,
        room_type='deluxe',
    )
    RoomMaintenanceRepository.report(room, 'Issue one')
    done = RoomMaintenanceRepository.report(room, 'Issue two')
    RoomMaintenanceRepository.resolve(done.log_id)
    RoomMaintenanceRepository.report(other, 'Issue three')

    by_room = RoomMaintenanceRepository.open_by_room()

    assert [l.issue_description for l in by_room[room.room_id]] == ['Issue one']
    assert len(by_room[other.room_id]) == 1


# ── Reporting through the dashboard ──


@pytest.mark.django_db
def test_marking_out_of_order_with_a_description_logs_the_issue(staff_client, room):
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'out_of_order',
         'issue_description': 'Aircon leaking onto the carpet'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    log = RoomMaintenanceLog.objects.get(room_id=room.room_id)
    assert log.issue_description == 'Aircon leaking onto the carpet'
    assert log.status == 'open'
    assert log.reported_by.username == 'roomtester', 'reported_by comes from request.user'


@pytest.mark.django_db
def test_marking_out_of_order_with_no_description_logs_nothing(staff_client, room):
    staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'out_of_order',
         'issue_description': '   '},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert not RoomMaintenanceLog.objects.exists()
    room.refresh_from_db()
    assert room.housekeeping_status == 'out_of_order', 'the status change still happens'


@pytest.mark.django_db
def test_a_description_on_any_other_status_change_logs_nothing(staff_client, room):
    """The textarea sits under all five condition buttons. Only Out of Order
    means 'this room has a fault'."""
    staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'empty_dirty',
         'issue_description': 'typed then thought better of it'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert not RoomMaintenanceLog.objects.exists()


@pytest.mark.django_db
def test_no_log_is_written_when_the_status_change_is_refused(staff_client, room):
    """A 409 from the status guard must not leave an open issue behind on a room
    that never went offline. This is why the log is written after room.save()."""
    room.housekeeping_status = 'out_of_order'
    room.save()

    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied',
         'issue_description': 'should never be stored'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409
    assert not RoomMaintenanceLog.objects.exists()


@pytest.mark.django_db
def test_an_over_long_description_is_refused_rather_than_truncated(staff_client, room):
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'out_of_order',
         'issue_description': 'x' * 1001},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 400
    assert not RoomMaintenanceLog.objects.exists()
    room.refresh_from_db()
    assert room.housekeeping_status != 'out_of_order', (
        'the refusal must come before the room write, not leave it half applied'
    )


# ── Resolving through the dashboard ──


@pytest.mark.django_db
def test_resolve_issue_action_resolves_the_log(staff_client, room):
    log = RoomMaintenanceRepository.report(room, 'Door will not latch')

    response = staff_client.post(
        reverse('room_dashboard'),
        {'action': 'resolve_issue', 'log_id': log.log_id},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    log.refresh_from_db()
    assert log.status == 'resolved'


@pytest.mark.django_db
def test_resolving_an_issue_leaves_the_room_out_of_order(staff_client, room):
    """The decision taken with Peter: resolve records that the fault is fixed,
    it does not put the room back in service. Staff do that with Empty Clean or
    Empty Dirty, so room status keeps a single driver."""
    room.housekeeping_status = 'out_of_order'
    room.save()
    log = RoomMaintenanceRepository.report(room, 'Aircon leaking')

    staff_client.post(
        reverse('room_dashboard'),
        {'action': 'resolve_issue', 'log_id': log.log_id},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    room.refresh_from_db()
    assert room.housekeeping_status == 'out_of_order'


@pytest.mark.django_db
def test_resolving_a_missing_or_non_numeric_log_id_is_a_404_not_a_crash(staff_client):
    # '²' is the catch: str.isdigit() is True for superscript two, but
    # int() only takes decimal digits and raises ValueError on it. Screening
    # with isdigit() and then calling int() turns that into a 500.
    for bad in ('999999', 'not-a-number', '', '²'):
        response = staff_client.post(
            reverse('room_dashboard'),
            {'action': 'resolve_issue', 'log_id': bad},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 404, f'log_id={bad!r} gave {response.status_code}'


# ── Gating ──


@pytest.mark.django_db
def test_a_customer_cannot_report_or_resolve(client, room):
    """Both new actions must sit behind the same staff gate as every other
    dashboard write, not just the status buttons."""
    from data.models import User
    customer = User.objects.create_user(
        username='guest1', email='guest1@example.com', password='x', role='customer',
    )
    client.force_login(customer, backend='home.auth_backend.CustomUserBackend')
    log = RoomMaintenanceRepository.report(room, 'Pre-existing issue')

    report = client.post(reverse('room_dashboard'), {
        'room_id': room.room_id, 'new_status': 'out_of_order',
        'issue_description': 'customer trying to report',
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    resolve = client.post(reverse('room_dashboard'), {
        'action': 'resolve_issue', 'log_id': log.log_id,
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    assert report.status_code == 302 and resolve.status_code == 302
    assert RoomMaintenanceLog.objects.count() == 1
    log.refresh_from_db()
    assert log.status == 'open'


# ── What the dashboard renders ──


@pytest.mark.django_db
def test_the_dashboard_carries_open_issues_and_escapes_the_free_text(staff_client, room):
    RoomMaintenanceRepository.report(room, '<script>alert(1)</script> broken')

    body = staff_client.get(reverse('room_dashboard')).content.decode()

    assert '<script>alert(1)</script> broken' not in body, (
        'staff-entered free text must not reach the page as live markup'
    )
    assert 'broken' in body, 'the issue should still reach the page'
    assert 'openIssuesData' in body


@pytest.mark.django_db
def test_a_room_with_an_open_issue_carries_a_badge_count(staff_client, room):
    RoomMaintenanceRepository.report(room, 'Issue one')
    RoomMaintenanceRepository.report(room, 'Issue two')

    response = staff_client.get(reverse('room_dashboard'))

    item = next(
        i for floor in response.context['floors'].values()
        for i in floor if i['room'].room_id == room.room_id
    )
    assert item['open_issue_count'] == 2


@pytest.mark.django_db
def test_resolved_issues_do_not_reach_the_dashboard(staff_client, room):
    log = RoomMaintenanceRepository.report(room, 'already fixed thing')
    RoomMaintenanceRepository.resolve(log.log_id)

    body = staff_client.get(reverse('room_dashboard')).content.decode()

    assert 'already fixed thing' not in body


# ── Returning a broken occupied room to service ──


@pytest.fixture
def broken_and_occupied(room, hotel):
    """A room a guest is in right now, taken out of order for a fault.

    Out of Order outranks the assignment in the derivation, so marking it is
    allowed on an occupied room and this is exactly what the maintenance flow
    encourages. Getting it back afterwards is the part that was stuck.
    """
    now = timezone.now()
    booking = CustomerBookingInfo.objects.create(
        hotel=hotel, guest_name='In House', room_type='deluxe', booking_date=now,
        check_in=date.today() - timedelta(days=1),
        check_out=date.today() + timedelta(days=2),
        booked_rate=Decimal('500000'), total_price=Decimal('1000000'),
        status='checked_in', created_at=now, updated_at=now,
    )
    RoomAssignment.objects.create(
        booking=booking, room=room, status='active',
        check_in=booking.check_in, check_out=booking.check_out,
    )
    room.reservation_status = 'occupied'
    room.housekeeping_status = 'out_of_order'
    room.save()
    return booking


def _disp_status(staff_client, room):
    response = staff_client.get(reverse('room_dashboard'))
    item = next(
        i for floor in response.context['floors'].values()
        for i in floor if i['room'].room_id == room.room_id
    )
    return item['disp_status']


@pytest.mark.django_db
def test_empty_clean_returns_a_broken_occupied_room_to_service(
    staff_client, room, broken_and_occupied
):
    """The reported case. Both clearing buttons used to refuse with a 409
    blaming the booking, so a fault reported on an occupied room could be
    marked and resolved but the room could never come back.

    Clearing is a maintenance write, not an occupancy one. It writes
    housekeeping and leaves reservation_status to the assignment.
    """
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'vacant'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.housekeeping_status == 'clean'
    assert room.reservation_status == 'occupied', (
        'occupancy is the assignment to state, so the clearing click must not '
        'write reservation_status'
    )
    assert _disp_status(staff_client, room) == 'occupied', (
        'the guest is still in the room, so the card goes back to occupied'
    )


@pytest.mark.django_db
def test_empty_dirty_returns_a_broken_occupied_room_to_service(
    staff_client, room, broken_and_occupied
):
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'empty_dirty'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200, response.content
    room.refresh_from_db()
    assert room.housekeeping_status == 'dirty'
    assert room.reservation_status == 'occupied'
    assert _disp_status(staff_client, room) == 'occupied'


@pytest.mark.django_db
def test_clearing_still_frees_a_room_with_no_assignment(staff_client, room):
    """The no-assignment path is untouched: there is no booking to defer to, so
    the clearing click owns both fields exactly as it did before."""
    room.reservation_status = 'occupied'
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
    assert room.reservation_status == 'vacant'


@pytest.mark.django_db
def test_occupied_on_a_broken_assigned_room_is_still_refused(
    staff_client, room, broken_and_occupied
):
    """Only the two clearing buttons get the maintenance carve-out. Occupied
    and Reserved still go through the guard untouched."""
    response = staff_client.post(
        reverse('room_dashboard'),
        {'room_id': room.room_id, 'new_status': 'occupied'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 409
    room.refresh_from_db()
    assert room.housekeeping_status == 'out_of_order', 'nothing saved on a refusal'


@pytest.mark.django_db
def test_the_whole_report_fix_resolve_return_loop(staff_client, room, broken_and_occupied):
    """End to end over the flow this feature actually creates: a guest is in the
    room, something breaks, staff log it, maintenance fix it, room comes back."""
    staff_client.post(reverse('room_dashboard'), {
        'room_id': room.room_id, 'new_status': 'out_of_order',
        'issue_description': 'Shower runs cold',
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    log = RoomMaintenanceLog.objects.get(room_id=room.room_id)

    staff_client.post(reverse('room_dashboard'), {
        'action': 'resolve_issue', 'log_id': log.log_id,
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    back = staff_client.post(reverse('room_dashboard'), {
        'room_id': room.room_id, 'new_status': 'vacant',
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    assert back.status_code == 200, back.content
    log.refresh_from_db()
    room.refresh_from_db()
    assert log.status == 'resolved'
    assert room.housekeeping_status == 'clean'
    assert _disp_status(staff_client, room) == 'occupied'

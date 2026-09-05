"""Concurrency proof for RoomService.allocate_room's select_for_update() guard.

Deselected from the default run (pytest.ini: addopts = -m "not mssql") because
it needs a real SQL Server instance. sqlite accepts select_for_update()
syntactically but never blocks a second transaction on it, so the guard cannot
be proven there. mssql-django compiles it to WITH (ROWLOCK, UPDLOCK), which
does block. Run explicitly:

    pytest -m mssql home/test_concurrency.py -v

Targets a disposable database (hotel_concurrency_test) — not the dev database
(hotelbooking), not the suite's sqlite default. The fixture rewrites the
'default' entry of the global DATABASES setting for the lifetime of this test
and restores it in a finally, so the rest of the suite is untouched. Closing
the sqlite connection does not lose its data: Django short-circuits close()
for in-memory databases.

The only manual step is creating the empty database:

    sqlcmd -S <host>\\MSSQLSERVER01 -E -Q "CREATE DATABASE hotel_concurrency_test"

The tables are then built from the Django models on first run, not from the
schema file, so this database only ever contains the handful of tables these
tests touch. Individual triggers are pulled out of the schema file where a test
needs one, by _install_trigger below.

Only missing tables are created, never altered, so after changing a model drop
the database and let the next run rebuild it:

    sqlcmd -S <host>\\MSSQLSERVER01 -E -Q "DROP DATABASE hotel_concurrency_test"
"""
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.db import connections
from django.db.utils import ConnectionHandler
from django.utils import timezone

pytestmark = pytest.mark.mssql

# Run through a throwaway ConnectionHandler so Django's own configure_settings
# fills in the defaults (OPTIONS, CONN_MAX_AGE, TEST, ...) instead of us
# hand-listing every key the connection wrapper expects.
REAL_MSSQL_SETTINGS = ConnectionHandler({
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'hotel_concurrency_test',
        'HOST': os.getenv('DB_HOST', 'DESKTOP-NS6H7CH\\MSSQLSERVER01'),
        'Trusted_Connection': 'yes',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'trust_server_certificate': 'yes',
        },
    }
}).databases['default']


def _evict():
    """Drop the cached connection wrapper so the next access rebuilds it from
    connections.databases. Swapping the settings dict alone is not enough --
    the wrapper caches its settings_dict at construction time."""
    try:
        del connections['default']
    except AttributeError:
        pass


def _ensure_schema():
    """Create any missing tables from the models. conftest.pytest_configure has
    already flipped managed = True, so the schema editor can build them."""
    from data.models import (
        AuditLog, CustomerBookingInfo, Hotel, Room, RoomAssignment, RoomPrice, User,
    )
    from django.db import connection

    # Creation order: referenced tables before the tables that point at them.
    order = [Hotel, User, RoomPrice, CustomerBookingInfo, Room, RoomAssignment, AuditLog]
    existing = set(connection.introspection.table_names())
    missing = [m for m in order if m._meta.db_table not in existing]
    if missing:
        with connection.schema_editor() as editor:
            for model in missing:
                editor.create_model(model)


SCHEMA_SQL = Path(__file__).resolve().parents[2] / 'tables v10 for hotel.sql'


def _install_trigger(name):
    """Recreate one trigger from the checked-in schema, so the assertions below
    are made against the definition in the schema file rather than against a
    copy that can drift from it. Pulled out by regex the same way
    test_booking_status.py pulls out the CHECK constraint.

    Dropped and recreated every run: the point is to test the current file.
    """
    from django.db import connection

    body = re.search(
        r'(CREATE TRIGGER\s+%s\b.*?)\n\s*GO\b' % re.escape(name),
        SCHEMA_SQL.read_text(encoding='utf-8'),
        re.S | re.IGNORECASE,
    )
    assert body, f'{name} not found in {SCHEMA_SQL.name}'

    with connection.cursor() as cursor:
        cursor.execute(f'DROP TRIGGER IF EXISTS {name};')
        cursor.execute(body.group(1))


@pytest.fixture
def mssql_default(django_db_blocker):
    """Repoint the default alias at the real SQL Server scratch database.

    django_db_blocker.unblock() is needed because this test deliberately does
    not use pytest-django's `db` fixture: this database is managed here, not
    built by Django's usual test-database machinery.
    """
    saved = connections.databases['default']
    connections['default'].close()
    _evict()
    connections.databases['default'] = REAL_MSSQL_SETTINGS
    with django_db_blocker.unblock():
        try:
            _ensure_schema()
            yield
        finally:
            for conn in connections.all():
                conn.close()
            _evict()
            connections.databases['default'] = saved


@pytest.fixture
def race_setup(mssql_default):
    """One deluxe room, two pending bookings over the same dates.

    Mirrors the real race: two guests both pass the availability check for the
    last room of a type before either has actually been assigned one.
    """
    from data.models import CustomerBookingInfo, Hotel, Room, RoomAssignment

    now = timezone.now()
    # room_code is unique; clear any row a hard-killed previous run left behind
    # so setup fails with nothing rather than a confusing constraint violation.
    Room.objects.filter(room_code='RACE-1').delete()

    hotel = Hotel.objects.create(hotel_name='Concurrency Test Hotel')
    room = Room.objects.create(
        hotel=hotel, room_code='RACE-1', floor_number=1, room_number=1,
        room_type='deluxe',
    )
    common = dict(
        hotel=hotel, room_type='deluxe', booking_date=now,
        check_in=date(2027, 6, 1), check_out=date(2027, 6, 3),
        booked_rate=500000, total_price=1000000,
        status='pending', payment_status='unpaid', amount_paid=0,
        created_at=now, updated_at=now,
    )
    booking_a = CustomerBookingInfo.objects.create(guest_name='Guest A', **common)
    booking_b = CustomerBookingInfo.objects.create(guest_name='Guest B', **common)

    try:
        yield room, booking_a, booking_b
    finally:
        RoomAssignment.objects.filter(room=room).delete()
        CustomerBookingInfo.objects.filter(pk__in=[booking_a.pk, booking_b.pk]).delete()
        Room.objects.filter(pk=room.pk).delete()
        Hotel.objects.filter(pk=hotel.pk).delete()


@pytest.fixture
def audit_actor(mssql_default):
    """A user_id to hang audit rows off: the FK on audit_log is NOT NULL.

    Raw SQL rather than the ORM. Deleting a User through the ORM makes the
    cascade collector walk every FK pointing at the user model, including
    django.contrib.admin's django_admin_log, which this scratch database does
    not have because it is built from data/ models only.
    """
    from django.db import connection

    def _cleanup(cursor):
        cursor.execute(
            'DELETE FROM audit_log WHERE user_id IN '
            "(SELECT user_id FROM users WHERE username = 'audit-probe')"
        )
        cursor.execute("DELETE FROM users WHERE username = 'audit-probe'")

    with connection.cursor() as cursor:
        _cleanup(cursor)  # in case a hard-killed run left one behind
        cursor.execute(
            'INSERT INTO users '
            '(username, email, password_hash, role, is_active, is_verified, created_at) '
            "VALUES ('audit-probe', 'audit-probe@example.com', 'unusable', 'admin', 1, 1, GETDATE())"
        )
        cursor.execute("SELECT user_id FROM users WHERE username = 'audit-probe'")
        user_id = cursor.fetchone()[0]

    try:
        yield user_id
    finally:
        with connection.cursor() as cursor:
            _cleanup(cursor)


def test_audit_log_is_append_only(audit_actor):
    """Audit rows can be written and then never altered or erased.

    home/audit.py only ever calls AuditLog.objects.create(), so nothing in the
    app needs UPDATE or DELETE here. Enforcing that at the database means a
    compromised staff session cannot quietly edit its own trail afterwards.

    Insert is asserted too, not just the two denials: a trigger that refused
    everything would satisfy the denial half while breaking every audit write
    in the app.
    """
    from data.models import AuditLog
    from django.db import connection

    _install_trigger('trg_audit_log_append_only')
    try:
        row = AuditLog.objects.create(
            user_id=audit_actor, action_type='LOGIN', table_name='users',
            record_id=audit_actor, ip_address='127.0.0.1',
        )
        assert row.pk, 'INSERT is the one operation that has to keep working'

        with connection.cursor() as cursor:
            with pytest.raises(Exception, match='append-only'):
                cursor.execute(
                    'UPDATE audit_log SET action_type = %s WHERE log_id = %s',
                    ['CREATE', row.pk],
                )
            with pytest.raises(Exception, match='append-only'):
                cursor.execute('DELETE FROM audit_log WHERE log_id = %s', [row.pk])

        # Still there, and still saying what it said when it was written.
        row.refresh_from_db()
        assert row.action_type == 'LOGIN'
    finally:
        # Before the fixture teardown, which has to delete the row this test
        # just made undeletable.
        with connection.cursor() as cursor:
            cursor.execute('DROP TRIGGER IF EXISTS trg_audit_log_append_only;')


def test_booking_writes_are_denied_without_a_session_context(race_setup):
    """trg_booking_ownership must deny by default and allow with an identity.

    This is the control that was failing open for months: the original trigger
    compared SESSION_CONTEXT inline, and NULL <> 'admin' is UNKNOWN rather than
    TRUE in T-SQL, so it never fired. The replacement fails closed, which means
    the failure mode of a regression flipped from "customers can edit other
    people's bookings" to "nobody can edit any booking". Both halves are
    asserted here so neither direction can rot unnoticed.

    SqlSessionContextMiddleware is what supplies the identity in the running
    app. It writes the same two keys this test writes by hand.
    """
    from django.db import connection

    _, booking_a, _ = race_setup
    _install_trigger('trg_booking_ownership')
    try:
        with connection.cursor() as cursor:
            cursor.execute("EXEC sp_set_session_context @key=N'user_role', @value=%s", [None])

            with pytest.raises(Exception, match='session context'):
                cursor.execute(
                    'UPDATE booking_info SET status = %s WHERE booking_id = %s',
                    ['confirmed', booking_a.pk],
                )

            # And the other half: a stamped identity gets through.
            cursor.execute("EXEC sp_set_session_context @key=N'user_role', @value=%s", ['admin'])
            cursor.execute(
                'UPDATE booking_info SET status = %s WHERE booking_id = %s',
                ['confirmed', booking_a.pk],
            )
            cursor.execute('SELECT status FROM booking_info WHERE booking_id = %s', [booking_a.pk])
            assert cursor.fetchone()[0] == 'confirmed'
    finally:
        with connection.cursor() as cursor:
            cursor.execute('DROP TRIGGER IF EXISTS trg_booking_ownership;')
            cursor.execute("EXEC sp_set_session_context @key=N'user_role', @value=%s", [None])


@pytest.fixture
def milestone_setup(mssql_default):
    """A guest two bookings deep, so the next one is their third: the milestone.

    Two physical rooms, because both concurrent bookings have to be able to
    allocate. If one failed on availability instead of on eligibility, the test
    would pass for the wrong reason.
    """
    from data.models import CustomerBookingInfo, Hotel, Room, RoomAssignment, RoomPrice, User

    from django.db import connection

    now = timezone.now()
    # Clear anything a hard-killed previous run left behind, so setup fails
    # with nothing rather than a confusing unique-constraint violation. Raw SQL
    # for the user, for the cascade-collector reason spelled out in teardown
    # below.
    RoomAssignment.objects.filter(room__room_code__in=['MILE-1', 'MILE-2']).delete()
    Room.objects.filter(room_code__in=['MILE-1', 'MILE-2']).delete()
    with connection.cursor() as cursor:
        cursor.execute(
            'DELETE FROM booking_info WHERE user_id IN '
            "(SELECT user_id FROM users WHERE username = 'milestone-probe')"
        )
        cursor.execute(
            'DELETE FROM audit_log WHERE user_id IN '
            "(SELECT user_id FROM users WHERE username = 'milestone-probe')"
        )
        cursor.execute("DELETE FROM users WHERE username = 'milestone-probe'")

    hotel = Hotel.objects.create(hotel_name='Milestone Test Hotel')
    RoomPrice.objects.create(hotel=hotel, room_type='deluxe', price_per_night=500000)
    rooms = [
        Room.objects.create(
            hotel=hotel, room_code=code, floor_number=9, room_number=number,
            room_type='deluxe',
        )
        for code, number in (('MILE-1', 91), ('MILE-2', 92))
    ]
    guest = User.objects.create(
        username='milestone-probe', email='milestone-probe@example.com',
        password_hash='unusable', role='customer', is_active=True,
        is_verified=True, created_at=now,
    )
    prior = dict(
        hotel=hotel, user=guest, guest_name='Milestone Probe', room_type='deluxe',
        booking_date=now, check_in=date(2027, 9, 1), check_out=date(2027, 9, 3),
        booked_rate=500000, total_price=1000000, status='pending',
        payment_status='unpaid', amount_paid=0, created_at=now, updated_at=now,
    )
    CustomerBookingInfo.objects.create(**prior)
    CustomerBookingInfo.objects.create(**prior)

    try:
        yield guest
    finally:
        from django.db import connection

        RoomAssignment.objects.filter(room__in=rooms).delete()
        CustomerBookingInfo.objects.filter(user=guest).delete()
        Room.objects.filter(pk__in=[r.pk for r in rooms]).delete()
        RoomPrice.objects.filter(hotel=hotel).delete()
        # Raw SQL for the audit rows and the user, for the reason audit_actor
        # spells out: deleting a User through the ORM sends the cascade
        # collector through every FK pointing at the user model, including
        # django.contrib.admin's django_admin_log, which this database does not
        # have. The view writes audit rows, and audit_log's FK is NOT NULL, so
        # they have to go first either way.
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM audit_log WHERE user_id = %s', [guest.pk])
            cursor.execute('DELETE FROM users WHERE user_id = %s', [guest.pk])
        Hotel.objects.filter(pk=hotel.pk).delete()


def test_concurrent_bookings_cannot_both_claim_one_milestone(milestone_setup):
    """Two bookings racing across the same milestone must not both take 10%.

    The count that grants the discount was an ordinary read. Both requests saw
    two prior bookings, both computed booking number three, and both qualified.
    The fix locks the guest's own user row and keeps the count in the same
    transaction as the booking it gates, so the second request counts three and
    pays full price.

    Drives the real view through RequestFactory rather than the test client:
    this scratch database is built from data/ models only, so it has no
    django_session table for force_login to write to. request.user is set
    directly, which is all the view reads.

    The confirmation email is patched out because email_queue is not one of the
    tables this database has.
    """
    import json
    from unittest.mock import patch

    from django.test import RequestFactory

    from data.models import CustomerBookingInfo
    from home.views import get_reservation

    guest = milestone_setup
    check_in = date.today() + timedelta(days=30)
    barrier = threading.Barrier(2)

    def book():
        request = RequestFactory().post('/reservation/', {
            'name': 'Milestone Probe',
            'email': 'milestone-probe@example.com',
            'phone': '123',
            'checkin_date': check_in.strftime('%m/%d/%Y'),
            'checkout_date': (check_in + timedelta(days=2)).strftime('%m/%d/%Y'),
            'adults': '1', 'children': '0', 'room_type': 'deluxe',
            'milestone_decision': 'redeem',
        })
        request.user = guest
        try:
            barrier.wait(timeout=10)  # both threads enter the locked block together
            return get_reservation(request)
        finally:
            connections['default'].close()

    with patch('backend.services.services.EmailService.queue_booking_confirmation'):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(book), pool.submit(book)]
            responses = [f.result(timeout=30) for f in futures]

    payloads = [json.loads(r.content) for r in responses]
    assert all(r.status_code == 200 for r in responses), (
        f'a booking failed for some other reason: {payloads!r}'
    )

    # 500000 a night for two nights. The milestone booking pays 900000.
    discounted = CustomerBookingInfo.objects.filter(
        user=guest, check_in=check_in, total_price=900000
    ).count()
    assert discounted == 1, (
        f'expected exactly one milestone discount, got {discounted}: {payloads!r}'
    )


def test_concurrent_allocation_prevents_double_booking(race_setup):
    room, booking_a, booking_b = race_setup
    from backend.services.services import RoomService
    from data.models import RoomAssignment

    barrier = threading.Barrier(2)

    def attempt(booking):
        try:
            barrier.wait(timeout=10)  # both threads enter allocate_room together
            return RoomService.allocate_room(booking)
        except BaseException as exc:  # noqa: BLE001 - returned, asserted on below
            return exc
        finally:
            connections['default'].close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        # Both submitted before either result is awaited, so the threads really
        # do run concurrently and meet at the barrier.
        futures = [pool.submit(attempt, booking_a), pool.submit(attempt, booking_b)]
        outcomes = [f.result(timeout=30) for f in futures]
    successes = [o for o in outcomes if not isinstance(o, BaseException)]
    rejections = [o for o in outcomes if isinstance(o, ValidationError)]
    unexpected = [
        o for o in outcomes
        if isinstance(o, BaseException) and not isinstance(o, ValidationError)
    ]

    assert not unexpected, f'unexpected error(s) instead of a clean rejection: {unexpected!r}'
    assert len(successes) == 1, f'expected exactly one winner, got {len(successes)}: {outcomes!r}'
    assert len(rejections) == 1, f'expected exactly one rejection, got {len(rejections)}: {outcomes!r}'

    active = RoomAssignment.objects.filter(room=room, status='active').count()
    assert active == 1, f'room ended up with {active} active assignments, expected exactly 1'

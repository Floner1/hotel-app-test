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

The tables are then built from the Django models on first run. They are built
from the models rather than from site1/schema.sql because schema.sql is stale:
it still declares the pre-44f0447 single `current_status` column on rooms,
where the models and the live database use split reservation_status /
housekeeping_status columns.

Only missing tables are created, never altered, so after changing a model drop
the database and let the next run rebuild it:

    sqlcmd -S <host>\\MSSQLSERVER01 -E -Q "DROP DATABASE hotel_concurrency_test"
"""
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
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
        CustomerBookingInfo, Hotel, Room, RoomAssignment, RoomPrice, User,
    )
    from django.db import connection

    # Creation order: referenced tables before the tables that point at them.
    order = [Hotel, User, RoomPrice, CustomerBookingInfo, Room, RoomAssignment]
    existing = set(connection.introspection.table_names())
    missing = [m for m in order if m._meta.db_table not in existing]
    if missing:
        with connection.schema_editor() as editor:
            for model in missing:
                editor.create_model(model)


SCHEMA_SQL = Path(__file__).resolve().parent.parent / 'schema.sql'


def _install_trigger(name):
    """Recreate one trigger from the checked-in schema, so the assertions below
    are made against the definition in site1/schema.sql rather than against a
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
    assert body, f'{name} not found in schema.sql'

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

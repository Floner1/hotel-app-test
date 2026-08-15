from django.db import migrations


class Migration(migrations.Migration):
    """
    Covering indexes for the booking, room-assignment and audit read paths.

    ix_ra_room_status_dates is the one that matters: RoomRepository.
    get_available_rooms_by_type runs an EXISTS subquery on
    (room_id, status, check_in, check_out) on every availability check.

    The tables are managed = False, so this is RunSQL rather than AddIndex.
    Reverse uses DROP INDEX IF EXISTS so a partial forward run still unwinds.
    """

    dependencies = [
        ('data', '0006_user_is_verified'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE INDEX ix_booking_check_in     ON booking_info (check_in) INCLUDE (check_out, status);",
                "CREATE INDEX ix_booking_check_out    ON booking_info (check_out);",
                "CREATE INDEX ix_booking_status       ON booking_info (status) INCLUDE (check_in, check_out);",
                "CREATE INDEX ix_booking_user         ON booking_info (user_id) INCLUDE (status, check_in);",
                "CREATE INDEX ix_booking_email        ON booking_info (email);",
                "CREATE INDEX ix_booking_date         ON booking_info (booking_date DESC);",
                "CREATE INDEX ix_ra_room_status_dates ON room_assignments (room_id, status, check_in, check_out);",
                "CREATE INDEX ix_ra_booking_status    ON room_assignments (booking_id, status);",
                "CREATE INDEX ix_rooms_type_status    ON rooms (room_type, reservation_status);",
                "CREATE INDEX ix_rooms_floor          ON rooms (floor_number, room_number);",
                "CREATE INDEX ix_audit_timestamp      ON audit_log (timestamp DESC);",
                "CREATE INDEX ix_audit_user_action    ON audit_log (user_id, action_type);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS ix_audit_user_action ON audit_log;",
                "DROP INDEX IF EXISTS ix_audit_timestamp ON audit_log;",
                "DROP INDEX IF EXISTS ix_rooms_floor ON rooms;",
                "DROP INDEX IF EXISTS ix_rooms_type_status ON rooms;",
                "DROP INDEX IF EXISTS ix_ra_booking_status ON room_assignments;",
                "DROP INDEX IF EXISTS ix_ra_room_status_dates ON room_assignments;",
                "DROP INDEX IF EXISTS ix_booking_date ON booking_info;",
                "DROP INDEX IF EXISTS ix_booking_email ON booking_info;",
                "DROP INDEX IF EXISTS ix_booking_user ON booking_info;",
                "DROP INDEX IF EXISTS ix_booking_status ON booking_info;",
                "DROP INDEX IF EXISTS ix_booking_check_out ON booking_info;",
                "DROP INDEX IF EXISTS ix_booking_check_in ON booking_info;",
            ],
        ),
    ]

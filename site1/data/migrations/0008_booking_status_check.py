from django.db import migrations

# The original constraint was declared inline in the CREATE TABLE, so SQL Server
# gave it a server-generated name (CK__booking_i__statu__30D918B3 on one box,
# something else on the next). Look it up by column instead of by name, and
# build the DROP as text because DROP CONSTRAINT takes an identifier, not a
# variable. sp_executesql needs a variable, not an expression, hence @drop_sql.
DROP_STATUS_CHECK = """
DECLARE @name NVARCHAR(128);
SELECT @name = cc.name
FROM sys.check_constraints cc
JOIN sys.columns col
    ON col.object_id = cc.parent_object_id
   AND col.column_id = cc.parent_column_id
WHERE cc.parent_object_id = OBJECT_ID('booking_info')
  AND col.name = 'status';

IF @name IS NOT NULL
BEGIN
    DECLARE @drop_sql NVARCHAR(MAX) =
        N'ALTER TABLE booking_info DROP CONSTRAINT ' + QUOTENAME(@name) + N';';
    EXEC sp_executesql @drop_sql;
END
"""


class Migration(migrations.Migration):
    """
    Widen the CHECK constraint on booking_info.status to the seven values
    home.views.BOOKING_STATUSES already accepts.

    The table only allowed pending/confirmed/cancelled/completed, so an admin
    moving a booking to checked_in, checked_out or rejected hit SQL error 547
    even though the app had already validated the value.

    Re-created as a named constraint (chk_booking_status) so this is repeatable
    and so the reverse can find it. booking_info is managed = False, hence
    RunSQL rather than AddConstraint.

    Reverse narrows the constraint back to the original four values and will
    fail, correctly, if any row has since been moved to one of the new three.
    """

    dependencies = [
        ('data', '0007_add_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                DROP_STATUS_CHECK,
                "ALTER TABLE booking_info ADD CONSTRAINT chk_booking_status "
                "CHECK (status IN ('pending','confirmed','checked_in','checked_out',"
                "'cancelled','completed','rejected'));",
            ],
            reverse_sql=[
                DROP_STATUS_CHECK,
                "ALTER TABLE booking_info ADD CONSTRAINT chk_booking_status "
                "CHECK (status IN ('pending','confirmed','cancelled','completed'));",
            ],
        ),
    ]

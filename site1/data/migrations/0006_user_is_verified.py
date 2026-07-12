from django.db import migrations


class Migration(migrations.Migration):
    """
    Add the `is_verified` column to the (managed=False) users table for email
    verification on self-service signup.

    DEFAULT 1 so every EXISTING account and every admin-provisioned account stays
    verified/able to log in. Only public register_view creates rows with
    is_verified = 0. Named default constraint so the reverse can drop it cleanly
    (SQL Server refuses DROP COLUMN while a default constraint is bound).
    """

    dependencies = [
        ('data', '0005_room_roomassignment'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "IF COL_LENGTH('users', 'is_verified') IS NULL "
                "ALTER TABLE users ADD is_verified BIT NOT NULL "
                "CONSTRAINT DF_users_is_verified DEFAULT 1;"
            ),
            reverse_sql=[
                "ALTER TABLE users DROP CONSTRAINT DF_users_is_verified;",
                "ALTER TABLE users DROP COLUMN is_verified;",
            ],
        ),
    ]

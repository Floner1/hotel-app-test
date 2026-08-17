import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0008_booking_status_check'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomMaintenanceLog',
            fields=[
                ('log_id', models.AutoField(primary_key=True, serialize=False)),
                ('issue_description', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved')], default='open', max_length=50)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(blank=True, null=True)),
                ('reported_by', models.ForeignKey(blank=True, db_column='reported_by', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='data.user')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='maintenance_logs', to='data.room')),
            ],
            options={
                'db_table': 'room_maintenance_logs',
                'ordering': ['-created_at'],
                'managed': False,
            },
        ),
    ]

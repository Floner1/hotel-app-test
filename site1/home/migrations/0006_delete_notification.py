from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_notification_delete_hotel'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Notification',
        ),
    ]

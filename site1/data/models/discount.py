from django.db import models


class DiscountCode(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('redeemed', 'Redeemed'),
        ('expired', 'Expired'),
        ('void', 'Void'),
    ]

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    subscriber = models.ForeignKey(
        'EmailSubscriber', models.DO_NOTHING,
        null=True, blank=True, db_column='subscriber_id',
    )
    discount_percent = models.IntegerField(default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    issued_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    redeemed_booking = models.ForeignKey(
        'CustomerBookingInfo', models.DO_NOTHING,
        null=True, blank=True, db_column='redeemed_booking_id',
    )
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'discount_codes'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.email}) [{self.status}]"

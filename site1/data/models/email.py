"""Email infrastructure models — mapped to the SQL Server email_* tables.

All three models are `managed = False`: the schema is owned by
`tables v6 for hotel.sql`, not by Django migrations.
"""
from django.db import models


class EmailSubscriber(models.Model):
    """Opt-in marketing list. Unique unsubscribe_token gates the unsubscribe flow."""

    STATUS_CHOICES = [
        ('subscribed', 'Subscribed'),
        ('unsubscribed', 'Unsubscribed'),
        ('bounced', 'Bounced'),
    ]

    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=225, null=True, blank=True)
    user = models.ForeignKey(
        'User', models.DO_NOTHING, null=True, blank=True, db_column='user_id'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='subscribed')
    source = models.CharField(max_length=100, null=True, blank=True)
    subscribed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'email_subscribers'
        managed = False
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.email} ({self.get_status_display()})"


class EmailCampaign(models.Model):
    """Newsletter / marketing campaign. Drafted then sent against active subscribers."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=225)
    subject = models.CharField(max_length=500)
    body_html = models.TextField()
    body_text = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        'User', models.DO_NOTHING, null=True, blank=True, db_column='created_by'
    )
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'email_campaigns'
        managed = False
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class EmailQueue(models.Model):
    """Per-send log. One row per send attempt; status is terminal (sent | failed)."""

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    EMAIL_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_cancellation', 'Booking Cancellation'),
        ('contact_receipt', 'Contact Form Receipt'),
        ('admin_notification', 'Admin Notification'),
        ('campaign', 'Marketing Campaign'),
        ('other', 'Other'),
    ]

    id = models.AutoField(primary_key=True)
    to_email = models.EmailField(max_length=255)
    to_name = models.CharField(max_length=225, null=True, blank=True)
    subject = models.CharField(max_length=500)
    template_name = models.CharField(max_length=100, null=True, blank=True)
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    attempts = models.IntegerField(default=1)
    error_message = models.TextField(null=True, blank=True)
    provider_msg_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        'User', models.DO_NOTHING, null=True, blank=True, db_column='user_id'
    )
    related_type = models.CharField(max_length=50, null=True, blank=True)
    related_id = models.IntegerField(null=True, blank=True)
    campaign = models.ForeignKey(
        'EmailCampaign', models.DO_NOTHING,
        null=True, blank=True, db_column='campaign_id',
    )

    class Meta:
        db_table = 'email_queue'
        managed = False
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"#{self.id} {self.email_type} -> {self.to_email} [{self.status}]"

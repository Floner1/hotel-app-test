from django.db import models
from django.utils import timezone

# Models are defined in data/models/hotel.py
# This file is kept for Django app structure but models are centralized in the data app

class Notification(models.Model):
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    booking_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message

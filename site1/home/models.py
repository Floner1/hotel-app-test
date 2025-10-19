from django.db import models

class Hotel(models.Model):
    hotel_id = models.IntegerField(primary_key=True)
    hotel_name = models.CharField(max_length=255)
    star_rating = models.IntegerField(null=True, blank=True)
    hotel_address = models.CharField(max_length=255, null=True, blank=True)
    hotel_email_address = models.CharField(max_length=30, null=True, blank=True)
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'hotel'
        managed = False  # This table already exists in SQL Server
# Import Django's model system for database interaction
from django.db import models

# Define the Hotel model that represents the hotel database table
class Hotel(models.Model):
    # Primary key field for unique hotel identification
    hotel_id = models.AutoField(primary_key=True)
    
    # Hotel name field with maximum length of 255 characters
    hotel_name = models.CharField(max_length=255)
    
    # Integer field to store hotel's star rating
    star_rating = models.IntegerField()
    
    # Hotel address field with maximum length of 255 characters
    hotel_address = models.CharField(max_length=255)
    
    # Date field to store when the hotel was established
    established_date = models.DateField()
    
    # Contact information fields
    phone = models.CharField(max_length=50)
    email = models.CharField(max_length=100)

    class Meta:
        # Specify the actual table name in the database
        db_table = 'hotel'
        # Indicate that Django shouldn't manage this table's schema
        managed = False  # This table already exists in SQL Server


# Define the CustomerBookingInfo model for storing guest booking information
class CustomerBookingInfo(models.Model):
    # Primary key field for unique booking identification
    booking_id = models.AutoField(primary_key=True)
    
    # Guest Information
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    
    # Reservation Details
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    
    # Guest Count
    adults = models.IntegerField(default=1)
    children = models.IntegerField(default=0)
    
    # Special Notes (optional field)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Specify the actual table name in the database
        db_table = 'customer_booking_info'
        # Table already exists in SQL Server, don't let Django manage it
        managed = False
        # Order bookings by most recent first
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking #{self.booking_id} - {self.name}"

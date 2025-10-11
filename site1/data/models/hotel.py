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


# Define the Reservation model for storing guest booking information
class Reservation(models.Model):
    # Primary key field for unique reservation identification
    reservation_id = models.AutoField(primary_key=True)
    
    # Guest Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=50)
    
    # Reservation Details
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    
    # Guest Count
    adults = models.IntegerField(default=1)
    children = models.IntegerField(default=0)
    
    # Room Information
    room_type = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Single", "Family", "Presidential"
    
    # Special Requests (optional field)
    special_requests = models.TextField(blank=True, null=True)
    
    # Reservation Status
    status = models.CharField(
        max_length=50, 
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
            ('completed', 'Completed')
        ]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Specify the actual table name in the database
        db_table = 'reservation'
        # Django will manage this table (create/modify schema)
        managed = True
        # Order reservations by most recent first
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reservation #{self.reservation_id} - {self.first_name} {self.last_name}"

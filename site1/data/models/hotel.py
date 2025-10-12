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
    """Model mapped to SQL Server's customer_booking_info table."""

    # Primary key field for unique booking identification
    booking_id = models.AutoField(db_column='customer_id', primary_key=True)

    # Guest Information
    name = models.CharField(db_column='customer_name', max_length=255)
    phone = models.CharField(db_column='customer_phone_number', max_length=20)
    email = models.EmailField(db_column='customer_email', max_length=255, unique=True)

    # Room type selected by the guest
    room_type = models.CharField(db_column='customer_room_type', max_length=255)

    # Reservation Details
    booking_date = models.DateField(db_column='booking_date')
    checkin_date = models.DateField(db_column='checkin_date')
    checkout_date = models.DateField(db_column='checkout_date')

    # Newly added columns
    total_days = models.IntegerField(db_column='total_days')
    total_cost_amount = models.IntegerField(db_column='total_cost_amount')

    # Guest Count
    adults = models.IntegerField(db_column='number_of_adults')
    children = models.IntegerField(db_column='number_of_children')

    # Optional link back to the hotel record
    hotel = models.ForeignKey(
        'Hotel',
        models.DO_NOTHING,
        db_column='hotel_id',
    )

    class Meta:
        # Specify the actual table name in the database
        db_table = 'customer_booking_info'
        # Table already exists in SQL Server, don't let Django manage it
        managed = False
        # Order bookings by most recent first (booking_date approximates created timestamp)
        ordering = ['-booking_date', '-checkin_date']

    def __str__(self):
        return f"Booking #{self.booking_id} - {self.name}"

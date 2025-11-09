# Import Django's model system for database interaction
from django.db import models


class Hotel(models.Model):
    """Model mapped to the SQL Server `hotel_info` table."""

    hotel_id = models.AutoField(primary_key=True)
    hotel_name = models.CharField(max_length=225, null=True, blank=True)
    address = models.CharField(max_length=225, null=True, blank=True)
    star_rating = models.IntegerField(null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)
    email = models.CharField(max_length=225, null=True, blank=True)
    phone = models.CharField(max_length=225, null=True, blank=True)

    class Meta:
        db_table = 'hotel_info'
        managed = False

    def __str__(self) -> str:
        return self.hotel_name or 'Unnamed Hotel'


class CustomerBookingInfo(models.Model):
    """Model mapped to SQL Server's booking_info table."""

    booking_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING)
    
    # Guest Information
    guest_name = models.CharField(max_length=225)
    email = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    
    # Booking Details
    room_type = models.CharField(max_length=100)
    
    # Dates
    booking_date = models.DateTimeField()
    check_in = models.DateField()
    check_out = models.DateField()
    
    # Guest Count
    adults = models.IntegerField(default=1)
    children = models.IntegerField(null=True, blank=True, default=0)
    
    # Pricing
    booked_rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status Tracking
    status = models.CharField(max_length=50, default='confirmed')
    payment_status = models.CharField(max_length=50, default='unpaid')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional Information
    special_requests = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Audit Fields
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'booking_info'
        managed = False
        ordering = ['-booking_date']

    def __str__(self) -> str:
        return f"Booking #{self.booking_id} - {self.guest_name}"


class RoomPrice(models.Model):
    """Room pricing information."""

    room_price_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    room_type = models.CharField(max_length=225, null=True, blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    room_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'room_price'
        managed = False

    def __str__(self) -> str:
        return f"RoomPrice #{self.room_price_id} - {self.room_type}"


class HotelServices(models.Model):
    """Model mapped to the SQL Server `hotel_services` table."""

    service_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    name_of_service = models.CharField(max_length=225, null=True, blank=True, db_column='service_name')
    service_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'hotel_services'
        managed = False

    def __str__(self) -> str:
        return f"{self.name_of_service}"


class HotelKeysMain(models.Model):
    """Model mapped to the SQL Server `hotel_keys_main` table."""

    key_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    room_key = models.CharField(max_length=225, null=True, blank=True)

    class Meta:
        db_table = 'hotel_keys_main'
        managed = False

    def __str__(self) -> str:
        return f"Key #{self.key_id} - {self.room_key}"


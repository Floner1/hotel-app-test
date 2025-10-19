# Import Django's model system for database interaction
from django.db import models


class Hotel(models.Model):
    """Model mapped to the SQL Server `hotel` table."""

    hotel_id = models.IntegerField(primary_key=True)
    hotel_name = models.CharField(max_length=255)
    star_rating = models.IntegerField(null=True, blank=True)
    hotel_address = models.CharField(max_length=255, null=True, blank=True)
    hotel_email_address = models.CharField(max_length=30, null=True, blank=True)
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'hotel'
        managed = False

    def __str__(self) -> str:
        return self.hotel_name


class CustomerBookingInfo(models.Model):
    """Model mapped to SQL Server's customer_booking_info table."""

    booking_id = models.AutoField(db_column='customer_id', primary_key=True)
    name = models.CharField(db_column='customer_name', max_length=255)
    phone = models.CharField(db_column='customer_phone_number', max_length=20)
    email = models.EmailField(db_column='customer_email', max_length=255, unique=True)
    room_type = models.CharField(db_column='customer_room_type', max_length=255)
    booking_date = models.DateField(db_column='booking_date')
    checkin_date = models.DateField(db_column='checkin_date')
    checkout_date = models.DateField(db_column='checkout_date')
    total_days = models.IntegerField(db_column='total_days')
    total_cost_amount = models.DecimalField(db_column='total_cost_amount', max_digits=10, decimal_places=2)
    adults = models.IntegerField(db_column='number_of_adults')
    children = models.IntegerField(db_column='number_of_children')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')

    class Meta:
        db_table = 'customer_booking_info'
        managed = False
        ordering = ['-booking_date', '-checkin_date']

    def __str__(self) -> str:
        return f"Booking #{self.booking_id} - {self.name}"


class RoomPrice(models.Model):
    """Snapshot of nightly pricing for each room type in a hotel."""

    room_price_id = models.IntegerField(primary_key=True, db_column='room_price_id')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id', null=True, blank=True)
    bed_1_balcony_room = models.DecimalField(
        db_column='1_bed_balcony_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_1_window_room = models.DecimalField(
        db_column='1_bed_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_2_no_window_room = models.DecimalField(
        db_column='2_bed_no_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_1_no_window_room = models.DecimalField(
        db_column='1_bed_no_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_2_condotel_balcony = models.DecimalField(
        db_column='2_bed_condotel_balcony', max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = 'room_price'
        managed = False

    def __str__(self) -> str:
        return f"RoomPrice #{self.room_price_id}"


class RoomInfo(models.Model):
    """Detailed information about each room including nightly price."""

    room_number = models.IntegerField(primary_key=True, db_column='room_number')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='room_hotel', null=True, blank=True)
    room_type = models.CharField(db_column='room_type', max_length=255, null=True, blank=True)
    room_size_sqm = models.IntegerField(db_column='room_size_sqm', null=True, blank=True)
    max_guests = models.IntegerField(db_column='max_guests', null=True, blank=True)
    bed_type = models.CharField(db_column='bed_type', max_length=100, null=True, blank=True)
    bed_count = models.IntegerField(db_column='bed_count', null=True, blank=True)
    has_balcony = models.BooleanField(db_column='has_balcony', null=True, blank=True)
    has_kitchenette = models.BooleanField(db_column='has_kitchenette', null=True, blank=True)
    has_bathtub = models.BooleanField(db_column='has_bathtub', null=True, blank=True)
    has_window = models.BooleanField(db_column='has_window', null=True, blank=True)
    room_description = models.CharField(db_column='room_description', max_length=255, null=True, blank=True)
    room_notes = models.CharField(db_column='room_notes', max_length=255, null=True, blank=True)
    price_per_night = models.DecimalField(
        db_column='price_per_night', max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_available = models.BooleanField(db_column='is_available', null=True, blank=True)

    class Meta:
        db_table = 'room_info'
        managed = False

    def __str__(self) -> str:
        return f"Room {self.room_number} ({self.room_type})"

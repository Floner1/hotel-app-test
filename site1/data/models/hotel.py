# Import Django's model system for database interaction
from django.db import models


class Hotel(models.Model):
    """Model mapped to the SQL Server `hotel_info` table."""

    hotel_id = models.IntegerField(primary_key=True, db_column='hotel_info_id')
    hotel_name = models.CharField(max_length=255, null=True, blank=True)
    star_rating = models.IntegerField(null=True, blank=True)
    hotel_address = models.CharField(max_length=255, null=True, blank=True)
    hotel_email_address = models.CharField(db_column='hotel_email_address', max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'hotel_info'
        managed = False

    def __str__(self) -> str:
        return self.hotel_name or 'Unnamed Hotel'


class CustomerBookingInfo(models.Model):
    """Model mapped to SQL Server's booking_info table."""

    booking_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')
    name = models.CharField(db_column='customer_name', max_length=255)
    phone = models.CharField(db_column='customer_phone_number', max_length=20)
    room_type = models.CharField(db_column='customer_room_type', max_length=100)
    booked_rate = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.CharField(db_column='customer_email', max_length=255, null=True, blank=True)
    booking_date = models.DateField()
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    total_days = models.IntegerField()
    total_cost_amount = models.DecimalField(max_digits=10, decimal_places=2)
    adults = models.IntegerField(db_column='number_of_adults')
    children = models.IntegerField(db_column='number_of_children')
    notes = models.CharField(db_column='admin_notes', max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'booking_info'
        managed = False
        ordering = ['-booking_date', '-checkin_date']

    def __str__(self) -> str:
        return f"Booking #{self.booking_id} - {self.name}"

class RoomPrice(models.Model):
    """Snapshot of nightly pricing for each room type in a hotel."""

    room_price_id = models.IntegerField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')
    bed_1_balcony_room = models.DecimalField(
        db_column='one_bed_balcony_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_1_window_room = models.DecimalField(
        db_column='one_bed_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_2_no_window_room = models.DecimalField(
        db_column='two_bed_no_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_1_no_window_room = models.DecimalField(
        db_column='one_bed_no_window_room', max_digits=10, decimal_places=2, null=True, blank=True
    )
    bed_2_condotel_balcony = models.DecimalField(
        db_column='two_bed_condotel_balcony', max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = 'room_price'
        managed = False

    def __str__(self) -> str:
        return f"RoomPrice #{self.room_price_id}"


class RoomInfo(models.Model):
    """Detailed information about each room including nightly price."""

    room_number = models.IntegerField(primary_key=True, db_column='room_number')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='room_hotel_id', null=True, blank=True)
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


class Account(models.Model):
    """Model mapped to the SQL Server `account` table."""

    account_id = models.IntegerField(primary_key=True, db_column='account_id')
    first_name = models.CharField(db_column='first_name', max_length=255, null=True, blank=True)
    last_name = models.CharField(db_column='last_name', max_length=255, null=True, blank=True)
    age = models.IntegerField(db_column='age', null=True, blank=True)
    gender = models.CharField(db_column='gender', max_length=255, null=True, blank=True)
    country_of_origin = models.CharField(db_column='country_of_origin', max_length=255, null=True, blank=True)
    country_current = models.CharField(db_column='country_current', max_length=255, null=True, blank=True)
    address_current = models.CharField(db_column='address_current', max_length=255, null=True, blank=True)
    phone_number = models.CharField(db_column='phone_number', max_length=20, null=True, blank=True)
    email = models.CharField(db_column='email', max_length=255, null=True, blank=True)
    username = models.CharField(db_column='username', max_length=255, null=True, blank=True)
    account_password = models.CharField(db_column='account_password', max_length=255, null=True, blank=True)
    account_type = models.CharField(db_column='account_type', max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(db_column='date_created', null=True, blank=True)
    last_login = models.DateTimeField(db_column='last_login', null=True, blank=True)

    class Meta:
        db_table = 'account'
        managed = False

    def __str__(self) -> str:
        return f"{self.username} ({self.account_type})"


class HotelServices(models.Model):
    """Model mapped to the SQL Server `hotel_services` table."""

    hotel_services_id = models.IntegerField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')
    name_of_service = models.CharField(db_column='service_name', max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'hotel_services'
        managed = False

    def __str__(self) -> str:
        return f"{self.name_of_service}"


class Minibar(models.Model):
    """Model mapped to the SQL Server `minibar` table."""

    room_number = models.IntegerField(primary_key=True, db_column='room_number')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='minibar_hotel_id', null=True, blank=True)
    coke = models.IntegerField(db_column='coke', null=True, blank=True)
    coffee = models.IntegerField(db_column='coffee', null=True, blank=True)
    water = models.IntegerField(db_column='water', null=True, blank=True)
    tea = models.IntegerField(db_column='tea', null=True, blank=True)
    snack_packet = models.IntegerField(db_column='snack_packet', null=True, blank=True)

    class Meta:
        db_table = 'minibar'
        managed = False

    def __str__(self) -> str:
        return f"Minibar for Room {self.room_number}"


class MinibarPrice(models.Model):
    """Model mapped to the SQL Server `minibar_price` table."""

    minibar_price_id = models.IntegerField(primary_key=True, db_column='minibar_price_id')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='minibar_price_hotel_id', null=True, blank=True)
    coke_price = models.DecimalField(db_column='coke_price', max_digits=10, decimal_places=2, null=True, blank=True)
    coffee_price = models.DecimalField(db_column='coffee_price', max_digits=10, decimal_places=2, null=True, blank=True)
    water_price = models.DecimalField(db_column='water_price', max_digits=10, decimal_places=2, null=True, blank=True)
    tea_price = models.DecimalField(db_column='tea_price', max_digits=10, decimal_places=2, null=True, blank=True)
    snack_packet_price = models.DecimalField(db_column='snack_packet_price', max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'minibar_price'
        managed = False

    def __str__(self) -> str:
        return f"Minibar Price #{self.minibar_price_id}"


class Payment(models.Model):
    """Model mapped to the SQL Server `payments` table."""

    payment_id = models.IntegerField(primary_key=True, db_column='payment_id')
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='payments_hotel_id', null=True, blank=True)
    booking = models.ForeignKey('CustomerBookingInfo', models.DO_NOTHING, db_column='booking_id', null=True, blank=True)
    payment_date = models.DateField(db_column='payment_date', null=True, blank=True)
    amount = models.DecimalField(db_column='amount', max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(db_column='payment_method', max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'payments'
        managed = False

    def __str__(self) -> str:
        return f"Payment #{self.payment_id} - {self.payment_method}"

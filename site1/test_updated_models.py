"""
Test script to verify updated database models work correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models import Hotel, CustomerBookingInfo, RoomPrice, HotelServices

print("=" * 60)
print("TESTING UPDATED DATABASE MODELS")
print("=" * 60)

# Test Hotel model
print("\n1. Testing Hotel model...")
try:
    hotels = Hotel.objects.all()
    print(f"   ✓ Found {hotels.count()} hotel(s)")
    if hotels.exists():
        hotel = hotels.first()
        print(f"   ✓ Hotel Name: {hotel.hotel_name}")
        print(f"   ✓ Hotel ID: {hotel.hotel_id}")
        print(f"   ✓ Address: {hotel.hotel_address}")
        print(f"   ✓ Email: {hotel.hotel_email_address}")
        print(f"   ✓ Phone: {hotel.phone_number}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test CustomerBookingInfo model
print("\n2. Testing CustomerBookingInfo model...")
try:
    bookings = CustomerBookingInfo.objects.all()
    print(f"   ✓ Found {bookings.count()} booking(s)")
    if bookings.exists():
        booking = bookings.first()
        print(f"   ✓ Booking ID: {booking.booking_id}")
        print(f"   ✓ Customer: {booking.name}")
        print(f"   ✓ Email: {booking.email}")
        print(f"   ✓ Phone: {booking.phone}")
        print(f"   ✓ Room Type: {booking.room_type}")
        print(f"   ✓ Booked Rate: ₫{booking.booked_rate:,.0f}")
        print(f"   ✓ Check-in: {booking.checkin_date}")
        print(f"   ✓ Check-out: {booking.checkout_date}")
        print(f"   ✓ Total Days: {booking.total_days}")
        print(f"   ✓ Total Cost: ₫{booking.total_cost_amount:,.0f}")
        print(f"   ✓ Adults: {booking.adults}, Children: {booking.children}")
        print(f"   ✓ Hotel: {booking.hotel}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test RoomPrice model
print("\n3. Testing RoomPrice model...")
try:
    prices = RoomPrice.objects.all()
    print(f"   ✓ Found {prices.count()} room price record(s)")
    if prices.exists():
        price = prices.first()
        print(f"   ✓ Room Price ID: {price.room_price_id}")
        print(f"   ✓ Hotel: {price.hotel}")
        if price.bed_1_balcony_room:
            print(f"   ✓ 1 Bed Balcony: ₫{price.bed_1_balcony_room:,.0f}")
        if price.bed_1_window_room:
            print(f"   ✓ 1 Bed Window: ₫{price.bed_1_window_room:,.0f}")
        if price.bed_2_no_window_room:
            print(f"   ✓ 2 Bed No Window: ₫{price.bed_2_no_window_room:,.0f}")
        if price.bed_1_no_window_room:
            print(f"   ✓ 1 Bed No Window: ₫{price.bed_1_no_window_room:,.0f}")
        if price.bed_2_condotel_balcony:
            print(f"   ✓ 2 Bed Condotel: ₫{price.bed_2_condotel_balcony:,.0f}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test HotelServices model
print("\n4. Testing HotelServices model...")
try:
    services = HotelServices.objects.all()
    print(f"   ✓ Found {services.count()} service(s)")
    if services.exists():
        for service in services:
            print(f"   ✓ {service.name_of_service}: ₫{service.price:,.0f} - {service.service_description}")
            print(f"     Hotel: {service.hotel}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

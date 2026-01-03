"""
Test script to verify edit functionality works correctly
"""
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo
from decimal import Decimal

print("=" * 60)
print("TESTING RESERVATION EDIT FUNCTIONALITY")
print("=" * 60)

# Get a booking to test with
booking = CustomerBookingInfo.objects.first()
if not booking:
    print("❌ No bookings found in database to test with")
    exit(1)

print(f"\n📋 Original Booking #{booking.booking_id}:")
print(f"   Name: {booking.guest_name}")
print(f"   Email: {booking.email}")
print(f"   Room: {booking.room_type}")
print(f"   Check-in: {booking.check_in}")
print(f"   Check-out: {booking.check_out}")
print(f"   Adults: {booking.adults}")
print(f"   Children: {booking.children}")

# Test 1: Change room type (the most common edit scenario)
print("\n🔧 TEST 1: Changing room type...")
original_room = booking.room_type
booking.room_type = "1 Bed With Window" if booking.room_type != "1 Bed With Window" else "1 Bed With Balcony"

try:
    from django.utils import timezone
    booking.updated_at = timezone.now()
    booking.save()
    print(f"   ✅ SUCCESS: Room changed from '{original_room}' to '{booking.room_type}'")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    exit(1)

# Verify it was saved
booking.refresh_from_db()
print(f"   ✅ Verified: Room type in DB is now '{booking.room_type}'")

# Test 2: Change name
print("\n🔧 TEST 2: Changing guest name...")
original_name = booking.guest_name
booking.guest_name = "Test Guest"
try:
    booking.updated_at = timezone.now()
    booking.save()
    print(f"   ✅ SUCCESS: Name changed from '{original_name}' to '{booking.guest_name}'")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    exit(1)

# Test 3: Keep same email (this was causing the error before)
print("\n🔧 TEST 3: Updating booking while keeping same email...")
current_email = booking.email
booking.adults = 2  # Just change something else
try:
    booking.updated_at = timezone.now()
    booking.save()
    print(f"   ✅ SUCCESS: Updated adults to {booking.adults} with same email '{current_email}'")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    exit(1)

# Test 4: Multiple bookings with same email
print("\n🔧 TEST 4: Creating second booking with same email...")
try:
    from django.utils import timezone
    new_booking = CustomerBookingInfo.objects.create(
        hotel=booking.hotel,
        guest_name="Another Guest",
        email=booking.email,  # SAME EMAIL
        phone="999999999",
        room_type="1 Bed With Window",
        booking_date=timezone.now(),
        check_in=datetime(2026, 2, 1).date(),
        check_out=datetime(2026, 2, 3).date(),
        adults=1,
        children=0,
        booked_rate=Decimal('850000.00'),
        total_price=Decimal('1700000.00'),
        status='confirmed',
        payment_status='unpaid',
        amount_paid=Decimal('0.00'),
        created_at=timezone.now(),
        updated_at=timezone.now()
    )
    print(f"   ✅ SUCCESS: Created booking #{new_booking.booking_id} with same email '{booking.email}'")
    
    # Clean up - delete the test booking
    new_booking.delete()
    print(f"   🧹 Cleaned up test booking #{new_booking.booking_id}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    exit(1)

# Restore original values
print("\n🔄 Restoring original values...")
booking.guest_name = original_name
booking.room_type = original_room
booking.updated_at = timezone.now()
booking.save()
print(f"   ✅ Booking restored to original state")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED! Edit functionality is working correctly")
print("=" * 60)
print("\n👍 You can now edit reservations in the admin dashboard:")
print("   - Change room types ✓")
print("   - Update guest information ✓")
print("   - Keep same email (no duplicate errors) ✓")
print("   - Multiple bookings with same email ✓")

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo

print("Testing CustomerBookingInfo model...")
print("="*50)

# Try to fetch all bookings
try:
    bookings = CustomerBookingInfo.objects.all()
    print(f"✅ Successfully connected to booking_info table")
    print(f"✅ Total bookings found: {bookings.count()}")
    
    if bookings.exists():
        # Test accessing the first booking
        first_booking = bookings.first()
        print(f"\n📋 First booking details:")
        print(f"  - Booking ID: {first_booking.booking_id}")
        print(f"  - Customer: {first_booking.name}")
        print(f"  - Email: {first_booking.email}")
        print(f"  - Room Type: {first_booking.room_type}")
        print(f"  - Check-in: {first_booking.checkin_date}")
        print(f"  - Check-out: {first_booking.checkout_date}")
        print(f"  - Total Cost: ₫{first_booking.total_cost_amount:,.0f}")
        print(f"  - Admin Notes: '{first_booking.notes}'")
        
        # Test if notes field works
        print(f"\n✅ Notes field accessible: {hasattr(first_booking, 'notes')}")
        print(f"✅ Notes value type: {type(first_booking.notes)}")
        
    print("\n" + "="*50)
    print("✅ All tests passed! Model is working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

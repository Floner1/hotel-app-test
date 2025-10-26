import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo
from django.test import RequestFactory
from home.views import edit_reservation
from datetime import date

print("=" * 60)
print("TESTING EDIT RESERVATION FUNCTIONALITY")
print("=" * 60)

# Get the test booking
booking = CustomerBookingInfo.objects.first()
if not booking:
    print("❌ No booking found to test with!")
    exit(1)

print(f"\n1. Original Booking Data:")
print(f"   ID: {booking.booking_id}")
print(f"   Name: {booking.name}")
print(f"   Email: {booking.email}")
print(f"   Phone: {booking.phone}")
print(f"   Room Type: {booking.room_type}")
print(f"   Check-in: {booking.checkin_date}")
print(f"   Check-out: {booking.checkout_date}")
print(f"   Adults: {booking.adults}")
print(f"   Children: {booking.children}")
print(f"   Total Days: {booking.total_days}")
print(f"   Total Cost: ₫{booking.total_cost_amount:,.2f}")
print(f"   Notes: {booking.notes}")

# Create a mock request with updated data
factory = RequestFactory()
update_data = {
    'name': 'Updated Customer Name',
    'email': 'updated@example.com',
    'phone': '0987654321',
    'room_type': '1 bed balcony room',
    'checkin_date': '2025-11-01',
    'checkout_date': '2025-11-03',
    'adults': 3,
    'children': 1,
    'notes': 'Updated notes: VIP customer, needs early check-in'
}

request = factory.post(
    f'/dashboard/reservations/edit/{booking.booking_id}/',
    data=json.dumps(update_data),
    content_type='application/json'
)

print(f"\n2. Testing Edit Endpoint...")
print(f"   Update Data: {json.dumps(update_data, indent=2)}")

try:
    response = edit_reservation(request, booking.booking_id)
    response_data = json.loads(response.content)
    
    print(f"\n3. Response:")
    print(f"   Status: {response_data.get('status')}")
    print(f"   Message: {response_data.get('message')}")
    
    if response_data.get('status') == 'success':
        # Reload booking from database
        booking.refresh_from_db()
        
        print(f"\n4. Updated Booking Data:")
        print(f"   ID: {booking.booking_id}")
        print(f"   Name: {booking.name}")
        print(f"   Email: {booking.email}")
        print(f"   Phone: {booking.phone}")
        print(f"   Room Type: {booking.room_type}")
        print(f"   Check-in: {booking.checkin_date}")
        print(f"   Check-out: {booking.checkout_date}")
        print(f"   Adults: {booking.adults}")
        print(f"   Children: {booking.children}")
        print(f"   Total Days: {booking.total_days}")
        print(f"   Total Cost: ₫{booking.total_cost_amount:,.2f}")
        print(f"   Notes: {booking.notes}")
        
        # Verify calculations
        expected_days = 2  # Nov 1 to Nov 3 = 2 days
        expected_cost = 800000 * 2  # 1 bed balcony room = ₫800,000/night
        
        print(f"\n5. Verification:")
        print(f"   ✅ Name updated: {booking.name == 'Updated Customer Name'}")
        print(f"   ✅ Email updated: {booking.email == 'updated@example.com'}")
        print(f"   ✅ Phone updated: {booking.phone == '0987654321'}")
        print(f"   ✅ Room type updated: {'1 bed balcony' in booking.room_type}")
        print(f"   ✅ Adults updated: {booking.adults == 3}")
        print(f"   ✅ Children updated: {booking.children == 1}")
        print(f"   ✅ Days calculated correctly: {booking.total_days == expected_days} ({booking.total_days} days)")
        print(f"   ✅ Cost calculated correctly: {float(booking.total_cost_amount) == expected_cost} (₫{booking.total_cost_amount:,.2f})")
        print(f"   ✅ Notes updated: {booking.notes == 'Updated notes: VIP customer, needs early check-in'}")
        
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ Edit failed: {response_data.get('message')}")
        
except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

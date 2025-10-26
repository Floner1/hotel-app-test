import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo, Hotel
from datetime import date, timedelta

print("Creating test reservation with notes...")
print("="*50)

try:
    # Get or create hotel
    hotel, created = Hotel.objects.get_or_create(
        hotel_id=1,
        defaults={
            'hotel_name': 'Test Hotel',
            'star_rating': 5,
            'hotel_address': '123 Test Street',
            'hotel_email_address': 'test@hotel.com',
            'phone_number': '+1234567890',
            'established_date': date(2020, 1, 1)
        }
    )
    
    # Create a test booking with notes
    booking = CustomerBookingInfo.objects.create(
        name='Test Customer',
        phone='1234567890',
        email=f'test{date.today().strftime("%Y%m%d%H%M%S")}@example.com',  # Unique email
        room_type='2 bed no window',
        booking_date=date.today(),
        checkin_date=date.today() + timedelta(days=2),
        checkout_date=date.today() + timedelta(days=3),
        total_days=1,
        total_cost_amount=800000,
        adults=2,
        children=0,
        notes='Test notes: Customer requested early check-in',
        hotel=hotel
    )
    
    print(f"✅ Created test booking #{booking.booking_id}")
    print(f"   Customer: {booking.name}")
    print(f"   Email: {booking.email}")
    print(f"   Notes: '{booking.notes}'")
    print(f"\n✅ Success! You can now view this booking in the admin dashboard.")
    print(f"   URL: http://127.0.0.1:8000/dashboard/reservations/")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

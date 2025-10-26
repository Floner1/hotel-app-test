import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo
import json

print("Testing view_reservation data preparation...")
print("="*50)

try:
    # Get the test booking
    booking = CustomerBookingInfo.objects.first()
    
    if booking:
        # Simulate what the view does
        booking_data = {
            'booking_id': booking.booking_id,
            'name': booking.name,
            'email': booking.email,
            'phone': booking.phone,
            'room_type': booking.room_type,
            'booking_date': booking.booking_date.strftime('%B %d, %Y'),
            'checkin_date': booking.checkin_date.strftime('%B %d, %Y'),
            'checkout_date': booking.checkout_date.strftime('%B %d, %Y'),
            'total_days': booking.total_days,
            'adults': booking.adults,
            'children': booking.children,
            'total_cost_amount': str(booking.total_cost_amount),
            'notes': booking.notes if booking.notes else '',
            'hotel_name': booking.hotel.hotel_name if booking.hotel else 'N/A',
        }
        
        print("✅ Booking data prepared successfully:")
        print(json.dumps(booking_data, indent=2))
        print(f"\n✅ Notes field present: {'notes' in booking_data}")
        print(f"✅ Notes value: '{booking_data['notes']}'")
        
    else:
        print("⚠️ No bookings found in database")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

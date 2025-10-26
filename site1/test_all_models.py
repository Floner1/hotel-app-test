import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import (
    Hotel, CustomerBookingInfo, RoomInfo, RoomPrice,
    Account, HotelServices, Minibar, MinibarPrice, Payment
)

print("=" * 60)
print("TESTING ALL MODELS")
print("=" * 60)

# Test each model
models_to_test = [
    ('Hotel', Hotel),
    ('CustomerBookingInfo', CustomerBookingInfo),
    ('RoomInfo', RoomInfo),
    ('RoomPrice', RoomPrice),
    ('Account', Account),
    ('HotelServices', HotelServices),
    ('Minibar', Minibar),
    ('MinibarPrice', MinibarPrice),
    ('Payment', Payment),
]

for model_name, model_class in models_to_test:
    try:
        count = model_class.objects.count()
        print(f"\n✅ {model_name}: {count} records")
        
        # Show first record if available
        if count > 0:
            first = model_class.objects.first()
            print(f"   Sample: {first}")
    except Exception as e:
        print(f"\n❌ {model_name}: Error - {e}")

print("\n" + "=" * 60)
print("TESTING RELATIONSHIPS")
print("=" * 60)

# Test RoomInfo relationship
try:
    room = RoomInfo.objects.first()
    if room:
        print(f"\n✅ RoomInfo.hotel relationship:")
        print(f"   Room #{room.room_number}")
        print(f"   Hotel: {room.hotel.hotel_name if room.hotel else 'None'}")
except Exception as e:
    print(f"\n❌ RoomInfo.hotel relationship failed: {e}")

# Test CustomerBookingInfo relationship
try:
    booking = CustomerBookingInfo.objects.first()
    if booking:
        print(f"\n✅ CustomerBookingInfo.hotel relationship:")
        print(f"   Booking #{booking.booking_id}")
        print(f"   Hotel: {booking.hotel.hotel_name if booking.hotel else 'None'}")
except Exception as e:
    print(f"\n❌ CustomerBookingInfo.hotel relationship failed: {e}")

# Test Payment relationships
try:
    payment = Payment.objects.first()
    if payment:
        print(f"\n✅ Payment relationships:")
        print(f"   Payment #{payment.payment_id}")
        print(f"   Hotel: {payment.hotel.hotel_name if payment.hotel else 'None'}")
        print(f"   Booking: {payment.booking if payment.booking else 'None'}")
except Exception as e:
    print(f"\n❌ Payment relationships failed: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED!")
print("=" * 60)

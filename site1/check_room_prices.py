import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import RoomInfo, RoomPrice
from backend.services.services import ReservationService

print("=" * 60)
print("CHECKING ROOM PRICING DATA")
print("=" * 60)

# Check room_info table
print("\n1. Checking room_info table:")
print("-" * 60)
room_infos = RoomInfo.objects.all()
if room_infos.exists():
    for room in room_infos:
        print(f"  Room Type: {room.room_type}")
        print(f"  Price per Night: {room.price_per_night}")
        print(f"  Description: {room.description}")
        print()
else:
    print("  ❌ No records found in room_info table")

# Check room_price table
print("\n2. Checking room_price table:")
print("-" * 60)
room_prices = RoomPrice.objects.all().order_by('-room_price_id')
if room_prices.exists():
    latest = room_prices.first()
    print(f"  Latest Price Record ID: {latest.room_price_id}")
    print(f"  1 Bed Balcony Room: {latest.bed_1_balcony_room}")
    print(f"  1 Bed Window Room: {latest.bed_1_window_room}")
    print(f"  2 Bed No Window: {latest.bed_2_no_window_room}")
    print(f"  1 Bed No Window: {latest.bed_1_no_window_room}")
    print(f"  2 Bed Condotel Balcony: {latest.bed_2_condotel_balcony}")
    print()
else:
    print("  ❌ No records found in room_price table")

# Test the service's rate loading
print("\n3. Testing ReservationService rate loading:")
print("-" * 60)
try:
    rates = ReservationService.get_room_rates(force_refresh=True)
    if rates:
        print("  ✅ Successfully loaded rates:")
        for room_type, price in rates.items():
            print(f"    {room_type}: ₫{price:,.2f}")
    else:
        print("  ⚠️ No rates loaded from database")
except Exception as e:
    print(f"  ❌ Error loading rates: {e}")

print("\n" + "=" * 60)

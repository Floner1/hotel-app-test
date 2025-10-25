import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import RoomPrice
from backend.services.services import ReservationService

print("Testing Room Price Loading...")
print("="*60)

# Check database
count = RoomPrice.objects.count()
print(f"RoomPrice records in database: {count}")

if count > 0:
    snapshot = RoomPrice.objects.first()
    print(f"\nFirst record ID: {snapshot.room_price_id}")
    print(f"Hotel FK: {snapshot.hotel_id if snapshot.hotel else 'NULL'}")
    print(f"1 bed balcony room: {snapshot.bed_1_balcony_room}")
    print(f"1 bed window room: {snapshot.bed_1_window_room}")
    print(f"2 bed balcony room: {snapshot.bed_2_balcony_room}")
    print(f"1 bed no window: {snapshot.bed_1_no_window_room}")
    print(f"2 bed condotel balcony: {snapshot.bed_2_condotel_balcony}")

# Test service loading
print("\n" + "="*60)
print("Testing ReservationService.get_room_rates()...")
rates = ReservationService.get_room_rates(force_refresh=True)
print(f"Loaded {len(rates)} rates:")
for room_type, rate in rates.items():
    print(f"  {room_type}: {rate}")

print("\n" + "="*60)
if len(rates) == 0:
    print("❌ WARNING: No rates loaded from database!")
else:
    print("✅ Rates loaded successfully from database!")

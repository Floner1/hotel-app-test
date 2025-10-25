import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import RoomPrice
from backend.services.services import ReservationService

print("Testing Room Price Loading with Fixed Column Names")
print("="*70)

# Check database
snapshot = RoomPrice.objects.first()
if snapshot:
    print(f"✓ Found RoomPrice record ID: {snapshot.room_price_id}\n")
    print("Database Values:")
    print(f"  1 bed balcony room:        {snapshot.bed_1_balcony_room}")
    print(f"  1 bed window room:         {snapshot.bed_1_window_room}")
    print(f"  2 bed no window room:      {snapshot.bed_2_no_window_room}")
    print(f"  1 bed no window room:      {snapshot.bed_1_no_window_room}")
    print(f"  2 bed condotel balcony:    {snapshot.bed_2_condotel_balcony}")
else:
    print("❌ No RoomPrice records found")
    sys.exit(1)

print("\n" + "="*70)
print("Testing Service Rate Loading...")
rates = ReservationService.get_room_rates(force_refresh=True)

print(f"\n✓ Loaded {len(rates)} rates from database:")
for room_type, rate in rates.items():
    print(f"  {room_type}: {rate:,.2f}")

if len(rates) == 5:
    print("\n✅ SUCCESS: All 5 room rates loaded from database!")
else:
    print(f"\n⚠️  WARNING: Expected 5 rates, got {len(rates)}")

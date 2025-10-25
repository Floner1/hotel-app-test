import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import RoomPrice
from decimal import Decimal

print("Direct Database Query Test")
print("="*60)

try:
    count = RoomPrice.objects.count()
    print(f"✓ RoomPrice.objects.count() = {count}")
    
    if count > 0:
        snapshot = RoomPrice.objects.order_by('-room_price_id').first()
        print(f"✓ Got snapshot with ID: {snapshot.room_price_id}")
        print(f"  Hotel: {snapshot.hotel}")
        
        # Test field access
        print("\nField Values:")
        print(f"  bed_1_balcony_room: {snapshot.bed_1_balcony_room} (type: {type(snapshot.bed_1_balcony_room)})")
        print(f"  bed_1_window_room: {snapshot.bed_1_window_room}")
        print(f"  bed_2_balcony_room: {snapshot.bed_2_balcony_room}")
        print(f"  bed_1_no_window_room: {snapshot.bed_1_no_window_room}")
        print(f"  bed_2_condotel_balcony: {snapshot.bed_2_condotel_balcony}")
        
        # Test the conversion logic
        print("\nTesting Conversion:")
        field_map = {
            '1 bed balcony room': 'bed_1_balcony_room',
            '1 bed window room': 'bed_1_window_room',
            '2 bed no window': 'bed_2_balcony_room',
            '1 bed no window': 'bed_1_no_window_room',
            'condotel 2 bed and balcony': 'bed_2_condotel_balcony',
        }
        
        rates = {}
        for canonical, field_name in field_map.items():
            value = getattr(snapshot, field_name, None)
            print(f"  {canonical}: getattr returned {value}")
            if value is not None:
                converted = Decimal(str(value))
                rates[canonical] = converted
                print(f"    → Converted to Decimal: {converted}")
        
        print(f"\n✓ Successfully loaded {len(rates)} rates")
        
    else:
        print("❌ No records found in room_price table")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

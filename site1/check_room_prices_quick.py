"""
Quick script to check room prices from database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models import RoomPrice

print("=" * 60)
print("ROOM PRICES FROM DATABASE")
print("=" * 60)

prices = RoomPrice.objects.all()
for price in prices:
    print(f"\nRoom Price ID: {price.room_price_id}")
    print(f"Hotel: {price.hotel}")
    if price.bed_1_balcony_room:
        print(f"1 Bed Balcony Room: ₫{price.bed_1_balcony_room:,.0f}")
    if price.bed_1_window_room:
        print(f"1 Bed Window Room: ₫{price.bed_1_window_room:,.0f}")
    if price.bed_2_no_window_room:
        print(f"2 Bed No Window Room: ₫{price.bed_2_no_window_room:,.0f}")
    if price.bed_1_no_window_room:
        print(f"1 Bed No Window Room: ₫{price.bed_1_no_window_room:,.0f}")
    if price.bed_2_condotel_balcony:
        print(f"Condotel 2 Bed and Balcony: ₫{price.bed_2_condotel_balcony:,.0f}")

print("\n" + "=" * 60)

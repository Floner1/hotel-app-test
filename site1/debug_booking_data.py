"""
Debug script to see what's in the booking and what's being saved
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import CustomerBookingInfo
from django.db import connection

# Get the booking
booking = CustomerBookingInfo.objects.first()

print("=" * 60)
print("BOOKING DATA")
print("=" * 60)
print(f"\nBooking ID: {booking.booking_id}")

# Print all fields
for field in booking._meta.get_fields():
    if not field.is_relation and hasattr(booking, field.name):
        value = getattr(booking, field.name)
        print(f"{field.name}: {value} (type: {type(value).__name__})")

# Check the database schema for users table
print("\n" + "=" * 60)
print("USERS TABLE SCHEMA")
print("=" * 60)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'users'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[0]}: {col[1]}", end="")
        if col[2]:
            print(f"({col[2]})", end="")
        if col[3] == 'NO':
            print(" NOT NULL", end="")
        print()

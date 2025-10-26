import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # List all tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
        AND TABLE_CATALOG = 'hotelbooking'
    """)
    
    tables = cursor.fetchall()
    print("Available tables in hotelbooking database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check for booking_info table structure
    print("\n" + "="*50)
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'booking_info'
        AND TABLE_CATALOG = 'hotelbooking'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    if columns:
        print("\nColumns in booking_info table:")
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            max_len = f"({col[3]})" if col[3] else ""
            print(f"  - {col[0]}: {col[1]}{max_len} {nullable}")
    else:
        print("\nNo booking_info table found!")

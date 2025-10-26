import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

print("=" * 60)
print("CHECKING ALL TABLES IN DATABASE")
print("=" * 60)

with connection.cursor() as cursor:
    # Get all user tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
        AND TABLE_SCHEMA = 'dbo'
        ORDER BY TABLE_NAME
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    
    # Check each table that might be relevant
    relevant_tables = ['booking_info', 'hotel', 'room_info', 'room_price', 'account', 
                       'hotel_services', 'minibar', 'minibar_price', 'payments']
    
    for table_name in relevant_tables:
        if table_name in tables:
            print(f"\n{'=' * 60}")
            print(f"TABLE: {table_name}")
            print('=' * 60)
            
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME, 
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """)
            
            for row in cursor.fetchall():
                col_name = row[0]
                data_type = row[1]
                max_len = row[2]
                nullable = row[3]
                
                type_str = data_type
                if max_len:
                    type_str = f"{data_type}({max_len})"
                
                null_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  {col_name}: {type_str} {null_str}")

print("\n" + "=" * 60)

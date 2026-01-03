"""
Check for triggers and foreign keys on booking_info table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

print("=" * 60)
print("TRIGGERS ON booking_info TABLE")
print("=" * 60)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            t.name AS trigger_name,
            OBJECT_NAME(t.parent_id) AS table_name,
            CASE WHEN t.is_instead_of_trigger = 1 THEN 'INSTEAD OF' ELSE 'AFTER' END AS trigger_type,
            (SELECT STRING_AGG(type_desc, ', ') 
             FROM sys.trigger_events te 
             WHERE te.object_id = t.object_id) AS trigger_events
        FROM sys.triggers t
        WHERE OBJECT_NAME(t.parent_id) = 'booking_info'
    """)
    
    triggers = cursor.fetchall()
    if triggers:
        for trigger in triggers:
            print(f"\nTrigger: {trigger[0]}")
            print(f"Type: {trigger[2]}")
            print(f"Events: {trigger[3]}")
    else:
        print("\n✅ No triggers found")
    
    print("\n" + "=" * 60)
    print("FOREIGN KEYS ON booking_info TABLE")
    print("=" * 60)
    
    cursor.execute("""
        SELECT 
            fk.name AS foreign_key_name,
            OBJECT_NAME(fk.parent_object_id) AS table_name,
            COL_NAME(fc.parent_object_id, fc.parent_column_id) AS column_name,
            OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
            COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column
        FROM sys.foreign_keys AS fk
        INNER JOIN sys.foreign_key_columns AS fc 
            ON fk.object_id = fc.constraint_object_id
        WHERE OBJECT_NAME(fk.parent_object_id) = 'booking_info'
    """)
    
    fks = cursor.fetchall()
    if fks:
        for fk in fks:
            print(f"\nFK Name: {fk[0]}")
            print(f"Column: {fk[2]}")
            print(f"References: {fk[3]}.{fk[4]}")
    else:
        print("\n✅ No foreign keys found")

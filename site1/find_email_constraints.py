"""Find all UNIQUE constraints on email columns"""
from django.db import connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME, kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'UNIQUE'
            AND (kcu.COLUMN_NAME LIKE '%email%' OR kcu.COLUMN_NAME LIKE '%mail%')
    """)
    
    results = cursor.fetchall()
    if results:
        print("Found UNIQUE constraints on email columns:")
        for row in results:
            table, constraint, column = row
            print(f"  Table: {table}")
            print(f"  Column: {column}")
            print(f"  Constraint: {constraint}")
            print()
            
            # Try to drop it
            try:
                cursor.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
                print(f"  ✓ Dropped constraint {constraint} from {table}.{column}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
            print()
    else:
        print("No UNIQUE constraints found on email columns")

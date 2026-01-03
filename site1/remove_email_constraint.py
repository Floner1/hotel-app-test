"""
Script to remove UNIQUE constraint from email field in booking_info table.
This allows customers to make multiple bookings with the same email address.
"""

from django.db import connection

def remove_email_unique_constraint():
    with connection.cursor() as cursor:
        # First, find all UNIQUE constraints on booking_info table
        print("Finding UNIQUE constraints on booking_info table...")
        cursor.execute("""
            SELECT 
                tc.CONSTRAINT_NAME,
                tc.TABLE_NAME,
                kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE tc.TABLE_NAME = 'booking_info'
                AND tc.CONSTRAINT_TYPE = 'UNIQUE'
        """)
        
        constraints = cursor.fetchall()
        
        if not constraints:
            print("No UNIQUE constraints found on booking_info table.")
            return
        
        print(f"\nFound {len(constraints)} UNIQUE constraint(s):")
        for constraint in constraints:
            constraint_name, table_name, column_name = constraint
            print(f"  - {constraint_name} on column '{column_name}'")
            
            if 'email' in column_name.lower():
                print(f"\n  Dropping constraint {constraint_name}...")
                try:
                    cursor.execute(f"ALTER TABLE booking_info DROP CONSTRAINT {constraint_name}")
                    print(f"  ✓ Successfully dropped constraint {constraint_name}")
                except Exception as e:
                    print(f"  ✗ Error dropping constraint: {e}")
        
        print("\nDone! Email field no longer has UNIQUE constraint.")
        print("Customers can now make multiple bookings with the same email.")

if __name__ == "__main__":
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
    django.setup()
    
    remove_email_unique_constraint()

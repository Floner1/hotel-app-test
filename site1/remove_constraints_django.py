"""
Remove UNIQUE constraints using Django's database connection
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    print("Finding UNIQUE constraints on users table...")
    
    # Find all UNIQUE constraints
    cursor.execute("""
        SELECT tc.CONSTRAINT_NAME, cu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE cu 
            ON tc.CONSTRAINT_NAME = cu.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'UNIQUE' AND tc.TABLE_NAME = 'users'
    """)
    
    constraints = cursor.fetchall()
    
    if not constraints:
        print("✅ No UNIQUE constraints found")
    else:
        print(f"\nFound {len(constraints)} constraint(s):")
        for constraint_name, column_name in constraints:
            print(f"\n  Constraint: {constraint_name}")
            print(f"  Column: {column_name}")
            print(f"  Removing...")
            
            try:
                cursor.execute(f"ALTER TABLE users DROP CONSTRAINT {constraint_name}")
                print(f"  ✅ Removed successfully")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    # Verify all are gone
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    cursor.execute("""
        SELECT tc.CONSTRAINT_NAME, cu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE cu 
            ON tc.CONSTRAINT_NAME = cu.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'UNIQUE' AND tc.TABLE_NAME = 'users'
    """)
    
    remaining = cursor.fetchall()
    
    if not remaining:
        print("\n✅ SUCCESS! All UNIQUE constraints removed from users table")
        print("\n👍 You can now:")
        print("   - Edit bookings without constraint errors")
        print("   - Have multiple bookings with same email")
        print("   - Update any field without duplicate key errors")
    else:
        print(f"\n⚠️ {len(remaining)} constraint(s) still remain:")
        for c_name, col_name in remaining:
            print(f"   - {c_name} on {col_name}")

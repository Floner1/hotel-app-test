"""
Find and remove ALL UNIQUE constraints from the users table
"""
import pyodbc

# Connection details
server = 'LAPTOP-9KD9Q7AE\\MSSQLSERVER01'
database = 'hotelbooking'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("FINDING ALL UNIQUE CONSTRAINTS ON users TABLE")
    print("=" * 60)
    
    # Find all UNIQUE constraints on users table
    query = """
    SELECT 
        tc.TABLE_NAME,
        tc.CONSTRAINT_NAME,
        cu.COLUMN_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE cu 
        ON tc.CONSTRAINT_NAME = cu.CONSTRAINT_NAME
    WHERE tc.CONSTRAINT_TYPE = 'UNIQUE'
        AND tc.TABLE_NAME = 'users'
    ORDER BY tc.CONSTRAINT_NAME
    """
    
    cursor.execute(query)
    constraints = cursor.fetchall()
    
    if not constraints:
        print("\n✅ No UNIQUE constraints found on users table")
    else:
        print(f"\nFound {len(constraints)} UNIQUE constraint(s):\n")
        
        for row in constraints:
            table_name = row[0]
            constraint_name = row[1]
            column_name = row[2]
            
            print(f"  Table: {table_name}")
            print(f"  Column: {column_name}")
            print(f"  Constraint: {constraint_name}")
            
            # Drop the constraint
            drop_sql = f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"
            try:
                cursor.execute(drop_sql)
                conn.commit()
                print(f"  ✅ Dropped constraint {constraint_name} from {table_name}.{column_name}")
            except Exception as e:
                print(f"  ❌ Error dropping constraint: {e}")
            
            print()
    
    # Verify all are gone
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    cursor.execute(query)
    remaining = cursor.fetchall()
    
    if not remaining:
        print("\n✅ SUCCESS: All UNIQUE constraints removed from users table")
        print("\n👍 The users table can now have:")
        print("   - Multiple users with same username")
        print("   - Multiple users with same email")
        print("   - Multiple bookings per customer")
    else:
        print(f"\n⚠️ WARNING: {len(remaining)} constraint(s) still remain:")
        for row in remaining:
            print(f"   - {row[1]} on {row[2]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

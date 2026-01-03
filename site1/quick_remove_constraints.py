"""
Quick script to remove UNIQUE constraints and test
"""
import pyodbc

server = 'LAPTOP-9KD9Q7AE\\MSSQLSERVER01'
database = 'hotelbooking'
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Find constraints
query = """
SELECT tc.CONSTRAINT_NAME, cu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE cu 
    ON tc.CONSTRAINT_NAME = cu.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_TYPE = 'UNIQUE' AND tc.TABLE_NAME = 'users'
"""

cursor.execute(query)
constraints = cursor.fetchall()

print(f"Found {len(constraints)} UNIQUE constraints on users table:")
for c in constraints:
    print(f"  - {c[0]} on column {c[1]}")
    try:
        cursor.execute(f"ALTER TABLE users DROP CONSTRAINT {c[0]}")
        conn.commit()
        print(f"    ✓ Removed")
    except Exception as e:
        print(f"    ✗ Error: {e}")

# Verify
cursor.execute(query)
remaining = cursor.fetchall()
print(f"\nRemaining UNIQUE constraints: {len(remaining)}")

cursor.close()
conn.close()
print("Done!")

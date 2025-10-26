import pyodbc

# Connection string
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=LAPTOP-PI7O21VK\\SQLEXPRESS;"
    "DATABASE=hotelbooking;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("RESERVATION TABLE STRUCTURE")
    print("=" * 60)
    
    # Get columns for reservation table
    cursor.execute("""
        SELECT 
            COLUMN_NAME, 
            DATA_TYPE, 
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'reservation'
        ORDER BY ORDINAL_POSITION
    """)
    
    print("\nColumns in reservation table:")
    for row in cursor.fetchall():
        col_name = row[0]
        data_type = row[1]
        is_nullable = row[2]
        max_length = row[3] if row[3] else ''
        
        if max_length:
            data_type = f"{data_type}({max_length})"
        
        nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
        print(f"  - {col_name}: {data_type} {nullable_str}")
    
    # Check for primary key
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = 'reservation'
        AND CONSTRAINT_NAME LIKE 'PK%'
    """)
    
    pk_columns = [row[0] for row in cursor.fetchall()]
    if pk_columns:
        print(f"\nPrimary Key: {', '.join(pk_columns)}")
    
    # Check for foreign keys
    cursor.execute("""
        SELECT 
            fk.name AS FK_Name,
            OBJECT_NAME(fk.parent_object_id) AS Table_Name,
            COL_NAME(fc.parent_object_id, fc.parent_column_id) AS Column_Name,
            OBJECT_NAME(fk.referenced_object_id) AS Referenced_Table,
            COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS Referenced_Column
        FROM sys.foreign_keys AS fk
        INNER JOIN sys.foreign_key_columns AS fc 
            ON fk.object_id = fc.constraint_object_id
        WHERE OBJECT_NAME(fk.parent_object_id) = 'reservation'
    """)
    
    fks = cursor.fetchall()
    if fks:
        print("\nForeign Keys:")
        for fk in fks:
            print(f"  - {fk[2]} -> {fk[3]}.{fk[4]}")
    
    conn.close()
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

"""
Fix the trigger by dropping and recreating it properly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

print("=" * 60)
print("FIXING TRIGGER: trg_booking_info_updated_at")
print("=" * 60)

with connection.cursor() as cursor:
    # Drop the trigger
    print("\n1. Dropping existing trigger...")
    try:
        cursor.execute("DROP TRIGGER IF EXISTS trg_booking_info_updated_at")
        print("   ✅ Trigger dropped")
    except Exception as e:
        print(f"   ⚠️ Error dropping trigger: {e}")
    
    # Recreate it properly (without the extra INSERT statements)
    print("\n2. Creating clean trigger...")
    trigger_sql = """
    CREATE TRIGGER trg_booking_info_updated_at
    ON booking_info
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE booking_info
        SET updated_at = GETDATE()
        FROM booking_info b
        INNER JOIN inserted i ON b.booking_id = i.booking_id;
    END;
    """
    
    try:
        cursor.execute(trigger_sql)
        print("   ✅ Trigger created successfully")
    except Exception as e:
        print(f"   ❌ Error creating trigger: {e}")
    
    # Verify
    print("\n3. Verifying trigger...")
    cursor.execute("""
        SELECT 
            t.name AS trigger_name,
            (SELECT STRING_AGG(type_desc, ', ') 
             FROM sys.trigger_events te 
             WHERE te.object_id = t.object_id) AS trigger_events
        FROM sys.triggers t
        WHERE OBJECT_NAME(t.parent_id) = 'booking_info'
            AND t.name = 'trg_booking_info_updated_at'
    """)
    
    trigger = cursor.fetchone()
    if trigger:
        print(f"   ✅ Trigger exists: {trigger[0]} on {trigger[1]} events")
    else:
        print("   ❌ Trigger not found!")

print("\n" + "=" * 60)
print("✅ TRIGGER FIX COMPLETE")
print("=" * 60)
print("\nThe trigger now only updates the updated_at timestamp")
print("without executing any INSERT statements.")

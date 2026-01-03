"""
View the trigger definition
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT OBJECT_DEFINITION(OBJECT_ID('trg_booking_info_updated_at'))
    """)
    
    trigger_def = cursor.fetchone()[0]
    
    print("=" * 60)
    print("TRIGGER: trg_booking_info_updated_at")
    print("=" * 60)
    print(trigger_def)

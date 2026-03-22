import os
import sys
import django
import datetime

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.db import connection

def run_schema():
    print('Reading schema.sql...')
    with open('schema.sql', 'r', encoding='iso-8859-1') as f:
        sql = f.read()

    import re
    batches = re.split(r'(?i)^\s*GO\s*$', sql, flags=re.MULTILINE)

    with connection.cursor() as cursor:
        # First, drop any tables that were preventing the drop of the users table.
        # This requires dropping FOREIGN KEY constraints that reference the users table.
        try:
            print("Dropping dependencies...")
            cursor.execute('''
                IF OBJECT_ID('dbo.trg_booking_ownership', 'TR') IS NOT NULL DROP TRIGGER dbo.trg_booking_ownership;
                IF OBJECT_ID('dbo.customer_requests', 'U') IS NOT NULL DROP TABLE dbo.customer_requests;
                IF OBJECT_ID('dbo.audit_log', 'U') IS NOT NULL DROP TABLE dbo.audit_log;
                IF OBJECT_ID('dbo.booking_info', 'U') IS NOT NULL DROP TABLE dbo.booking_info;
                
                -- Also drop the foreign key inside the users table that references itself
                BEGIN TRY
                    ALTER TABLE dbo.users DROP CONSTRAINT fk_users_created_by;
                END TRY
                BEGIN CATCH
                END CATCH
            ''')
        except Exception as e:
            print(f"Error dropping dependencies: {e}")
            
        for batch in batches:
            if not batch.strip():
                continue
            if 'USE hotelbooking' in batch:
                continue
            try:
                cursor.execute(batch)
            except Exception as e:
                print(f"Error executing batch:\n{batch[:100]}...\n{e}")
                
    print('? Database schema updated successfully!')
    print('Seeding database with test users...')
    
    from data.models import User, Hotel, CustomerBookingInfo
    from django.contrib.auth.hashers import make_password
    from django.utils import timezone
    
    # Refresh users block
    with connection.cursor() as c:
        pass # All tables should be reset now

    # 1. Create Admin
    User.objects.create(
        username='admin',
        email='admin@example.com',
        password_hash=make_password('admin123'),
        role='admin',
        is_active=True,
        created_at=timezone.now()
    )
    print('? Admin account created (admin / admin123)')

    # 2. Create Staff
    User.objects.create(
        username='staff',
        email='staff@example.com',
        password_hash=make_password('staff123'),
        role='staff',
        is_active=True,
        created_at=timezone.now()
    )
    print('? Staff account created (staff / staff123)')

    # 3. Create Customer
    customer = User.objects.create(
        username='customer',
        email='customer@example.com',
        password_hash=make_password('customer123'),
        role='customer',
        is_active=True,
        created_at=timezone.now()
    )
    print('? Customer account created (customer / customer123)')

    print('Seeding a sample reservation for the customer...')
    hotel = Hotel.objects.first()
    if hotel:
        CustomerBookingInfo.objects.create(
            hotel=hotel,
            user=customer,
            guest_name='John Doe',
            email='customer@example.com',
            phone='+84 987654321',
            room_type='1 Bed With Window',
            booking_date=timezone.now(),
            check_in=timezone.now().date(),
            check_out=timezone.now().date() + datetime.timedelta(days=2),
            adults=2,
            booked_rate=850000,
            total_price=1700000,
            status='confirmed',
            payment_status='paid'
        )
        print('? Sample reservation added!')

if __name__ == '__main__':
    run_schema()


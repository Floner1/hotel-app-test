import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models import User, Hotel, CustomerBookingInfo
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import connection, transaction

with transaction.atomic():
    # Clear existing users just in case
    User.objects.all().delete()
    
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
    
    # Refresh hotel
    hotel = Hotel.objects.first()
    if hotel:
        CustomerBookingInfo.objects.filter(user=customer).delete()
        CustomerBookingInfo.objects.create(
            hotel=hotel,
            user=customer,
            guest_name='John Doe',
            email='customer@example.com',
            phone='+84 987654321',
            room_type='1 Bed With Window',
            booking_date=timezone.now(),
            check_in=timezone.now().date(),
            check_out=timezone.now().date() + timedelta(days=2),
            adults=2,
            booked_rate=850000,
            total_price=1700000,
            status='confirmed',
            payment_status='paid',
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        print('? Sample reservation added!')

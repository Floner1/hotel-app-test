import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from django.contrib.auth.models import User

try:
    admin = User.objects.get(username='admin')
    print(f'Username: {admin.username}')
    print(f'Is staff: {admin.is_staff}')
    print(f'Is superuser: {admin.is_superuser}')
    print(f'Has usable password: {admin.has_usable_password()}')
    
    # Test password
    from django.contrib.auth import authenticate
    test_auth = authenticate(username='admin', password='admin123')
    if test_auth:
        print(f'✓ Password "admin123" works!')
    else:
        print(f'✗ Password "admin123" does NOT work')
        print('Resetting password to admin123...')
        admin.set_password('admin123')
        admin.save()
        print('Password has been reset.')
        
except User.DoesNotExist:
    print('Admin user does not exist!')
    print('Creating admin user...')
    User.objects.create_superuser('admin', 'admin@hotel.com', 'admin123')
    print('Admin user created with password: admin123')

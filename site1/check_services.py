import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from data.models.hotel import HotelServices

print("=" * 60)
print("HOTEL SERVICES IN DATABASE")
print("=" * 60)

services = HotelServices.objects.all()
print(f"\nTotal services: {services.count()}\n")

for service in services:
    print(f"ID: {service.hotel_services_id}")
    print(f"Name: {service.name_of_service}")
    print(f"Description: {service.service_description}")
    print(f"Price: ₫{service.price:,.2f}" if service.price else "Price: N/A")
    print("-" * 60)

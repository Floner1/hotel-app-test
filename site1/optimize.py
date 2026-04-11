import sys, re

with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix N+1 in admin_reservations
text = text.replace(
    'all_reservations = CustomerBookingInfo.objects.all().order_by(',
    "all_reservations = CustomerBookingInfo.objects.select_related('hotel', 'user').all().order_by("
)

# Fix N+1 in view_reservation
text = text.replace(
    'booking = CustomerBookingInfo.objects.get(',
    "booking = CustomerBookingInfo.objects.select_related('hotel', 'user').get("
)

with open('home/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Added select_related")

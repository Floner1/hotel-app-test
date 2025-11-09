from django.core.management.base import BaseCommand
from data.models.hotel import RoomPrice, Hotel
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate room_price table with all available room types'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting room types population...'))
        
        # Get the first hotel (or you can specify which hotel)
        hotel = Hotel.objects.first()
        
        if not hotel:
            self.stdout.write(self.style.ERROR('❌ No hotel found in database. Please create a hotel first.'))
            return
        
        self.stdout.write(f'Using hotel: {hotel.hotel_name} (ID: {hotel.hotel_id})')
        
        # Define room types with their prices and descriptions
        room_types_data = [
            {
                'room_type': 'one_bed_balcony_room',
                'price_per_night': Decimal('1500000.00'),
                'room_description': 'Cozy room with one bed and a private balcony with city views'
            },
            {
                'room_type': 'one_bed_window_room',
                'price_per_night': Decimal('1200000.00'),
                'room_description': 'Comfortable room with one bed and large windows'
            },
            {
                'room_type': 'one_bed_no_window_room',
                'price_per_night': Decimal('900000.00'),
                'room_description': 'Budget-friendly room with one bed, interior room'
            },
            {
                'room_type': 'two_bed_no_window_room',
                'price_per_night': Decimal('1400000.00'),
                'room_description': 'Spacious room with two beds, perfect for families'
            },
            {
                'room_type': 'two_bed_condotel_balcony',
                'price_per_night': Decimal('2500000.00'),
                'room_description': 'Luxury condotel suite with two beds and spacious balcony'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in room_types_data:
            # Check if room type already exists for this hotel
            room_price, created = RoomPrice.objects.update_or_create(
                hotel=hotel,
                room_type=data['room_type'],
                defaults={
                    'price_per_night': data['price_per_night'],
                    'room_description': data['room_description']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {data["room_type"]} - ₫{data["price_per_night"]:,.0f}/night')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {data["room_type"]} - ₫{data["price_per_night"]:,.0f}/night')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS(f'✓ Room types population complete!'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count + updated_count}'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Display current room types
        self.stdout.write('')
        self.stdout.write('Current room types in database:')
        all_rooms = RoomPrice.objects.filter(hotel=hotel).order_by('price_per_night')
        for room in all_rooms:
            try:
                price = float(room.price_per_night)
                self.stdout.write(f'  • {room.room_type}: ₫{price:,.0f}/night')
            except (ValueError, TypeError):
                self.stdout.write(f'  • {room.room_type}: ₫{room.price_per_night}/night')

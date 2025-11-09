"""
Middleware to automatically initialize room types on first request
"""
from django.utils.deprecation import MiddlewareMixin
from data.models.hotel import RoomPrice, Hotel
from decimal import Decimal


class RoomTypesInitializerMiddleware(MiddlewareMixin):
    """Initialize room types automatically on first request"""
    
    _initialized = False
    
    def process_request(self, request):
        if RoomTypesInitializerMiddleware._initialized:
            return None
        
        try:
            # Get the first hotel
            hotel = Hotel.objects.first()
            if not hotel:
                return None
            
            # Check if we already have room types
            existing_count = RoomPrice.objects.filter(hotel=hotel).count()
            if existing_count >= 5:
                RoomTypesInitializerMiddleware._initialized = True
                return None
            
            # Define default room types
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
            
            # Create room types if they don't exist
            for data in room_types_data:
                RoomPrice.objects.get_or_create(
                    hotel=hotel,
                    room_type=data['room_type'],
                    defaults={
                        'price_per_night': data['price_per_night'],
                        'room_description': data['room_description']
                    }
                )
            
            RoomTypesInitializerMiddleware._initialized = True
            
        except Exception:
            # Silently fail if database isn't ready
            pass
        
        return None

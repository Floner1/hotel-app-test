# Import the Hotel model from the home app
from home.models import Hotel

# Service class to handle hotel-related business logic
class HotelService:
    @staticmethod
    def get_hotel_name():
        """
        Retrieve just the hotel name from the database
        Returns the hotel name or a default message if not found
        """
        result = Hotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        """
        Retrieve hotel contact information from the database
        Returns a dictionary containing hotel name, address, phone, and email
        Returns None if no hotel record exists
        """
        return Hotel.objects.values(
            'hotel_name',
            'hotel_address',
            'phone',
            'email'
        ).first()

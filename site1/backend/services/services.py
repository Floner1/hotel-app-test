from home.models import Hotel

class HotelService:
    @staticmethod
    def get_hotel_name():
        result = Hotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        return Hotel.objects.values(
            'hotel_name',
            'hotel_address',
            'phone',
            'email'
        ).first()

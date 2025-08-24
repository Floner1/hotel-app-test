from data.models.hotel import Hotel

class HotelRepository:
    @staticmethod
    def get_hotel_name():
        # Query specifically for hotel name
        result = Hotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        # For contact page and other places where full info is needed
        return Hotel.objects.values(
            'hotel_name',
            'hotel_address',
            'phone',
            'email'
        ).first()

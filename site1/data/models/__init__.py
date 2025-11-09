# Import all models to make them discoverable by Django
from .hotel import (
    Hotel, 
    CustomerBookingInfo, 
    RoomPrice,
    HotelServices,
    HotelKeysMain
)
from .images import ImagesRef

__all__ = [
    'Hotel', 
    'CustomerBookingInfo', 
    'RoomPrice',
    'HotelServices',
    'HotelKeysMain',
    'ImagesRef'
]

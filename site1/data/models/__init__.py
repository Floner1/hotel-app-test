# Import all models to make them discoverable by Django
from .hotel import (
    Hotel, 
    CustomerBookingInfo, 
    RoomInfo, 
    RoomPrice,
    Account,
    HotelServices,
    Minibar,
    MinibarPrice,
    Payment
)
from .images import ImagesRef

__all__ = [
    'Hotel', 
    'CustomerBookingInfo', 
    'RoomInfo', 
    'RoomPrice',
    'Account',
    'HotelServices',
    'Minibar',
    'MinibarPrice',
    'Payment',
    'ImagesRef'
]

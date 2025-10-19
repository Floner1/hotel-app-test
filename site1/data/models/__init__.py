# Import all models to make them discoverable by Django
from .hotel import Hotel, CustomerBookingInfo, RoomInfo, RoomPrice
from .images import ImagesRef

__all__ = ['Hotel', 'CustomerBookingInfo', 'RoomInfo', 'RoomPrice', 'ImagesRef']

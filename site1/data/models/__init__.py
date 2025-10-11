# Import all models to make them discoverable by Django
from .hotel import Hotel, CustomerBookingInfo
from .images import ImagesRef

__all__ = ['Hotel', 'CustomerBookingInfo', 'ImagesRef']

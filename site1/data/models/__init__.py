# Import all models to make them discoverable by Django
from .hotel import Hotel, Reservation
from .images import ImagesRef

__all__ = ['Hotel', 'Reservation', 'ImagesRef']

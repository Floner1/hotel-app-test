# Import all models to make them discoverable by Django
from .hotel import (
    User,
    Hotel, 
    CustomerBookingInfo, 
    RoomPrice,
    HotelServices,
    HotelKeysMain,
    CustomerRequest,
    AuditLog
)
from .images import ImagesRef
from .site_content import SiteContent

__all__ = [
    'User',
    'Hotel',
    'CustomerBookingInfo',
    'RoomPrice',
    'HotelServices',
    'HotelKeysMain',
    'CustomerRequest',
    'AuditLog',
    'ImagesRef',
    'SiteContent',
]

# Import all models to make them discoverable by Django
from .hotel import (
    User,
    Hotel,
    CustomerBookingInfo,
    RoomPrice,
    Room,
    RoomAssignment,
    HotelServices,
    AuditLog
)
from .images import ImagesRef
from .site_content import SiteContent
from .email import EmailSubscriber, EmailCampaign, EmailQueue
from .discount import DiscountCode

__all__ = [
    'User',
    'Hotel',
    'CustomerBookingInfo',
    'RoomPrice',
    'Room',
    'RoomAssignment',
    'HotelServices',
    'AuditLog',
    'ImagesRef',
    'SiteContent',
    'EmailSubscriber',
    'EmailCampaign',
    'EmailQueue',
    'DiscountCode',
]

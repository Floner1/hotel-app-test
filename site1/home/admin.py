from django.contrib import admin
from data.models.hotel import Hotel, RoomPrice, HotelServices, CustomerBookingInfo
from data.models.images import ImagesRef

# Register models for Django admin interface
admin.site.register(Hotel)
admin.site.register(RoomPrice)
admin.site.register(HotelServices)
admin.site.register(CustomerBookingInfo)
admin.site.register(ImagesRef)

from django.contrib import admin
from data.models.hotel import Hotel
from data.models.images import ImagesRef

# Register your models here.
admin.site.register(Hotel)
admin.site.register(ImagesRef)

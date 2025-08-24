from data.models.hotel import Hotel
from data.models.images import ImagesRef
import base64

class HotelRepository:
    @staticmethod
    def get_hotel_info():
        return Hotel.objects.first()

class ImageRepository:
    @staticmethod
    def get_all_images():
        images_data = []
        for img in ImagesRef.objects.all():
            image_base64 = base64.b64encode(img.ImageData).decode('utf-8')
            images_data.append({
                'id': img.ImageId,
                'image_data': image_base64
            })
        return images_data

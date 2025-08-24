from data.repos.repositories import HotelRepository, ImageRepository

class HotelService:
    @staticmethod
    def get_hotel_info():
        return HotelRepository.get_hotel_info()

class ImageService:
    @staticmethod
    def get_all_images():
        return ImageRepository.get_all_images()

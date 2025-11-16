from backend.services.services import HotelService

rooms = HotelService.get_available_room_types()
for r in rooms:
    print(f'{r["display"]}: canonical="{r["canonical"]}"')

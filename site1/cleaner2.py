import re
with open('home/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Pattern for hotel setup
text = re.sub(r'# Get hotel name and contact information\s*hotel_name = HotelService\.get_hotel_name\(\)\s*hotel_info = HotelService\.get_hotel_info\(\)', '', text)
text = re.sub(r'# Get hotel services from database\s*hotel_services = HotelServices\.objects\.all\(\)', '', text)

text = re.sub(r'hotel_name = HotelService\.get_hotel_name\(\)\s*hotel_info = HotelService\.get_hotel_info\(\)\s*hotel_services = HotelServices\.objects\.all\(\)', '', text)

text = re.sub(r"'hotel_name':\s*hotel_name,", "", text)
text = re.sub(r"'hotel_info':\s*hotel_info,", "", text)
text = re.sub(r"'hotel':\s*hotel_info,", "", text)
text = re.sub(r"'hotel_services':\s*hotel_services,", "", text)

with open('home/views.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Cleaned views.py dictionary references!")

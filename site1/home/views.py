from django.shortcuts import render
from django.http import JsonResponse
from backend.services.services import HotelService

# Create your views here.
def get_home(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    return render(request, 'home.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info  # For contact info in footer
    })

def get_about(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'about.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info
    })

def get_contact(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'contact.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info
    })


def index(request):
    return render(request,'index.html')

def get_reservation(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'reservation.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info
    })

def get_rooms(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'rooms.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info
    })

def newsletter_signup(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        email = request.POST.get('email', None)
        return JsonResponse({
            'status': 'ok'
        })
    return JsonResponse({'status': 'ok'})
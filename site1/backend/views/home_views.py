from django.shortcuts import render
from django.http import JsonResponse
from backend.services.services import HotelService, ImageService

def get_home(request):
    # Get all images from the database
    images_data = ImageService.get_all_images()
    
    # Get hotel contact information
    hotel_info = HotelService.get_hotel_info()
    
    return render(request, 'home.html', {
        'images': images_data,
        'hotel': hotel_info
    })

def get_about(request):
    return render(request,'about.html')

def get_contact(request):
    # Get hotel contact information
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'contact.html', {'hotel': hotel_info})

def get_events(request):
    return render(request,'events.html')

def index(request):
    return render(request,'index.html')

def get_reservation(request):
    return render(request,'reservation.html')

def get_rooms(request):
    return render(request,'rooms.html')

def newsletter_signup(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        email = request.POST.get('email', None)
        return JsonResponse({
            'status': 'ok'
        })
    return JsonResponse({'status': 'ok'})

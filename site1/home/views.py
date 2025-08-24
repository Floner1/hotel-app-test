from django.shortcuts import render
from django.http import JsonResponse
from .models import Hotel, ImagesRef
import base64

# Create your views here.
def get_home(request):
    # Get all images from the database
    images_data = []
    for img in ImagesRef.objects.all():
        # Convert binary data to base64 string
        image_base64 = base64.b64encode(img.ImageData).decode('utf-8')
        images_data.append({
            'id': img.ImageId,
            'image_data': image_base64
        })
    
    # Get hotel contact information
    hotel_info = Hotel.objects.first()  # Get the first (and presumably only) hotel record
    
    return render(request, 'home.html', {
        'images': images_data,
        'hotel': hotel_info
    })

def get_about(request):
    return render(request,'about.html')

def get_contact(request):
    # Get hotel contact information
    hotel_info = Hotel.objects.first()  # Get the first (and presumably only) hotel record
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
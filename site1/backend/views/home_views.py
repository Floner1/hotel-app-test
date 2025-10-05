# Import necessary Django modules
from django.shortcuts import render  # For rendering templates
from django.http import JsonResponse  # For JSON responses
from backend.services.services import HotelService, ImageService  # Import our service classes

def get_home(request):
    """
    View function for the home page
    Retrieves all images and hotel information to display on the homepage
    """
    # Get all images from the database for the image gallery
    images_data = ImageService.get_all_images()
    
    # Get hotel contact information to display in the footer
    hotel_info = HotelService.get_hotel_info()
    
    # Render the home template with both images and hotel info
    return render(request, 'home.html', {
        'images': images_data,
        'hotel': hotel_info
    })

def get_about(request):
    """
    View function for the about page
    Displays information about the hotel and its staff
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'about.html', {'hotel': hotel_info})

def get_contact(request):
    """
    View function for the contact page
    Shows hotel's contact information and contact form
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'contact.html', {'hotel': hotel_info})

def get_events(request):
    """
    View function for the events page
    Displays hotel's events and functions information
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'events.html', {'hotel': hotel_info})

def index(request):
    """
    View function for the index page
    Alternative landing page
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'index.html', {'hotel': hotel_info})

def get_reservation(request):
    """
    View function for the reservation page
    Handles room booking and reservation form
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'reservation.html', {'hotel': hotel_info})

def get_rooms(request):
    """
    View function for the rooms page
    Displays available room types and their information
    """
    hotel_info = HotelService.get_hotel_info()
    return render(request, 'rooms.html', {'hotel': hotel_info})

def newsletter_signup(request):
    """
    AJAX endpoint for newsletter signup
    Handles the newsletter subscription form submission
    Only processes AJAX POST requests
    """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        email = request.POST.get('email', None)
        # Currently just returns success without actually storing the email
        return JsonResponse({
            'status': 'ok'
        })
    return JsonResponse({'status': 'ok'})

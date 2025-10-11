from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from backend.services.services import HotelService, ReservationService

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

def get_reservation(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        try:
            # Prepare reservation data from form
            reservation_data = {
                'name': request.POST.get('name'),
                'phone': request.POST.get('phone'),
                'email': request.POST.get('email'),
                'checkin_date': request.POST.get('checkin_date'),
                'checkout_date': request.POST.get('checkout_date'),
                'adults': request.POST.get('adults', 1),
                'children': request.POST.get('children', 0),
                'notes': request.POST.get('notes', '')
            }
            
            # Create reservation using the service
            booking = ReservationService.create_reservation(reservation_data)
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Reservation submitted successfully!',
                'booking_id': booking.booking_id
            })
            
        except ValidationError as e:
            # Return validation error response
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
            
        except Exception as e:
            # Return generic error response
            return JsonResponse({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=500)
    
    # Handle GET request (display form)
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
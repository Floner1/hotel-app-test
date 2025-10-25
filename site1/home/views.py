from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from backend.services.services import HotelService, ReservationService
from data.models.hotel import CustomerBookingInfo
from django.db.models import Sum, Q
from datetime import date

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
                'room_type': request.POST.get('room_type'),
                'notes': request.POST.get('notes', '')
            }
            
            # Create reservation using the service
            booking = ReservationService.create_reservation(reservation_data)
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Reservation submitted successfully!',
                'booking_id': booking.booking_id,
                'total_days': booking.total_days,
                'total_cost_amount': booking.total_cost_amount
            })
            
        except ValidationError as e:
            # Log error context for easier debugging
            import traceback
            print('[reservation] validation error:', e)
            print('Traceback:', traceback.format_exc())
            # Return validation error response
            error_message = str(e)
            if hasattr(e, 'message_dict'):
                error_message = '; '.join([f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()])
            elif hasattr(e, 'messages'):
                error_message = '; '.join(e.messages)
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=400)
            
        except Exception as e:
            import traceback
            print('[reservation] unexpected error:', type(e).__name__, str(e))
            print('Traceback:', traceback.format_exc())
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


def admin_reservations(request):
    """
    Admin dashboard view to display all customer reservations.
    Shows statistics and a filterable table of bookings with pagination.
    """
    # Get hotel information
    hotel_info = HotelService.get_hotel_info()
    
    # Get all reservations, ordered by most recent first
    all_reservations = CustomerBookingInfo.objects.all().select_related('hotel')
    
    # Calculate statistics
    today = date.today()
    
    total_reservations = all_reservations.count()
    
    # Check-ins happening today
    today_checkins = all_reservations.filter(checkin_date=today).count()
    
    # Upcoming reservations (check-in date is in the future)
    upcoming_reservations = all_reservations.filter(checkin_date__gt=today).count()
    
    # Calculate total revenue
    total_revenue = all_reservations.aggregate(
        total=Sum('total_cost_amount')
    )['total'] or 0
    
    # Pagination - 10 items per page
    page = request.GET.get('page', 1)
    paginator = Paginator(all_reservations, 10)  # Show 10 reservations per page
    
    try:
        reservations = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        reservations = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        reservations = paginator.page(paginator.num_pages)
    
    # Prepare context data
    context = {
        'hotel': hotel_info,
        'reservations': reservations,
        'total_reservations': total_reservations,
        'today_checkins': today_checkins,
        'upcoming_reservations': upcoming_reservations,
        'total_revenue': total_revenue,
        'today': today,
    }
    
    return render(request, 'admin_reservations.html', context)


def delete_reservation(request, booking_id):
    """
    Delete a reservation by booking_id.
    Only accepts POST requests for security.
    """
    if request.method == 'POST':
        try:
            # Find the booking
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            booking_name = booking.name
            
            # Delete the booking
            booking.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Reservation for {booking_name} (Booking #{booking_id}) has been deleted successfully.'
            })
        except CustomerBookingInfo.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Booking #{booking_id} not found.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)
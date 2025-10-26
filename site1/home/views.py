from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from backend.services.services import HotelService, ReservationService
from data.models.hotel import CustomerBookingInfo, HotelServices
from django.db.models import Sum, Q
from datetime import date

# Create your views here.
def get_home(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    return render(request, 'home.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,  # For contact info in footer
        'hotel_services': hotel_services
    })

def get_about(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    return render(request, 'about.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,
        'hotel_services': hotel_services
    })

def get_contact(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    return render(request, 'contact.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,
        'hotel_services': hotel_services
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
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    # Handle GET request (display form)
    return render(request, 'reservation.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,
        'hotel_services': hotel_services
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


def view_reservation(request, booking_id):
    """
    View detailed information about a specific reservation.
    Returns JSON data for AJAX requests or renders a detail page.
    """
    try:
        # Find the booking
        booking = CustomerBookingInfo.objects.select_related('hotel').get(booking_id=booking_id)
        
        # Prepare booking data
        booking_data = {
            'booking_id': booking.booking_id,
            'name': booking.name,
            'email': booking.email,
            'phone': booking.phone,
            'room_type': booking.room_type,
            'booking_date': booking.booking_date.strftime('%B %d, %Y'),
            'checkin_date': booking.checkin_date.strftime('%B %d, %Y'),
            'checkout_date': booking.checkout_date.strftime('%B %d, %Y'),
            'total_days': booking.total_days,
            'adults': booking.adults,
            'children': booking.children,
            'total_cost_amount': str(booking.total_cost_amount),
            'notes': booking.notes if booking.notes else '',
            'hotel_name': booking.hotel.hotel_name if booking.hotel else 'N/A',
        }
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'booking': booking_data
            })
        
        # Otherwise, return as context for template rendering (optional detail page)
        context = {
            'booking': booking,
            'hotel': HotelService.get_hotel_info(),
        }
        return render(request, 'reservation_detail.html', context)
        
    except CustomerBookingInfo.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f'Booking #{booking_id} not found.'
            }, status=404)
        return render(request, '404.html', status=404)


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


def edit_reservation(request, booking_id):
    """
    Edit an existing reservation.
    Only accepts POST requests with JSON data.
    """
    if request.method == 'POST':
        try:
            import json
            from datetime import datetime
            from decimal import Decimal
            
            # Find the booking
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            
            # Parse JSON data
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['name', 'email', 'phone', 'room_type', 'checkin_date', 'checkout_date', 'adults']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Missing required field: {field}'
                    }, status=400)
            
            # Parse dates
            try:
                checkin_date = datetime.strptime(data['checkin_date'], '%Y-%m-%d').date()
                checkout_date = datetime.strptime(data['checkout_date'], '%Y-%m-%d').date()
            except ValueError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Invalid date format: {str(e)}'
                }, status=400)
            
            # Validate dates
            if checkout_date <= checkin_date:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Check-out date must be after check-in date.'
                }, status=400)
            
            # Calculate new totals
            total_days = (checkout_date - checkin_date).days
            
            # Get room rate and calculate new cost
            try:
                rate = ReservationService._resolve_rate(data['room_type'])
                total_cost = rate * total_days
            except ValidationError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            
            # Update booking fields
            booking.name = data['name'].strip()
            booking.email = data['email'].strip().lower()
            booking.phone = data['phone'].strip()
            booking.room_type = data['room_type'].strip()
            booking.checkin_date = checkin_date
            booking.checkout_date = checkout_date
            booking.adults = int(data['adults'])
            booking.children = int(data.get('children', 0))
            booking.total_days = total_days
            booking.total_cost_amount = total_cost
            booking.notes = data.get('notes', '').strip()
            
            # Save changes
            booking.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Reservation #{booking_id} updated successfully!',
                'booking': {
                    'booking_id': booking.booking_id,
                    'name': booking.name,
                    'total_days': booking.total_days,
                    'total_cost_amount': str(booking.total_cost_amount),
                }
            })
            
        except CustomerBookingInfo.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Booking #{booking_id} not found.'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data.'
            }, status=400)
        except Exception as e:
            import traceback
            print('[edit_reservation] error:', type(e).__name__, str(e))
            print('Traceback:', traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)
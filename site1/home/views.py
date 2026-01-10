from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from backend.services.services import HotelService, ReservationService
from data.models import User, CustomerBookingInfo, HotelServices
from django.db.models import Sum, Q
from datetime import date

# Helper function to check if user is admin/staff
def is_staff_or_admin(user):
    """Check if user has staff or admin role."""
    if not user.is_authenticated:
        return False
    # Use the new role-based system
    return hasattr(user, 'role') and user.role in ['admin', 'staff']

# Create your views here.
def get_home(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    # Get available room types with pricing from database
    room_types = HotelService.get_available_room_types()
    
    return render(request, 'home.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,  # For contact info in footer
        'hotel_services': hotel_services,
        'room_types': room_types
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
    
    # Handle POST request (form submission) - requires login
    if request.method == 'POST':
        # Check if user is logged in before processing reservation
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'Please log in to make a reservation',
                'redirect': '/accounts/login/?next=/reservation/'
            }, status=401)
        
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
                'notes': request.POST.get('notes', ''),
                'user': request.user,  # Link booking to logged-in user
            }
            
            # Create reservation using the service
            booking = ReservationService.create_reservation(reservation_data)
            
            # Calculate total days
            from datetime import datetime
            checkin = datetime.strptime(request.POST.get('checkin_date'), '%m/%d/%Y').date()
            checkout = datetime.strptime(request.POST.get('checkout_date'), '%m/%d/%Y').date()
            total_days = (checkout - checkin).days
            # For same-day bookings, display as 1 day
            if total_days == 0:
                total_days = 1
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Reservation submitted successfully!',
                'booking_id': booking.booking_id,
                'total_days': total_days,
                'total_cost_amount': str(booking.total_price)
            })
            
        except ValidationError as e:
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
            # Return generic error response
            return JsonResponse({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=500)
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    # Get available room types from database
    room_types = HotelService.get_available_room_types()
    
    # Handle GET request (display form)
    return render(request, 'reservation.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,
        'hotel_services': hotel_services,
        'room_types': room_types
    })

def get_rooms(request):
    # Get hotel name and contact information
    hotel_name = HotelService.get_hotel_name()
    hotel_info = HotelService.get_hotel_info()
    
    # Get hotel services from database
    hotel_services = HotelServices.objects.all()
    
    # Get available room types with pricing from database
    room_types = HotelService.get_available_room_types()
    
    return render(request, 'rooms.html', {
        'hotel_name': hotel_name,
        'hotel': hotel_info,
        'hotel_services': hotel_services,
        'room_types': room_types
    })

def newsletter_signup(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        email = request.POST.get('email', None)
        return JsonResponse({
            'status': 'ok'
        })
    return JsonResponse({'status': 'ok'})


def login_view(request):
    """
    Custom login view that logs in the user and shows a success message.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Set SQL Server session context for RBAC triggers
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("EXEC sp_set_session_context 'user_id', %s", [user.id])
                    cursor.execute("EXEC sp_set_session_context 'user_role', %s", [user.role])
                
                messages.success(request, 'You have been successfully logged in.')
                # Redirect to next parameter or home
                next_url = request.POST.get('next') or request.GET.get('next') or 'home'
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    """
    Custom logout view that logs out the user and redirects to home page.
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')


def register_view(request):
    """
    Registration view for creating new customer accounts.
    """
    if request.user.is_authenticated:
        # Redirect if already logged in
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Validation
        errors = {}
        
        if not username:
            errors['username'] = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username already exists.'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters.'
        
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'Email already registered.'
        elif '@' not in email:
            errors['email'] = 'Enter a valid email address.'
        
        if not password1:
            errors['password1'] = 'Password is required.'
        elif len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters.'
        
        if not password2:
            errors['password2'] = 'Please confirm your password.'
        elif password1 != password2:
            errors['password2'] = 'Passwords do not match.'
        
        if errors:
            # Return form with errors
            context = {
                'form': {
                    'username': {'value': username, 'errors': [errors.get('username')]},
                    'email': {'value': email, 'errors': [errors.get('email')]},
                    'password1': {'errors': [errors.get('password1')]},
                    'password2': {'errors': [errors.get('password2')]},
                },
                'hotel_name': HotelService.get_hotel_name(),
                'hotel': HotelService.get_hotel_info(),
            }
            return render(request, 'register.html', context)
        
        # Create user
        try:
            from django.utils import timezone
            from django.contrib.auth.hashers import make_password
            
            user = User.objects.create(
                username=username,
                email=email,
                password_hash=make_password(password1),
                role='customer',
                is_active=True,
                created_at=timezone.now()
            )
            
            # Log the user in - specify backend since we have multiple
            login(request, user, backend='home.auth_backend.CustomUserBackend')
            messages.success(request, f'Welcome {username}! Your account has been created successfully.')
            return redirect('reservation')
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            context = {
                'form': {
                    'username': {'value': username},
                    'email': {'value': email},
                },
                'hotel_name': HotelService.get_hotel_name(),
                'hotel': HotelService.get_hotel_info(),
            }
            return render(request, 'register.html', context)
    
    # GET request
    context = {
        'form': {},
        'hotel_name': HotelService.get_hotel_name(),
        'hotel': HotelService.get_hotel_info(),
    }
    return render(request, 'register.html', context)


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def admin_reservations(request):
    """
    Admin dashboard view to display all customer reservations.
    Shows statistics and a filterable table of bookings with pagination.
    Requires user to be logged in and have staff/admin role.
    """
    # Get hotel information
    hotel_info = HotelService.get_hotel_info()
    
    # Get available room types from database
    room_types = HotelService.get_available_room_types()
    
    # Get all reservations, ordered by most recent first
    all_reservations = CustomerBookingInfo.objects.all().select_related('hotel')
    
    # Calculate statistics
    today = date.today()
    
    total_reservations = all_reservations.count()
    
    # Check-ins happening today
    today_checkins = all_reservations.filter(check_in=today).count()
    
    # Check-outs happening today
    today_checkouts = all_reservations.filter(check_out=today).count()
    
    # Upcoming reservations (check-in date is in the future)
    upcoming_reservations = all_reservations.filter(check_in__gt=today).count()
    
    # Currently checked in (check-in date is today or past, check-out date is today or future)
    currently_checked_in = all_reservations.filter(
        check_in__lte=today,
        check_out__gte=today
    ).count()
    
    # Calculate total revenue
    total_revenue = all_reservations.aggregate(
        total=Sum('total_price')
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
        'today_checkouts': today_checkouts,
        'currently_checked_in': currently_checked_in,
        'upcoming_reservations': upcoming_reservations,
        'total_revenue': total_revenue,
        'today': today,
        'room_types': room_types,
    }
    
    return render(request, 'admin_reservations.html', context)


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def view_reservation(request, booking_id):
    """
    View detailed information about a specific reservation.
    Returns JSON data for AJAX requests or renders a detail page.
    Requires user to be logged in and have staff/admin role.
    """
    try:
        # Find the booking
        booking = CustomerBookingInfo.objects.select_related('hotel').get(booking_id=booking_id)
        
        # Calculate total days
        total_days = (booking.check_out - booking.check_in).days
        
        # Prepare booking data
        booking_data = {
            'booking_id': booking.booking_id,
            'name': booking.guest_name,
            'email': booking.email if booking.email else '',
            'phone': booking.phone if booking.phone else '',
            'room_type': booking.room_type,
            'booking_date': booking.booking_date.strftime('%B %d, %Y'),
            'checkin_date': booking.check_in.strftime('%B %d, %Y'),
            'checkout_date': booking.check_out.strftime('%B %d, %Y'),
            'total_days': total_days,
            'adults': booking.adults,
            'children': booking.children if booking.children else 0,
            'booked_rate': str(booking.booked_rate),
            'total_cost_amount': str(booking.total_price),
            'status': booking.status,
            'payment_status': booking.payment_status,
            'amount_paid': str(booking.amount_paid),
            'special_requests': booking.special_requests if booking.special_requests else '',
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


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def delete_reservation(request, booking_id):
    """
    Delete a reservation by booking_id.
    Only accepts POST requests for security.
    Requires user to be logged in and have staff/admin role.
    """
    if request.method == 'POST':
        try:
            # Find the booking
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            booking_name = booking.guest_name
            
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


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def edit_reservation(request, booking_id):
    """
    Edit an existing reservation.
    Only accepts POST requests with JSON data.
    Requires user to be logged in and have staff/admin role.
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
            required_fields = ['name', 'checkin_date', 'checkout_date', 'adults', 'room_type']
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
            if checkout_date < checkin_date:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Check-out date cannot be before check-in date.'
                }, status=400)
            
            # Calculate new totals
            total_days = (checkout_date - checkin_date).days
            # For same-day bookings, charge for at least 1 day
            if total_days == 0:
                total_days = 1
            
            # Get room rate for the selected room type
            try:
                canonical_room_type = ReservationService._canonicalise_room_type(data['room_type'])
                if not canonical_room_type:
                    raise ValidationError('Invalid room type selected.')
                rate = ReservationService._resolve_rate(data['room_type'])
                total_cost = rate * total_days
            except ValidationError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            
            # Prepare new email value
            new_email = data.get('email', '').strip() if data.get('email') else None
            
            # Update booking fields
            booking.guest_name = data['name'].strip()
            booking.email = new_email
            booking.phone = data.get('phone', '').strip() if data.get('phone') else None
            booking.room_type = canonical_room_type
            booking.check_in = checkin_date
            booking.check_out = checkout_date
            booking.adults = int(data['adults'])
            booking.children = int(data.get('children', 0))
            booking.booked_rate = rate
            booking.total_price = total_cost
            booking.special_requests = data.get('special_requests', '').strip() if data.get('special_requests') else None
            booking.notes = data.get('notes', '').strip() if data.get('notes') else None
            
            # Update timestamp
            from django.utils import timezone
            booking.updated_at = timezone.now()
            
            # Update status if provided
            if 'status' in data:
                booking.status = data['status']
            if 'payment_status' in data:
                booking.payment_status = data['payment_status']
            if 'amount_paid' in data:
                booking.amount_paid = Decimal(str(data['amount_paid']))
            
            # Save changes
            booking.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Reservation #{booking_id} updated successfully!',
                'booking': {
                    'booking_id': booking.booking_id,
                    'name': booking.guest_name,
                    'total_days': total_days,
                    'total_cost_amount': str(booking.total_price),
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
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)
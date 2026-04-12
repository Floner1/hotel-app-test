from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django_ratelimit.decorators import ratelimit
from backend.services.services import HotelService, ReservationService, RoomService
from data.models import User, CustomerBookingInfo
from django.db.models import Sum
from datetime import date, datetime
import logging
from home.audit import log_booking_create, log_booking_update, log_booking_delete, log_user_login

logger = logging.getLogger(__name__)

def is_admin(user):
    """Check if user has admin role."""
    if not user.is_authenticated:
        return False
    return hasattr(user, 'role') and user.role == 'admin'

def is_staff_or_admin(user):
    """Check if user has staff or admin role."""
    if not user.is_authenticated:
        return False
    # Use the new role-based system
    return hasattr(user, 'role') and user.role in ['admin', 'staff']

def _can_manage_target(request_user, target_user=None, target_role=None):
    """Enforce role hierarchy: admin manages all, staff manages only customers."""
    effective_role = target_role or (target_user.role if target_user else 'customer')
    if request_user.role == 'admin':
        return True, None
    if effective_role in ('staff', 'admin'):
        return False, 'You do not have permission to manage staff or admin accounts.'
    return True, None

def _db_image_exists(name):
    """Return True if an image with this name exists in the DB."""
    try:
        from data.models.images import ImagesRef
        return ImagesRef.objects.filter(ImageName=name).exists()
    except Exception:
        return False


def _db_images_exist(names):
    """Batch-check which image names exist in the DB. Returns a dict {name: bool}."""
    try:
        from data.models.images import ImagesRef
        existing = set(
            ImagesRef.objects.filter(ImageName__in=names)
            .values_list('ImageName', flat=True)
        )
        return {name: name in existing for name in names}
    except Exception:
        return {name: False for name in names}











def _room_image_url(db_key, static_path):
    """Return serve_image URL if uploaded to DB, otherwise the static file URL."""
    from django.urls import reverse
    from django.templatetags.static import static
    if _db_image_exists(db_key):
        return reverse('serve_image', args=[db_key])
    return static(static_path)


def _get_room_images():
    """Return resolved URLs for all 5 room images."""
    return {
        'single_bed': _room_image_url('room-single-bed', 'images/single bed.png'),
        'double':     _room_image_url('room-double',      'images/double room.png'),
        'window':     _room_image_url('room-window',      'images/window room.png'),
        'balcony':    _room_image_url('room-balcony',     'images/balcony.png'),
        'condotel':   _room_image_url('room-condotel',    'images/condotel.png'),
    }


# Create your views here.
def get_home(request):
    

    

    # Get available room types with pricing from database
    room_types = HotelService.get_available_room_types()

    # Resolve image sources: DB if uploaded, otherwise mark as static fallback
    db_images = _db_images_exist(['hero', 'food-1', 'img-1', 'reserve-bg'])
    db_images = {
        'hero':       db_images.get('hero', False),
        'food_1':     db_images.get('food-1', False),
        'img_1':      db_images.get('img-1', False),
        'reserve_bg': db_images.get('reserve-bg', False),
    }

    return render(request, 'home.html', {
        'active_page': 'home',
        
        
        
        'room_types': room_types,
        'db_images': db_images,
        'room_images': _get_room_images(),
        })

def get_about(request):
    
    
    
    
    # Resolve image sources: DB if uploaded, otherwise static
    db_images = _db_images_exist(['food-1', 'img-1'])
    db_images = {
        'food_1': db_images.get('food-1', False),
        'img_1':  db_images.get('img-1', False),
    }

    return render(request, 'about.html', {
        'active_page': 'about',
        
        
        
        'db_images': db_images,
        })

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def get_contact(request):
    

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, 'Please fill in Name, Email and Message fields.')
        else:
            logger.info('Contact form submission from %s <%s>', name, email)
            messages.success(request, 'Your message has been sent. We will get back to you soon!')
            return redirect('contact')

    return render(request, 'contact.html', {
        'active_page': 'contact',
        
        
        
        })

@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def get_reservation(request):
    
    
    # Handle POST request (form submission) - requires login
    if request.method == 'POST':
        # Check if user is logged in before processing reservation
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'You need to be logged into an account to book a room. Please log in or create an account to continue.'
            }, status=400)
        
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

            # Allow staff/admin to override the per-night rate
            custom_price = request.POST.get('custom_price')
            if custom_price and request.user.is_staff:
                reservation_data['custom_rate'] = custom_price
            
            # Create reservation using the service
            booking = ReservationService.create_reservation(reservation_data)
            
            # Audit log
            log_booking_create(request.user, booking, request)

            # Calculate total days
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
            logger.exception('Reservation creation failed')
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=500)
    
    
    
    # Get available room types from database
    room_types = HotelService.get_available_room_types()
    
    # Handle GET request (display form)
    return render(request, 'reservation.html', {
        'active_page': 'reservation',
        
        
        
        'room_types': room_types
    })

def get_rooms(request):
    
    
    
    
    # Get available room types with pricing from database
    room_types = HotelService.get_available_room_types()
    
    return render(request, 'rooms.html', {
        'active_page': 'rooms',
        
        
        
        'room_types': room_types,
        'room_images': _get_room_images(),
        })

@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def newsletter_signup(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        email = request.POST.get('email', '').strip()
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'Please provide a valid email address.'}, status=400)
        logger.info('Newsletter signup: %s', email)
        return JsonResponse({'status': 'ok', 'message': 'Thank you for subscribing!'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
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
                log_user_login(user, request)
                
                # Set SQL Server session context for RBAC triggers
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("EXEC sp_set_session_context @key=N'user_id', @value=%s", [str(user.id)])
                    cursor.execute("EXEC sp_set_session_context @key=N'user_role', @value=%s", [user.role])
                
                messages.success(request, 'You have been successfully logged in.')
                # Redirect to next parameter or home (validate to prevent open redirect)
                from django.utils.http import url_has_allowed_host_and_scheme
                next_url = request.POST.get('next') or request.GET.get('next') or 'home'
                if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    next_url = 'home'
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


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
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
                'active_page': 'register',
                'form': {
                    'username': {'value': username, 'errors': [errors['username']] if 'username' in errors else []},
                    'email': {'value': email, 'errors': [errors['email']] if 'email' in errors else []},
                    'password1': {'errors': [errors['password1']] if 'password1' in errors else []},
                    'password2': {'errors': [errors['password2']] if 'password2' in errors else []},
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
            logger.exception('User registration failed')
            messages.error(request, 'An error occurred during registration. Please try again.')
            context = {
                'active_page': 'register',
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
    HotelService.get_hotel_info()
    
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
def room_dashboard(request):
    """Room status dashboard showing all physical rooms grouped by floor."""
    from data.models import Room, RoomAssignment

    # Handle status update via POST (staff/admin changes a room's status)
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        new_status = request.POST.get('new_status') # backwards-compatibility
        
        if room_id and new_status:
            try:
                room = Room.objects.get(room_id=room_id)
                if new_status == 'vacant':
                    room.reservation_status = 'vacant'
                    room.housekeeping_status = 'clean'
                elif new_status == 'empty_dirty': # keeping old mappings
                    room.reservation_status = 'vacant'
                    room.housekeeping_status = 'dirty'
                elif new_status == 'occupied':
                    room.reservation_status = 'occupied'
                elif new_status == 'reserved':
                    room.reservation_status = 'reserved'
                elif new_status == 'out_of_order':
                    room.housekeeping_status = 'out_of_order'
                room.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok'})
                messages.success(request, f'Room {room.room_code} updated status.')
            except Room.DoesNotExist:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Room not found.'}, status=404)
                messages.error(request, 'Room not found.')
        return redirect('room_dashboard')

    # Build room data with active assignments
    rooms = Room.objects.select_related('hotel').order_by('floor_number', 'room_number')

    # Pre-fetch active assignments with their bookings
    active_assignments = RoomAssignment.objects.filter(
        status='active'
    ).select_related('booking', 'room')

    assignment_map = {}
    for a in active_assignments:
        assignment_map[a.room_id] = a

    # Group rooms by floor
    floors = {}
    status_counts = {
        'vacant': 0, 'occupied': 0, 'out_of_order': 0, 'reserved': 0,
    }
    for room in rooms:
        assignment = assignment_map.get(room.room_id)
        duration = None
        if assignment:
            duration = (assignment.check_out - assignment.check_in).days

        room_data = {
            'room': room,
            'assignment': assignment,
            'duration': duration,
        }
        floors.setdefault(room.floor_number, []).append(room_data)
        
        # Mapping to old format for UI rendering
        disp_status = room.reservation_status # defaults to vacant/occupied/reserved
        if room.housekeeping_status == 'out_of_order':
            disp_status = 'out_of_order'
        status_counts[disp_status] = status_counts.get(disp_status, 0) + 1

    # Active filter from query string
    status_filter = request.GET.get('status', 'all')

    context = {
        'floors': dict(sorted(floors.items())),
        'status_counts': status_counts,
        'total_rooms': len(rooms),
        'status_filter': status_filter,
        'hotel': HotelService.get_hotel_info(),
    }
    return render(request, 'room_dashboard.html', context)


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
        
        # Non-AJAX: redirect to the reservations dashboard
        return redirect('admin_reservations')
        
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
            booking = CustomerBookingInfo.objects.select_related('hotel', 'user').get(booking_id=booking_id)
            booking_name = booking.guest_name
            booking_data = {
                'guest_name': booking.guest_name,
                'room_type': booking.room_type,
                'check_in': str(booking.check_in),
                'check_out': str(booking.check_out),
                'total_price': str(booking.total_price),
            }

            # Delete the booking
            booking.delete()
            log_booking_delete(request.user, booking_id, booking_data, request)
            
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
            logger.exception('Reservation deletion failed for #%s', booking_id)
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred while deleting the reservation.'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)

@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def manage_accounts(request):
    """View to manage user accounts (CRUD operations)."""
    HotelService.get_hotel_info()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            is_staff = request.POST.get('is_staff') == 'true'

            # Role hierarchy check: staff cannot create staff/admin accounts
            new_role = 'staff' if is_staff else 'customer'
            allowed, err_msg = _can_manage_target(request.user, target_role=new_role)
            if not allowed:
                messages.error(request, err_msg)
                return redirect('manage_accounts')

            try:
                from django.utils import timezone
                # Create new user
                user = User(
                    username=username,
                    email=email,
                    role=new_role,
                    created_at=timezone.now(),
                    is_active=True
                )
                user.set_password(password)
                user.save()
                messages.success(request, f'Account "{username}" created successfully!')
            except Exception as e:
                logger.exception('Account creation failed')
                messages.error(request, 'An error occurred while creating the account.')

        elif action == 'edit':
            account_id = request.POST.get('account_id')
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            is_staff = request.POST.get('is_staff') == 'true'

            try:
                user = User.objects.get(user_id=account_id)

                # Prevent staff from editing staff/admin accounts
                allowed, err_msg = _can_manage_target(request.user, target_user=user)
                if not allowed:
                    messages.error(request, err_msg)
                    return redirect('manage_accounts')

                # Prevent role escalation: staff cannot set role to staff/admin
                new_role = 'staff' if is_staff else 'customer'
                allowed, err_msg = _can_manage_target(request.user, target_role=new_role)
                if not allowed:
                    messages.error(request, err_msg)
                    return redirect('manage_accounts')

                user.username = username
                user.email = email
                user.role = new_role

                # Only update password if provided
                if password:
                    user.set_password(password)

                user.save()
                messages.success(request, f'Account "{username}" updated successfully!')
            except User.DoesNotExist:
                messages.error(request, 'Account not found.')
            except Exception as e:
                logger.exception('Account update failed for #%s', account_id)
                messages.error(request, 'An error occurred while updating the account.')

        elif action == 'delete':
            account_id = request.POST.get('account_id')

            try:
                user = User.objects.get(user_id=account_id)

                # Prevent self-deletion
                if user.user_id == request.user.user_id:
                    messages.error(request, 'You cannot delete your own account.')
                    return redirect('manage_accounts')

                # Prevent staff from deleting staff/admin accounts
                allowed, err_msg = _can_manage_target(request.user, target_user=user)
                if not allowed:
                    messages.error(request, err_msg)
                    return redirect('manage_accounts')

                username = user.username
                user.delete()
                messages.success(request, f'Account "{username}" deleted successfully!')
            except User.DoesNotExist:
                messages.error(request, 'Account not found.')
            except Exception as e:
                logger.exception('Account deletion failed for #%s', account_id)
                messages.error(request, 'An error occurred while deleting the account.')
        
        return redirect('manage_accounts')
    
    # GET request - display accounts based on role hierarchy
    if request.user.role == 'admin':
        accounts = User.objects.filter(is_active=True).order_by('-created_at')
    else:
        accounts = User.objects.filter(is_active=True, role='customer').order_by('-created_at')
    
    return render(request, 'manage_accounts.html', {
        
        'accounts': accounts
    })

@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def upload_image(request):
    """Handle image upload for admin users — saves binary data to the ImagesRef DB table."""
    if request.method == 'POST':
        try:
            from PIL import Image
            from io import BytesIO
            from data.models.images import ImagesRef

            image_file = request.FILES.get('image')
            image_id = request.POST.get('image_id')

            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'No image file provided'}, status=400)

            if not image_id:
                return JsonResponse({'status': 'error', 'message': 'No image ID provided'}, status=400)

            # Validate file size (5 MB)
            if image_file.size > 5 * 1024 * 1024:
                return JsonResponse({'status': 'error', 'message': 'File size must be less than 5MB'}, status=400)

            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if image_file.content_type not in allowed_types:
                return JsonResponse({'status': 'error', 'message': 'Invalid file type. Only JPG, PNG, and GIF are allowed'}, status=400)

            # Open, convert, and compress with Pillow
            img = Image.open(image_file)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode in ('P', 'LA'):
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1])
                img = background

            buffer = BytesIO()
            img.save(buffer, 'JPEG', quality=85, optimize=True)
            image_bytes = buffer.getvalue()

            # Upsert: update if name exists, otherwise insert
            obj, created = ImagesRef.objects.update_or_create(
                ImageName=image_id,
                defaults={
                    'ImageData': image_bytes,
                    'ImageContentType': 'image/jpeg',
                }
            )

            return JsonResponse({
                'status': 'success',
                'message': f'Image "{image_id}" saved to database successfully!',
            })

        except Exception as e:
            logger.exception('Image upload failed')
            return JsonResponse({'status': 'error', 'message': 'Image upload failed. Please try again.'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)


def serve_image(request, image_name):
    """Serve an image stored as binary in the ImagesRef table."""
    from django.http import HttpResponse, Http404
    from data.models.images import ImagesRef
    try:
        img = ImagesRef.objects.get(ImageName=image_name)
        return HttpResponse(bytes(img.ImageData), content_type=img.ImageContentType)
    except ImagesRef.DoesNotExist:
        raise Http404


@login_required
@user_passes_test(is_admin, login_url='/accounts/login/')
def save_content(request):
    """Save a site content value to the DB (any key allowed for inline editing).
    If a 'db_key' is also provided, the value is saved under that key too
    (for elements originally rendered from {{ ct.xxx }} template variables)."""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            key   = data.get('key', '').strip()
            value = data.get('value', '').strip()
            db_key = data.get('db_key', '').strip()   # optional original DB key
            if not key:
                return JsonResponse({'status': 'error', 'message': 'No key provided'}, status=400)
            if len(key) > 100:
                return JsonResponse({'status': 'error', 'message': 'Key too long'}, status=400)
            from data.models.site_content import SiteContent
            # Save the page-level override key
            SiteContent.objects.update_or_create(
                content_key=key,
                defaults={'content_value': value}
            )
            # Also save to the original DB key if provided
            if db_key and len(db_key) <= 100:
                SiteContent.objects.update_or_create(
                    content_key=db_key,
                    defaults={'content_value': value}
                )
            return JsonResponse({'status': 'success', 'value': value})
        except Exception as e:
            logger.exception('Content save failed')
            return JsonResponse({'status': 'error', 'message': 'An error occurred while saving content.'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)


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
            booking = CustomerBookingInfo.objects.select_related('hotel', 'user').get(booking_id=booking_id)

            # Capture old data for audit
            old_status = booking.status
            old_data = {
                'guest_name': booking.guest_name,
                'room_type': booking.room_type,
                'check_in': str(booking.check_in),
                'check_out': str(booking.check_out),
                'total_price': str(booking.total_price),
            }

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
                rate = ReservationService._resolve_rate(canonical_room_type)
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

            # Handle room allocation on status transitions
            new_status = booking.status
            if new_status != old_status:
                try:
                    from django.core.exceptions import ValidationError
                    if new_status == 'confirmed':
                        RoomService.allocate_room(booking, assigned_by=request.user)
                    elif new_status == 'checked_in':
                        RoomService.check_in_room(booking)
                    elif new_status == 'checked_out':
                        RoomService.check_out_room(booking)
                    elif new_status in ('cancelled', 'rejected'):
                        RoomService.deallocate_room(booking)
                except ValidationError as room_err:
                    # No rooms available — roll back the status change
                    booking.status = old_status
                    booking.save()
                    return JsonResponse({
                        'status': 'error',
                        'message': str(room_err),
                    }, status=400)

            log_booking_update(request.user, booking, old_data, request)
            
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
            logger.exception('Reservation edit failed for #%s', booking_id)
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred while updating the reservation.'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)

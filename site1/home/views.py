from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django_ratelimit.core import get_usage
from django_ratelimit.decorators import ratelimit
from backend.services.services import HotelService, ReservationService, RoomService, EmailService, DiscountService, ChatService
from data.models import User, CustomerBookingInfo
from data.models.hotel import BookingStatus
from data.repos.repositories import DiscountRepository, HotelRepository, RoomMaintenanceRepository
from backend.services.ai_providers import ProviderBusy, model_slot
from django.db import IntegrityError
from django.db.models import Sum
from datetime import date, datetime
import logging
from home.audit import log_booking_create, log_booking_update, log_booking_delete, log_user_login

logger = logging.getLogger(__name__)

# Derived, not restated. The list lives on the model (data/models/hotel.py) so
# this check and the model field cannot drift apart. The DB's chk_booking_status
# constraint is still a separate artefact and must be ALTERed by hand to match.
BOOKING_STATUSES = set(BookingStatus.values)

# Free text from a staff form into an NVARCHAR(MAX) column. The column will take
# anything; the form should not.
MAX_ISSUE_DESCRIPTION = 1000

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

def _milestone_booking_number(user):
    """Which booking number the guest's next stay would be, for loyalty.

    Cancelled and rejected bookings are excluded because neither is a stay the
    guest ever took. Counting them let anyone book and cancel twice, then take
    10% off the third, which is the discount the milestone exists to reward.

    Both milestone counts in get_reservation go through here. They have to
    agree: the first decides whether to interrupt and offer the discount, the
    second decides whether it comes off the price, and a guest offered one and
    then charged full rate is a worse bug than either count alone.
    """
    return CustomerBookingInfo.objects.filter(user=user).exclude(
        status__in=(BookingStatus.CANCELLED, BookingStatus.REJECTED)
    ).count() + 1

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











def _get_room_images():
    """Return resolved URLs for all 5 room images, in one query.

    This runs on /, /about/ and /rooms/, so it goes through the batched
    _db_images_exist() rather than one EXISTS per room type.
    """
    from django.urls import reverse
    from django.templatetags.static import static
    sources = {
        'single_bed': ('room-single-bed', 'images/single bed.png'),
        'double':     ('room-double',      'images/double room.png'),
        'window':     ('room-window',      'images/window room.png'),
        'balcony':    ('room-balcony',     'images/balcony.png'),
        'condotel':   ('room-condotel',    'images/condotel.png'),
    }
    in_db = _db_images_exist([db_key for db_key, _ in sources.values()])
    return {
        key: reverse('serve_image', args=[db_key]) if in_db[db_key] else static(static_path)
        for key, (db_key, static_path) in sources.items()
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
        'room_images': _get_room_images(),
        })

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def get_contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, 'Please fill in Name, Email and Message fields.')
        else:
            logger.info('Contact form submission from %s <%s>', name, email)
            try:
                EmailService.queue_contact_receipt(name=name, email=email, message=message)
            except Exception:
                logger.exception('queue_contact_receipt failed')
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
                'user': request.user,
                'discount_code': request.POST.get('discount_code', '').strip().upper(),
            }

            # Allow staff/admin to override the per-night rate
            custom_price = request.POST.get('custom_price')
            if custom_price and request.user.is_staff:
                reservation_data['custom_rate'] = custom_price
            
            # Milestone check: intercept before booking if this is a loyalty milestone
            # and the guest hasn't yet decided whether to redeem it.
            #
            # This first count is deliberately unlocked. It only decides whether
            # to interrupt and ask the guest, and nothing is written on that
            # path, so a stale answer costs nothing.
            milestone_decision = request.POST.get('milestone_decision', '')
            if not milestone_decision:
                provisional_number = _milestone_booking_number(request.user)
                if provisional_number % 3 == 0:
                    return JsonResponse({
                        'status': 'milestone_check',
                        'booking_number': provisional_number,
                    })

            # Past here a booking gets written, so the count that decides the
            # discount is taken under a lock on the guest's own row and stays in
            # the same transaction as the booking it gates. Unlocked, two
            # bookings from one guest around their third both read the same
            # count, both compute booking number three, and both take 10% off.
            # The lock goes on the user row because there is no row to lock for
            # a booking that does not exist yet.
            from django.db import transaction
            with transaction.atomic():
                User.objects.select_for_update().filter(pk=request.user.pk).first()
                milestone_booking_number = _milestone_booking_number(request.user)

                if milestone_decision == 'redeem' and milestone_booking_number % 3 == 0:
                    reservation_data['milestone_discount_percent'] = 10

                # Create reservation using the service, inside the same block so
                # the lock is still held when the row lands.
                booking = ReservationService.create_reservation(reservation_data)

            # Audit log
            log_booking_create(request.user, booking, request)

            # Total days off the dates the service parsed and stored, not off
            # the raw POST. This used to re-parse the request strings with a
            # single hard-coded '%m/%d/%Y', while ReservationService._parse_date
            # accepts six formats. Any of the other five raised ValueError here,
            # which is not a ValidationError, so the catch-all below answered
            # 500 for a booking that had already committed and been emailed.
            total_days = (booking.check_out - booking.check_in).days
            # For same-day bookings, display as 1 day
            if total_days == 0:
                total_days = 1

            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Reservation submitted successfully!',
                'booking_id': booking.booking_id,
                'total_days': total_days,
                'total_cost_amount': str(booking.total_price),
                'milestone_applied': milestone_decision == 'redeem',
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
        from django.core.validators import validate_email as _validate_email
        from django.core.exceptions import ValidationError as _VE
        from data.repos.repositories import EmailRepository
        email = request.POST.get('email', '').strip().lower()
        try:
            _validate_email(email)
        except _VE:
            return JsonResponse({'status': 'error', 'message': 'Please provide a valid email address.'}, status=400)

        user = request.user if request.user.is_authenticated else None
        source = request.POST.get('source', 'footer_signup')
        if source not in ('footer_signup', 'popup'):
            source = 'footer_signup'

        try:
            subscriber, sub_created = EmailRepository.create_subscriber(
                email=email, user=user, source=source
            )
        except Exception:
            logger.exception('Newsletter signup persist failed for %s', email)
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong saving your subscription. Please try again.'
            }, status=500)

        if subscriber is None:
            return JsonResponse({'status': 'error', 'message': 'Please provide a valid email address.'}, status=400)

        try:
            discount, code_created = DiscountService.issue_for_subscriber(subscriber, email)
        except Exception:
            logger.exception('Discount issue failed for %s', email)
            discount, code_created = None, False

        if discount and code_created:
            try:
                EmailService.queue_welcome_discount(subscriber, discount)
            except Exception:
                logger.exception('queue_welcome_discount failed for %s', email)

        if discount:
            # The code goes out by email only. newsletter-discount-plan.md's
            # implementation note C1 rejected re-displaying it, and neither the
            # popup nor the footer handler reads a 'code' key, so returning one
            # only put it on the wire.
            if code_created:
                msg = 'Subscribed! Your 10% discount code is on its way to your inbox.'
            else:
                msg = 'You are already subscribed. Check your inbox for the original email.'
            return JsonResponse({
                'status': 'ok',
                'message': msg,
                'already': not code_created,
            })

        msg = 'Thank you for subscribing!' if sub_created else 'You are already subscribed — thank you!'
        return JsonResponse({'status': 'ok', 'message': msg})
    return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def validate_discount_code(request):
    """AJAX endpoint: check whether a code is valid for a given email (no redemption)."""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from data.repos.repositories import DiscountRepository
        code = request.POST.get('code', '').strip()
        if not code:
            return JsonResponse({'valid': False, 'message': 'Code is required.'}, status=400)
        # No email means the binding cannot be checked. Answering 'valid' here
        # would promise a discount that create_reservation then refuses, so
        # this fails closed rather than optimistically.
        email = request.POST.get('email', '').strip()
        if not email:
            return JsonResponse({
                'valid': False,
                'message': 'Enter the email address you are booking with to check this code.',
            })
        disc = DiscountRepository.get_by_code(code)
        try:
            DiscountService.validate(disc, email)
        except ValidationError as exc:
            return JsonResponse({'valid': False, 'message': exc.message})
        return JsonResponse({
            'valid': True,
            'discount_percent': disc.discount_percent,
            'message': f'{disc.discount_percent}% discount applied.',
        })
    return JsonResponse({'valid': False, 'message': 'Invalid request.'}, status=400)


def unsubscribe_view(request, token):
    """Token-based unsubscribe. GET shows a confirm screen; POST acts."""
    from data.repos.repositories import EmailRepository
    subscriber = EmailRepository.get_by_token(token)
    if not subscriber:
        return render(request, 'email/unsubscribe.html', {'status': 'invalid'}, status=404)

    if subscriber.status == 'unsubscribed':
        return render(request, 'email/unsubscribe.html', {
            'status': 'already_unsubscribed',
            'subscriber': subscriber,
        })

    if request.method == 'POST':
        EmailRepository.unsubscribe(subscriber)
        return render(request, 'email/unsubscribe.html', {
            'status': 'unsubscribed',
            'subscriber': subscriber,
        })

    return render(request, 'email/unsubscribe.html', {
        'status': 'confirm',
        'subscriber': subscriber,
    })


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    """
    Custom login view that logs in the user and shows a success message.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # AuthenticationForm.clean() already ran authenticate(request, ...) with
            # the request, so django-axes recorded the attempt and can enforce
            # per-username lockout. Reuse that cached user instead of a second,
            # request-less authenticate() call (which axes cannot track).
            user = form.get_user()
            if user is not None:
                # Block self-signup accounts that haven't verified their email.
                # is_verified defaults True, so existing and admin-created accounts
                # are unaffected; only unverified public signups are stopped here.
                if not user.is_verified:
                    messages.error(request, 'Please verify your email before signing in. Check your inbox or request a new link below.')
                    return render(request, 'registration/verify_email_invalid.html', {'email': user.email})
                login(request, user)
                log_user_login(user, request)

                # SqlSessionContextMiddleware stamps user_id/user_role on every
                # request from here on, so setting them again here bought
                # nothing: this request only redirects, and the value it wrote
                # died with the connection anyway.

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


def _send_verification_email(request, user):
    """Build and send a single-use email-verification link to the user."""
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.urls import reverse
    from home.tokens import email_verification_token

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = request.build_absolute_uri(reverse('verify_email', args=[uid, token]))
    body = render_to_string('registration/verify_email_email.html', {
        'link': link,
        'username': user.username,
    })
    try:
        send_mail(
            'Verify your Thiên Tài Hotel account',
            body,
            None,  # DEFAULT_FROM_EMAIL
            [user.email],
            fail_silently=False,
        )
    except Exception:
        # Non-fatal: signup still succeeds; user can use the resend endpoint.
        logger.exception('Verification email send failed for %s', user.email)


def verify_email(request, uidb64, token):
    """Confirm an email-verification token, mark the account verified, log in."""
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from home.tokens import email_verification_token

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    # Token is single-use: it embeds is_verified, so it stops validating once set.
    if user is not None and email_verification_token.check_token(user, token):
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
        login(request, user, backend='home.auth_backend.CustomUserBackend')
        messages.success(request, 'Your email has been verified. Welcome!')
        return redirect('home')

    return render(request, 'registration/verify_email_invalid.html')


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def resend_verification(request):
    """Re-send a verification link. Generic response — never reveals whether an
    account exists or is already verified (anti-enumeration)."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email, is_verified=False).first()
            if user:
                _send_verification_email(request, user)
        return render(request, 'registration/verify_email_sent.html', {
            'email': email, 'resent': True,
        })
    return render(request, 'registration/verify_email_invalid.html')


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
        
        # Distinct "Username already exists." / "Email already registered."
        # messages confirmed which of the two exists to anyone who could POST
        # this form. Login answers a bad username and a bad password
        # identically, so this was the only endpoint handing that out. Which
        # field carries the error is itself the disclosure, so one collision
        # marks both fields and the two cases render the same.
        # Both lookups always run. `or` would short-circuit past the second on
        # a username hit, so the two cases would differ by a query -- a smaller
        # tell than the old messages, but this fix exists to remove the tell.
        username_taken = bool(username) and User.objects.filter(username=username).exists()
        email_taken = bool(email) and User.objects.filter(email=email).exists()
        taken = username_taken or email_taken
        collision = 'That username or email address is already in use.'

        if not username:
            errors['username'] = 'Username is required.'
        elif taken:
            errors['username'] = collision
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters.'

        if not email:
            errors['email'] = 'Email is required.'
        elif taken:
            errors['email'] = collision
        elif '@' not in email:
            errors['email'] = 'Enter a valid email address.'
        
        if not password1:
            errors['password1'] = 'Password is required.'
        else:
            # AUTH_PASSWORD_VALIDATORS is configured in settings but was inert
            # here: a bare length check accepted '12345678', which
            # NumericPasswordValidator and CommonPasswordValidator both reject.
            # MinimumLengthValidator covers the eight-character rule, so the
            # old elif is folded into this call rather than kept alongside it.
            # The unsaved User is what makes UserAttributeSimilarityValidator do
            # anything: it returns immediately on a None user, so passing the
            # password alone would leave one of the four configured validators
            # inert and let someone register with their password set to their
            # own username. Nothing is saved by constructing it.
            try:
                validate_password(password1, User(username=username, email=email))
            except ValidationError as e:
                errors['password1'] = ' '.join(e.messages)
        
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
            }
            return render(request, 'register.html', context)
        
        # Create user (unverified — must confirm email before first login)
        try:
            from django.utils import timezone
            from django.contrib.auth.hashers import make_password

            user = User.objects.create(
                username=username,
                email=email,
                password_hash=make_password(password1),
                role='customer',
                is_active=True,
                is_verified=False,   # email not confirmed yet
                created_at=timezone.now()
            )

            # Send the verification link; do NOT log in until verified.
            _send_verification_email(request, user)
            return render(request, 'registration/verify_email_sent.html', {'email': email})
            
        except Exception as e:
            logger.exception('User registration failed')
            messages.error(request, 'An error occurred during registration. Please try again.')
            context = {
                'active_page': 'register',
                'form': {
                    'username': {'value': username},
                    'email': {'value': email},
                },
            }
            return render(request, 'register.html', context)
    
    # GET request
    context = {
        'form': {},
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
    
    # Calculate today's revenue (bookings made today)
    total_revenue = all_reservations.filter(booking_date__date=today).aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    reservations = Paginator(all_reservations, 200).get_page(request.GET.get('page'))
    
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


def _pick_assignment(assignments, today):
    """Which active assignment speaks for a room when it has more than one.

    A room can hold a stay in progress and a booking for next week at the same
    time. The render used to keep whichever row came last out of an unordered
    queryset while the POST guard took an unordered .first(), which are
    opposite rules over a set with no defined order. Left alone they can judge
    the same room against different bookings, which is the silent override this
    was meant to close.

    Current stay first, then the soonest upcoming one, then anything still
    marked active whose dates have passed.
    """
    def rank(assignment):
        if assignment.check_in <= today <= assignment.check_out:
            stage = 0
        elif assignment.check_in > today:
            stage = 1
        else:
            stage = 2
        return stage, assignment.check_in, assignment.pk

    return min(assignments, key=rank) if assignments else None


def _display_status(room, assignment, today):
    """The one derivation of what a room's card shows.

    Both the dashboard render and the manual-status POST call this. They used
    to hold separate copies and disagree: the POST wrote reservation_status
    while the render preferred an active RoomAssignment covering today, so
    'Empty Clean' on a booked room saved and then reloaded as 'Occupied' with
    nothing to say why. An active assignment is what availability checks read,
    so it outranks the room's own fields; out_of_order outranks everything,
    because a room can be broken while a guest is booked into it.
    """
    if room.housekeeping_status == 'out_of_order':
        return 'out_of_order'
    if assignment and assignment.check_in <= today <= assignment.check_out:
        return 'occupied'
    if assignment and assignment.check_in > today:
        return 'reserved'
    if room.reservation_status == 'vacant' and room.housekeeping_status == 'dirty':
        return 'dirty'
    if room.reservation_status == 'vacant':
        return 'vacant'
    return room.reservation_status


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def room_dashboard(request):
    """Room status dashboard showing all physical rooms grouped by floor."""
    from data.models import Room, RoomAssignment

    # Handle status update via POST (staff/admin changes a room's status)
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        new_status = request.POST.get('new_status') # backwards-compatibility
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        # Resolving a maintenance issue is its own action, not a room status
        # write, so it answers and returns before the status machinery below.
        # Resolving deliberately leaves the room out of order: staff bring it
        # back with Empty Clean or Empty Dirty, which keeps _display_status
        # driven from one place instead of quietly gaining a second source.
        if request.POST.get('action') == 'resolve_issue':
            log_id = request.POST.get('log_id', '')
            # A non-numeric log_id would raise ValueError out of the queryset,
            # so it is screened here rather than caught downstream. isdecimal,
            # not isdigit: isdigit is True for superscripts like '²', which
            # int() then refuses, turning a bad request into a 500.
            log = (
                RoomMaintenanceRepository.resolve(int(log_id))
                if log_id.isdecimal() else None
            )
            if log is None:
                msg = 'That issue is not open, or no longer exists.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': msg}, status=404)
                messages.error(request, msg)
                return redirect('room_dashboard')
            if is_ajax:
                return JsonResponse({'status': 'ok'})
            messages.success(request, f'Issue #{log.log_id} resolved.')
            return redirect('room_dashboard')

        if room_id and new_status:
            # Screened before any write, so an over-long description refuses the
            # whole click rather than leaving the room changed and the issue
            # unrecorded.
            issue = request.POST.get('issue_description', '').strip()
            if len(issue) > MAX_ISSUE_DESCRIPTION:
                msg = (
                    f'Issue description is too long ({len(issue)} characters, '
                    f'limit {MAX_ISSUE_DESCRIPTION}).'
                )
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': msg}, status=400)
                messages.error(request, msg)
                return redirect('room_dashboard')
            try:
                room = Room.objects.get(room_id=room_id)

                # Resolved before the writes below, because whether this click
                # is a maintenance clear depends on the room as it stands now,
                # not as it is about to be.
                assignment = _pick_assignment(
                    list(
                        RoomAssignment.objects
                        .filter(room_id=room.room_id, status='active')
                        .select_related('booking')
                    ),
                    date.today(),
                )

                # Clearing out_of_order on a room an assignment still holds is a
                # maintenance write, not an occupancy one. The click means the
                # fault is fixed, not that the guest has gone. So it writes
                # housekeeping and leaves reservation_status to the assignment,
                # which is what the derivation already reads for every other
                # occupied room.
                #
                # Without this a broken occupied room could never be returned to
                # service: both clearing buttons refused, because the derivation
                # correctly came back 'occupied' and the guard compared that
                # against the 'vacant' the button asked for. The maintenance log
                # flow walks straight into it, since Out of Order is allowed on
                # an occupied room in the first place.
                # An assignment whose dates have passed does not hold the room,
                # and _pick_assignment returns those. today <= check_out is the
                # test, not "covers today": it keeps the exemption for a room
                # booked for next week, which the derivation renders Reserved.
                clearing_maintenance = (
                    room.housekeeping_status == 'out_of_order'
                    and assignment is not None
                    and date.today() <= assignment.check_out
                    and new_status in ('vacant', 'empty_dirty')
                )

                if new_status == 'vacant':
                    if not clearing_maintenance:
                        room.reservation_status = 'vacant'
                    room.housekeeping_status = 'clean'
                elif new_status == 'empty_dirty': # keeping old mappings
                    if not clearing_maintenance:
                        room.reservation_status = 'vacant'
                    room.housekeeping_status = 'dirty'
                elif new_status == 'occupied':
                    room.reservation_status = 'occupied'
                elif new_status == 'reserved':
                    room.reservation_status = 'reserved'
                elif new_status == 'out_of_order':
                    room.housekeeping_status = 'out_of_order'

                # Run the pending write through the same derivation the page
                # renders. If the card would not come back showing what was
                # asked for, refuse and say which booking holds the room,
                # rather than saving a value the next render discards. A
                # maintenance clear is exempt: it never claimed the card would
                # read 'vacant', only that the fault is gone.
                requested = 'dirty' if new_status == 'empty_dirty' else new_status
                if not clearing_maintenance and _display_status(room, assignment, date.today()) != requested:
                    # Name whatever actually outranked the write. out_of_order
                    # comes first in the derivation, so when a room is both
                    # broken and booked it is the housekeeping status blocking
                    # this, and pointing staff at the booking sends them
                    # somewhere that will not help. A room being cleared with
                    # Empty Clean or Empty Dirty never lands here: with an
                    # assignment it took the exemption above, and without one
                    # housekeeping has already been reset.
                    if room.housekeeping_status == 'out_of_order':
                        msg = (
                            f'Room {room.room_code} is out of order. Clear that '
                            f'first, with Empty Clean or Empty Dirty.'
                        )
                    elif assignment is not None:
                        msg = (
                            f'Room {room.room_code} is assigned to booking '
                            f'#{assignment.booking_id} ({assignment.check_in} to '
                            f'{assignment.check_out}). Change that booking to free '
                            f'the room.'
                        )
                    else:
                        # Not reachable today: with no assignment and nothing
                        # out of order, every button's write matches what the
                        # derivation returns. Kept honest rather than repeating
                        # one of the reasons above and misleading whoever finds
                        # a way here.
                        msg = (
                            f'Room {room.room_code} cannot be set to '
                            f'{requested}. Reload the dashboard to see its '
                            f'current status.'
                        )
                    if is_ajax:
                        return JsonResponse({'status': 'error', 'message': msg}, status=409)
                    messages.error(request, msg)
                    return redirect('room_dashboard')

                room.save()
                # After the save, not before: the guard above can still refuse
                # this click with a 409, and an open issue against a room that
                # never went offline is worse than no record at all.
                if issue and new_status == 'out_of_order':
                    RoomMaintenanceRepository.report(room, issue, request.user)
                if is_ajax:
                    return JsonResponse({'status': 'ok'})
                messages.success(request, f'Room {room.room_code} updated status.')
            except Room.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Room not found.'}, status=404)
                messages.error(request, 'Room not found.')
        return redirect('room_dashboard')

    # Build room data with active assignments
    rooms = Room.objects.select_related('hotel').order_by('floor_number', 'room_number')

    # Pre-fetch active assignments with their bookings
    active_assignments = RoomAssignment.objects.filter(
        status='active'
    ).select_related('booking', 'room')

    # Grouped, then resolved through the same picker the POST guard uses, so a
    # room holding both a current stay and a future booking is judged and
    # rendered against the same one.
    by_room = {}
    for a in active_assignments:
        by_room.setdefault(a.room_id, []).append(a)

    # One query for both the card badges and the modal lists.
    open_issues = RoomMaintenanceRepository.open_by_room()

    # Group rooms by floor
    floors = {}
    status_counts = {
        'vacant': 0, 'dirty': 0, 'occupied': 0, 'out_of_order': 0, 'reserved': 0,
    }
    today = date.today()
    for room in rooms:
        assignment = _pick_assignment(by_room.get(room.room_id), today)
        duration = None
        if assignment:
            duration = (assignment.check_out - assignment.check_in).days

        disp_status = _display_status(room, assignment, today)

        status_counts[disp_status] = status_counts.get(disp_status, 0) + 1

        room_data = {
            'room': room,
            'assignment': assignment,
            'duration': duration,
            'disp_status': disp_status, # Include disp_status
            'open_issue_count': len(open_issues.get(room.room_id, [])),
        }
        floors.setdefault(room.floor_number, []).append(room_data)

    status_filter = request.GET.get('status', 'all')

    # Keyed by string because JSON object keys are strings once this reaches JS.
    # Rendered through the json_script filter in the template, which escapes the
    # free-text description so it cannot break out of the script tag.
    issues_json = {
        str(room_id): [
            {
                'log_id': log.log_id,
                'description': log.issue_description,
                'reported_by': log.reported_by.username if log.reported_by else 'Unknown',
                'created_at': log.created_at.strftime('%d %b') if log.created_at else '',
            }
            for log in logs
        ]
        for room_id, logs in open_issues.items()
    }

    context = {
        'floors': dict(sorted(floors.items())),
        'status_counts': status_counts,
        'total_rooms': len(rooms),
        'status_filter': status_filter,
        'open_issues_json': issues_json,
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
@require_POST
def delete_reservation(request, booking_id):
    """
    Delete a reservation by booking_id.
    Only accepts POST requests for security.
    Requires user to be logged in and have staff/admin role.
    """
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

        # Delete related records to prevent Foreign Key constraint errors
        booking.room_assignments.all().delete()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM customer_requests WHERE booking_id = %s", [booking_id])

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

@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def manage_accounts(request):
    """View to manage user accounts (CRUD operations)."""
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

            # The same validators register_view runs. The unsaved User is what
            # gives UserAttributeSimilarityValidator anything to work with: it
            # returns immediately on a None user, so passing the password alone
            # would leave one of the four configured validators inert.
            try:
                validate_password(password or '', User(username=username, email=email))
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
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

                # Only update password if provided, and hold it to the same bar
                # as creation. Validating one branch and not the other just
                # moves the hole to the next button on the same screen.
                if password:
                    try:
                        validate_password(password, user)
                    except ValidationError as e:
                        messages.error(request, ' '.join(e.messages))
                        return redirect('manage_accounts')
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
                # Soft delete. audit_log.user_id is an FK to users with no ON
                # DELETE action and every login writes a row, so a hard delete
                # raises IntegrityError for anyone who has ever signed in and
                # the handler below turns that into a message nobody can act
                # on. is_active is the soft-delete flag the model already
                # documents, and the account list above filters is_active=False
                # out, so the account still disappears from every page staff see.
                user.is_active = False
                user.save(update_fields=['is_active'])
                messages.success(
                    request,
                    f'Account "{username}" deactivated. Its records are kept for the audit trail.',
                )
            except User.DoesNotExist:
                messages.error(request, 'Account not found.')
            except Exception as e:
                logger.exception('Account deletion failed for #%s', account_id)
                messages.error(request, 'An error occurred while deleting the account.')
        
        return redirect('manage_accounts')
    
    # GET request - display accounts based on role hierarchy
    tab = request.GET.get('tab', 'all')
    if request.user.role == 'admin':
        qs = User.objects.exclude(is_active=False).order_by('-created_at')
        if tab == 'staff':
            qs = qs.filter(role__in=['staff', 'admin'])
        elif tab == 'customers':
            qs = qs.filter(role='customer')
    else:
        qs = User.objects.exclude(is_active=False).filter(role='customer').order_by('-created_at')
        tab = 'customers'

    # 200, matching admin_reservations rather than the email views: this page
    # has a client-side search box, which can only ever search the rows the
    # server rendered.
    # get_page() is Django's own version of the PageNotAnInteger/EmptyPage
    # ladder the three sibling views hand-roll, with identical semantics.
    rows = Paginator(qs, 200).get_page(request.GET.get('page'))

    return render(request, 'manage_accounts.html', {
        'accounts': rows,
        'active_tab': tab,
    })

@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def email_log(request):
    """Admin view: list email_queue rows with filters."""
    from data.models import EmailQueue

    status = request.GET.get('status') or None
    email_type = request.GET.get('type') or None

    qs = EmailQueue.objects.all().order_by('-created_at')
    if status in ('sent', 'failed'):
        qs = qs.filter(status=status)
    if email_type:
        qs = qs.filter(email_type=email_type)

    rows = Paginator(qs, 25).get_page(request.GET.get('page'))

    stats = {
        'total': EmailQueue.objects.count(),
        'sent': EmailQueue.objects.filter(status='sent').count(),
        'failed': EmailQueue.objects.filter(status='failed').count(),
    }

    return render(request, 'admin_email_log.html', {
        'rows': rows,
        'stats': stats,
        'filter_status': status or '',
        'filter_type': email_type or '',
    })


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def email_subscribers(request):
    """Admin view: list subscribers; allow manual unsubscribe."""
    from data.repos.repositories import EmailRepository
    from data.models import EmailSubscriber

    if request.method == 'POST':
        action = request.POST.get('action')
        sub_id = request.POST.get('subscriber_id')
        if action == 'unsubscribe' and sub_id:
            sub = EmailSubscriber.objects.filter(id=sub_id).first()
            if sub:
                EmailRepository.unsubscribe(sub)
                messages.success(request, f'{sub.email} has been unsubscribed.')
            else:
                messages.error(request, 'Subscriber not found.')
        return redirect('email_subscribers')

    status = request.GET.get('status') or None
    qs = EmailSubscriber.objects.all().order_by('-created_at')
    if status in ('subscribed', 'unsubscribed', 'bounced'):
        qs = qs.filter(status=status)

    rows = Paginator(qs, 25).get_page(request.GET.get('page'))

    stats = {
        'total': EmailSubscriber.objects.count(),
        'subscribed': EmailSubscriber.objects.filter(status='subscribed').count(),
        'unsubscribed': EmailSubscriber.objects.filter(status='unsubscribed').count(),
        'bounced': EmailSubscriber.objects.filter(status='bounced').count(),
    }

    return render(request, 'admin_email_subscribers.html', {
        'rows': rows,
        'stats': stats,
        'filter_status': status or '',
    })


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def email_campaigns(request):
    """Admin view: list email campaigns."""
    from data.repos.repositories import EmailRepository
    campaigns = EmailRepository.list_campaigns()
    return render(request, 'admin_email_campaigns.html', {
        'campaigns': campaigns,
    })


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def email_campaign_edit(request, campaign_id=None):
    """Create or edit a campaign draft."""
    from data.repos.repositories import EmailRepository

    campaign = None
    if campaign_id:
        campaign = EmailRepository.get_campaign(campaign_id)
        if not campaign:
            return render(request, '404.html', status=404)

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        subject = (request.POST.get('subject') or '').strip()
        body_html = request.POST.get('body_html') or ''
        body_text = request.POST.get('body_text') or ''

        if not name or not subject or not body_html:
            messages.error(request, 'Name, subject, and HTML body are required.')
            return render(request, 'admin_email_campaign_edit.html', {
                'campaign': campaign,
                'form_values': {
                    'name': name, 'subject': subject,
                    'body_html': body_html, 'body_text': body_text,
                },
            })

        if campaign:
            if campaign.status != 'draft':
                messages.error(request, 'Only drafts can be edited.')
                return redirect('email_campaigns')
            EmailRepository.update_campaign(
                campaign.id, name=name, subject=subject,
                body_html=body_html, body_text=body_text or None,
            )
            messages.success(request, 'Campaign updated.')
            return redirect('email_campaigns')
        else:
            new_camp = EmailRepository.create_campaign(
                name=name, subject=subject, body_html=body_html,
                body_text=body_text or None, created_by=request.user,
            )
            messages.success(request, f'Campaign "{new_camp.name}" saved as draft.')
            return redirect('email_campaigns')

    return render(request, 'admin_email_campaign_edit.html', {
        'campaign': campaign,
        'form_values': None,
    })


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
def email_campaign_send(request, campaign_id):
    """Send a draft campaign to all active subscribers."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)

    from data.repos.repositories import EmailRepository
    campaign = EmailRepository.get_campaign(campaign_id)
    if not campaign:
        messages.error(request, 'Campaign not found.')
        return redirect('email_campaigns')
    if campaign.status != 'draft':
        messages.error(request, 'Only drafts can be sent.')
        return redirect('email_campaigns')

    result = EmailService.queue_campaign(campaign.id)
    if result:
        messages.success(
            request,
            f'Campaign "{result.name}" sent: {result.sent_count} delivered, '
            f'{result.failed_count} failed (of {result.recipient_count} recipients).'
        )
    else:
        messages.error(request, 'Campaign send failed. Check server logs.')
    return redirect('email_campaigns')


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
@require_POST
def upload_image(request):
    """Handle image upload for admin users — saves binary data to the ImagesRef DB table."""
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
@require_POST
def save_content(request):
    """Save a site content value to the DB (any key allowed for inline editing).
    If a 'db_key' is also provided, the value is saved under that key too
    (for elements originally rendered from {{ ct.xxx }} template variables)."""
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


@login_required
@user_passes_test(is_staff_or_admin, login_url='/accounts/login/')
@require_POST
def edit_reservation(request, booking_id):
    """
    Edit an existing reservation.
    Only accepts POST requests with JSON data.
    Requires user to be logged in and have staff/admin role.
    """
    try:
        import json
        from datetime import datetime
        from decimal import Decimal
        
        # Find the booking
        booking = CustomerBookingInfo.objects.select_related('hotel', 'user').get(booking_id=booking_id)

        # Capture old data for audit
        old_status = booking.status
        old_allocation = (booking.check_in, booking.check_out, booking.room_type)
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
            if data['status'] not in BOOKING_STATUSES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid booking status.'
                }, status=400)
            booking.status = data['status']
        if 'payment_status' in data:
            booking.payment_status = data['payment_status']
        if 'amount_paid' in data:
            booking.amount_paid = Decimal(str(data['amount_paid']))
        
        # Save changes. A DB CHECK-constraint rejection (chk_booking_status is the
        # likely one, since the model's status list and the constraint are separate
        # artefacts) arrives as IntegrityError. Catch it here so it returns a real
        # 400 naming the value, instead of falling through to the generic
        # `except Exception` below and reporting an opaque 500.
        #
        # The assignment re-sync shares this transaction with the save.
        # allocate_room cancels the stale assignment before it looks for a free
        # room, so a booking moved onto dates with nothing available has to
        # roll the save back too. Without that, the booking keeps its new dates
        # and loses its room. Status transitions are handled further down; this
        # covers the case the old code missed entirely, where dates or room
        # type move while status stays put.
        from django.db import transaction
        needs_resync = (
            (booking.check_in, booking.check_out, booking.room_type) != old_allocation
            and booking.status not in ('cancelled', 'rejected', 'checked_out')
        )
        try:
            with transaction.atomic():
                booking.save()
                if needs_resync:
                    RoomService.allocate_room(booking, assigned_by=request.user)
        except ValidationError as room_err:
            # str() on a ValidationError renders its message list, brackets and
            # quotes included, so the guest-facing text arrived as
            # ["No available ... rooms"]. get_reservation already joins.
            return JsonResponse({
                'status': 'error',
                'message': '; '.join(room_err.messages),
            }, status=400)
        except IntegrityError:
            logger.exception(
                'Booking #%s rejected by a DB constraint (status=%r)',
                booking_id, booking.status,
            )
            return JsonResponse({
                'status': 'error',
                'message': (
                    f'The database rejected this booking. Status "{booking.status}" '
                    f'may not be permitted by the booking_info constraint.'
                ),
            }, status=400)

        # Handle room allocation on status transitions
        new_status = booking.status
        if new_status != old_status:
            try:
                # NB: do not re-import ValidationError here. It is already imported
                # at module level, and a function-local import binds the name for
                # this whole function — which made the `raise ValidationError` in
                # the room-rate block above raise UnboundLocalError instead.
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

            # Fire transactional email for guest-facing status changes.
            # Confirmation email is already sent on booking creation (services.py).
            # Email failure is non-fatal — handled inside EmailService.
            try:
                if new_status in ('cancelled', 'rejected'):
                    EmailService.queue_booking_cancellation(
                        booking.booking_id,
                        reason=data.get('cancellation_reason') or None,
                    )
            except Exception:
                logger.exception('Email dispatch failed for booking #%s', booking.booking_id)

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


# Two counters, not one. Per-session is the tighter limit and does the real
# work: it stops a single browser tab hammering the model. Per-IP is the wider
# net for many sessions driven from one host, and it has to stay loose enough
# not to lock out a hotel or cafe behind NAT where guests share an address.
#
# Sized against how a real guest behaves rather than against the other AJAX
# endpoints. Median reply time measured 2026-08-23 was 11.6s, and the widget
# disables its send button while a request is in flight, so a person waiting
# for each answer tops out near 5 messages a minute. 8/m sits just above that:
# a guest reading the answers never reaches it, and a script has to be visibly
# scripted to. 20/m per IP is about two and a half such sessions, so a shared
# address does not collide.
#
# These were 15/m and 35/m, sized to leave headroom that nothing needed. They
# came down when MAX_CONCURRENT_MODEL_CALLS landed: the counters were carrying
# an argument about GPU capacity they were never able to win, because a minute
# is not the unit that matters when Ollama serves one request at a time. The
# cap in ai_providers.py bounds capacity now, so these are free to be what they
# should always have been, which is a bound on how fast one guest can talk.
CHAT_RATE_PER_SESSION = '8/m'
CHAT_RATE_PER_IP = '20/m'


def _chat_session_key(group, request):
    return request.session.session_key


def _chat_phone_handoff(lead):
    """429 that gives the guest a phone number instead of a countdown.

    Used where a countdown is no use: the session has spent its minute, or the
    model has no free slot and nobody can say when one frees up.

    No Retry-After, and that is load-bearing rather than an omission.
    chat-widget.js replaces the response body with its own "wait N seconds"
    copy whenever that header is present, so a phone number sent alongside one
    never reaches the guest. Sending no header is what lets the widget fall
    through to this message.

    The number comes from the hotel row, same source as the contact page, with
    settings.HOTEL_DEFAULT_PHONE behind it. Not a literal here, which would go
    stale the first time the hotel changed its number.
    """
    phone = (HotelRepository.get_hotel_info() or {}).get('phone')
    where = f'call us on {phone}' if phone else 'call the hotel'
    return JsonResponse({
        'status': 'error',
        'message': f'{lead} Please {where} and the front desk will help you straight away.',
    }, status=429)


def _chat_rate_limit(request):
    """(session limit tripped?, seconds to wait). (False, 0) if within both.

    get_usage() rather than the @ratelimit decorator because the decorator
    raises Ratelimited, which the site-wide handler403 turns into a 429 with no
    Retry-After header. Doing the check here keeps the header, and keeps the
    change inside the chat endpoint instead of altering how the other seven
    rate-limited views report themselves.
    """
    # get_usage keys a session limit off session_key, which is None until the
    # session is written. An anonymous guest opening the widget has no session
    # yet, and without this every one of them would share a single None bucket.
    #
    # create(), not save(). save() writes the row but leaves session.modified
    # False, so SessionMiddleware never sets the cookie, so the next request
    # arrives with no session and gets another new key — the per-session limit
    # silently counts to one forever. create() sets modified, which is what
    # actually gets the cookie onto the response.
    #
    # ponytail: a client that refuses cookies gets a fresh key every request and
    # is therefore governed by the per-IP limit alone. That is the intended
    # fallback; tighten only if cookie-less abuse shows up in the logs.
    if not request.session.session_key:
        request.session.create()

    # Both counters are read every call, whichever trips first. Short-circuiting
    # on the session limit would stop incrementing the IP counter, and a caller
    # cycling sessions would then never fill the wider bucket at all.
    session_hit = False
    wait = 0
    for group, key, rate in (
        ('chat-session', _chat_session_key, CHAT_RATE_PER_SESSION),
        ('chat-ip', 'ip', CHAT_RATE_PER_IP),
    ):
        usage = get_usage(request, group=group, key=key, rate=rate,
                          method='POST', increment=True)
        if usage and usage['should_limit']:
            wait = max(wait, usage['time_left'])
            session_hit = session_hit or group == 'chat-session'
    return session_hit, wait


@require_POST
def chat_message(request):
    """Guest chat endpoint. POST only, CSRF-protected by the site-wide middleware."""
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request.'}, status=400)

    # The capacity check comes first, ahead of the counters, and the order is
    # the whole point. get_usage(increment=True) spends a request from the
    # guest's budget the moment it is called, so asking it before knowing
    # whether the machine can serve anyone charged guests for refusals they had
    # no part in. A busy box now answers without touching a counter, which
    # means a guest turned away during a busy spell still has their full 8/m
    # once it clears.
    #
    # The slot is held across the rate-limit check too. That is a few
    # milliseconds of session write and cache reads inside the cap, which is
    # nothing against an 11.6s model call, and it is what lets the check run
    # knowing a slot is already reserved for the answer.
    try:
        with model_slot():
            session_hit, wait = _chat_rate_limit(request)
            if session_hit:
                # This guest has spent their minute. Telling them to wait 40
                # seconds invites them to sit and watch the widget; the front
                # desk answers now. Returning here releases the slot on the way
                # out, so a throttled guest never holds capacity.
                return _chat_phone_handoff('I cannot take any more messages just now.')
            if wait:
                # The IP counter, which means a shared address: NAT, hotel
                # wifi, a cafe. The guest on the other side of it has not done
                # anything wrong, so they keep the countdown rather than being
                # pushed to the phone.
                response = JsonResponse({
                    'status': 'error',
                    'message': 'Too many messages. Please wait a moment and try again.',
                }, status=429)
                response['Retry-After'] = str(max(1, wait))
                return response

            reply = ChatService.reply(request.POST.get('message', ''))
    except ProviderBusy:
        # No slot. Caught above the generic handler on purpose: this is not a
        # fault, and 503 "the assistant is unavailable" would tell the guest
        # the wrong thing about a machine that is working fine and merely full.
        # model_slot() is the only thing that raises this, so nothing else can
        # land here.
        return _chat_phone_handoff('The assistant is busy with another guest right now.')
    except ValidationError as exc:
        return JsonResponse({'status': 'error', 'message': exc.message}, status=400)
    except Exception:
        # Ollama down, model pulled, socket refused. The guest gets a plain
        # sentence; the stack trace goes to the log, not onto the page.
        #
        # This now covers the rate-limit check as well as the model call, since
        # both sit inside the block. A cache backend failing mid-check answers
        # 503 instead of raising a 500 at the guest, which is the better of the
        # two and logs the same either way.
        logger.exception('Chat reply failed')
        return JsonResponse({
            'status': 'error',
            'message': "The assistant is unavailable right now. Please try again shortly.",
        }, status=503)

    return JsonResponse({'status': 'ok', 'reply': reply})

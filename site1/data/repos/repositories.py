from django.conf import settings

from data.models.hotel import Hotel, Room, RoomAssignment
from data.models import CustomerBookingInfo
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone

_DEFAULT_PHONE = getattr(settings, 'HOTEL_DEFAULT_PHONE', '')
_DEFAULT_EMAIL = getattr(settings, 'HOTEL_DEFAULT_EMAIL', '')


class HotelRepository:
    @staticmethod
    def get_hotel_name():
        # Query specifically for hotel name
        result = Hotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        # For contact page and other places where full info is needed
        result = Hotel.objects.values(
            'hotel_name',
            'address',
            'star_rating',
            'established_date',
            'phone',
            'email'
        ).first()

        if not result:
            return {
                'hotel_name': 'Hotel Name Not Found',
                'hotel_address': '',
                'star_rating': None,
                'established_date': None,
                'phone': _DEFAULT_PHONE,
                'email': _DEFAULT_EMAIL,
            }

        # Map the database field names to template-expected names
        return {
            'hotel_name': result['hotel_name'],
            'hotel_address': result['address'],  # Map 'address' to 'hotel_address'
            'star_rating': result['star_rating'],
            'established_date': result['established_date'],
            'phone': result['phone'] or _DEFAULT_PHONE,
            'email': result['email'] or _DEFAULT_EMAIL,
        }


class ReservationRepository:
    """
    Repository class to handle all database operations for reservations
    """

    @staticmethod
    def create(booking_data):
        """
        Create a new booking record in the database

        Args:
            booking_data (dict): Dictionary containing booking information

        Returns:
            CustomerBookingInfo: The created booking object
        """
        now = timezone.now()

        # Add timestamp fields
        booking_data['created_at'] = now
        booking_data['updated_at'] = now

        booking = CustomerBookingInfo(**booking_data)
        booking.save()
        return booking

    @staticmethod
    def get_by_id(booking_id):
        """
        Retrieve a booking by its ID
        """
        try:
            return CustomerBookingInfo.objects.get(booking_id=booking_id)
        except CustomerBookingInfo.DoesNotExist:
            return None

    @staticmethod
    def get_all(order_by='-booking_date'):
        """
        Retrieve all bookings
        """
        return CustomerBookingInfo.objects.all().order_by(order_by)

    @staticmethod
    def get_by_email(email):
        """
        Retrieve all bookings for a specific email address
        """
        return CustomerBookingInfo.objects.filter(
            email__iexact=email
        ).order_by('-booking_date', '-check_in')

    @staticmethod
    def email_exists(email):
        """Check whether a reservation already exists for the email."""
        return CustomerBookingInfo.objects.filter(email__iexact=email).exists()

    @staticmethod
    def get_upcoming_bookings():
        """
        Retrieve all upcoming bookings (check-in date is today or in the future)
        """
        today = timezone.now().date()
        return (
            CustomerBookingInfo.objects
            .filter(check_in__gte=today)
            .order_by('check_in')
        )

    @staticmethod
    def get_bookings_by_date_range(start_date, end_date):
        """
        Retrieve bookings within a specific date range
        """
        return CustomerBookingInfo.objects.filter(
            Q(check_in__gte=start_date, check_in__lte=end_date) |
            Q(check_out__gte=start_date, check_out__lte=end_date)
        ).order_by('check_in')

    @staticmethod
    def search_bookings(search_term):
        """
        Search bookings by name, email, or phone
        """
        return (
            CustomerBookingInfo.objects
            .filter(
                Q(guest_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )
            .order_by('-booking_date', '-check_in')
        )

    @staticmethod
    def get_booking_count():
        """
        Get the total count of all bookings
        """
        return CustomerBookingInfo.objects.count()

    @staticmethod
    def get_bookings_today():
        """
        Get bookings checking in today
        """
        today = timezone.now().date()
        return CustomerBookingInfo.objects.filter(
            check_in=today
        ).order_by('booking_date', 'booking_id')

    @staticmethod
    def update_booking(booking_id, update_data):
        """
        Update an existing booking
        """
        try:
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            for key, value in update_data.items():
                setattr(booking, key, value)
            booking.save()
            return booking
        except CustomerBookingInfo.DoesNotExist:
            return None

    @staticmethod
    def delete_booking(booking_id):
        """
        Delete a booking by ID
        """
        try:
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            booking.delete()
            return True
        except CustomerBookingInfo.DoesNotExist:
            return False

class RoomRepository:
    """Repository for physical room and room assignment operations."""

    @staticmethod
    def get_available_rooms_by_type(room_type, check_in, check_out):
        """
        Return an unevaluated queryset of Room objects that:
        - match the given room_type
        - have reservation_status = 'vacant'
        - have NO active RoomAssignment overlapping [check_in, check_out)

        Returns a queryset so the caller can chain .select_for_update().
        """
        overlapping = RoomAssignment.objects.filter(
            room_id=OuterRef('room_id'),
            status='active',
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
        return Room.objects.filter(
            room_type=room_type,
            reservation_status='vacant',
        ).exclude(Exists(overlapping))

    @staticmethod
    def count_available_rooms_by_type(room_type, check_in, check_out):
        """Return the number of available rooms for the given type and date range."""
        return RoomRepository.get_available_rooms_by_type(
            room_type, check_in, check_out
        ).count()

    @staticmethod
    def create_assignment(booking, room, assigned_by=None):
        """Create and return a new active RoomAssignment."""
        assignment = RoomAssignment(
            booking=booking,
            room=room,
            check_in=booking.check_in,
            check_out=booking.check_out,
            assigned_at=timezone.now(),
            assigned_by=assigned_by,
            status='active',
        )
        assignment.save()
        return assignment

    @staticmethod
    def get_active_assignment_for_booking(booking_id):
        """Return the active RoomAssignment for a booking, or None."""
        return (
            RoomAssignment.objects
            .filter(booking_id=booking_id, status='active')
            .select_related('room')
            .first()
        )

    @staticmethod
    def update_room_status(room_id, reservation_status, housekeeping_status=None):
        """Update a room's reservation (and optionally housekeeping) status."""
        room = Room.objects.get(room_id=room_id)
        room.reservation_status = reservation_status
        if housekeeping_status is not None:
            room.housekeeping_status = housekeeping_status
        room.updated_at = timezone.now()
        room.save()
        return room


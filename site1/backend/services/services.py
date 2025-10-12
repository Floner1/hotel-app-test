# Import models and repositories
from home.models import Hotel as HomeHotel
from data.models.hotel import Hotel as BookingHotel
from data.repos.repositories import ReservationRepository
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils import timezone

# Service class to handle hotel-related business logic
class HotelService:
    @staticmethod
    def get_hotel_name():
        """
        Retrieve just the hotel name from the database
        Returns the hotel name or a default message if not found
        """
        result = HomeHotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        """
        Retrieve hotel contact information from the database
        Returns a dictionary containing hotel name, address, phone, and email
        Returns None if no hotel record exists
        """
        return HomeHotel.objects.values(
            'hotel_name',
            'hotel_address',
            'phone',
            'email'
        ).first()


# Service class to handle reservation-related business logic
ROOM_TYPE_RATES = {
    '1 bed balcony room': 700_000,
    '1 bed window room': 600_000,
    '2 bed no window': 800_000,
    '1 bed no window': 500_000,
    'condotel 2 bed and balcony': 1_000_000,
}


class ReservationService:

    @staticmethod
    def create_reservation(reservation_data):
        """
        Create a new reservation with validation
        
        Args:
            reservation_data (dict): Dictionary containing reservation details
                - name: Guest's full name
                - phone: Contact phone number
                - email: Contact email address
                - checkin_date: Check-in date (string in MM/DD/YYYY format)
                - checkout_date: Check-out date (string in MM/DD/YYYY format)
                - adults: Number of adults
                - children: Number of children
                - notes: Special requests/notes (optional)
        
        Returns:
            CustomerBookingInfo: The created booking object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate required fields
            required_fields = ['name', 'phone', 'email', 'checkin_date', 'checkout_date', 'room_type']
            for field in required_fields:
                if not reservation_data.get(field):
                    raise ValidationError(f"Missing required field: {field}")
            
            # Parse and validate dates
            checkin_date = ReservationService._parse_date(reservation_data['checkin_date'])
            checkout_date = ReservationService._parse_date(reservation_data['checkout_date'])
            
            # Validate date logic
            ReservationService._validate_dates(checkin_date, checkout_date)
            
            # Validate email format (basic check)
            email = reservation_data['email']
            if '@' not in email or '.' not in email:
                raise ValidationError("Invalid email format")

            # Prevent duplicates before hitting the database unique constraint
            if ReservationRepository.email_exists(email):
                raise ValidationError(
                    "A reservation for this email already exists. Please contact the hotel to modify the existing booking."
                )
            
            # Validate and normalise room type
            room_type = reservation_data.get('room_type', '').strip()
            if room_type not in ROOM_TYPE_RATES:
                raise ValidationError("Invalid room type selected")

            # Get guest counts with defaults
            adults = int(reservation_data.get('adults', 1))
            children = int(reservation_data.get('children', 0))
            
            # Validate guest counts
            if adults < 1:
                raise ValidationError("At least one adult is required")
            if children < 0:
                raise ValidationError("Number of children cannot be negative")
            
            # Prepare booking data
            notes_value = reservation_data.get('notes', '')
            notes_value = notes_value.strip() if notes_value else ''

            # Calculate stay duration and total cost
            stay_duration = (checkout_date - checkin_date).days
            nightly_rate = ROOM_TYPE_RATES[room_type]
            total_cost = stay_duration * nightly_rate

            # Persist notes by appending to room type when provided (until dedicated column exists)
            stored_room_type = room_type if not notes_value else f"{room_type} | Notes: {notes_value}"

            # Ensure a valid hotel reference exists
            hotel_record = BookingHotel.objects.order_by('hotel_id').first()
            if not hotel_record:
                raise ValidationError("Hotel information is not configured. Please contact the administrator.")

            booking_data = {
                'name': reservation_data['name'].strip(),
                'phone': reservation_data['phone'].strip(),
                'email': email.strip().lower(),
                'checkin_date': checkin_date,
                'checkout_date': checkout_date,
                'adults': adults,
                'children': children,
                'room_type': stored_room_type,
                'booking_date': timezone.now().date(),
                'total_days': stay_duration,
                'total_cost_amount': total_cost,
                'hotel': hotel_record
            }
            
            # Create the booking using repository
            booking = ReservationRepository.create(booking_data)
            
            return booking
            
        except ValueError as e:
            raise ValidationError(f"Invalid data format: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error creating reservation: {str(e)}")
    
    @staticmethod
    def _parse_date(date_string):
        """
        Parse incoming date strings and normalise to a date object.

        Supports multiple common formats produced by the UI datepicker or
        entered manually by users.

        Args:
            date_string (str): Date string supplied by the reservation form.

        Returns:
            date: Python date object

        Raises:
            ValueError: If no supported format matches the input value
        """
        if not date_string:
            raise ValueError("Date value is required")

        cleaned_value = date_string.strip()
        supported_formats = [
            '%m/%d/%Y',          # 10/23/2025
            '%Y-%m-%d',          # 2025-10-23
            '%d %B, %Y',         # 23 October, 2025
            '%B %d, %Y',         # October 23, 2025
            '%d %b %Y',          # 23 Oct 2025
            '%b %d, %Y',         # Oct 23, 2025
        ]

        for fmt in supported_formats:
            try:
                return datetime.strptime(cleaned_value, fmt).date()
            except ValueError:
                continue

        readable_formats = [
            'MM/DD/YYYY',
            'YYYY-MM-DD',
            'DD Month, YYYY',
            'Month DD, YYYY'
        ]
        raise ValueError(
            "Invalid date format: {}. Expected one of: {}".format(
                cleaned_value,
                ', '.join(readable_formats)
            )
        )
    
    @staticmethod
    def _validate_dates(checkin_date, checkout_date):
        """
        Validate check-in and check-out dates
        
        Args:
            checkin_date (date): Check-in date
            checkout_date (date): Check-out date
            
        Raises:
            ValidationError: If dates are invalid
        """
        today = datetime.now().date()
        
        # Check if check-in is in the past
        if checkin_date < today:
            raise ValidationError("Check-in date cannot be in the past")
        
        # Check if check-out is after check-in
        if checkout_date <= checkin_date:
            raise ValidationError("Check-out date must be after check-in date")
        
        # Calculate stay duration
        stay_duration = (checkout_date - checkin_date).days
        
        # Validate reasonable stay duration (e.g., max 30 days)
        if stay_duration > 30:
            raise ValidationError("Maximum stay duration is 30 days")
    
    @staticmethod
    def get_reservation_by_id(booking_id):
        """
        Retrieve a reservation by its ID
        
        Args:
            booking_id (int): The booking ID
            
        Returns:
            CustomerBookingInfo: The booking object or None if not found
        """
        return ReservationRepository.get_by_id(booking_id)
    
    @staticmethod
    def get_all_reservations():
        """
        Retrieve all reservations ordered by creation date (most recent first)
        
        Returns:
            QuerySet: All reservations
        """
        return ReservationRepository.get_all()
    
    @staticmethod
    def get_reservations_by_email(email):
        """
        Retrieve all reservations for a specific email address
        
        Args:
            email (str): The email address to search for
            
        Returns:
            QuerySet: Reservations matching the email
        """
        return ReservationRepository.get_by_email(email)

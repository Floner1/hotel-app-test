# Import models and repositories
from home.models import Hotel
from data.repos.repositories import ReservationRepository
from datetime import datetime
from django.core.exceptions import ValidationError

# Service class to handle hotel-related business logic
class HotelService:
    @staticmethod
    def get_hotel_name():
        """
        Retrieve just the hotel name from the database
        Returns the hotel name or a default message if not found
        """
        result = Hotel.objects.values('hotel_name').first()
        return result['hotel_name'] if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info():
        """
        Retrieve hotel contact information from the database
        Returns a dictionary containing hotel name, address, phone, and email
        Returns None if no hotel record exists
        """
        return Hotel.objects.values(
            'hotel_name',
            'hotel_address',
            'phone',
            'email'
        ).first()


# Service class to handle reservation-related business logic
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
            required_fields = ['name', 'phone', 'email', 'checkin_date', 'checkout_date']
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
            
            # Get guest counts with defaults
            adults = int(reservation_data.get('adults', 1))
            children = int(reservation_data.get('children', 0))
            
            # Validate guest counts
            if adults < 1:
                raise ValidationError("At least one adult is required")
            if children < 0:
                raise ValidationError("Number of children cannot be negative")
            
            # Prepare booking data
            booking_data = {
                'name': reservation_data['name'].strip(),
                'phone': reservation_data['phone'].strip(),
                'email': email.strip().lower(),
                'checkin_date': checkin_date,
                'checkout_date': checkout_date,
                'adults': adults,
                'children': children,
                'notes': reservation_data.get('notes', '').strip()
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
        Parse date string from MM/DD/YYYY format
        
        Args:
            date_string (str): Date in MM/DD/YYYY format
            
        Returns:
            date: Python date object
            
        Raises:
            ValueError: If date format is invalid
        """
        try:
            return datetime.strptime(date_string, '%m/%d/%Y').date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_string}. Expected MM/DD/YYYY")
    
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

from django.conf import settings

from data.models.hotel import Hotel
from data.models import CustomerBookingInfo
from django.db.models import Q
from datetime import datetime, timedelta

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
            'phone': result['phone'],
            'email': result['email'],
        }

        # Return with consistent key names
        return {
            'hotel_name': result['hotel_name'],
            'address': result['address'],
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
                - name: Guest name
                - phone: Contact phone
                - email: Contact email
                - checkin_date: Check-in date (date object)
                - checkout_date: Check-out date (date object)
                - adults: Number of adults
                - children: Number of children
                - room_type: Selected room type
                - booking_date: Date booking was created
                - total_days: Total length of stay in nights
                - total_cost_amount: Total booking cost in chosen currency units
                - hotel: Related Hotel instance
        
        Returns:
            CustomerBookingInfo: The created booking object
        """
        booking = CustomerBookingInfo(**booking_data)
        booking.save()
        return booking
    
    @staticmethod
    def get_by_id(booking_id):
        """
        Retrieve a booking by its ID
        
        Args:
            booking_id (int): The booking ID
            
        Returns:
            CustomerBookingInfo: The booking object or None if not found
        """
        try:
            return CustomerBookingInfo.objects.get(booking_id=booking_id)
        except CustomerBookingInfo.DoesNotExist:
            return None
    
    @staticmethod
    def get_all(order_by='-booking_date'):
        """
        Retrieve all bookings
        
        Args:
            order_by (str): Field to order by (default: most recent first)
            
        Returns:
            QuerySet: All bookings ordered as specified
        """
        return CustomerBookingInfo.objects.all().order_by(order_by)
    
    @staticmethod
    def get_by_email(email):
        """
        Retrieve all bookings for a specific email address
        
        Args:
            email (str): The email address to search for
            
        Returns:
            QuerySet: Bookings matching the email
        """
        return CustomerBookingInfo.objects.filter(
            email__iexact=email
        ).order_by('-booking_date', '-checkin_date')

    @staticmethod
    def email_exists(email):
        """Check whether a reservation already exists for the email."""
        return CustomerBookingInfo.objects.filter(email__iexact=email).exists()
    
    @staticmethod
    def get_upcoming_bookings():
        """
        Retrieve all upcoming bookings (check-in date is today or in the future)
        
        Returns:
            QuerySet: Upcoming bookings
        """
        today = datetime.now().date()
        return (
            CustomerBookingInfo.objects
            .filter(checkin_date__gte=today)
            .order_by('checkin_date')
        )
    
    @staticmethod
    def get_bookings_by_date_range(start_date, end_date):
        """
        Retrieve bookings within a specific date range
        
        Args:
            start_date (date): Start date
            end_date (date): End date
            
        Returns:
            QuerySet: Bookings within the date range
        """
        return CustomerBookingInfo.objects.filter(
            Q(checkin_date__gte=start_date, checkin_date__lte=end_date) |
            Q(checkout_date__gte=start_date, checkout_date__lte=end_date)
        ).order_by('checkin_date')
    
    @staticmethod
    def search_bookings(search_term):
        """
        Search bookings by name, email, or phone
        
        Args:
            search_term (str): The search term
            
        Returns:
            QuerySet: Matching bookings
        """
        return (
            CustomerBookingInfo.objects
            .filter(
                Q(name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )
            .order_by('-booking_date', '-checkin_date')
        )
    
    @staticmethod
    def get_booking_count():
        """
        Get the total count of all bookings
        
        Returns:
            int: Total number of bookings
        """
        return CustomerBookingInfo.objects.count()
    
    @staticmethod
    def get_bookings_today():
        """
        Get bookings checking in today
        
        Returns:
            QuerySet: Today's check-ins
        """
        today = datetime.now().date()
        return CustomerBookingInfo.objects.filter(
            checkin_date=today
        ).order_by('booking_date', 'booking_id')
    
    @staticmethod
    def update_booking(booking_id, update_data):
        """
        Update an existing booking
        
        Args:
            booking_id (int): The booking ID to update
            update_data (dict): Dictionary of fields to update
            
        Returns:
            CustomerBookingInfo: Updated booking object or None if not found
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
        
        Args:
            booking_id (int): The booking ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            booking = CustomerBookingInfo.objects.get(booking_id=booking_id)
            booking.delete()
            return True
        except CustomerBookingInfo.DoesNotExist:
            return False

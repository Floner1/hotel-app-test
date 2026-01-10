from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from data.models.hotel import Hotel as BookingHotel, RoomPrice
from data.repos.repositories import HotelRepository, ReservationRepository


class HotelService:
    """Application-facing helpers for hotel metadata."""

    @staticmethod
    def get_hotel_name() -> str:
        result = HotelRepository.get_hotel_name()
        return result if result else 'Hotel Name Not Found'

    @staticmethod
    def get_hotel_info() -> Optional[Dict[str, Any]]:
        return HotelRepository.get_hotel_info()
    
    @staticmethod
    def get_available_room_types() -> list:
        """
        Get list of available room types from database.
        Returns list of dicts: {canonical, display, price, description}
        """
        from data.models.hotel import RoomPrice
        
        room_types = []
        try:
            # Get all room types from room_price table
            price_rows = RoomPrice.objects.filter(
                room_type__isnull=False,
                price_per_night__isnull=False
            ).values_list('room_type', 'price_per_night', 'room_description')
            
            for room_type, price, description in price_rows:
                if room_type:
                    # Use the database room_type directly as canonical
                    canonical = room_type.strip()
                    
                    # Create a nice display name from the room_type
                    display_name = canonical.replace('_', ' ').title()
                    
                    # Convert price to Decimal if it's a string
                    try:
                        from decimal import Decimal
                        if isinstance(price, str):
                            price = Decimal(price)
                    except:
                        pass
                    
                    room_types.append({
                        'canonical': canonical,
                        'display': display_name,
                        'price': price,
                        'description': description
                    })
            
            # Remove duplicates based on canonical name (keep first occurrence)
            seen = set()
            unique_rooms = []
            for room in room_types:
                if room['canonical'] not in seen:
                    seen.add(room['canonical'])
                    unique_rooms.append(room)
            
            return unique_rooms
        except Exception as e:
            print(f"[HotelService] Error loading room types: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list if database fails
            return []


class ReservationService:
    """Business logic for reservation workflow."""

    _RATE_CACHE: Optional[Dict[str, Decimal]] = None
    _RATE_CACHE_FETCHED_AT: Optional[datetime] = None
    _RATE_CACHE_TTL_SECONDS = 300

    _ROOM_TYPE_ALIASES: Dict[str, Iterable[str]] = {
        'one_bed_balcony_room': (
            '1 bed balcony room',
            '1 bed balcony',
            '1-bed balcony room',
            'one bed balcony room',
            'one_bed_balcony_room',
        ),
        'one_bed_window_room': (
            '1 bed window room',
            '1 bed window',
            'one bed window room',
            'one_bed_window_room',
        ),
        'two_bed_no_window_room': (
            '2 bed no window',
            'two bed no window',
            '2-bed no window room',
            '2 bed balcony room',
            'two_bed_no_window_room',
        ),
        'one_bed_no_window_room': (
            '1 bed no window',
            'one bed no window',
            'one_bed_no_window_room',
        ),
        'two_bed_condotel_balcony': (
            'condotel 2 bed and balcony',
            'condotel 2 bed balcony',
            '2 bed condotel balcony',
            'condotel 2 bed with balcony',
            'two_bed_condotel_balcony',
        ),
    }

    @classmethod
    def create_reservation(cls, reservation_data: Dict[str, Any]):
        cls._ensure_required_fields(reservation_data)

        try:
            checkin_date = cls._parse_date(reservation_data['checkin_date'])
            checkout_date = cls._parse_date(reservation_data['checkout_date'])
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        cls._validate_dates(checkin_date, checkout_date)

        adults = cls._parse_positive_int(reservation_data.get('adults', 1), 'adults', minimum=1)
        children = cls._parse_positive_int(reservation_data.get('children', 0), 'children', minimum=0)

        # Get canonical room type
        room_type_input = reservation_data.get('room_type', '')
        canonical_room_type = cls._canonicalise_room_type(room_type_input)
        if not canonical_room_type:
            raise ValidationError('Invalid room type selected.')

        # Get the rate for this room type
        rate = cls._resolve_rate(room_type_input)
        total_days = (checkout_date - checkin_date).days
        # For same-day bookings, charge for at least 1 day
        if total_days == 0:
            total_days = 1

        total_cost = (rate * total_days).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        hotel_record = BookingHotel.objects.order_by('hotel_id').first()
        if hotel_record is None:
            raise ValidationError('Hotel information is not configured. Please contact the administrator.')

        guest_name = (reservation_data.get('name') or '').strip()
        if not guest_name:
            raise ValidationError('Guest name is required.')

        email = (reservation_data.get('email') or '').strip()
        phone = (reservation_data.get('phone') or '').strip()
        notes = (reservation_data.get('notes') or '').strip()
        special_requests = (reservation_data.get('special_requests') or '').strip()

        # Get user from reservation_data if provided (for logged-in users)
        user = reservation_data.get('user', None)
        
        booking_data = {
            'hotel': hotel_record,
            'user': user,  # Link to user if logged in
            'guest_name': guest_name,
            'email': email if email else None,
            'phone': phone if phone else None,
            'room_type': canonical_room_type,
            'booking_date': timezone.now(),
            'check_in': checkin_date,
            'check_out': checkout_date,
            'adults': adults,
            'children': children,
            'booked_rate': rate,
            'total_price': total_cost,
            'status': 'pending',  # Changed to pending - admin must confirm
            'payment_status': reservation_data.get('payment_status', 'unpaid'),
            'amount_paid': Decimal('0.00'),
            'special_requests': special_requests if special_requests else None,
            'notes': notes if notes else None,
        }

        return ReservationRepository.create(booking_data)

    @classmethod
    def get_room_rates(cls, force_refresh: bool = False) -> Dict[str, Decimal]:
        if force_refresh or cls._RATE_CACHE is None or cls._rates_expired():
            cls._RATE_CACHE = cls._load_room_rates()
            cls._RATE_CACHE_FETCHED_AT = timezone.now()
        return dict(cls._RATE_CACHE)

    @classmethod
    def refresh_room_rates(cls) -> None:
        cls.get_room_rates(force_refresh=True)

    @staticmethod
    def _parse_date(date_string: str):
        if not date_string:
            raise ValueError('Date value is required.')

        cleaned_value = date_string.strip()
        formats = (
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%d %B, %Y',
            '%B %d, %Y',
            '%d %b %Y',
            '%b %d, %Y',
        )

        for fmt in formats:
            try:
                return datetime.strptime(cleaned_value, fmt).date()
            except ValueError:
                continue

        readable_formats = 'MM/DD/YYYY, YYYY-MM-DD, DD Month, YYYY, Month DD, YYYY'
        raise ValueError(f'Invalid date format: {cleaned_value}. Expected one of {readable_formats}.')

    @staticmethod
    def _validate_dates(checkin_date, checkout_date) -> None:
        today = timezone.now().date()
        if checkin_date < today:
            raise ValidationError('Check-in date cannot be in the past.')
        if checkout_date < checkin_date:
            raise ValidationError('Check-out date cannot be before check-in date.')

    @classmethod
    def _resolve_rate(cls, room_type: str) -> Decimal:
        canonical = cls._canonicalise_room_type(room_type)
        if not canonical:
            raise ValidationError('Invalid room type selected.')

        # Always try to load fresh rates from database
        rates = cls.get_room_rates(force_refresh=True)
        rate = rates.get(canonical)
        
        if rate is None or rate <= 0:
            raise ValidationError(
                f'No nightly rate configured for room type: {canonical}. '
                f'Please ensure room_info or room_price table contains pricing data.'
            )
        return rate

    @classmethod
    def _canonicalise_room_type(cls, room_type: str) -> Optional[str]:
        if not room_type:
            return None
        normalised = room_type.strip().lower()
        
        # First, check if it's already a valid database room type (direct match)
        # This handles room types coming directly from the database like '1_bed_with_window'
        from data.models.hotel import RoomPrice
        try:
            if RoomPrice.objects.filter(room_type__iexact=normalised).exists():
                return normalised
        except Exception as e:
            print(f"[_canonicalise_room_type] Database check error: {e}")
        
        # Then check against aliases for backward compatibility
        for canonical, aliases in cls._ROOM_TYPE_ALIASES.items():
            if normalised in (alias.lower() for alias in aliases):
                return canonical
        
        # If no match found, return None
        return None

    @classmethod
    def _load_room_rates(cls) -> Dict[str, Decimal]:
        """Load room rates from database room_price table."""
        rates: Dict[str, Decimal] = {}

        # Load from room_price table
        try:
            price_rows = RoomPrice.objects.filter(price_per_night__isnull=False).values_list('room_type', 'price_per_night')
            for room_type, price_str in price_rows:
                if room_type and price_str:
                    # Use the database room_type directly as the key (already normalized)
                    canonical = room_type.strip().lower()
                    try:
                        # Convert string price to Decimal
                        price = Decimal(str(price_str)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        rates[canonical] = price
                        print(f"[RATES] Loaded: {canonical} = {rates[canonical]}")
                    except (ValueError, TypeError) as e:
                        print(f"[RATES] Could not parse price for {room_type}: {e}")
        except Exception as e:
            print(f"[RATES] Could not load from room_price table: {e}")

        print(f"[RATES] Total rates loaded: {len(rates)}")
        return rates

    @classmethod
    def _rates_expired(cls) -> bool:
        if cls._RATE_CACHE_FETCHED_AT is None:
            return True
        elapsed = (timezone.now() - cls._RATE_CACHE_FETCHED_AT).total_seconds()
        return elapsed > cls._RATE_CACHE_TTL_SECONDS

    @staticmethod
    def _parse_positive_int(value: Any, field: str, minimum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f'{field.title()} must be a number.') from exc

        if parsed < minimum:
            comparator = 'at least' if minimum > 0 else 'zero or greater'
            requirement = f'{comparator} {minimum}' if minimum > 0 else comparator
            raise ValidationError(f'{field.title()} must be {requirement}.')
        return parsed

    @staticmethod
    def _ensure_required_fields(payload: Dict[str, Any]) -> None:
        required = ('name', 'checkin_date', 'checkout_date', 'room_type')
        missing = [field for field in required if not (payload.get(field) or '').strip()]
        if missing:
            joined = ', '.join(missing)
            raise ValidationError(f'Missing required fields: {joined}.')

    @staticmethod
    def get_reservation_by_id(booking_id):
        return ReservationRepository.get_by_id(booking_id)

    @staticmethod
    def get_all_reservations():
        return ReservationRepository.get_all()

    @staticmethod
    def get_reservations_by_email(email):
        return ReservationRepository.get_by_email(email)
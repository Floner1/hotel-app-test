from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from data.models.hotel import Hotel as BookingHotel, RoomInfo, RoomPrice
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

    _ROOM_PRICE_FIELD_MAP: Dict[str, str] = {
        'one_bed_balcony_room': 'bed_1_balcony_room',
        'one_bed_window_room': 'bed_1_window_room',
        'two_bed_no_window_room': 'bed_2_no_window_room',
        'one_bed_no_window_room': 'bed_1_no_window_room',
        'two_bed_condotel_balcony': 'bed_2_condotel_balcony',
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

        email = (reservation_data.get('email') or '').strip()
        # Validate email format (now required)
        if not email:
            raise ValidationError('Email is required.')
        if '@' not in email or '.' not in email:
            raise ValidationError('Invalid email format.')

        adults = cls._parse_positive_int(reservation_data.get('adults', 1), 'adults', minimum=1)
        children = cls._parse_positive_int(reservation_data.get('children', 0), 'children', minimum=0)

        rate = cls._resolve_rate(reservation_data.get('room_type', ''))
        total_days = (checkout_date - checkin_date).days
        if total_days <= 0:
            raise ValidationError('Stay must be at least one night.')

        total_cost = (rate * total_days).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        hotel_record = BookingHotel.objects.order_by('hotel_id').first()
        if hotel_record is None:
            raise ValidationError('Hotel information is not configured. Please contact the administrator.')

        notes = (reservation_data.get('notes') or '').strip()
        stored_room_type = cls._canonicalise_room_type(reservation_data.get('room_type', '')) or reservation_data.get('room_type', '').strip()

        booking_data = {
            'hotel': hotel_record,
            'name': (reservation_data.get('name') or '').strip(),
            'phone': (reservation_data.get('phone') or '').strip(),
            'room_type': stored_room_type,
            'booked_rate': rate,
            'email': email.lower(),
            'booking_date': timezone.now().date(),
            'checkin_date': checkin_date,
            'checkout_date': checkout_date,
            'total_days': total_days,
            'total_cost_amount': total_cost,
            'adults': adults,
            'children': children,
            'notes': notes if notes else None,
        }

        if not booking_data['name']:
            raise ValidationError('Guest name is required.')
        if not booking_data['phone']:
            raise ValidationError('Phone number is required.')

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
        if checkout_date <= checkin_date:
            raise ValidationError('Check-out date must be after check-in date.')

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
        for canonical, aliases in cls._ROOM_TYPE_ALIASES.items():
            if normalised in (alias.lower() for alias in aliases):
                return canonical
        return None

    @classmethod
    def _load_room_rates(cls) -> Dict[str, Decimal]:
        """Load room rates from database, preferring room_info over room_price."""
        rates: Dict[str, Decimal] = {}

        # Try room_info table first
        try:
            info_rows = RoomInfo.objects.filter(price_per_night__isnull=False).values_list('room_type', 'price_per_night')
            for room_type, price in info_rows:
                canonical = cls._canonicalise_room_type(room_type or '')
                if canonical and price is not None:
                    rates[canonical] = Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    print(f"[RATES] Loaded from room_info: {canonical} = {rates[canonical]}")

            if rates:
                print(f"[RATES] Loaded {len(rates)} rates from room_info table")
                return rates
        except Exception as e:
            print(f"[RATES] Could not load from room_info table: {e}")

        # Fallback to room_price snapshot table
        try:
            snapshot = RoomPrice.objects.order_by('-room_price_id').first()
            if snapshot:
                print(f"[RATES] Loading from room_price snapshot ID {snapshot.room_price_id}")
                for canonical, field_name in cls._ROOM_PRICE_FIELD_MAP.items():
                    value = getattr(snapshot, field_name, None)
                    if value is not None:
                        rates[canonical] = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        print(f"[RATES] Loaded: {canonical} = {rates[canonical]}")
                    else:
                        print(f"[RATES] Skipped {canonical} (value is None)")
            else:
                print("[RATES] WARNING: No room_price records found in database")
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
        required = ('name', 'phone', 'email', 'checkin_date', 'checkout_date', 'room_type')
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
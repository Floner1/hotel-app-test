from __future__ import annotations

import random
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from data.models.hotel import Hotel as BookingHotel, RoomPrice
from data.repos.repositories import (
    HotelRepository,
    ReservationRepository,
    RoomRepository,
    EmailRepository,
    DiscountRepository,
)

logger = logging.getLogger(__name__)


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
                    if isinstance(price, str):
                        try:
                            price = Decimal(price)
                        except (ValueError, InvalidOperation):
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
        except Exception:
            logger.exception("Error loading room types")
            return []


class DiscountService:
    """Business logic for newsletter discount codes."""

    @classmethod
    def issue_for_subscriber(cls, subscriber, email):
        """Return (discount, code_created). Never raises."""
        return DiscountRepository.get_or_issue_for_email(email, subscriber)

    @staticmethod
    def validate(discount, booking_email):
        """Raise ValidationError if the discount cannot be applied."""
        if discount is None:
            raise ValidationError('Discount code not found.')
        if discount.status != 'active':
            raise ValidationError('This code has already been used.')
        if (discount.email or '').lower() != (booking_email or '').lower().strip():
            raise ValidationError('This code was issued to a different email address.')


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
            '2 bed balcony room',
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

        from django.db import transaction
        from data.models.hotel import CustomerBookingInfo

        with transaction.atomic():
            # 1. Lock the room rate row for serializing bookings to prevent race conditions
            #    This ensures no two users can book simultaneously using the same room type.
            RoomPrice.objects.select_for_update().filter(room_type=canonical_room_type).first()

            # 2. Check physical room availability for the requested type and dates
            available_count = RoomRepository.count_available_rooms_by_type(
                canonical_room_type, checkin_date, checkout_date
            )
            if available_count == 0:
                raise ValidationError(
                    f'No {canonical_room_type.replace("_", " ")} rooms are available for the selected dates.'
                )

            # Get the rate for this room type (custom rate overrides preset)        
            custom_rate_raw = reservation_data.get('custom_rate')
            if custom_rate_raw is not None:
                try:
                    rate = Decimal(str(custom_rate_raw))
                    if rate <= 0:
                        raise ValidationError('Custom price must be greater than zero.')
                except (InvalidOperation, ValueError):
                    raise ValidationError('Invalid custom price value.')
            else:
                rate = cls._resolve_rate(room_type_input)
            total_days = (checkout_date - checkin_date).days
            # For same-day bookings, charge for at least 1 day
            if total_days == 0:
                total_days = 1

            total_cost = (rate * total_days).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Discount code validation (optional field)
            discount_code_input = (reservation_data.get('discount_code') or '').strip()
            applied_discount = None
            if discount_code_input:
                from data.models import DiscountCode as _DiscountCode
                disc = (
                    _DiscountCode.objects
                    .select_for_update()
                    .filter(code__iexact=discount_code_input)
                    .first()
                )
                booking_email = (reservation_data.get('email') or '').strip().lower()
                DiscountService.validate(disc, booking_email)
                total_cost = (
                    total_cost * Decimal(100 - disc.discount_percent) / Decimal(100)
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                applied_discount = disc

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

            booking = ReservationRepository.create(booking_data)

            if applied_discount:
                DiscountRepository.redeem(applied_discount, booking)

            # Auto-assign an available room so it immediately appears on the Room Dashboard
            try:
                RoomService.allocate_room(booking, assigned_by=user)
            except Exception as e:
                logger.warning(f"Could not auto-allocate room for booking. Error: {e}")

        # Fire booking confirmation email AFTER the transaction commits so
        # the row is guaranteed visible to the email service. Failure is
        # logged into email_queue and never bubbles up to the caller.
        try:
            EmailService.queue_booking_confirmation(booking.booking_id)
        except Exception:
            logger.exception("queue_booking_confirmation failed for #%s", booking.booking_id)

        return booking

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

        rates = cls.get_room_rates()
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
        try:
            if RoomPrice.objects.filter(room_type__iexact=normalised).exists():
                return normalised
        except Exception:
            logger.exception("Database check error in _canonicalise_room_type")

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

        try:
            price_rows = RoomPrice.objects.filter(price_per_night__isnull=False).values_list('room_type', 'price_per_night')
            for room_type, price_str in price_rows:
                if room_type and price_str:
                    canonical = room_type.strip().lower()
                    try:
                        price = Decimal(str(price_str)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        rates[canonical] = price
                    except (ValueError, TypeError, InvalidOperation) as e:
                        logger.warning("Could not parse price for %s: %s", room_type, e)
        except Exception:
            logger.exception("Could not load from room_price table")

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

class RoomService:
    """Handles physical room allocation tied to booking status transitions."""

    @classmethod
    def allocate_room(cls, booking, assigned_by=None):
        """
        Allocate a physical room when a booking is confirmed.
        Uses select_for_update() to prevent two concurrent confirmations
        from grabbing the same room.
        """
        from django.db import transaction

        # Guard: don't double-allocate
        existing = RoomRepository.get_active_assignment_for_booking(booking.booking_id)
        if existing:
            return existing

        with transaction.atomic():
            candidates = (
                RoomRepository.get_available_rooms_by_type(
                    booking.room_type, booking.check_in, booking.check_out
                )
                .select_for_update()
            )
            candidate_list = list(candidates)  # evaluate under lock

            if not candidate_list:
                raise ValidationError(
                    f'No available {booking.room_type.replace("_", " ")} rooms '
                    f'for {booking.check_in} – {booking.check_out}.'
                )

            room = random.choice(candidate_list)
            assignment = RoomRepository.create_assignment(booking, room, assigned_by)
            RoomRepository.update_room_status(room.room_id, 'reserved')
            return assignment

    @classmethod
    def check_in_room(cls, booking):
        """Mark the assigned room as occupied on guest check-in."""
        assignment = RoomRepository.get_active_assignment_for_booking(booking.booking_id)
        if assignment:
            RoomRepository.update_room_status(assignment.room_id, 'occupied')

    @classmethod
    def check_out_room(cls, booking):
        """
        Mark the room as vacant (dirty) and complete the assignment on check-out.
        """
        assignment = RoomRepository.get_active_assignment_for_booking(booking.booking_id)
        if assignment:
            RoomRepository.update_room_status(
                assignment.room_id, 'vacant', housekeeping_status='dirty'
            )
            assignment.status = 'completed'
            assignment.save()

    @classmethod
    def deallocate_room(cls, booking):
        """
        Release the room and cancel the assignment when a booking is
        cancelled or rejected.
        """
        assignment = RoomRepository.get_active_assignment_for_booking(booking.booking_id)
        if assignment:
            RoomRepository.update_room_status(assignment.room_id, 'vacant')
            assignment.status = 'cancelled'
            assignment.save()


class EmailService:
    """Centralised email send pipeline.

    Every public method follows the same shape:
      1. resolve the recipient + context
      2. render the right template
      3. call the provider
      4. write a row into email_queue (sent or failed)
      5. NEVER raise — email failure is non-fatal for the caller
    """

    # --------------- transactional helpers ---------------

    @classmethod
    def queue_booking_confirmation(cls, reservation_id):
        """Send 'we received your booking' to the guest, plus admin notification."""
        from data.models import CustomerBookingInfo
        try:
            booking = (
                CustomerBookingInfo.objects
                .select_related('hotel', 'user')
                .get(booking_id=reservation_id)
            )
        except CustomerBookingInfo.DoesNotExist:
            logger.warning("queue_booking_confirmation: booking %s missing", reservation_id)
            return

        if not booking.email:
            logger.info("Booking #%s has no guest email; skipping confirmation", reservation_id)
        else:
            cls._send(
                to_email=booking.email,
                to_name=booking.guest_name,
                subject=f"Booking confirmation — {booking.hotel.hotel_name}",
                template_name='email/booking_confirmation.html',
                email_type='booking_confirmation',
                context={'booking': booking, 'hotel': booking.hotel},
                user=booking.user,
                related_type='booking',
                related_id=booking.booking_id,
            )

        # Mirror to admin so the front desk sees new bookings in their inbox.
        cls.queue_admin_notification('new_booking', {
            'booking_id': booking.booking_id,
            'guest_name': booking.guest_name,
            'room_type': booking.room_type,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
            'total_price': str(booking.total_price),
            'email': booking.email or '(none)',
            'phone': booking.phone or '(none)',
            'booking': booking,
            'hotel': booking.hotel,
        })

    @classmethod
    def queue_booking_cancellation(cls, reservation_id, reason=None):
        from data.models import CustomerBookingInfo
        try:
            booking = (
                CustomerBookingInfo.objects
                .select_related('hotel', 'user')
                .get(booking_id=reservation_id)
            )
        except CustomerBookingInfo.DoesNotExist:
            logger.warning("queue_booking_cancellation: booking %s missing", reservation_id)
            return

        if not booking.email:
            logger.info("Booking #%s has no guest email; skipping cancellation", reservation_id)
            return

        cls._send(
            to_email=booking.email,
            to_name=booking.guest_name,
            subject=f"Booking cancellation — {booking.hotel.hotel_name}",
            template_name='email/booking_cancellation.html',
            email_type='booking_cancellation',
            context={'booking': booking, 'hotel': booking.hotel, 'reason': reason},
            user=booking.user,
            related_type='booking',
            related_id=booking.booking_id,
        )

    @classmethod
    def queue_contact_receipt(cls, name, email, message):
        """Acknowledge a contact form submission; also notify admin."""
        if not email:
            return
        hotel = HotelService.get_hotel_info()
        cls._send(
            to_email=email,
            to_name=name,
            subject=f"We received your message — {hotel['hotel_name']}",
            template_name='email/contact_receipt.html',
            email_type='contact_receipt',
            context={'name': name, 'email': email, 'message': message, 'hotel': hotel},
            related_type='contact',
        )
        cls.queue_admin_notification('contact_form', {
            'name': name,
            'email': email,
            'message': message,
            'hotel': hotel,
        })

    @classmethod
    def queue_admin_notification(cls, event_type, payload):
        """Send an internal notification to ADMIN_NOTIFICATION_EMAIL."""
        admin_addr = getattr(settings_module, 'ADMIN_NOTIFICATION_EMAIL', None)
        if not admin_addr:
            logger.info("ADMIN_NOTIFICATION_EMAIL not configured; skipping admin notify")
            return
        subject_map = {
            'new_booking': 'New booking received',
            'contact_form': 'New contact form submission',
        }
        subject = subject_map.get(event_type, f'Notification: {event_type}')
        cls._send(
            to_email=admin_addr,
            subject=f"[Thien Tai Hotel] {subject}",
            template_name='email/admin_notification.html',
            email_type='admin_notification',
            context={'event_type': event_type, 'payload': payload},
            related_type=event_type,
            related_id=payload.get('booking_id') if isinstance(payload, dict) else None,
        )

    @classmethod
    def queue_welcome_discount(cls, subscriber, discount):
        """Send the welcome-discount email. Never raises."""
        unsubscribe_url = cls._build_unsubscribe_url(subscriber.unsubscribe_token)
        cls._send(
            to_email=subscriber.email,
            to_name=subscriber.name,
            subject='Your 10% discount code is inside — Thien Tai Hotel',
            template_name='email/welcome_discount.html',
            email_type='discount_welcome',
            context={
                'subscriber': subscriber,
                'discount': discount,
                'unsubscribe_url': unsubscribe_url,
            },
            user=subscriber.user,
            related_type='subscriber',
            related_id=subscriber.id,
        )

    @classmethod
    def queue_campaign(cls, campaign_id):
        """Send a draft campaign to every active subscriber. Logs per-recipient
        rows into email_queue and updates the campaign's send stats."""
        campaign = EmailRepository.get_campaign(campaign_id)
        if not campaign:
            logger.warning("queue_campaign: campaign %s missing", campaign_id)
            return None
        if campaign.status != 'draft':
            logger.warning("queue_campaign: campaign %s is not in draft status", campaign_id)
            return campaign

        subscribers = list(EmailRepository.active_subscribers())
        sent_count = 0
        failed_count = 0

        for sub in subscribers:
            # Personalise the unsubscribe link per recipient.
            unsubscribe_url = cls._build_unsubscribe_url(sub.unsubscribe_token)
            context = {
                'campaign': campaign,
                'subscriber': sub,
                'unsubscribe_url': unsubscribe_url,
                'hotel': HotelService.get_hotel_info(),
            }
            try:
                # Render the campaign body wrapped in base_email; campaign body
                # is rich HTML the admin authored.
                html = cls._render('email/campaign.html', context, fallback_body=campaign.body_html)
                from backend.email_providers import send_email
                msg_id = send_email(
                    to=[sub.email],
                    subject=campaign.subject,
                    html_body=html,
                    text_body=campaign.body_text or None,
                    headers={'List-Unsubscribe': f'<{unsubscribe_url}>'},
                )
                EmailRepository.log_sent(
                    to_email=sub.email,
                    to_name=sub.name,
                    subject=campaign.subject,
                    email_type='campaign',
                    template_name='email/campaign.html',
                    user=sub.user,
                    related_type='subscriber',
                    related_id=sub.id,
                    campaign=campaign,
                    provider_msg_id=msg_id,
                )
                sent_count += 1
            except Exception as exc:
                logger.exception("Campaign %s send to %s failed", campaign.id, sub.email)
                EmailRepository.log_failed(
                    to_email=sub.email,
                    to_name=sub.name,
                    subject=campaign.subject,
                    email_type='campaign',
                    template_name='email/campaign.html',
                    error=exc,
                    user=sub.user,
                    related_type='subscriber',
                    related_id=sub.id,
                    campaign=campaign,
                )
                failed_count += 1

        EmailRepository.mark_campaign_sent(
            campaign.id,
            recipient_count=len(subscribers),
            sent_count=sent_count,
            failed_count=failed_count,
        )
        return EmailRepository.get_campaign(campaign.id)

    # --------------- internal plumbing ---------------

    @classmethod
    def _send(cls, *, to_email, subject, template_name, email_type, context,
              to_name=None, user=None, related_type=None, related_id=None,
              campaign=None):
        """Render → send → log. Never raises."""
        try:
            html = cls._render(template_name, context)
        except Exception as exc:
            logger.exception("Failed to render %s", template_name)
            try:
                EmailRepository.log_failed(
                    to_email=to_email, subject=subject, email_type=email_type,
                    template_name=template_name, to_name=to_name, user=user,
                    related_type=related_type, related_id=related_id, campaign=campaign,
                    error=f"template render failed: {exc}",
                )
            except Exception:
                logger.exception("log_failed also failed for %s -> %s", email_type, to_email)
            return None

        try:
            from backend.email_providers import send_email
            msg_id = send_email(
                to=[to_email],
                subject=subject,
                html_body=html,
            )
            EmailRepository.log_sent(
                to_email=to_email, to_name=to_name, subject=subject,
                email_type=email_type, template_name=template_name,
                user=user, related_type=related_type, related_id=related_id,
                campaign=campaign, provider_msg_id=msg_id,
            )
            return msg_id
        except Exception as exc:
            logger.exception("Email send failed (%s -> %s)", email_type, to_email)
            try:
                EmailRepository.log_failed(
                    to_email=to_email, subject=subject, email_type=email_type,
                    template_name=template_name, to_name=to_name, user=user,
                    related_type=related_type, related_id=related_id, campaign=campaign,
                    error=exc,
                )
            except Exception:
                logger.exception("log_failed also failed for %s -> %s", email_type, to_email)
            return None

    @staticmethod
    def _render(template_name, context, fallback_body=None):
        from django.template.loader import render_to_string
        try:
            return render_to_string(template_name, context)
        except Exception:
            if fallback_body is not None:
                # Used by queue_campaign when the admin pastes raw HTML.
                base_ctx = dict(context)
                base_ctx['raw_body'] = fallback_body
                return render_to_string('email/campaign.html', base_ctx)
            raise

    @staticmethod
    def _build_unsubscribe_url(token):
        base = getattr(settings_module, 'SITE_BASE_URL', '').rstrip('/')
        path = f'/unsubscribe/{token}/'
        return f"{base}{path}" if base else path


# Late import for settings to avoid circulars at module load.
from django.conf import settings as settings_module  # noqa: E402


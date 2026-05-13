import secrets
from datetime import timedelta

from django.conf import settings

from data.models.hotel import Hotel, Room, RoomAssignment
from data.models import CustomerBookingInfo, EmailQueue, EmailSubscriber, EmailCampaign
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


class EmailRepository:
    """Data access for email_queue, email_subscribers, email_campaigns."""

    # ---------------- email_queue ----------------

    @staticmethod
    def log_sent(to_email, subject, email_type, template_name=None, to_name=None,
                 user=None, related_type=None, related_id=None, campaign=None,
                 provider_msg_id=None):
        """Insert a 'sent' row into email_queue."""
        now = timezone.now()
        return EmailQueue.objects.create(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template_name=template_name,
            email_type=email_type,
            status='sent',
            attempts=1,
            provider_msg_id=provider_msg_id,
            created_at=now,
            sent_at=now,
            user=user,
            related_type=related_type,
            related_id=related_id,
            campaign=campaign,
        )

    @staticmethod
    def log_failed(to_email, subject, email_type, error, template_name=None,
                   to_name=None, user=None, related_type=None, related_id=None,
                   campaign=None):
        """Insert a 'failed' row into email_queue."""
        return EmailQueue.objects.create(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template_name=template_name,
            email_type=email_type,
            status='failed',
            attempts=1,
            error_message=str(error)[:4000] if error else None,
            created_at=timezone.now(),
            user=user,
            related_type=related_type,
            related_id=related_id,
            campaign=campaign,
        )

    @staticmethod
    def get_failed(limit=None):
        qs = EmailQueue.objects.filter(status='failed').order_by('-created_at')
        if limit:
            qs = qs[:limit]
        return qs

    @staticmethod
    def mark_retried_sent(email_id, provider_msg_id=None):
        """Update an existing failed row after a successful retry."""
        try:
            row = EmailQueue.objects.get(id=email_id)
        except EmailQueue.DoesNotExist:
            return None
        row.status = 'sent'
        row.attempts = (row.attempts or 0) + 1
        row.sent_at = timezone.now()
        row.error_message = None
        if provider_msg_id:
            row.provider_msg_id = provider_msg_id
        row.save(update_fields=['status', 'attempts', 'sent_at', 'error_message', 'provider_msg_id'])
        return row

    @staticmethod
    def mark_retried_failed(email_id, error):
        try:
            row = EmailQueue.objects.get(id=email_id)
        except EmailQueue.DoesNotExist:
            return None
        row.attempts = (row.attempts or 0) + 1
        row.error_message = str(error)[:4000] if error else None
        row.save(update_fields=['attempts', 'error_message'])
        return row

    @staticmethod
    def delete_older_than(days):
        """Retention cleanup — remove queue rows older than N days."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = EmailQueue.objects.filter(created_at__lt=cutoff).delete()
        return deleted

    @staticmethod
    def list_recent(limit=200, status=None, email_type=None):
        qs = EmailQueue.objects.all().order_by('-created_at')
        if status:
            qs = qs.filter(status=status)
        if email_type:
            qs = qs.filter(email_type=email_type)
        return qs[:limit]

    # ---------------- email_subscribers ----------------

    @staticmethod
    def _new_token():
        return secrets.token_urlsafe(32)[:64]

    @classmethod
    def create_subscriber(cls, email, name=None, user=None, source='footer_signup'):
        """Idempotent subscribe: re-subscribe a previously unsubscribed email,
        return existing row if already subscribed. Returns (subscriber, created)."""
        email = (email or '').strip().lower()
        if not email:
            return None, False
        existing = EmailSubscriber.objects.filter(email__iexact=email).first()
        now = timezone.now()
        if existing:
            if existing.status != 'subscribed':
                existing.status = 'subscribed'
                existing.subscribed_at = now
                existing.unsubscribed_at = None
                if name:
                    existing.name = name
                existing.save(update_fields=['status', 'subscribed_at', 'unsubscribed_at', 'name'])
            return existing, False
        sub = EmailSubscriber.objects.create(
            email=email,
            name=name,
            user=user,
            status='subscribed',
            source=source,
            subscribed_at=now,
            unsubscribe_token=cls._new_token(),
            created_at=now,
        )
        return sub, True

    @staticmethod
    def get_by_token(token):
        if not token:
            return None
        return EmailSubscriber.objects.filter(unsubscribe_token=token).first()

    @staticmethod
    def unsubscribe(subscriber):
        if not subscriber:
            return None
        subscriber.status = 'unsubscribed'
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=['status', 'unsubscribed_at'])
        return subscriber

    @staticmethod
    def get_by_email(email):
        return EmailSubscriber.objects.filter(email__iexact=(email or '').strip()).first()

    @staticmethod
    def list_subscribers(status=None, limit=None):
        qs = EmailSubscriber.objects.all().order_by('-created_at')
        if status:
            qs = qs.filter(status=status)
        if limit:
            qs = qs[:limit]
        return qs

    @staticmethod
    def active_subscribers():
        return EmailSubscriber.objects.filter(status='subscribed').order_by('email')

    # ---------------- email_campaigns ----------------

    @staticmethod
    def create_campaign(name, subject, body_html, body_text=None, created_by=None):
        now = timezone.now()
        return EmailCampaign.objects.create(
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            status='draft',
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def update_campaign(campaign_id, **fields):
        try:
            camp = EmailCampaign.objects.get(id=campaign_id)
        except EmailCampaign.DoesNotExist:
            return None
        allowed = {'name', 'subject', 'body_html', 'body_text', 'status'}
        for k, v in fields.items():
            if k in allowed:
                setattr(camp, k, v)
        camp.updated_at = timezone.now()
        camp.save()
        return camp

    @staticmethod
    def get_campaign(campaign_id):
        return EmailCampaign.objects.filter(id=campaign_id).first()

    @staticmethod
    def list_campaigns():
        return EmailCampaign.objects.all().order_by('-created_at')

    @staticmethod
    def mark_campaign_sent(campaign_id, recipient_count, sent_count, failed_count):
        camp = EmailCampaign.objects.filter(id=campaign_id).first()
        if not camp:
            return None
        camp.status = 'sent'
        camp.sent_at = timezone.now()
        camp.recipient_count = recipient_count
        camp.sent_count = sent_count
        camp.failed_count = failed_count
        camp.updated_at = timezone.now()
        camp.save()
        return camp


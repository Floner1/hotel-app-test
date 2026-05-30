"""Template filters used by email templates."""
from datetime import datetime, timezone, timedelta

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def static_url(path):
    """Return an absolute URL to a static asset, suitable for use in emails."""
    base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000').rstrip('/')
    static = getattr(settings, 'STATIC_URL', '/static/').strip('/')
    return f"{base}/{static}/{path.lstrip('/')}"


@register.simple_tag
def inline_image(path):
    """Embed a static image as a base64 data URL so it renders in email clients
    regardless of whether the server is publicly accessible."""
    import base64
    import mimetypes
    from django.contrib.staticfiles import finders
    found = finders.find(path)
    if not found:
        return ''
    mime, _ = mimetypes.guess_type(found)
    with open(found, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime or 'image/png'};base64,{data}"

VN_TZ = timezone(timedelta(hours=7))


@register.filter
def vietnam_time(dt):
    """Render a datetime as Vietnam time (ICT, UTC+7).

    Format: "20 Jun 2025, 02:00 PM (ICT)".
    Accepts naive datetimes (treated as UTC), aware datetimes, and dates.
    Returns an empty string if `dt` is None or not convertible.
    """
    if dt is None:
        return ''
    # date objects don't have astimezone — render as a plain date string.
    if not isinstance(dt, datetime):
        try:
            return dt.strftime('%d %b %Y')
        except Exception:
            return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(VN_TZ).strftime('%d %b %Y, %I:%M %p (ICT)')
    except Exception:
        return ''


@register.filter
def vietnam_date(dt):
    """Date-only variant: '20 Jun 2025'."""
    if dt is None:
        return ''
    if not isinstance(dt, datetime):
        try:
            return dt.strftime('%d %b %Y')
        except Exception:
            return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(VN_TZ).strftime('%d %b %Y')
    except Exception:
        return ''


@register.filter
def vnd(value):
    """Format a number as VND with comma-separated thousands, e.g. 750,000.00."""
    try:
        return f'{float(value):,.2f}'
    except (TypeError, ValueError):
        return value


_KEY_LABELS = {
    'booking_id': 'Booking ID',
    'guest_name': 'Guest Name',
    'room_type': 'Room Type',
    'check_in': 'Check-in',
    'check_out': 'Check-out',
    'total_price': 'Total Price',
    'email': 'Email',
    'phone': 'Phone',
}

_EVENT_LABELS = {
    'new_booking': 'New Booking',
    'edit_booking': 'Edit Booking',
    'cancel_booking': 'Cancellation',
}


@register.filter
def prettify_key(key):
    return _KEY_LABELS.get(key, key.replace('_', ' ').title())


@register.filter
def prettify_event(event_type):
    return _EVENT_LABELS.get(event_type, event_type.replace('_', ' ').title())


@register.filter
def format_date_value(value):
    """Convert ISO date strings (YYYY-MM-DD) to DD/MM/YYYY."""
    import re
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        y, m, d = value.split('-')
        return f'{d}/{m}/{y}'
    return value

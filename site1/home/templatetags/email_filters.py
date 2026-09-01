"""Template filters used by email templates."""
from datetime import datetime, timezone, timedelta

from django import template

register = template.Library()


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


_EVENT_LABELS = {
    'new_booking': 'New Booking',
    'edit_booking': 'Edit Booking',
    'cancel_booking': 'Cancellation',
}


@register.filter
def prettify_event(event_type):
    return _EVENT_LABELS.get(event_type, event_type.replace('_', ' ').title())

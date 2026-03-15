"""
Audit logging utilities for tracking changes via the AuditLog model.
"""
import json
import logging

from data.models import AuditLog

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Extract client IP from request."""
    if request is None:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action_type, table_name, record_id=None, old_values=None, new_values=None, request=None):
    """Log an action to the audit trail."""
    try:
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            table_name=table_name,
            record_id=record_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=_get_client_ip(request),
        )
        return True
    except Exception:
        logger.exception('Failed to write audit log')
        return False


def log_booking_create(user, booking, request=None):
    """Log creation of a booking."""
    return log_action(
        user=user,
        action_type='CREATE',
        table_name='booking_info',
        record_id=booking.booking_id,
        new_values={
            'guest_name': booking.guest_name,
            'room_type': booking.room_type,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
            'total_price': str(booking.total_price),
        },
        request=request,
    )


def log_booking_update(user, booking, old_data, request=None):
    """Log update of a booking."""
    return log_action(
        user=user,
        action_type='UPDATE',
        table_name='booking_info',
        record_id=booking.booking_id,
        old_values=old_data,
        new_values={
            'guest_name': booking.guest_name,
            'room_type': booking.room_type,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
            'total_price': str(booking.total_price),
        },
        request=request,
    )


def log_booking_delete(user, booking_id, booking_data, request=None):
    """Log deletion of a booking."""
    return log_action(
        user=user,
        action_type='DELETE',
        table_name='booking_info',
        record_id=booking_id,
        old_values=booking_data,
        request=request,
    )


def log_role_change(user, target_user, old_role, new_role, request=None):
    """Log change of user role."""
    return log_action(
        user=user,
        action_type='ROLE_CHANGE',
        table_name='users',
        record_id=target_user.user_id,
        old_values={'role': old_role},
        new_values={'role': new_role},
        request=request,
    )


def log_user_login(user, request=None):
    """Log user login."""
    return log_action(
        user=user,
        action_type='LOGIN',
        table_name='users',
        record_id=user.user_id,
        request=request,
    )


def get_recent_audit_logs(user=None, action_type=None, limit=100):
    """Get recent audit logs with optional filters."""
    try:
        qs = AuditLog.objects.all()
        if user is not None:
            qs = qs.filter(user=user)
        if action_type is not None:
            qs = qs.filter(action_type=action_type)
        return list(qs[:limit])
    except Exception:
        logger.exception('Failed to retrieve audit logs')
        return []

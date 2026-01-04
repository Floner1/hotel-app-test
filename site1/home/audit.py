"""
Audit logging utilities for tracking changes
NOTE: These functions are disabled until audit_log table is created
"""
import json
from datetime import datetime
# from data.models import AuditLog  # Commented out until table exists


def log_action(user, action_type, table_name, record_id=None, old_values=None, new_values=None, request=None):
    """
    Log an action to the audit trail.
    DISABLED: Audit log table not yet created
    """
    # TODO: Uncomment after running database schema SQL
    return True  # Placeholder - does nothing for now


def log_booking_create(user, booking, request=None):
    """Log creation of a booking. DISABLED."""
    return True


def log_booking_update(user, booking, old_data, request=None):
    """Log update of a booking. DISABLED."""
    return True


def log_booking_delete(user, booking_id, booking_data, request=None):
    """Log deletion of a booking. DISABLED."""
    return True


def log_role_change(user, target_user, old_role, new_role, request=None):
    """Log change of user role. DISABLED."""
    return True


def log_user_login(user, request=None):
    """Log user login. DISABLED."""
    return True


def get_recent_audit_logs(user=None, action_type=None, limit=100):
    """Get recent audit logs. DISABLED."""
    return []

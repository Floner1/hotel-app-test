"""
Permission checking utilities for role-based access control
"""
from datetime import datetime, timedelta


def is_admin(user):
    """Check if user is an admin."""
    return hasattr(user, 'role') and user.role == 'admin'


def is_staff(user):
    """Check if user is staff (or admin)."""
    return hasattr(user, 'role') and user.role in ['admin', 'staff']


def is_customer(user):
    """Check if user is a customer."""
    return hasattr(user, 'role') and user.role == 'customer'


def can_edit_booking(user, booking):
    """
    Check if user can edit a booking.
    
    Rules:
    - Admin: Can edit any booking
    - Staff: Can edit any booking
    - Customer: Cannot edit (must request through staff)
    """
    if is_staff(user):
        return True
    
    return False


def can_delete_booking(user, booking):
    """
    Check if user can delete a booking.
    
    Rules:
    - Admin: Can delete any booking
    - Staff: Can delete any booking
    - Customer: Cannot delete (must request through staff)
    """
    return is_staff(user)


def can_view_booking(user, booking):
    """
    Check if user can view a booking.
    
    Rules:
    - Admin: Can view any booking
    - Staff: Can view any booking
    - Customer: Can only view their own bookings
    """
    if is_staff(user):
        return True
    
    # Customer can only view their own bookings
    if is_customer(user):
        # Check if booking belongs to user (by foreign key or email)
        if hasattr(booking, 'user') and booking.user and booking.user.pk == user.pk:
            return True
        if hasattr(booking, 'email') and booking.email and booking.email.lower() == user.email.lower():
            return True
    
    return False


def can_create_booking(user):
    """
    Check if user can create a booking.
    
    Rules:
    - Admin: Can create bookings
    - Staff: Can create bookings
    - Customer: Cannot create directly (creates pending booking/request)
    """
    return is_staff(user)


def can_manage_users(user):
    """
    Check if user can manage other users.
    
    Rules:
    - Admin: Can manage all users
    - Staff: Can manage customer accounts only
    - Customer: Cannot manage users
    """
    return is_admin(user) or is_staff(user)


def can_manage_staff(user):
    """
    Check if user can manage staff accounts.
    
    Rules:
    - Admin: Can manage staff accounts
    - Staff: Cannot manage other staff
    - Customer: Cannot manage staff
    """
    return is_admin(user)


def can_change_role(user):
    """
    Check if user can change other users' roles.
    
    Rules:
    - Admin: Can change any role
    - Staff: Cannot change roles
    - Customer: Cannot change roles
    """
    return is_admin(user)


def can_view_statistics(user):
    """
    Check if user can view statistics.
    
    Rules:
    - Admin: Can view all statistics
    - Staff: Can view limited statistics (today's check-ins/outs, occupancy)
    - Customer: Cannot view statistics
    """
    return is_staff(user)


def can_view_full_statistics(user):
    """Check if user can view full statistics (admin only)."""
    return is_admin(user)


def can_manage_settings(user):
    """
    Check if user can manage hotel settings (room prices, etc.).
    
    Rules:
    - Admin: Can manage settings
    - Staff: Cannot manage settings
    - Customer: Cannot manage settings
    """
    return is_admin(user)


def can_export_data(user):
    """
    Check if user can export data.
    
    Rules:
    - Admin: Can export data
    - Staff: Cannot export data
    - Customer: Cannot export data
    """
    return is_admin(user)


def can_view_financial_reports(user):
    """
    Check if user can view financial reports.
    
    Rules:
    - Admin: Can view financial reports
    - Staff: Cannot view financial reports
    - Customer: Cannot view financial reports
    """
    return is_admin(user)


def can_customer_request_edit(booking, user):
    """
    Check if customer can request an edit for their booking.
    Must be more than 24 hours before check-in.
    
    Rules:
    - Must be their booking
    - Check-in must be more than 24 hours away
    """
    if not is_customer(user):
        return False
    
    # Check if it's their booking
    if not can_view_booking(user, booking):
        return False
    
    # Check if more than 24 hours before check-in
    if hasattr(booking, 'check_in'):
        check_in_datetime = datetime.combine(booking.check_in, datetime.min.time())
        hours_until_checkin = (check_in_datetime - datetime.now()).total_seconds() / 3600
        
        if hours_until_checkin > 24:
            return True
    
    return False


def get_user_role_display(user):
    """Get display name for user role."""
    if not hasattr(user, 'role'):
        return 'Unknown'
    
    role_map = {
        'admin': 'Administrator',
        'staff': 'Staff Member',
        'customer': 'Customer'
    }
    
    return role_map.get(user.role, user.role.title())

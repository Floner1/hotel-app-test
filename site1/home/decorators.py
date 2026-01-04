"""
Custom decorators for role-based access control
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    """
    Decorator to restrict access to admin users only.
    Redirects non-admin users to appropriate pages.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has admin role in users table
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        
        # Redirect based on role
        if hasattr(request.user, 'role'):
            if request.user.role == 'staff':
                messages.error(request, 'Access denied. Admin privileges required.')
                return redirect('admin_reservations')
            elif request.user.role == 'customer':
                messages.error(request, 'Access denied. This page is for staff only.')
                return redirect('customer_portal')
        
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return wrapper


def staff_required(view_func):
    """
    Decorator to restrict access to staff and admin users.
    Redirects customers to their portal.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has staff or admin role
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'staff']:
            return view_func(request, *args, **kwargs)
        
        # Redirect customers to their portal
        if hasattr(request.user, 'role') and request.user.role == 'customer':
            messages.error(request, 'Access denied. This page is for staff only.')
            return redirect('customer_portal')
        
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return wrapper


def customer_required(view_func):
    """
    Decorator to restrict access to customer users only.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has customer role
        if hasattr(request.user, 'role') and request.user.role == 'customer':
            return view_func(request, *args, **kwargs)
        
        # Redirect staff/admin to dashboard
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'staff']:
            messages.info(request, 'You are logged in as staff. Redirected to dashboard.')
            return redirect('admin_reservations')
        
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return wrapper

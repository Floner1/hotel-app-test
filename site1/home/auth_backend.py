"""
Custom authentication backend for the custom User model
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from data.models import User


class CustomUserBackend(BaseBackend):
    """
    Custom authentication backend that uses the custom User model
    with password_hash field instead of password.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with username and password.
        """
        try:
            # Try to get user by username
            user = User.objects.get(username=username)
            
            # Check if password matches
            if user.check_password(password):
                # Update last_login
                from django.utils import timezone
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                return user
                
        except User.DoesNotExist:
            # Try by email as fallback
            try:
                user = User.objects.get(email=username)
                if user.check_password(password):
                    from django.utils import timezone
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    return user
            except User.DoesNotExist:
                pass
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

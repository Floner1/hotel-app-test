"""
Custom authentication backend for the custom User model
"""
from django.contrib.auth.backends import BaseBackend
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
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                User().set_password(password)
                return None

        if not user.is_active:
            return None

        if user.check_password(password):
            return user

        return None
    
    def get_user(self, user_id):
        """
        Get user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

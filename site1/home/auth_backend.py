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
                # Timing-attack mitigation. DO NOT DELETE — this line looks like
                # a no-op (the User() is discarded) but it is load-bearing.
                #
                # A real account reaches check_password() below, which runs the
                # full PBKDF2 hash: hundreds of thousands of iterations, tens of
                # milliseconds. Returning None here without hashing would make a
                # miss return almost instantly. That measurable gap lets an
                # attacker enumerate which usernames and emails exist by timing
                # the response alone, without ever guessing a password.
                #
                # set_password() burns the same hashing work on a throwaway
                # object so a nonexistent user costs roughly what a real one
                # does. The result is deliberately unused.
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

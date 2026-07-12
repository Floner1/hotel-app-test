"""
Signed, single-use, expiring tokens for email verification.

Reuses Django's PasswordResetTokenGenerator machinery (HMAC over user state +
timestamp, checked against settings.PASSWORD_RESET_TIMEOUT). Including
`is_verified` in the hash makes the token single-use: once the account is
verified the flag flips and any previously issued token stops validating.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Deliberately EXCLUDES last_login: our custom auth backend updates
        # last_login on every successful password check, including the blocked
        # login attempts an unverified user makes — including it here would
        # silently invalidate the pending verification link. Single-use is
        # provided by is_verified (flips on confirm); expiry by timestamp +
        # PASSWORD_RESET_TIMEOUT; binding by pk + password_hash + email.
        return f"{user.pk}{user.password}{timestamp}{user.is_verified}{user.email}"


email_verification_token = EmailVerificationTokenGenerator()

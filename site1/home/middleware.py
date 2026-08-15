"""Request-scoped SQL Server session context for the RBAC triggers."""

from django.db import connection


class SqlSessionContextMiddleware:
    """
    Stamp the SQL Server session context on every request so the RBAC triggers
    (trg_prevent_role_escalation, trg_booking_ownership) see the acting user.

    Must be listed after AuthenticationMiddleware so request.user exists.

    SESSION_CONTEXT lives on the *connection*, not on the Django session.
    login_view used to set it once, at login, which meant the triggers saw
    NULL on every later request and, because NULL <> 'admin' is UNKNOWN in
    T-SQL rather than TRUE, never fired at all.

    The anonymous branch clears the keys rather than skipping the write. With
    CONN_MAX_AGE > 0 the connection outlives the request, so leaving the last
    value in place would hand the next visitor on that connection the previous
    user's identity.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ponytail: one round trip per request, both keys in a single batch.
        # Static files never reach here (WhiteNoise sits earlier in the chain).
        # Only SQL Server has SESSION_CONTEXT; the test suite runs on SQLite.
        if connection.vendor == 'microsoft':
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated:
                user_id, role = str(user.pk), getattr(user, 'role', None)
            else:
                user_id, role = None, None

            with connection.cursor() as cursor:
                cursor.execute(
                    "EXEC sp_set_session_context @key=N'user_id',   @value=%s;"
                    "EXEC sp_set_session_context @key=N'user_role', @value=%s;",
                    [user_id, role],
                )

        return self.get_response(request)

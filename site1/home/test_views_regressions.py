"""Regressions in home/views.py.

Three separate bugs, one section each. They share a file because they share a
module; nothing else connects them.
"""

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from data.models import AuditLog, User


# ── Bug 1: deleting an account with history ────────────────────────────
#
# audit_log.user_id is an FK to users(user_id) with no ON DELETE action, and
# every login writes a row. So user.delete() raises IntegrityError for anyone
# who has ever signed in, the generic handler swallows it, and the admin is
# told "An error occurred" with no idea why. Deactivation is what this repo
# already does everywhere else the append-only audit table holds an FK.


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_user(
        username='accountadmin',
        email='accountadmin@example.com',
        password='irrelevant-for-force-login',
        role='admin',
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


@pytest.fixture
def guest_with_history(db):
    """A customer who has logged in at least once, so audit_log holds a row
    pointing at them. That row is what makes the FK refuse the delete."""
    guest = User.objects.create_user(
        username='longtimeguest',
        email='longtimeguest@example.com',
        password='irrelevant',
        role='customer',
    )
    AuditLog.objects.create(
        user=guest,
        action_type='LOGIN',
        table_name='users',
        record_id=guest.user_id,
    )
    return guest


def test_removing_an_account_with_audit_history_deactivates_it(
    admin_client, guest_with_history
):
    """The account has to end up gone from the admin's list, and the row has to
    survive so audit_log keeps pointing at something."""
    admin_client.post(reverse('manage_accounts'), {
        'action': 'delete',
        'account_id': guest_with_history.user_id,
    })

    assert User.objects.filter(pk=guest_with_history.pk).exists(), (
        'the row was deleted out from under audit_log, orphaning its FK'
    )
    guest_with_history.refresh_from_db()
    assert guest_with_history.is_active is False, (
        'the account is still active, so nothing was done to it'
    )
    assert AuditLog.objects.filter(user=guest_with_history).exists(), (
        'the audit trail lost its actor'
    )


def test_removing_an_account_reports_what_actually_happened(
    admin_client, guest_with_history
):
    """The old message claimed a delete that never happened. The new one has to
    say deactivated, and must not be the generic error."""
    response = admin_client.post(reverse('manage_accounts'), {
        'action': 'delete',
        'account_id': guest_with_history.user_id,
    })

    text = ' '.join(m.message for m in get_messages(response.wsgi_request))
    assert 'error' not in text.lower(), f'admin saw a failure: {text!r}'
    assert 'deactivated' in text.lower(), (
        f'the message does not say what happened to the account: {text!r}'
    )

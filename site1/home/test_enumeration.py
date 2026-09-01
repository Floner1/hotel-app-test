"""Two information-disclosure findings from the 2026-08 audit.

Registration answered differently depending on whether the username or the
email collided, which confirms an account or an address exists to anyone who
can POST the form. Login already gives one error for a bad username and a bad
password, so registration was the only endpoint handing that out.

Separately, the audit trail took its client IP from a client-supplied
X-Forwarded-For header with no trusted-proxy allowlist, so a caller could
choose the IP recorded against their own logins and booking edits in a table
the schema makes append-only.
"""

import pytest
from unittest.mock import patch

from django.test import RequestFactory
from django.urls import reverse

from data.models import User
from home.audit import _get_client_ip

STRONG = 'Str0ng-Passw0rd!'


def _clear_ratelimit():
    """register_view is @ratelimit(key='ip', rate='3/m') and django-ratelimit
    counts in the process-wide default cache, so without this the later posts
    in a run get a 403 instead of the rejection under test."""
    from django.core.cache import cache
    cache.clear()


def _register(client, username, email):
    _clear_ratelimit()
    with patch('home.views._send_verification_email'):
        return client.post(reverse('register'), {
            'username': username,
            'email': email,
            'password1': STRONG,
            'password2': STRONG,
        })


@pytest.fixture
def existing_user(db):
    return User.objects.create_user(
        username='taken',
        email='taken@example.com',
        password='irrelevant-for-this-test',
        role='customer',
    )


# ── Registration must not say which field collided ──


@pytest.mark.django_db
def test_registration_does_not_name_the_username_as_taken(client, existing_user):
    response = _register(client, 'taken', 'fresh@example.com')

    assert b'Username already exists' not in response.content, (
        'the form confirmed the username exists'
    )


@pytest.mark.django_db
def test_registration_does_not_name_the_email_as_registered(client, existing_user):
    response = _register(client, 'fresh', 'taken@example.com')

    assert b'Email already registered' not in response.content, (
        'the form confirmed an account exists for that address'
    )


@pytest.mark.django_db
def test_both_collisions_give_the_same_message(client, existing_user):
    """The actual oracle. Two different messages is what lets a caller tell a
    taken username from a registered address; one shared message does not."""
    username_collision = _register(client, 'taken', 'fresh@example.com')
    email_collision = _register(client, 'fresh', 'taken@example.com')

    assert b'already in use' in username_collision.content
    assert b'already in use' in email_collision.content


@pytest.mark.django_db
def test_a_colliding_registration_is_still_refused(client, existing_user):
    """The message got quieter, not the check. A generic message that let the
    registration through would be a worse bug than the one being fixed."""
    _register(client, 'taken', 'fresh@example.com')

    assert User.objects.filter(username='taken').count() == 1, (
        'a duplicate account was created'
    )
    assert not User.objects.filter(email='fresh@example.com').exists()


@pytest.mark.django_db
def test_a_clean_registration_still_succeeds(client, existing_user):
    """The other half of the pair, so the test above cannot pass by refusing
    every registration."""
    _register(client, 'brandnew', 'brandnew@example.com')

    assert User.objects.filter(username='brandnew').exists(), (
        'a registration with no collision was refused'
    )


# ── The audit trail records the peer address, not a header ──


def test_client_ip_ignores_a_forged_forwarded_for_header():
    """Any caller can set X-Forwarded-For. Trusting it lets someone choose the
    IP written against their own row in the append-only audit trail."""
    request = RequestFactory().post(
        '/accounts/login/',
        HTTP_X_FORWARDED_FOR='1.2.3.4',
        REMOTE_ADDR='198.51.100.7',
    )

    assert _get_client_ip(request) == '198.51.100.7', (
        'a client-supplied header decided what the audit trail recorded'
    )


def test_client_ip_ignores_a_forwarded_for_chain():
    """The old code took the first comma-separated value, which is the part
    furthest from the server and entirely attacker-controlled."""
    request = RequestFactory().post(
        '/accounts/login/',
        HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8, 9.10.11.12',
        REMOTE_ADDR='198.51.100.7',
    )

    assert _get_client_ip(request) == '198.51.100.7'


def test_client_ip_returns_the_peer_address_when_no_header_is_sent():
    request = RequestFactory().post('/accounts/login/', REMOTE_ADDR='203.0.113.9')

    assert _get_client_ip(request) == '203.0.113.9'


def test_client_ip_of_no_request_is_none():
    """log_action is called with request=None from management commands."""
    assert _get_client_ip(None) is None

"""The newsletter signup response must not carry the discount code.

newsletter-discount-plan.md's implementation notes (line 11) settle this: "No
code is shown in the popup or footer response." Both consumers already agree
with that. _discount_popup.html renders static copy ("check your inbox for the
original email") and base.html's success handler reads only status and already.
Neither reads a code key, so returning one put the code on the wire for nothing
to display.
"""

import pytest
from django.core.cache import cache
from django.urls import reverse

from data.models import DiscountCode


@pytest.fixture
def issued_code(db):
    """An existing code, so the repeat-signup branch has something to find."""
    return DiscountCode.objects.create(
        code='TT10-OWNER1',
        email='owner@example.com',
        discount_percent=10,
        status='active',
    )


@pytest.fixture(autouse=True)
def _clear_ratelimit():
    """newsletter_signup is @ratelimit(key='ip', rate='3/m'), and
    django-ratelimit counts in the default cache, which is process-wide and
    outlives a test. Four signup POSTs in one run, two here and two in
    tests.py, would otherwise push the last one into a 403 that has nothing to
    do with what it asserts."""
    cache.clear()
    yield


@pytest.mark.django_db
def test_new_signup_response_omits_the_code(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'fresh@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    payload = response.json()
    assert payload['status'] == 'ok'
    # Absent, not merely empty. An empty string would still be a code-shaped
    # field that a later change could quietly start filling in.
    assert 'code' not in payload, f'the code was echoed back: {payload!r}'


@pytest.mark.django_db
def test_repeat_signup_response_omits_the_code(client, issued_code):
    """The already-subscribed branch is the one the doc names."""
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'owner@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    payload = response.json()
    assert payload['already'] is True, f'not the already-subscribed branch: {payload!r}'
    assert 'code' not in payload, f'the code was echoed back: {payload!r}'

import pytest
from unittest.mock import patch
from django.urls import reverse
from data.models import User
from data.repos.repositories import EmailRepository

# Campaign body_html is rendered with |safe into the outgoing email, so it must
# be sanitized on the way IN, at save time. These tests assert on the value
# handed to the ORM rather than reading it back: the suite cannot build a test
# database (data.User is managed=False, so the users table never exists and
# django_admin_log's FK fails), and the value passed to .create()/.save() is
# exactly what would be written.

DIRTY = '<p>Spring rates</p><script>alert(1)</script><a href="javascript:alert(2)">x</a>'


@patch('data.repos.repositories.EmailCampaign.objects.create')
def test_create_campaign_sanitizes_body_html(mock_create):
    EmailRepository.create_campaign(name='Spring', subject='Rates', body_html=DIRTY)

    saved = mock_create.call_args.kwargs['body_html']
    assert '<script>' not in saved, f'script tag reached the DB: {saved!r}'
    assert 'javascript:' not in saved, f'javascript: URL reached the DB: {saved!r}'
    assert '<p>Spring rates</p>' in saved, f'safe markup was stripped: {saved!r}'


@patch('data.repos.repositories.EmailCampaign.objects.get')
def test_update_campaign_sanitizes_body_html(mock_get):
    camp = mock_get.return_value

    EmailRepository.update_campaign(1, body_html=DIRTY)

    assert '<script>' not in camp.body_html, f'script tag reached the DB: {camp.body_html!r}'
    assert 'javascript:' not in camp.body_html
    assert '<p>Spring rates</p>' in camp.body_html

@pytest.mark.django_db
def test_newsletter_signup_invalid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'invalid-email'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 400
    assert response.json()['status'] == 'error'

@pytest.mark.django_db
def test_newsletter_signup_valid_email(client):
    response = client.post(
        reverse('newsletter_signup'),
        {'email': 'test@example.com'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

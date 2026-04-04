import pytest
from django.urls import reverse
from home.models import User

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

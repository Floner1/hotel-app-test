"""admin-edit.css is editing-UI chrome (4.4 KB) that a non-admin can never see,
so it must not ship on anonymous page loads.

admin-edit.js is a different story and these tests exist mostly to say so.
AdminEdit.init() calls applyOverrides() for *every* visitor, not just admins -
only buildUI() is behind the isAdmin flag. Those overrides are the saved
inline-edit copy for the public site, so dropping the script (or the init call)
for anonymous users would silently revert edited content everywhere. Test (c)
is the tripwire for anyone who later "simplifies" this by wrapping the whole
block in {% if is_admin_user %}.
"""

import pytest
from django.test import Client

from data.models import User

CSS = 'admin-edit.css'
JS = 'admin-edit.js'
INIT = 'AdminEdit.init('


@pytest.fixture
def hotel_admin_client(db):
    """Its own Client, not the `client` fixture. A test that needs both an
    anonymous and an admin session would otherwise get one shared object and
    send both requests as the admin."""
    admin = User.objects.create_user(
        username='perfadmin',
        email='perfadmin@example.com',
        password='irrelevant-for-force-login',
        role='admin',
    )
    admin_client = Client()
    admin_client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return admin_client


def _body(response):
    assert response.status_code == 200, f'home page returned {response.status_code}'
    return response.content.decode()


@pytest.mark.django_db
def test_anonymous_home_page_omits_the_admin_edit_stylesheet(client):
    body = _body(client.get('/'))
    assert CSS not in body, 'admin-edit.css shipped to an anonymous visitor'


@pytest.mark.django_db
def test_admin_home_page_still_loads_the_admin_edit_stylesheet(hotel_admin_client):
    body = _body(hotel_admin_client.get('/'))
    assert CSS in body, 'admin-edit.css missing for an admin, editing UI is unstyled'


@pytest.mark.django_db
def test_both_audiences_keep_the_admin_edit_script_and_init(client, hotel_admin_client):
    """Guard: gating the whole block would break public content overrides."""
    for label, response in (
        ('anonymous', client.get('/')),
        ('admin', hotel_admin_client.get('/')),
    ):
        body = _body(response)
        assert JS in body, (
            f'{label} lost admin-edit.js; applyOverrides() no longer runs and '
            'saved inline-edit content reverts on the public site'
        )
        assert INIT in body, (
            f'{label} lost the AdminEdit.init() call; the script loads but the '
            'saved overrides are never applied'
        )

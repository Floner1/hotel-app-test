"""Two performance regressions in home/views.py.

1. _get_room_images() fanned out one EXISTS query per room type (5 queries) on
   every render of /, /about/ and /rooms/, even though a batched helper for the
   same lookup already sat directly above it in the same file.
2. manage_accounts rendered the whole active-user table with no paginator, so
   the page grew without bound as accounts were added.

The query-count assertions are the point of the first test: a test that only
checked the returned dict would still pass if someone reintroduced the fan-out.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from data.models import User
from home.views import _get_room_images


# ── Finding 1: room image resolution ──


@pytest.mark.django_db
def test_room_images_resolve_in_a_single_query(django_assert_num_queries):
    with django_assert_num_queries(1):
        _get_room_images()


@pytest.mark.django_db
def test_room_images_still_pick_db_over_static(django_assert_num_queries):
    """The batching must not change which URL each key resolves to."""
    from data.models.images import ImagesRef
    ImagesRef.objects.create(ImageName='room-double', ImageData=b'x')

    with django_assert_num_queries(1):
        images = _get_room_images()

    assert set(images) == {'single_bed', 'double', 'window', 'balcony', 'condotel'}
    assert images['double'] == reverse('serve_image', args=['room-double'])
    # The other four have no DB row, so they stay on the static fallback.
    assert images['balcony'].endswith('images/balcony.png')
    assert 'serve_image' not in images['balcony']


# ── Finding 2: manage_accounts pagination ──


@pytest.fixture
def account_admin(db, client):
    """manage_accounts is behind login_required plus a staff/admin check."""
    admin = User.objects.create_user(
        username='pageadmin', email='pageadmin@example.com',
        password='irrelevant-for-force-login', role='admin',
        created_at=timezone.now(),
    )
    client.force_login(admin, backend='home.auth_backend.CustomUserBackend')
    return client


@pytest.fixture
def many_accounts(db):
    """210 customers and 30 staff, enough to push the 200-row page size onto a
    second page. bulk_create with a literal unusable password, not create_user:
    none of these ever log in, and 240 real PBKDF2 hashes would dominate the
    runtime of the suite. created_at is set explicitly because the column is
    nullable, nothing populates it, and the view orders on it."""
    now = timezone.now()
    User.objects.bulk_create(
        [
            User(
                username=f'cust{i}', email=f'cust{i}@example.com',
                password='!unusable', role='customer',
                created_at=now - timedelta(minutes=i),
            )
            for i in range(210)
        ]
        + [
            User(
                username=f'stf{i}', email=f'stf{i}@example.com',
                password='!unusable', role='staff',
                created_at=now - timedelta(minutes=i),
            )
            for i in range(30)
        ]
    )


@pytest.mark.django_db
def test_manage_accounts_first_page_caps_at_200(account_admin, many_accounts):
    """241 active accounts exist (210 + 30 + the admin), so an unpaginated
    queryset renders all 241 and this fails."""
    response = account_admin.get(reverse('manage_accounts'))

    assert response.status_code == 200
    accounts = response.context['accounts']
    assert len(accounts) == 200, f'rendered {len(accounts)} rows, expected one page of 200'


@pytest.mark.django_db
def test_manage_accounts_tab_filter_survives_onto_page_2(account_admin, many_accounts):
    response = account_admin.get(reverse('manage_accounts'), {'tab': 'customers', 'page': 2})

    assert response.status_code == 200
    accounts = response.context['accounts']
    assert len(accounts) == 10, f'page 2 of 210 customers should hold 10, got {len(accounts)}'
    assert {a.role for a in accounts} == {'customer'}, 'page 2 leaked non-customers'


@pytest.mark.django_db
def test_manage_accounts_page_links_keep_the_tab(account_admin, many_accounts):
    """Without tab= on the next-page link, paging from a tab silently resets
    it to 'all', which is how the pagination would quietly undo the filter."""
    response = account_admin.get(reverse('manage_accounts'), {'tab': 'customers'})

    body = response.content.decode()
    # The & is literal template text, not variable output, so Django does not
    # escape it. Asserting the one string that actually renders, rather than an
    # `or` across both, so a change in escaping shows up as a failure.
    assert 'page=2&tab=customers' in body, (
        'next-page link drops the tab query parameter'
    )

"""text_overrides runs on every template render site-wide, so anything it does
twice is paid for on every page load. It used to call HotelService.get_hotel_name()
and HotelService.get_hotel_info() back to back; both SELECT the same single
hotel_info row and the first one's columns are a subset of the second's.

These tests pin the query count, not just the returned values: a value-only test
passes on the old two-query code and so proves nothing.
"""

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from home.context_processors import text_overrides


def _anon_request():
    request = RequestFactory().get('/')
    request.user = AnonymousUser()
    return request


def _hotel_table_queries(captured):
    return [q['sql'] for q in captured.captured_queries if 'hotel_info' in q['sql']]



class _AdminUser:
    """Minimal stand-in: the processor only reads is_authenticated and role."""
    is_authenticated = True
    role = 'admin'

def test_context_processor_hits_hotel_table_once(hotel):
    with CaptureQueriesContext(connection) as captured:
        ctx = text_overrides(_anon_request())

    # The processor swallows every exception and returns a defaults dict whose
    # hotel_name is 'Thiên Tài Hotel' and whose hotel is None. Assert on the
    # real fixture values so a silent trip through that branch fails here
    # instead of passing as a "zero hotel queries" win.
    assert ctx['hotel_name'] == 'Thien Tai Hotel'
    assert ctx['hotel']['hotel_name'] == 'Thien Tai Hotel'

    hotel_sql = _hotel_table_queries(captured)
    assert len(hotel_sql) == 1, (
        f'expected 1 hotel_info query, got {len(hotel_sql)}:\n' + '\n'.join(hotel_sql)
    )


def test_empty_hotel_table_still_falls_back(db):
    with CaptureQueriesContext(connection) as captured:
        ctx = text_overrides(_anon_request())

    # get_hotel_info() returns its own defaults dict when there is no row, so
    # a non-None 'hotel' proves we reached the real code, not the except branch.
    assert ctx['hotel'] is not None
    assert ctx['hotel']['hotel_name'] == 'Hotel Name Not Found'
    assert ctx['hotel_name'] == 'Hotel Name Not Found'

    hotel_sql = _hotel_table_queries(captured)
    assert len(hotel_sql) == 1, (
        f'expected 1 hotel_info query, got {len(hotel_sql)}:\n' + '\n'.join(hotel_sql)
    )


def test_output_contract_keys_intact(hotel):
    """Templates and other agents' work depend on these exact keys."""
    ctx = text_overrides(_anon_request())
    assert set(ctx) == {
        'text_overrides_json', 'ct', 'is_admin_user',
        'hotel_name', 'hotel', 'hotel_services',
    }
    assert ctx['is_admin_user'] is False


def test_a_none_hotel_info_does_not_collapse_the_whole_context(db, monkeypatch):
    """The `or {}` guard in the processor is load-bearing beyond the hotel name.

    get_hotel_info() cannot return None today, but it is annotated Optional. If it
    ever did and the guard were gone, the subscript would raise into the bare
    `except Exception`, which replaces the ENTIRE context with defaults -- including
    is_admin_user=False. base.html gates admin-edit.css on that flag, so the admin
    editing UI would silently vanish site-wide because of a missing hotel row.
    """
    from backend.services.services import HotelService

    monkeypatch.setattr(HotelService, 'get_hotel_info', staticmethod(lambda: None))

    request = _anon_request()
    request.user = _AdminUser()
    ctx = text_overrides(request)

    assert ctx['is_admin_user'] is True, (
        'a None hotel_info collapsed the context and stripped admin privileges'
    )
    assert ctx['hotel_name'] == 'Hotel Name Not Found'

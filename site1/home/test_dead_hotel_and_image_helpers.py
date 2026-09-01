"""Helpers that only became dead once the performance batch landed.

_room_image_url lost its last caller when _get_room_images started resolving all
five URLs from one batched lookup, and _db_image_exists was only ever reached
through _room_image_url. HotelService.get_hotel_name lost its last caller when
the context processor switched to deriving the name from get_hotel_info(), and
HotelRepository.get_hotel_name was only ever reached through the service.

None of the four could be removed in the code-quality batch, because that batch
branched from a commit where all four were still live. Pinning them here so the
unbatched single-image lookup cannot quietly come back and reintroduce the
per-room query fan-out the performance batch removed.
"""

import home.views
from backend.services.services import HotelService
from data.repos.repositories import HotelRepository


def test_unbatched_single_image_lookup_stays_deleted():
    """_db_image_exists ran one EXISTS per name. _db_images_exist replaces it.

    Leaving the per-row helper next to the batched one is how the fan-out gets
    reintroduced by someone reaching for the obvious-looking name.
    """
    assert not hasattr(home.views, '_db_image_exists'), (
        '_db_image_exists is back; use the batched _db_images_exist instead'
    )
    assert hasattr(home.views, '_db_images_exist'), (
        'the batched lookup is missing, which is the one callers should use'
    )


def test_single_room_image_url_helper_stays_deleted():
    assert not hasattr(home.views, '_room_image_url'), (
        '_room_image_url is back; _get_room_images resolves all five inline '
        'from one batched lookup'
    )


def test_hotel_name_only_query_stays_deleted():
    """Its single column is a subset of get_hotel_info()'s, so calling it
    alongside get_hotel_info was two round trips for one row."""
    assert not hasattr(HotelService, 'get_hotel_name'), (
        'HotelService.get_hotel_name is back; derive the name from '
        'get_hotel_info() rather than paying a second SELECT'
    )
    assert not hasattr(HotelRepository, 'get_hotel_name'), (
        'HotelRepository.get_hotel_name is back'
    )


def test_the_replacement_still_supplies_the_name():
    """Guard on the other side: the surviving call has to keep returning the
    key the context processor reads, or this deletion breaks every page."""
    assert hasattr(HotelService, 'get_hotel_info')
    assert hasattr(HotelRepository, 'get_hotel_info')

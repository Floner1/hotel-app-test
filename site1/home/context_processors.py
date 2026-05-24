import json

_CONTENT_DEFAULTS = {
    'hero_subtitle':         'Relax Your Soul',
    'welcome_heading':       'Welcome!',
    'welcome_body':          'Thiên Tài Hotel is a modern, centrally located hotel in Ho Chi Minh City offering comfortable, individually designed rooms with contemporary amenities. Featuring a rooftop terrace, on-site restaurant and café, and attentive 24-hour service, the hotel provides a convenient and relaxing stay close to major attractions, shopping areas, and local landmarks.',
    'rooms_heading':         'Rooms & Suites',
    'rooms_description':     'Our rooms offer a quiet place to rest. Simple layouts, comfortable beds, and a calm setting make it easy to relax. Each room is clean, well kept, and designed for a good night\'s sleep. Whether you stay one night or longer, you will have everything you need to feel comfortable.',
    'services_heading':      'Our Premium Services',
    'services_description':  'Making your stay comfortable and memorable with our range of exclusive services.',
    'reserve_heading':          'A Best Place To Stay.\nReserve Now!',
    'about_welcome_heading':    'Welcome!',
    'about_welcome_body':       'Thiên Tài Hotel is a modern, centrally located hotel in Ho Chi Minh City offering comfortable, individually designed rooms with contemporary amenities. Featuring a rooftop terrace, on-site restaurant and café, and attentive 24-hour service, the hotel provides a convenient and relaxing stay close to major attractions, shopping areas, and local landmarks.',
    'about_photos_heading':     'Photos',
    'about_photos_description': 'These photos give you a clear look at the hotel before you arrive. From the rooms to shared spaces, each image shows the atmosphere you can expect during your stay. Take a moment to look around and get a feel for the place, so you arrive knowing what awaits you.',
    'about_services_heading':   'Our Premium Services',
    'rooms_offers_heading':     'Great Offers',
    'rooms_offers_description': 'Discover our exclusive room selections designed for your perfect stay.',
    'rooms_section_heading':    'Rooms & Suites',
    'rooms_section_description': 'Five room types, each with a fixed nightly rate. Quiet layouts, comfortable beds, and consistent upkeep across the property.',
    'rooms_rates_heading':      'Room Rates',
    'rooms_rates_description':  'All rates per room, per night. Prices shown at time of booking.',
    'rooms_cta_heading':        'Book directly. No agency fees.',
    'contact_map_heading':      'Find Us',
    'contact_map_embed':        'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d6083.477482324672!2d106.68195077662561!3d10.768664389379548!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31752f3d9ad5dd29%3A0xd002ee29a19b9caf!2zVGhpw6puIFTDoGkgSG90ZWw!5e0!3m2!1sen!2s!4v1769936238563!5m2!1sen!2s',
    'footer_newsletter_copy':   'Occasional updates on availability and seasonal rates.',
}

def text_overrides(request):
    """
    Inject all inline-edit text overrides into every template context as JSON.  
    Keys with ':' are inline-edit overrides (page:tag:hash format).
    Embedded in the page so JS can apply them instantly with no AJAX flash.
    """
    try:
        from data.models.site_content import SiteContent
        from data.models import HotelServices
        from backend.services.services import HotelService
        
        # Load all content keys to provide defaults and overrides globally
        all_content = SiteContent.objects.all()
        inline_overrides = {c.content_key: c.content_value for c in all_content if ':' in c.content_key}
        
        # Global CT dictionary for top-level static site content keys
        base_keys = {c.content_key: c.content_value for c in all_content if c.content_key in _CONTENT_DEFAULTS.keys()}
        ct = {k: base_keys.get(k, v) for k, v in _CONTENT_DEFAULTS.items()}
        
        return {
            'text_overrides_json': json.dumps(inline_overrides, ensure_ascii=False),   
            'ct': ct,
            'is_admin_user': (
                request.user.is_authenticated
                and hasattr(request.user, 'role')
                and request.user.role == 'admin'
            ),
            'hotel_name': HotelService.get_hotel_name(),
            'hotel': HotelService.get_hotel_info(),
            'hotel_services': HotelServices.objects.all(),
        }
    except Exception:
        return {
            'text_overrides_json': '{}',
            'ct': _CONTENT_DEFAULTS,
            'is_admin_user': False,
            'hotel_name': 'Thiên Tài Hotel',
            'hotel': None,
            'hotel_services': [],
        }

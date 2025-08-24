from django.urls import path
from backend.views import home_views

urlpatterns = [
    path('', home_views.get_home, name=''),  # Root URL
    path('home/', home_views.get_home, name='home'),  # /home URL
    path('about/', home_views.get_about, name='about'),
    path('contact/', home_views.get_contact, name='contact'),
    path('events/', home_views.get_events, name='events'),
    path('reservation/', home_views.get_reservation, name='reservation'),
    path('rooms/', home_views.get_rooms, name='rooms'),
    path('index/', home_views.get_home, name='index'),  # alias for home
    path('newsletter/signup/', home_views.newsletter_signup, name='newsletter_signup'),
]

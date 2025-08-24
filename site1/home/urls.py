from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_home, name=''),  # Root URL
    path('home/', views.get_home, name='home'),  # /home URL
    path('about/', views.get_about, name='about'),
    path('contact/', views.get_contact, name='contact'),
    path('events/', views.get_events, name='events'),
    path('reservation/', views.get_reservation, name='reservation'),
    path('rooms/', views.get_rooms, name='rooms'),
    path('index/', views.get_home, name='index'),  # alias for home
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
]
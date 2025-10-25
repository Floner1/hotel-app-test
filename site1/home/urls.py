from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_home, name='home'),  # Root URL
    path('about/', views.get_about, name='about'),
    path('contact/', views.get_contact, name='contact'),
    path('reservation/', views.get_reservation, name='reservation'),
    path('rooms/', views.get_rooms, name='rooms'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
    path('dashboard/reservations/', views.admin_reservations, name='admin_reservations'),
    path('dashboard/reservations/delete/<int:booking_id>/', views.delete_reservation, name='delete_reservation'),
]
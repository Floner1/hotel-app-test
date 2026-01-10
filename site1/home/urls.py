from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_home, name='home'),  # Root URL
    path('about/', views.get_about, name='about'),
    path('contact/', views.get_contact, name='contact'),
    path('reservation/', views.get_reservation, name='reservation'),
    path('rooms/', views.get_rooms, name='rooms'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/reservations/', views.admin_reservations, name='admin_reservations'),
    path('dashboard/reservations/view/<int:booking_id>/', views.view_reservation, name='view_reservation'),
    path('dashboard/reservations/edit/<int:booking_id>/', views.edit_reservation, name='edit_reservation'),
    path('dashboard/reservations/delete/<int:booking_id>/', views.delete_reservation, name='delete_reservation'),
]
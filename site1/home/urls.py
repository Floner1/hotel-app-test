from django.urls import path
from django.contrib.auth import views as auth_views
from django_ratelimit.decorators import ratelimit
from . import views

# Password reset request view (stock Django views + custom templates).
# The custom data.User exposes a `password` property mapping to password_hash,
# and pk = user_id, so Django's stock PasswordResetTokenGenerator works as-is.
# Rate-limited by IP separately from login to block email enumeration / spam.
password_reset_request = ratelimit(key='ip', rate='5/m', method='POST', block=True)(
    auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        html_email_template_name='registration/password_reset_email_html.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url='/accounts/password_reset/done/',
    )
)

urlpatterns = [
    path('', views.get_home, name='home'),  # Root URL
    # ---- Password reset (stock auth views) ----
    path('accounts/password_reset/', password_reset_request, name='password_reset'),
    path('accounts/password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/accounts/reset/done/'),
         name='password_reset_confirm'),
    path('accounts/reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
    path('about/', views.get_about, name='about'),
    path('contact/', views.get_contact, name='contact'),
    path('reservation/', views.get_reservation, name='reservation'),
    path('rooms/', views.get_rooms, name='rooms'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
    path('chat/', views.chat_message, name='chat'),
    path('discount/validate/', views.validate_discount_code, name='validate_discount_code'),
    path('unsubscribe/<str:token>/', views.unsubscribe_view, name='unsubscribe'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('accounts/verify/resend/', views.resend_verification, name='resend_verification'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/reservations/', views.admin_reservations, name='admin_reservations'),
    path('dashboard/rooms/', views.room_dashboard, name='room_dashboard'),
    path('dashboard/reservations/view/<int:booking_id>/', views.view_reservation, name='view_reservation'),
    path('dashboard/reservations/edit/<int:booking_id>/', views.edit_reservation, name='edit_reservation'),
    path('dashboard/reservations/delete/<int:booking_id>/', views.delete_reservation, name='delete_reservation'),
    path('dashboard/accounts/', views.manage_accounts, name='manage_accounts'),
    path('dashboard/email/log/', views.email_log, name='email_log'),
    path('dashboard/email/subscribers/', views.email_subscribers, name='email_subscribers'),
    path('dashboard/email/campaigns/', views.email_campaigns, name='email_campaigns'),
    path('dashboard/email/campaigns/new/', views.email_campaign_edit, name='email_campaign_new'),
    path('dashboard/email/campaigns/<int:campaign_id>/edit/', views.email_campaign_edit, name='email_campaign_edit'),
    path('dashboard/email/campaigns/<int:campaign_id>/send/', views.email_campaign_send, name='email_campaign_send'),
    path('staff/upload-image/', views.upload_image, name='upload_image'),
    path('staff/save-content/', views.save_content, name='save_content'),
    path('images/<str:image_name>/', views.serve_image, name='serve_image'),
]
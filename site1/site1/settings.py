"""
Django settings for site1 project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
assert SECRET_KEY, "SECRET_KEY must be set in the environment variables"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',  
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For number formatting (intcomma)
    'home',  # Keep original app name
    'backend',  # Add backend package
    'data',  # Add data package
    'axes',  # Account lockout / brute-force protection (per-username)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'csp.middleware.CSPMiddleware',  # Content-Security-Policy (report-only for now)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # django-axes must be LAST so request.user is populated before it runs.
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'site1.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Use only the new templates directory
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'home.context_processors.text_overrides',
            ],
        },
    },
]

WSGI_APPLICATION = 'site1.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.getenv('DB_NAME', 'hotelbooking'),
        'HOST': os.getenv('DB_HOST', 'DESKTOP-NS6H7CH\\MSSQLSERVER01'),
        'Trusted_Connection': 'yes',  # Use Windows Authentication
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'trust_server_certificate': 'yes',
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Use only the new static directory
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Password reset token lifetime (seconds). Default is 3 days; 1 hour is tighter
# and appropriate for a hotel admin/guest app. Also used by the email
# verification token generator (same signing infrastructure).
PASSWORD_RESET_TIMEOUT = 3600

# Default contact details used when database columns are absent
HOTEL_DEFAULT_PHONE = os.getenv('HOTEL_DEFAULT_PHONE', '+63 900 000 0000')
HOTEL_DEFAULT_EMAIL = os.getenv('HOTEL_DEFAULT_EMAIL', 'info@hotelbooking.local')

# ---------- Email (Gmail SMTP via django.core.mail) ----------
# Use SMTP whenever Gmail credentials are present (even in DEBUG).
# Falls back to console-only when no credentials are configured.
#
# Production SMTP env vars (set these in the deploy environment, never hardcode):
#   GMAIL_APP_PASSWORD  -> EMAIL_HOST_PASSWORD (also flips backend to SMTP)
#   GMAIL_FROM_EMAIL    -> EMAIL_HOST_USER / DEFAULT_FROM_EMAIL sender
#   EMAIL_HOST          -> SMTP host (default smtp.gmail.com)
#   EMAIL_PORT          -> SMTP port (default 587, STARTTLS)
# TLS is on (EMAIL_USE_TLS=True). Without GMAIL_APP_PASSWORD, mail prints to the
# console — fine for dev, do not rely on it in prod.
if os.getenv('GMAIL_APP_PASSWORD'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('GMAIL_FROM_EMAIL', '')
EMAIL_HOST_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
EMAIL_TIMEOUT = 15  # seconds — fail fast rather than hanging the request

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    f"Thien Tai Hotel <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else 'webmaster@localhost'
)
ADMIN_NOTIFICATION_EMAIL = os.getenv('ADMIN_NOTIFICATION_EMAIL', EMAIL_HOST_USER)

# Base URL used when building absolute unsubscribe links inside emails.
SITE_BASE_URL = os.getenv('SITE_BASE_URL', 'http://localhost:8000')

# Email queue retention (days) — used by retry_failed_emails cleanup pass.
EMAIL_QUEUE_RETENTION_DAYS = int(os.getenv('EMAIL_QUEUE_RETENTION_DAYS', '90'))

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'data.User'

# Authentication Backend - Use custom backend for RBAC User model
# AxesStandaloneBackend MUST be first: it short-circuits authentication with a
# PermissionDenied when an account/IP is locked out, before credentials are checked.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # Brute-force lockout gate (must be first)
    'home.auth_backend.CustomUserBackend',  # Custom backend for our User model
    'django.contrib.auth.backends.ModelBackend',  # Fallback for Django admin
]

# ---------- django-axes: brute-force / account lockout ----------
# Locks on USERNAME (not just IP) so lockout survives IP rotation. Sits alongside
# the existing per-IP django-ratelimit on login_view, does not replace it.
from datetime import timedelta
# Two independent lockout keys. The ["username"] key makes lockout survive IP
# rotation (an attacker changing IPs still hits the same account lock); the
# ["ip_address"] key catches one IP spraying many usernames. Either tripping
# locks. This is why W006 (ip-bypass) does not apply.
AXES_LOCKOUT_PARAMETERS = [["ip_address"], ["username"]]
AXES_FAILURE_LIMIT = 5                      # attempts before lockout  [confirm value]
AXES_COOLOFF_TIME = timedelta(minutes=30)  # auto-unlock after 30 min  [confirm value]
AXES_RESET_ON_SUCCESS = True               # a good login clears the counter
AXES_LOCKOUT_TEMPLATE = '403_ratelimited.html'  # reuse existing "too many requests" page

# ---------- Session & cookie security ----------
SESSION_COOKIE_HTTPONLY = True          # Prevent JS access to session cookie
SESSION_COOKIE_AGE = 3600              # 1-hour session lifetime
SESSION_EXPIRE_AT_BROWSER_CLOSE = True # Session dies when browser closes
SESSION_SAVE_EVERY_REQUEST = True      # Sliding expiry: resets on each request
CSRF_COOKIE_HTTPONLY = False           # Must be False so JS can read CSRF token for AJAX

# SameSite: 'Lax' is correct here. No cross-site redirect flow (payment/SSO)
# depends on the cookie; unsubscribe and password-reset links are token-based and
# do not rely on the session cookie, so 'Strict' would also work but 'Lax' is the
# safer default for normal navigation from external links.
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# CSRF trusted origins: required for Django 4+ when the site is served from a
# real HTTPS domain (POSTs are checked against the Origin/Referer scheme+host).
# Set the real deploy domain(s) via env as full origins, e.g.
#   CSRF_TRUSTED_ORIGINS="https://book.thientai.example,https://www.thientai.example"
# Not needed for same-origin localhost dev. [MISSING: production domain(s) —
# Railway deploy was removed; fill in once the prod host is known.]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

# ---------- Content Security Policy (django-csp 4.x) ----------
# REPORT-ONLY for now. This policy is the intended enforce target: `default-src
# 'self'` and a strict `script-src 'self'` (no 'unsafe-inline') so that injected
# script — e.g. via the stored `campaign.body_html|safe` field — has nothing to
# execute. Report-only emits `Content-Security-Policy-Report-Only`; violations
# appear in the browser console and DO NOT block, so shipping this is safe.
#
# Why it is NOT enforced yet: the templates use inline <script> blocks in 8 files
# and dozens of inline on*= handlers (onclick, onchange, ...). Nonces can cover
# <script> blocks but NOT inline event handlers. Enforcing today would break the
# admin dashboards and public pages. To flip to enforced (rename the setting to
# CONTENT_SECURITY_POLICY): (1) add a nonce to every inline <script>
# (`<script nonce="{{ request.csp_nonce }}">` + "script-src" gets the nonce),
# and (2) convert every inline on*= handler to addEventListener in a static JS
# file. Do not flip before that refactor.
#
# NOTE: CSP headers are enforced by BROWSERS on web pages only. They do NOT
# govern email clients, so this does NOT mitigate the campaign.html email XSS —
# that needs server-side HTML sanitization of body_html (bleach/nh3). Flagged
# separately.
CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:"],
        "frame-src": ["https://www.google.com"],  # Google Maps embed on contact page
        "base-uri": ["'self'"],
        "object-src": ["'none'"],
        "form-action": ["'self'"],
    },
}

# ---------- Security settings (apply when DEBUG=False) ----------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

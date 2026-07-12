# Security Remediation Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax. Tier 1 first (items 1-3), run security-review after each. Tier 2 next (items 4-7). code-review on full diff before reporting.

**Goal:** Close seven findings from the prior security audit of the Django hotel app (SQL Server backend) without breaking existing staff/guest login, session, or booking flows.

**Architecture:** Prefer Django stock machinery over custom code. The custom `data.User` (`AbstractBaseUser`, `managed=False`, `password` property bridges to `password_hash`, pk = `user_id`) is compatible with Django's stock `PasswordResetTokenGenerator` and stock auth views, so Item 1 uses them directly. Session fixation is already handled by `django.contrib.auth.login()`. Lockout via django-axes, CSP via django-csp, verification via a second token generator.

**Tech Stack:** Django 5.2.16, mssql-django 1.6, django-ratelimit 4.1 (installed), django-axes 8.3.1 (new), django-csp (new). SQL Server dev DB is reachable locally, so migrations are applied and verified for real.

**Environment facts established during investigation:**
- Single login view `home.views.login_view` serves both staff and guest. `register_view` is separate. Both call `django.contrib.auth.login()`.
- "SESSION_CONTEXT" is not middleware; it is `sp_set_session_context` called inline in `login_view` for SQL Server RBAC triggers (see schema.sql).
- pytest suite CANNOT build a test DB (managed=False + SQL Server → `users` table missing → `django_admin_log` FK fails). Verification is manual against the dev DB via `manage.py shell` + `runserver` + curl.
- `is_active` is a soft-delete marker in `manage_accounts`. Verification state needs a separate `is_verified` column.
- No DRF token API / no `/api/` routes exist (Item 7 is a report, not a build).

---

## Task 1: Password reset (Tier 1, item 1)

**Files:**
- Modify: `site1/site1/settings.py` (PASSWORD_RESET_TIMEOUT, document SMTP env vars)
- Modify: `site1/home/urls.py` (5 reset routes, rate-limited request view)
- Create: `site1/templates/registration/password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, `password_reset_email.html`, `password_reset_subject.txt`
- Modify: `site1/templates/registration/login.html` (forgot-password link)

- [ ] Add `PASSWORD_RESET_TIMEOUT = 3600` to settings.
- [ ] Wire stock `PasswordResetView` / `PasswordResetDoneView` / `PasswordResetConfirmView` / `PasswordResetCompleteView` in urls with template + email template overrides. Wrap the request view (`PasswordResetView`) with `ratelimit(key='ip', rate='5/m', method='POST', block=True)` — separate from login limiter, stops enumeration/spam.
- [ ] Build the four page templates + email + subject.
- [ ] Add "Forgot your password?" link on login page → `{% url 'password_reset' %}`.
- [ ] EMAIL_BACKEND already switches SMTP/console on `GMAIL_APP_PASSWORD`. Document required prod env vars in settings comment; keep console for dev.
- [ ] Verify: stock done-page renders identically whether email exists or not (no enumeration). `runserver` + curl POST for a real and a fake email, diff responses.

## Task 2: Session fixation (Tier 1, item 2)

**Files:** none expected.

- [ ] Confirm both `login_view` and `register_view` route through `django.contrib.auth.login()` (they do → `cycle_key()` runs). Demonstrate key change with a shell script using `RequestFactory` + `login()`. Report "already closed."

## Task 3: Account lockout per-username (Tier 1, item 3)

**Files:**
- Modify: `requirements.txt` (django-axes==8.3.1)
- Modify: `site1/site1/settings.py` (INSTALLED_APPS axes, AUTHENTICATION_BACKENDS axes first, MIDDLEWARE AxesMiddleware last, AXES_* config)
- Modify: `site1/home/views.py:407` (`authenticate(request, ...)` — pass request)

- [ ] `pip install django-axes==8.3.1`, pin in requirements.
- [ ] settings: add `axes` to INSTALLED_APPS; `axes.backends.AxesStandaloneBackend` first in AUTHENTICATION_BACKENDS; `axes.middleware.AxesMiddleware` last in MIDDLEWARE; `AXES_LOCKOUT_PARAMETERS = [["username"]]`; `AXES_FAILURE_LIMIT = 5`; `AXES_COOLOFF_TIME = timedelta(minutes=30)` (FLAG for confirmation); `AXES_RESET_ON_SUCCESS = True`.
- [ ] Fix `login_view` to pass `request` to `authenticate()` so axes can record attempts.
- [ ] `manage.py migrate axes` against SQL Server; confirm clean.
- [ ] Verify: 6 failed POSTs to `/accounts/login/` for one username → 6th blocked by axes (not just ratelimit). Confirm the existing IP ratelimit still coexists.

## Task 4: CSP header (Tier 2, item 4)

**Files:**
- Modify: `requirements.txt` (django-csp)
- Modify: `site1/site1/settings.py` (middleware + CSP config, report-only first)

- [ ] Install django-csp, pin.
- [ ] Add CSP middleware. Start report-only. default-src 'self'; no inline script execution. Inventory inline `<script>` blocks (home.html, base.html, reservation.html, room_dashboard.html) and Google Maps iframe (frame-src) before enforcing.
- [ ] Verify report-only emits `Content-Security-Policy-Report-Only` header via curl -I. Flip to enforced only after confirming templates keep working. FLAG: CSP does not govern email clients, so it does not actually mitigate the `campaign.html` email XSS — real fix is HTML sanitization of `body_html`; note for Peter.

## Task 5: CSRF trusted origins + cookie settings (Tier 2, item 5)

**Files:** Modify `site1/site1/settings.py`.

- [ ] `CSRF_TRUSTED_ORIGINS` from env `CSRF_TRUSTED_ORIGINS` (comma-split). Mark `[MISSING: production domain]` in comment since deploy domain unknown (Railway removed).
- [ ] `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE = 'Lax'`. SECURE cookie flags already set under `if not DEBUG`.

## Task 6: Email verification on signup (Tier 2, item 6)

**Files:**
- Modify: `site1/data/models/hotel.py` (add `is_verified` field to User, managed=False)
- Create: `site1/data/migrations/000X_user_is_verified.py` (RunSQL ALTER TABLE, reversible)
- Create: token generator (reuse reset infra) in `site1/home/tokens.py`
- Modify: `site1/home/views.py` (register sets is_verified=0, sends email, no auto-login; add verify + resend endpoints; login blocks unverified)
- Modify: `site1/home/urls.py` (verify + resend routes, resend rate-limited)
- Create: verification email + "check your inbox" / "verified" templates

- [ ] Add `is_verified` column via RunSQL migration (`DEFAULT 1` so existing users unaffected; new signups 0). FLAG: schema change to unmanaged table.
- [ ] `EmailVerificationTokenGenerator(PasswordResetTokenGenerator)` keyed on pk + is_verified + email.
- [ ] Register: create user is_verified=0, send verification link, show "check inbox" (no login).
- [ ] Verify endpoint sets is_verified=1 then logs in. Resend endpoint rate-limited (`3/m`).
- [ ] login_view blocks unverified with message + resend link.
- [ ] Verify: register → not logged in; click link → verified + logged in; unverified login blocked.

## Task 7: API token security (Tier 2, item 7)

- [ ] Report only: no DRF TokenAuthentication, no api key model, no `/api/` routes. DRF is an unused dependency. Nothing to secure. Flag assumption back to Peter.

---

## Cross-cutting
- Run `security-review` after each Tier 1 item.
- Run `code-review` on the full diff before reporting.
- No plaintext secrets committed; `.env` stays untracked.
- Commit directly to `main` per project git workflow.

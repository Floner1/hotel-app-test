# Implementation Plan — Newsletter Signup + Discount Code System

**Project:** hotel-app-test (Django 5.2, SQL Server via mssql-django, Bootstrap 4, jQuery)
**Date:** 2026-05-31
**Status:** Implemented (2026-06-06 to 2026-06-07)

## Implementation notes (added 2026-06-07)

The system was built largely as planned. A few clarifications were resolved during implementation:

- **C1 (code re-display):** Resolved against re-displaying the code. The "already subscribed" step now says "check your inbox for the original email." No code is shown in the popup or footer response.
- **C3 (client-side discount preview):** Implemented. The reservation form tracks `discountPercent` in JS and updates the running total live when a valid code is validated on blur.
- **C4 (popup copy):** Static, not inline-editable.
- **C5 (email send timing):** Synchronous. The welcome email sends inline during the signup request. Acceptable for v1.

One change from the plan: the footer newsletter form no longer opens the discount popup on submit. It submits via AJAX directly and shows inline feedback in `#newsletter-feedback`. The popup remains a separate entry point, auto-shown once per session on the home page only.

The discount code field on the reservation form no longer requires the email field to be filled before validating. The email check happens server-side at redemption time, not at the validation step.

---

## Decisions locked (from Q&A)

1. **Reuse `EmailSubscriber`** + add a **new `DiscountCode` table/model**. Do not duplicate the subscriber concept.
2. **Code binds to the email typed in the booking form.** The discount field on the reservation form carries helper text: *"Enter the code you received for the email address you're booking with."* Validation compares the code's issued email to the reservation form's email field, case-insensitive.
3. **Popup on all public pages, hidden for authenticated users.** Suppressed on dashboards and once dismissed (localStorage).
4. **Apply discount by reducing `booking_info.total_price`;** record the redemption (`redeemed_at`, `redeemed_booking_id`, `status`) on the `discount_codes` row. No `booking_info` schema change.

---

## ⚠️ Scope authorization note

`CLAUDE.md` restricts edits to frontend files "unless explicitly asked." This task **explicitly asks** for a full-stack feature, which overrides that restriction for this work. The plan therefore touches backend files (SQL schema, models, repositories, services, views, urls) **and** frontend files. The CLAUDE.md design-system rules (tokens, `var(--ease)`, no decorative emoji, radius tokens, etc.) still apply to every template/CSS change.

---

## 1. Every new or modified file and why

### New files

| File | Why |
|---|---|
| `tables v10 for hotel.sql` (repo root) | Adds the `discount_codes` table. Schema is owned by SQL, not Django (`managed = False`). Must be applied manually to SQL Server. |
| `site1/data/models/discount.py` | New `DiscountCode` model (`managed = False`) mapped to `discount_codes`. |
| `site1/templates/email/welcome_discount.html` | The welcome email that delivers the code; extends `email/base_email.html`. |
| `site1/templates/_discount_popup.html` | The signup popup markup, included site-wide from `base.html`. |

### Modified files

| File | Change |
|---|---|
| `site1/data/models/__init__.py` | Import + export `DiscountCode`. |
| `site1/data/repos/repositories.py` | New `DiscountRepository` (issue, lookup, validate, redeem, unique-code generation). |
| `site1/backend/services/services.py` | New `DiscountService`; integrate validation/redemption into `ReservationService.create_reservation`; add `EmailService.queue_welcome_discount`; add `'discount_welcome'` to `EmailQueue.EMAIL_TYPES` (display only). |
| `site1/home/views.py` | Augment `newsletter_signup` to issue a code + send the welcome email + return the code in JSON; pass `discount_code` from the reservation POST into the service. |
| `site1/templates/base.html` | `{% include "_discount_popup.html" %}` (guarded for non-authenticated/public pages); popup show/dismiss/submit JS; extend the existing footer-newsletter success handler to surface the returned code. |
| `site1/templates/reservation.html` | Add an optional **Discount code** field + helper text; include it in the AJAX payload; optionally reflect 10% in the live estimate. |
| `site1/static/css/style.css` | Popup + discount-field + code-chip styles, all using existing design tokens. |
| `site1/home/context_processors.py` *(only if popup copy is made inline-editable)* | Expose popup copy keys. **[NEEDS CLARIFICATION: should popup headline/copy be admin-inline-editable like footer `data-ct-key` fields, or static?]** |

> Note: there is **no Django migration file**. All three email tables and the existing domain tables are `managed = False`; the project applies schema by hand-running the `tables vN` SQL. `discount_codes` follows the same convention.

---

## 2. The data model — `DiscountCode`

The spec's "NewsletterSubscriber" requirement is satisfied by the **existing** `EmailSubscriber` (the subscriber identity) **plus** this new `DiscountCode` (the per-email single-use code). One code per email enforces "no duplicates" at the DB level.

### SQL (`tables v10 for hotel.sql`) — matches existing schema conventions

```sql
CREATE TABLE discount_codes (
    id                 INT IDENTITY(1,1) PRIMARY KEY,
    code               NVARCHAR(20)  NOT NULL UNIQUE,
    email              NVARCHAR(255) NOT NULL UNIQUE,   -- one code per email
    subscriber_id      INT NULL,
    discount_percent   INT NOT NULL DEFAULT 10,
    status             NVARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','redeemed','expired','void')),
    issued_at          DATETIME DEFAULT GETDATE(),
    redeemed_at        DATETIME NULL,
    redeemed_booking_id INT NULL,
    created_at         DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_discount_subscriber FOREIGN KEY (subscriber_id) REFERENCES email_subscribers(id),
    CONSTRAINT fk_discount_booking    FOREIGN KEY (redeemed_booking_id) REFERENCES booking_info(booking_id)
);
GO
CREATE INDEX ix_discount_codes_email ON discount_codes (email);
GO
```

### Django model (`site1/data/models/discount.py`)

| Field | Type | Constraints / notes |
|---|---|---|
| `id` | `AutoField` PK | identity |
| `code` | `CharField(max_length=20)` | `unique=True`; generated, see §3 |
| `email` | `EmailField(max_length=255)` | `unique=True` — enforces single code per email |
| `subscriber` | `ForeignKey('EmailSubscriber', DO_NOTHING, null=True, blank=True, db_column='subscriber_id')` | link to subscriber row |
| `discount_percent` | `IntegerField(default=10)` | flexible, defaults to the 10% rule |
| `status` | `CharField(max_length=20, choices=...)` | `active` / `redeemed` / `expired` / `void`, default `active` |
| `issued_at` | `DateTimeField(null=True, blank=True)` | set at creation |
| `redeemed_at` | `DateTimeField(null=True, blank=True)` | set on redemption |
| `redeemed_booking` | `ForeignKey('CustomerBookingInfo', DO_NOTHING, null=True, blank=True, db_column='redeemed_booking_id')` | audit link |
| `created_at` | `DateTimeField(null=True, blank=True)` | GETDATE() default |

`Meta`: `db_table = 'discount_codes'`, `managed = False`, `ordering = ['-created_at']`.

**Single-use** is enforced by `status` (only `active` is redeemable) + a `SELECT ... FOR UPDATE` lock during redemption (§4). **No duplicates** is enforced by `UNIQUE(email)` + get-or-issue logic (§3).

---

## 3. Full data flow: signup → layers → database → email

Both the **footer form** (`#newsletter-form`, existing) and the **new popup form** POST to the same endpoint: `newsletter_signup` (`/newsletter/signup/`, AJAX, rate-limited 3/min/IP). One endpoint, augmented.

```
Popup/Footer form (email)
  └─ POST /newsletter/signup/  (X-Requested-With: XMLHttpRequest, csrf)
       └─ views.newsletter_signup
            1. validate_email(email)                          [existing]
            2. EmailRepository.create_subscriber(email,...)   [existing]
                 → (subscriber, created)                       idempotent; reactivates unsubscribed
            3. DiscountService.issue_for_subscriber(subscriber, email)
                 └─ DiscountRepository.get_or_issue_for_email(email, subscriber)
                      → (discount, code_created)
                      • existing row  → return it, code_created=False
                      • no row        → generate unique code, INSERT, return it, True
            4. EmailService.queue_welcome_discount(subscriber, discount)   [non-fatal]
                 └─ EmailService._send(template='email/welcome_discount.html',
                                       email_type='discount_welcome', ...)
                      render → send_email() → log row in email_queue
            5. JsonResponse:
                 • code_created  → {status:'ok', code:<CODE>, message:'Here is your 10% code…'}
                 • already had   → {status:'ok', code:<CODE>?, already:true,
                                    message:'You already have a code — check your email.'}
```

### Layer responsibilities

- **View (`newsletter_signup`)** — request parsing, email validation, rate-limit, orchestration, JSON shaping. No business rules.
- **`DiscountService.issue_for_subscriber`** — business policy ("one code per email", 10%, what status a new code gets). Wraps the repository; never raises into the view (returns a result object/tuple).
- **`DiscountRepository.get_or_issue_for_email`** — pure data access + unique-code generation. Idempotent by `email`.
- **`EmailService.queue_welcome_discount`** — render + send + log; never raises (mirrors existing `_send` contract).

### Code generation (`DiscountRepository._generate_unique_code`)
- Format `TT10-XXXXXX` — prefix `TT10` + 6 chars from an unambiguous alphabet (`ABCDEFGHJKMNPQRSTUVWXYZ23456789`, excludes `0/O/1/I/L`) via `secrets.choice`.
- Loop: generate → check `DiscountCode.objects.filter(code=...).exists()` → retry on collision (cap ~5 attempts, then raise).

### "Already have a code" behavior
Per spec: do **not** issue another; tell them they already have one. **[NEEDS CLARIFICATION: when the email already has a code, should the JSON re-display the existing code in the popup, or only say "check your email" without revealing it? Default in this plan: re-display it — it's the user's own email and reduces support friction.]**

---

## 4. Full discount validation + redemption flow at booking

The reservation POST already requires login and runs through `ReservationService.create_reservation` inside a single `transaction.atomic()` block (which already `select_for_update()`s the room rate). Discount handling slots into that same block so room allocation + redemption commit atomically.

```
views.get_reservation (POST)
  └─ reservation_data['discount_code'] = request.POST.get('discount_code','').strip()   [NEW]
  └─ ReservationService.create_reservation(reservation_data)
       … parse dates, resolve rate, compute total_cost = rate * nights …
       with transaction.atomic():                                  [existing block]
         RoomPrice.select_for_update()…                            [existing]
         availability check…                                       [existing]
         ── DISCOUNT (NEW) ──────────────────────────────
         code = reservation_data.get('discount_code')
         applied_discount = None
         if code:
           disc = DiscountCode.objects.select_for_update()
                    .filter(code__iexact=code).first()              # row lock → no double-redeem
           DiscountService.validate(disc, code, booking_email):
             • disc is None              → ValidationError('Discount code not found.')
             • disc.status != 'active'   → ValidationError('This code has already been used.')
             • disc.email != email (ci)  → ValidationError('This code was issued to a different email.')
             • (optional expiry)         → ValidationError('This code has expired.')
           total_cost = (total_cost * (100 - disc.discount_percent)/100)
                          .quantize(0.01, ROUND_HALF_UP)
           applied_discount = disc
         ────────────────────────────────────────────────
         booking = ReservationRepository.create({... total_price: total_cost ...})
         if applied_discount:
           DiscountRepository.redeem(applied_discount, booking)     # status='redeemed',
                                                                     # redeemed_at, redeemed_booking_id
         RoomService.allocate_room(booking, …)                      [existing]
       # after commit:
       EmailService.queue_booking_confirmation(booking.booking_id)  [existing — shows discounted total]
```

- **Invalid code** → `ValidationError` → existing view handler returns HTTP 400 JSON with the message; the reservation is **not** created (whole transaction rolls back). The reservation form's existing error path already renders that message.
- **Single-use guarantee** — the `select_for_update()` on the discount row serializes two concurrent bookings using the same code; the second sees `status='redeemed'` and is rejected.
- **`booked_rate` stays the undiscounted nightly rate**; only `total_price` reflects the discount. The audit of *which* code produced the discount lives on `discount_codes.redeemed_booking_id`.
- The booking confirmation email automatically reflects the reduced `total_price`. **[NEEDS CLARIFICATION: should the confirmation email show an explicit "Discount applied (-10%)" line? Requires passing the applied discount into the confirmation context. Default: not in v1 — the total is simply lower.]**

---

## 5. Exact template insertion points

### a) Popup — `_discount_popup.html` included from `base.html`
- In `base.html`, immediately after the `{% block navbar %}` include and before `{% block content %}` (around line 41–44), add:
  ```django
  {% if not user.is_authenticated %}{% include "_discount_popup.html" %}{% endif %}
  ```
  Authenticated users (including staff/admin dashboards) never see it. localStorage gates once-only display.
- Popup contains: backdrop, a card with a close (×) button, a short headline + copy, an `<input type="email">` + Subscribe button (`type="submit"`), and a hidden **result area** that reveals the code after success.
- JS lives in `base.html` `extra` script area (or `main.js`): on `DOMContentLoaded`, if `localStorage.getItem('ttDiscountPopupSeen')` is unset, show after a short delay; on close **or** successful submit, `setItem('ttDiscountPopupSeen','1')`. Submit reuses the same `$.ajax` pattern as the footer form (`X-Requested-With`, csrf), then renders `data.code` into the result area.

### b) Footer wiring — already present
- `_footer.html` already has `#newsletter-form` (lines 42–50). **No structural change required.**
- In `base.html`, the existing `#newsletter-form` `success` handler (lines 87–121) is extended: when `data.code` is present, show it (e.g., append to the toast text "Your code: TT10-XXXXXX — check your inbox"). Optionally add a small result `<span>` to `_footer.html` for inline display.

### c) Reservation discount field — `reservation.html`
- Insert a new `form-group` **after the email row (lines 92–97) and before the dates row**, or directly **above the `reservation-total` box (line 160)**. Recommended placement: just above the totals box so the discount sits next to the price.
  ```django
  <div class="row">
    <div class="col-md-12 form-group">
      <label for="discount_code">Discount code</label>
      <input type="text" id="discount_code" name="discount_code" class="form-control"
             placeholder="Optional">
      <small class="form-text text-muted">
        Enter the code you received for the email address you're booking with.
      </small>
    </div>
  </div>
  ```
- In the page's AJAX `formData` (around lines 295–306), add `'discount_code': $('#discount_code').val()`.
- Optional: extend `updateTotal()` (lines 230–245) to subtract 10% client-side when a code is entered — **estimate only**, clearly labeled; the server is authoritative. **[NEEDS CLARIFICATION: live client-side preview of the discount, or only reflect it in the server response? Default: skip client preview in v1 to avoid implying validation the client can't perform.]**

---

## 6. Exact colours, fonts, and CSS variables to use

### Popup + reservation discount field (use tokens from `style.css :root`)
- Backdrop: `rgba(0,0,0,0.5)` overlay (one allowed raw value — overlay scrim; **[NEEDS CLARIFICATION: acceptable, or define a token?]**).
- Card surface: `--color-bg` (`#ffffff`); border `1px solid var(--color-border)` (`#e5e7eb`); `border-radius: var(--radius-md)` (8px).
- CTA / Subscribe button: `background: var(--color-primary)` (`#ffba5a`); `border-radius: var(--radius-md)`; hover `translateY(-4px)` max with ≤8px shadow spread (CLAUDE.md cap).
- Code chip (revealed code): `1px dashed var(--color-accent)` (`#d49040`), `background: var(--color-surface)` (`#f9fafb`), monospace, `--text-h3` size.
- Headline font: **Playfair Display** (`.font-family-serif`); body font: **Roboto** (`.font-family-sans-serif`).
- Text: `--color-text` (`#1a1a1a`); helper/muted: `--color-text-muted` (`#6b7280`).
- Type scale: headline `--text-h2`/`--text-h3`, body `--text-body`, helper `--text-caption`.
- Spacing: `--space-sm` / `--space-md` / `--space-lg` only.
- All transitions: `var(--duration-base) var(--ease)` — **never** bare `ease`/`linear` (CLAUDE.md). Popup entrance reuses the existing `.tt-fade-in` / `tt-appear` keyframe rather than a new animation.

### Welcome email — `welcome_discount.html` extends `email/base_email.html`
Email clients don't support CSS variables, so use the **literal hex equivalents** of the tokens (consistent with the existing email templates):
- Header band: `#ffba5a` (= `--color-primary`); header title `#1a1a1a`.
- Body text `#1a1a1a`, `line-height:1.6`, `font-family:Arial,Helvetica,sans-serif` (email-safe — site web fonts are intentionally not used in email, matching existing convention).
- **Code box**: `border:1px dashed #d49040` (= `--color-accent`), `background:#f9fafb` (= `--color-surface`), code text `#1a1a1a`, bold, ~22px.
- Footer band `#f9fafb`, muted text `#6b7280`, unsubscribe link `#d49040` — all inherited from `base_email.html`.
- The `{% block extra %}` slot in `base_email.html` is the natural home for the prominent code/CTA box.

---

## 7. Conflicts and risks in existing code

1. **CLAUDE.md frontend-only scope** — overridden by the explicit full-stack request, but worth re-confirming before backend edits land. Design-system rules still bind all template/CSS work.
2. **Naming mismatch** — spec says "NewsletterSubscriber"; we reuse `EmailSubscriber` + add `DiscountCode`. (Resolved by Q&A, noted for the reviewer.)
3. **`managed = False` / no migrations** — `discount_codes` must be created by **manually running** `tables v10 for hotel.sql` against SQL Server. Forgetting this → `OperationalError` at runtime. Add a clear "run this SQL first" note to the PR.
4. **Synchronous email send in the request** — `queue_welcome_discount` sends inline (like contact/booking emails), so a slow SMTP handshake can add up to `EMAIL_TIMEOUT` (15s) to the signup response and make the popup feel slow. Mitigation: the code is generated and returned **before**/independent of the email result, and `_send` never raises. **[NEEDS CLARIFICATION: acceptable for v1, or should signup return immediately and defer the email?]**
5. **`email_type` choices** — `EmailQueue.EMAIL_TYPES` lacks a discount type. The DB column has **no CHECK constraint** on `email_type`, so `'discount_welcome'` inserts fine; adding it to the model `choices` is display-only (admin email log). Minor backend edit.
6. **Booking email is free-text** — a guest can enter any email in the reservation form. Binding the code to the form email (per Q&A) means someone could try another person's code if they know both the code and that email. The `UNIQUE(email)`/single-use design limits damage to one redemption; acceptable for a hotel promo. The helper-text wording reduces honest-user confusion.
7. **Rate limiting** — `newsletter_signup` is 3/min/IP on POST. The popup auto-*shows* without POSTing, so it won't trip the limit; only submissions count. Fine.
8. **Popup on `base.html`** — confirm every public page extends `base.html` and that error pages (`403/404/500`) and dashboards won't render an unwanted popup. The `{% if not user.is_authenticated %}` guard plus localStorage covers dashboards/staff; verify the standalone error templates don't include it unintentionally.
9. **`select_for_update` on SQL Server** — already used in `create_reservation` for `RoomPrice`, so the pattern is proven on this stack. Adding a second locked row (discount) in the same transaction is consistent.
10. **Re-subscribe path** — `create_subscriber` reactivates an unsubscribed row (same `id`); `get_or_issue_for_email` keys on `email`, so the user keeps their original single code. No duplicate issued. Correct.

---

## 8. Exact execution order

1. **SQL** — add `tables v10 for hotel.sql` with `discount_codes`; run it against the dev SQL Server. Verify the table + FKs + unique constraints exist.
2. **Model** — add `site1/data/models/discount.py` (`DiscountCode`); import/export in `data/models/__init__.py`. Sanity-check with a Django shell query.
3. **Repository** — add `DiscountRepository` to `repositories.py`: `_generate_unique_code`, `get_or_issue_for_email`, `get_by_code`, `validate_for_redemption`, `redeem`.
4. **Service** — add `DiscountService` (issue/validate) to `services.py`; add `EmailService.queue_welcome_discount`; add `'discount_welcome'` to `EMAIL_TYPES`. Then wire discount validation/redemption into `ReservationService.create_reservation` inside the existing atomic block.
5. **Email template** — add `email/welcome_discount.html` extending `base_email.html`; render-test via the shell.
6. **Views** — augment `newsletter_signup` (issue code, send welcome email, return `code` in JSON); add `discount_code` to the `reservation_data` built in `get_reservation`.
7. **Frontend — reservation** — add the discount field + helper text to `reservation.html`; include it in the AJAX payload.
8. **Frontend — popup + footer** — add `_discount_popup.html`; include it (guarded) in `base.html`; add popup show/dismiss/submit JS + localStorage; extend the footer success handler to surface the code; add popup/chip CSS to `style.css` using tokens.
9. **End-to-end verification:**
   - New email via popup → row in `email_subscribers` + `discount_codes`, welcome email logged in `email_queue`, code shown in popup.
   - Same email again → no new code, "already have a code" response.
   - Book with a valid code (matching form email) → `total_price` reduced 10%, `discount_codes` row → `redeemed` with `redeemed_booking_id`.
   - Reuse the same code → rejected "already been used"; booking not created.
   - Wrong-email code → rejected.
   - Popup: appears once for anonymous users, never after dismiss/submit, never for logged-in users.

---

### Open clarifications (collected)
- C1 — "Already have a code": re-display the code or only "check your email"? (default: re-display)
- C2 — Confirmation email: explicit "−10% discount" line? (default: no, total just lower)
- C3 — Reservation form: client-side discount preview in the estimate? (default: no)
- C4 — Popup copy: admin-inline-editable (`data-ct-key`) or static? (default: static)
- C5 — Welcome email: synchronous (default) vs deferred send?
- C6 — Backdrop scrim `rgba(0,0,0,0.5)` raw value vs a new token?

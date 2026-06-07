# Design spec: home page hero redesign and booking widget

**Date:** 2026-06-06
**Status:** Implemented. Widget color scheme redesigned 2026-06-07 (see update at bottom).

---

## Overview

Redesign the Thien Tai Hotel homepage hero to push the title into the upper third of the viewport and add a booking widget that straddles the hero/content boundary. The widget pre-fills the reservation page via GET params.

---

## Hero changes

**Overlay:** Replaced flat `rgba(0,0,0,0.45)` with a vertical gradient, nearly transparent at the top and darkening to `rgba(0,0,0,0.64)` at the bottom. Keeps the photo readable while giving the widget enough contrast.

**Title position:** Changed `.site-hero-inner` from `align-items: center` to `align-items: flex-start` with `padding-top: 20vh`. Title sits at roughly the upper quarter of the viewport.

**Mobile:** Title drops to `2.25rem` with `white-space: normal` below 768px. Padding-top reduces to `14vh`.

**Scroll indicator:** Moved from `bottom: 20px` to `bottom: 64px` to clear the booking widget.

---

## Booking widget

**Position:** `position: absolute; bottom: 0; left: 50%; transform: translateX(-50%) translateY(50%)`. Straddles the hero bottom edge, overlapping the section below by half its height.

**Card (original dark version, 2026-06-06):** `rgba(10,10,10,0.97)` background, `1px solid rgba(255,255,255,0.07)` border, `border-radius: var(--radius-md)`, large drop shadow.

**Fields (desktop, left to right):**
1. Destination: static "Thien Tai Hotel" in Playfair Display italic
2. Check In: `input[type=text]` with bootstrap-datepicker (`format: mm/dd/yyyy`, `startDate: today`)
3. Check Out: same, minDate auto-advances to the day after check-in
4. Room type: custom dropdown listing room types from the database
5. Guests: counter panel for adults (1-4)
6. Check Rates button: `background: var(--color-primary)`, uppercase

**Mobile (<768px):** Fields stack vertically. Button goes full width.

**Section below:** Gets `padding-top: calc(3rem + 72px)` to compensate for widget overlap (200px on mobile).

---

## Form behavior

**Validation:** Client-side check before submit. Fields with no value get `.bw-field-invalid` (red label). Prevents empty GET submission.

**Loading state:** On valid submit, button text changes to "Loading..." and is disabled.

**Check Rates URL:** `GET /reservation/?checkin_date=MM/DD/YYYY&checkout_date=MM/DD/YYYY&adults=N&room_type=X`

**Pre-fill on reservation page:** `reservation.html` reads `URLSearchParams` on load and sets `#checkin_date`, `#checkout_date`, `#adults`, and `#room_type` values, firing `change input` events so the price calculation updates.

---

## Date library

Uses bootstrap-datepicker (already loaded globally in `base.html`). No new dependency. Format: `mm/dd/yyyy` to match what the reservation service expects. `orientation: 'top left'` keeps the calendar opening upward and left-aligned when the widget sits at the viewport bottom.

---

## Files changed

- `site1/templates/home.html`: CSS, hero HTML, booking widget HTML, datepicker JS
- `site1/templates/reservation.html`: GET param pre-fill script

---

## Council verdict applied

LLM Council (2026-06-06) confirmed Flatpickr over native inputs for cross-browser consistency. Implementation uses bootstrap-datepicker instead (already in the project). Key findings applied:

- Separate check-in/check-out fields (not range mode) to match the `checkin_date`/`checkout_date` GET param contract
- Date format verified from `reservation.html` `formatDateForSubmit` function: `MM/DD/YYYY`
- Design tokens used throughout widget CSS

---

## Update: 2026-06-07 widget redesign

The widget color scheme was changed from dark/glass to light/white. The reasoning: the dark translucent card was hard to read against some hero images and the dropdown panels clipped in some scroll positions.

**What changed:**

Card background changed from `rgba(10,10,10,0.97)` to `rgba(255,255,255,0.92)` with a standard box shadow. All field text, labels, and values changed from white/rgba-white to dark grays (`#111827`, `#374151`). Dropdown panels changed from dark glass to white with `1px solid #e5e7eb`. Datepicker calendar sized down and orientation locked to `top left`.

The widget position and field layout stayed the same. No structural HTML changes.

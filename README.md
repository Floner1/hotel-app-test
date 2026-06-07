# Thien Tai hotel booking system

A Django app for managing hotel reservations at Thien Tai Hotel. SQL Server backend, Bootstrap 4 frontend, role-based access control.

## Quick start

```bash
cd site1
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

## Technologies

- Django 5.2.4, Python 3.x
- SQL Server via mssql-django (Windows Authentication)
- Bootstrap 4, jQuery
- Three-layer architecture: Presentation, Application, Data

## What it does

### Booking flow

The homepage has a booking widget fixed to the bottom of the hero image. Guests fill in check-in date, check-out date, guest count, and room type, then click through to the reservation form. The form pre-fills those values from the URL.

On the reservation form there's an "Any room" option. Pick it and the system randomly selects an available room type and shows a confirmation modal before submitting. A discount code field lets guests apply a code they received by email. The running total updates live when a valid code is entered.

All reservations require login. Customers see only their own bookings.

### Newsletter and discounts

The footer has a newsletter signup form that submits by AJAX and shows feedback inline (no page reload). On the home page, a slide-in popup offers 10% off a booking in exchange for a newsletter signup. It appears once per browser session for guests who aren't logged in.

Each email address gets one discount code. The code is emailed immediately after signup, then validated at booking time. Codes are single-use and tied to the subscriber's email address.

### Admin

- Booking management dashboard with status tracking: pending, confirmed, cancelled, completed
- Email campaign editor and subscriber list
- Email log showing every outbound message
- Room dashboard
- User account management

### Security

Database-level triggers enforce RBAC. A session context column tracks which user is acting. Bookings can only be modified by their owner (or staff). The audit log is append-only.

## Project structure

```
hotel-app-test/
├── CLAUDE.md
├── README.md
├── tables v10 for hotel.sql    ← current SQL schema — apply manually to SQL Server
├── docs/
│   └── plans/
│       └── newsletter-discount-plan.md
└── site1/
    ├── manage.py
    ├── site1/                  ← Django config (settings, urls, wsgi)
    ├── home/                   ← views and URL routing
    ├── backend/services/       ← business logic layer
    ├── data/                   ← models and repositories
    ├── templates/              ← all HTML templates
    └── static/                 ← CSS, JS, images
```

## Database tables

- `users`: accounts and roles
- `hotel_info`: hotel details
- `room_price`: room types and nightly rates
- `booking_info`: guest reservations
- `hotel_services`: services list
- `customer_requests`: modification requests from guests
- `audit_log`: append-only change history
- `email_subscribers`: newsletter subscribers
- `discount_codes`: single-use codes, one per email address
- `email_queue`: outbound email log

No Django migration files. The schema is applied by running the latest `tables vN for hotel.sql` file directly against SQL Server.

## Common commands

```bash
cd site1

# Start dev server
python manage.py runserver

# Collect static files
python manage.py collectstatic --noinput

# Django shell
python manage.py shell
```

## Database connection

- **Server:** DESKTOP-NS6H7CH\MSSQLSERVER01
- **Database:** hotelbooking
- **Auth:** Windows Authentication
- **Driver:** SQL Server Native Client 11.0

## User roles

- **Admin**: full access to all bookings, users, hotel config, and audit log
- **Staff**: view and manage bookings, confirm or cancel reservations
- **Customer**: make reservations (login required), view own bookings, request modifications

## Troubleshooting

**Site won't load**

```bash
cd site1
python manage.py migrate
python manage.py collectstatic --noinput
```

Confirm SQL Server is running first.

**Static files missing:** run `collectstatic`.

**Database errors:** check that SQL Server is running and that `.env` has the correct connection string. Windows Authentication means the process user needs access to the `hotelbooking` database.

**Discount codes not issuing:** the `discount_codes` table must exist. Run `tables v10 for hotel.sql` against the database if you haven't already.

# Thien Tai Hotel Booking System

A Django web application for managing hotel reservations at Thien Tai Hotel. SQL Server backend, Bootstrap 4 frontend, role-based access control.

---

## System requirements

Before you begin, make sure you have the following installed on your machine. This project runs on **Windows only** because it uses Windows Authentication to connect to SQL Server.

- **Python 3.11 or newer** — [python.org/downloads](https://www.python.org/downloads/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **Microsoft SQL Server** (any edition — Express is free) — [microsoft.com/en-us/sql-server/sql-server-downloads](https://www.microsoft.com/en-us/sql-server/sql-server-downloads)
- **ODBC Driver 17 for SQL Server** — [learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- **SQL Server Management Studio (SSMS)** (optional but strongly recommended) — [learn.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms](https://learn.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms)

---

## Installation

### 1. Verify Python is installed

Open a terminal (Command Prompt or PowerShell) and run:

```
python --version
```

You should see `Python 3.11.x` or higher. If not, install Python first and make sure "Add Python to PATH" is checked during installation.

### 2. Verify Git is installed

```
git --version
```

### 3. Clone the repository

```
git clone https://github.com/Floner1/hotel-app-test.git
cd hotel-app-test
```

### 4. Create a virtual environment

```
python -m venv venv
```

### 5. Activate the virtual environment

```
venv\Scripts\activate
```

Your terminal prompt should now show `(venv)` at the start. You must do this every time you open a new terminal before running any project commands.

### 6. Install Python dependencies

```
pip install -r requirements.txt
```

This installs Django, mssql-django, pyodbc, and all other packages the project needs. It may take a minute.

### 7. Verify ODBC Driver 17 is installed

Open the Windows start menu, search for "ODBC Data Sources", and open it. Click the "Drivers" tab and confirm "ODBC Driver 17 for SQL Server" appears in the list. If it does not, download and install it from the link in the system requirements section above.

### 8. Set up the SQL Server database

**a. Open SQL Server Management Studio (SSMS)**

Connect to your SQL Server instance. The instance name is usually in the format `COMPUTERNAME\INSTANCENAME` (for example, `DESKTOP-NS6H7CH\MSSQLSERVER01`). Use Windows Authentication.

**b. Create the database**

In the Object Explorer panel on the left, right-click "Databases" and choose "New Database". Name it `hotelbooking` and click OK.

Alternatively, open a New Query window and run:

```sql
CREATE DATABASE hotelbooking;
```

**c. Apply the schema**

In SSMS, open the file `tables v10 for hotel.sql` from the project root (File → Open → File). Make sure the database dropdown at the top of the query window is set to `hotelbooking`, then press F5 or click Execute.

This creates all tables, indexes, triggers, and seeds the database with hotel info, room types, room inventory, and three default user accounts.

### 9. Create the environment file

Create a file at `site1/.env` with the following content:

```
DJANGO_SECRET_KEY=replace-this-with-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

`DJANGO_SECRET_KEY` is required. Django will refuse to start without it. Generate a random one — it just needs to be a long string of random characters.

### 10. Configure the database connection (if needed)

The default database connection points to `DESKTOP-NS6H7CH\MSSQLSERVER01`. If your SQL Server instance name is different, add this line to `site1/.env`:

```
DB_HOST=YOUR_COMPUTER_NAME\YOUR_INSTANCE_NAME
```

To find your instance name, open SSMS and look at the "Server name" field in the connection dialog.

You do not need to set a username or password — the project uses Windows Authentication, which means it connects as whichever Windows user is running the Python process. Make sure that Windows account has access to the `hotelbooking` database in SQL Server.

### 11. Collect static files

```
cd site1
python manage.py collectstatic --noinput
```

This copies all CSS, JavaScript, and image files into the `staticfiles/` folder so Django can serve them.

### 12. Start the development server

```
python manage.py runserver
```

### 13. Open the site

Go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## Default accounts

The schema seeds three accounts into the database. Use these to log in without creating anything manually.

| Role     | Email                        | Password    |
|----------|------------------------------|-------------|
| Admin    | admin@thientaihotel.com      | admin123    |
| Staff    | staff@thientaihotel.com      | staff123    |
| Customer | customer@thientaihotel.com   | customer123 |

---

## Environment variables reference

All of these go in `site1/.env`. Only `DJANGO_SECRET_KEY` is required; the rest fall back to safe defaults.

| Variable                  | Default                          | Description                                                                 |
|---------------------------|----------------------------------|-----------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`       | *(none — required)*              | Long random string used for session signing. Keep this secret.              |
| `DJANGO_DEBUG`            | `False`                          | Set to `True` for local development to see detailed error pages.            |
| `DJANGO_ALLOWED_HOSTS`    | `localhost,127.0.0.1`            | Comma-separated list of hostnames Django will serve.                        |
| `DB_NAME`                 | `hotelbooking`                   | SQL Server database name.                                                   |
| `DB_HOST`                 | `DESKTOP-NS6H7CH\MSSQLSERVER01`  | SQL Server instance name.                                                   |
| `GMAIL_FROM_EMAIL`        | *(none)*                         | Gmail address used to send emails. Leave blank to use console backend.      |
| `GMAIL_APP_PASSWORD`      | *(none)*                         | Gmail App Password (not your Gmail login password). Required for real email.|
| `HOTEL_DEFAULT_PHONE`     | `+63 900 000 0000`               | Phone number shown on the site when the database value is missing.          |
| `HOTEL_DEFAULT_EMAIL`     | `info@hotelbooking.local`        | Contact email shown on the site when the database value is missing.         |
| `SITE_BASE_URL`           | `http://localhost:8000`          | Base URL used when building links inside emails (e.g. unsubscribe links).  |

---

## Common commands

All of these must be run from inside the `site1/` directory with the virtual environment activated.

```
cd site1

# Start the dev server
python manage.py runserver

# Collect static files (run this after any CSS/JS change)
python manage.py collectstatic --noinput

# Open the Django shell (for debugging or manual database queries)
python manage.py shell
```

---

## Project structure

```
hotel-app-test/
├── CLAUDE.md                       ← coding rules and design system
├── README.md                       ← this file
├── requirements.txt                ← Python dependencies
├── tables v10 for hotel.sql        ← current SQL Server schema (apply this manually)
├── docs/
│   └── plans/
└── site1/
    ├── .env                        ← local environment variables (not committed)
    ├── manage.py
    ├── site1/                      ← Django config (settings.py, urls.py, wsgi.py)
    ├── home/                       ← views, URL routing, auth backend
    ├── backend/services/           ← business logic layer
    ├── data/                       ← models and database repositories
    ├── templates/                  ← all HTML templates
    └── static/                     ← CSS, JavaScript, images
```

---

## Database tables

| Table                | Description                                                  |
|----------------------|--------------------------------------------------------------|
| `users`              | Accounts and roles (admin, staff, customer)                  |
| `hotel_info`         | Hotel name, address, contact details                         |
| `room_price`         | Room types and nightly rates                                 |
| `rooms`              | Individual room inventory with status tracking               |
| `booking_info`       | Guest reservations                                           |
| `room_assignments`   | Links a booking to a specific physical room                  |
| `hotel_services`     | Services offered (restaurant, laundry, motorbike rental)     |
| `customer_requests`  | Modification requests submitted by guests                    |
| `room_maintenance_logs` | Reported maintenance issues per room                      |
| `audit_log`          | Append-only change history                                   |
| `email_subscribers`  | Newsletter subscribers                                       |
| `discount_codes`     | Single-use 10% discount codes, one per email address         |
| `email_campaigns`    | Bulk email campaigns managed through the admin panel         |
| `email_queue`        | Log of every outbound email sent by the system               |

There are no Django migration files. The schema is applied by running `tables v10 for hotel.sql` directly against SQL Server.

---

## User roles

| Role     | Access                                                                                   |
|----------|------------------------------------------------------------------------------------------|
| Admin    | Full access: bookings, users, hotel config, room dashboard, email campaigns, audit log   |
| Staff    | View and manage bookings, confirm or cancel reservations, room dashboard                 |
| Customer | Make reservations (login required), view own bookings, request modifications             |

---

## What the site does

### Booking flow

The homepage has a booking widget fixed to the bottom of the hero image. Guests fill in check-in date, check-out date, guest count, and room type, then click through to the reservation form. The form pre-fills those values from the URL.

There is an "Any room" option on the reservation form — pick it and the system randomly selects an available room type, then shows a confirmation modal before submitting. A discount code field lets guests apply a code they received by email. The running total updates live when a valid code is entered.

All reservations require login. Customers see only their own bookings.

### Newsletter and discounts

The footer has a newsletter signup form that submits by AJAX and shows feedback inline without a page reload. On the home page, a slide-in popup offers 10% off a booking in exchange for a newsletter signup. It appears once per browser session for guests who are not logged in.

Each email address gets one discount code. The code is emailed immediately after signup, then validated at booking time. Codes are single-use and tied to the subscriber's email address. Loyalty discounts apply automatically for guests who have stayed multiple times before.

### Admin panel

- Booking management dashboard with status tracking: pending, confirmed, cancelled, completed
- Room dashboard with reservation and housekeeping status per room
- Email campaign editor and subscriber list
- Email log showing every outbound message and its delivery status
- User account management

---

## Troubleshooting

**The server fails to start with a database connection error**

Check that SQL Server is running. Open the Windows Services panel (search "Services" in the start menu) and confirm the SQL Server service is started. Then verify that:
- The database named `hotelbooking` exists
- The `tables v10 for hotel.sql` schema has been applied
- If your instance name is not `DESKTOP-NS6H7CH\MSSQLSERVER01`, set `DB_HOST` in `site1/.env`

**ODBC driver not found error**

Install ODBC Driver 17 for SQL Server from Microsoft's site (link in system requirements above). Do not install a different version number — the driver name in settings.py is pinned to version 17.

**Static files are missing (CSS/images not loading)**

Run `python manage.py collectstatic --noinput` from inside the `site1/` directory with the virtual environment active.

**Discount codes are not being issued**

The `discount_codes` table must exist. If the schema was applied partially or from an older version, re-apply `tables v10 for hotel.sql` to get all tables including this one.

**Emails are not sending**

Without `GMAIL_APP_PASSWORD` set in `.env`, the email backend falls back to the Django console — emails are printed to the terminal instead of sent. To send real emails, create a Gmail App Password (Google Account → Security → 2-Step Verification → App passwords) and set both `GMAIL_FROM_EMAIL` and `GMAIL_APP_PASSWORD` in `.env`.

**`(venv)` is not showing in the terminal**

You need to activate the virtual environment first. Run `venv\Scripts\activate` from the project root directory every time you open a new terminal. Without this, `python` and `pip` will point to your system Python and the dependencies will not be found.

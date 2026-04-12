# Quick Reference Guide

## Starting Your Server

```bash
cd site1
python manage.py runserver
```

Then open: http://127.0.0.1:8000/

## 📄 Main Pages & Their Files

| Page URL | Template File | View Function |
|----------|--------------|---------------|
| `/` (Homepage) | `templates/home.html` | `views.home_view()` |
| `/rooms/` | `templates/rooms.html` | `views.rooms_view()` |
| `/reservation/` | `templates/reservation.html` | `views.reservation_view()` |
| `/about/` | `templates/about.html` | `views.about_view()` |
| `/contact/` | `templates/contact.html` | `views.contact_view()` |

## 🎨 Styling Files

| File | What It Controls |
|------|------------------|
| `static/css/style.css` | Main stylesheet (base theme) |
| `static/css/_custom.css` | Your custom styles |
| Template `<style>` blocks | Page-specific styles |

## 🗄️ Database Models (Tables)

| Model Class | Table Name | What It Stores |
|-------------|------------|----------------|
| `Hotel` | `hotel` | Hotel name, address, phone, email |
| `RoomPrice` | `room_price` | Room types and prices |
| `HotelService` | `hotel_service` | Services offered (WiFi, Pool, etc.) |
| `CustomerBookingInfo` | `customer_booking_info` | Guest reservations |

## 🔧 Common Tasks

### Add a New Room Type
1. Add to database: `room_price` table
2. Images: Add to `static/images/` as `img_X.jpg`
3. Display: Already auto-populated from database

### Change Hotel Name
1. Edit in database: `hotel` table
2. Or via Django admin: http://127.0.0.1:8000/admin/

### Add a New Service
1. Add to database: `hotel_service` table
2. Or via Django admin

### Modify Reservation Form
1. Edit: `templates/reservation.html`
2. Update logic: `backend/services/services.py` → `ReservationService`

## 📂 File Organization

```
PRESENTATION (What users see)
  └── templates/*.html
  └── static/css/
  └── static/js/
  └── static/images/

APPLICATION (Business logic)
  └── home/views.py (handles requests)
  └── backend/services/services.py (business rules)

DATA (Database operations)
  └── data/models/hotel.py (tables)
  └── data/repos/repositories.py (queries)
```

## ⚠️ Don't Edit These

- `staticfiles/` - Auto-generated, edit `static/` instead
- `__pycache__/` - Python cache files
- `migrations/*.py` - Database migration files (unless you know what you're doing)
- `db.sqlite3` - Backup database, not currently used

## 🐛 Quick Fixes

**Site won't load?**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

**Images not showing?**
```bash
python manage.py collectstatic --noinput
```

**After changing models?**
```bash
python manage.py makemigrations
python manage.py migrate
```

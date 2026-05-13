# Thien Tai hotel booking system

A Django-based hotel booking web application with a SQL Server backend, featuring role-based access control, interactive UI components, and booking management.

## Quick start

```bash
# Navigate to project directory
cd site1

# Start the development server
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

## Documentation

- **[PROJECT_STRUCTURE.md](site1/PROJECT_STRUCTURE.md)** - Complete project architecture and file organization
- **[QUICK_REFERENCE.md](site1/QUICK_REFERENCE.md)** - Quick reference for common tasks
- **[UI_FEATURES.md](site1/UI_FEATURES.md)** - UI components and animations documentation
- **[DEPLOYMENT.md](site1/DEPLOYMENT.md)** - Production deployment guide

## Technologies

- **Backend:** Django 5.2.4 with Python 3.x
- **Database:** SQL Server (MSSQLSERVER01) with Windows Authentication
- **Frontend:** HTML5, CSS3, Bootstrap 4, JavaScript (jQuery)
- **Architecture:** Three-layer architecture (Presentation, Application, Data)
- **Authentication:** Custom user model with role-based access control (RBAC)

## Key features

### User management
- **Role-based access control** - Admin, staff, and customer roles
- **Secure authentication** - PBKDF2-SHA256 password hashing (1,000,000 iterations)
- **Protected login** - Mandatory authentication for booking
- **User-linked bookings** - Reservations tied to user accounts

### Booking system
- **Online reservations** - Booking form with date validation
- **Pending approval** - All bookings require admin/staff confirmation
- **Admin dashboard** - Booking management interface
- **Status tracking** - Pending, confirmed, cancelled, completed states

### UI/UX
- **Infinite scroll galleries** - Horizontal scrolling for photos and rooms
- **Room rate menu** - Expandable tabs with room images, descriptions, and pricing
- **Responsive design** - Mobile-optimized layouts
- **Design tokens** - CSS custom properties for consistent color, spacing, radius, and type scale

### Database security
- **Database-level RBAC** - Triggers enforce role permissions
- **Session context** - User tracking at database level
- **Role escalation protection** - Prevents unauthorized role changes
- **Booking ownership** - Customers can only modify their own bookings
- **Immutable audit log** - Append-only change tracking

## Project structure

```
hotel-app-test/
├── README.md                    # This file
└── site1/                       # Django project root
    ├── manage.py                # Django management script
    ├── .env                     # Environment variables (database config)
    │
    ├── site1/                   # Project configuration
    │   ├── settings.py          # Django settings
    │   ├── urls.py              # Main URL routing
    │   └── wsgi.py              # WSGI deployment config
    │
    ├── home/                    # Presentation layer
    │   ├── views.py             # View functions
    │   ├── urls.py              # URL patterns
    │   └── auth_backend.py      # Custom authentication
    │
    ├── backend/                 # Application layer
    │   └── services/
    │       └── services.py      # Business logic (HotelService, ReservationService)
    │
    ├── data/                    # Data layer
    │   ├── models/
    │   │   └── hotel.py         # Database models
    │   └── repos/
    │       └── repositories.py  # Data access
    │
    ├── templates/               # HTML templates
    │   ├── home.html            # Homepage with infinite scroll
    │   ├── rooms.html           # Rooms page with Great Offers menu
    │   ├── reservation.html     # Booking form
    │   ├── about.html           # About page with photo gallery
    │   ├── contact.html         # Contact page
    │   └── admin_reservations.html  # Admin dashboard
    │
    ├── static/                  # Static assets
    │   ├── css/                 # Stylesheets
    │   ├── js/                  # JavaScript
    │   └── images/              # Images
    │
    └── staticfiles/             # Collected static files (auto-generated)
```

## Common commands

```bash
# Navigate to project directory first
cd site1

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Collect static files for production
python manage.py collectstatic --noinput

# Run Django shell for testing
python manage.py shell

# Start development server
python manage.py runserver
```

## Database information

**Connection details:**
- **Server:** DESKTOP-NS6H7CH\MSSQLSERVER01
- **Database:** hotelbooking
- **Authentication:** Windows Authentication
- **Driver:** SQL Server Native Client 11.0

**Main tables:**
- `users` - User accounts with RBAC
- `hotel_info` - Hotel details (Thien Tai Hotel)
- `room_price` - Room types and pricing
- `booking_info` - Customer reservations
- `hotel_services` - Available services
- `customer_requests` - Booking modification requests
- `audit_log` - Change history tracking

**Security features:**
- Database-level triggers for access control
- Session context for user tracking
- Role escalation prevention
- Booking ownership enforcement
- Immutable audit logging

## UI features

### Infinite scroll galleries
- Horizontal animation (22s duration)
- Gradient fade-out edges
- Responsive sizing (280px desktop, 200px mobile)

### Service cards
- White backgrounds, subtle shadow
- Hover lift: max translateY(-4px), box-shadow capped at 8px spread
- Responsive grid layout

### Room rates menu (rooms.html)
- Hover-expandable dropdown tabs
- Room images, descriptions, and per-night pricing
- Database-driven content
- Responsive design

### Design system
- CSS custom properties in `style.css :root`
- 1 primary color, 1 accent, 2 radius values, 3 spacing levels, 1 type scale, 1 easing curve
- All transitions use `cubic-bezier(0.25, 0.1, 0.25, 1)`

## Troubleshooting

### Site won't load
```bash
# Ensure SQL Server is running
# Then run migrations
cd site1
python manage.py migrate
python manage.py collectstatic --noinput
```

### Static files not loading
```bash
cd site1
python manage.py collectstatic --noinput
```

### Database connection issues
- Verify SQL Server service is running
- Check `.env` file for correct database credentials
- Ensure Windows Authentication is enabled

### Login issues
- Verify user exists in `users` table
- Check password hash with `check_password()` method
- Ensure `SESSION_CONTEXT` is set properly

## User roles

### Admin
- Full system access
- Manage all bookings and users
- Modify hotel configuration
- Access audit logs

### Staff
- View and manage bookings
- Confirm/cancel reservations
- Limited configuration access

### Customer
- Make reservations (requires login)
- View own bookings only
- Request booking modifications
- Cannot access admin features

## Additional resources

For detailed information, see the documentation files in the `site1/` directory:
- Architecture details
- UI component specifications
- Deployment instructions
- Database schema
- Security implementation

## Recent updates

**Latest update (February 2026):**
- Implemented infinite scroll photo galleries
- Added Great Offers expandable menu
- Redesigned Premium Services cards
- Enhanced responsive design
- Improved animations and transitions

**Security enhancements:**
- Database-level RBAC enforcement
- Session context tracking
- Audit log protection
- Booking ownership validation

---

Built for Thien Tai Hotel

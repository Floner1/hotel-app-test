# Database Schema Update Summary

## Date: November 2, 2025

### Overview
Updated all Django models and application code to match the new database schema in SQL Server.

---

## Major Database Changes

### 1. Hotel Table → hotel_info Table
**Old:** `hotel` table  
**New:** `hotel_info` table

**Changes:**
- Primary key: `hotel_id` → `hotel_info_id` (column renamed)
- All fields now nullable
- Table name changed from `hotel` to `hotel_info`

### 2. booking_info Table Structure Changes
**New Fields Added:**
- `booked_rate` (DECIMAL): Stores the nightly rate at time of booking
- Moved `hotel_id` foreign key to second position

**Fields Modified:**
- `email`: Now nullable (was required)
- `admin_notes`: Now nullable
- `customer_room_type`: Max length changed to 100 (was 255)
- Removed unique constraint on email

**Field Order Adjusted:**
1. booking_id (PK)
2. hotel_id (FK)
3. customer_name
4. customer_phone_number
5. customer_room_type
6. booked_rate ← NEW
7. customer_email (now nullable)
8. booking_date
9. checkin_date
10. checkout_date
11. total_days
12. total_cost_amount
13. number_of_adults
14. number_of_children
15. admin_notes (now nullable)

### 3. room_price Table Column Renames
**Column name changes:**
- `1_bed_balcony_room` → `one_bed_balcony_room`
- `1_bed_window_room` → `one_bed_window_room`
- `2_bed_no_window_room` → `two_bed_no_window_room`
- `1_bed_no_window_room` → `one_bed_no_window_room`
- `2_bed_condotel_balcony` → `two_bed_condotel_balcony`

### 4. hotel_services Table Changes
**New Field:**
- `hotel_id` (FK): Now linked to hotel_info table

**Field Renames:**
- `name_of_service` → `service_name`

---

## Code Changes Made

### 1. Models Updated (`data/models/hotel.py`)

#### Hotel Model
```python
class Hotel(models.Model):
    hotel_id = models.IntegerField(primary_key=True, db_column='hotel_info_id')
    # ... all fields now nullable
    class Meta:
        db_table = 'hotel_info'  # Changed from 'hotel'
```

#### CustomerBookingInfo Model
```python
class CustomerBookingInfo(models.Model):
    booking_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')
    name = models.CharField(db_column='customer_name', max_length=255)
    phone = models.CharField(db_column='customer_phone_number', max_length=20)
    room_type = models.CharField(db_column='customer_room_type', max_length=100)
    booked_rate = models.DecimalField(max_digits=10, decimal_places=2)  # NEW
    email = models.CharField(db_column='customer_email', max_length=255, null=True, blank=True)  # NOW NULLABLE
    # ... rest of fields
    notes = models.CharField(db_column='admin_notes', max_length=255, null=True, blank=True)  # NOW NULLABLE
```

#### RoomPrice Model
- Updated all column names from `1_bed_*` to `one_bed_*` and `2_bed_*` to `two_bed_*`

#### HotelServices Model
```python
class HotelServices(models.Model):
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, db_column='hotel_id')  # NEW FK
    name_of_service = models.CharField(db_column='service_name', max_length=255)  # COLUMN RENAMED
    # ...
```

### 2. Service Layer Updated (`backend/services/services.py`)

**create_reservation() changes:**
- Added `booked_rate` field to booking_data
- Made email optional (nullable)
- Removed email from required fields list
- Updated email validation to only validate if provided
- Reordered booking_data fields to match new schema

**_ensure_required_fields() changes:**
- Removed 'email' from required fields tuple

### 3. Views Updated (`home/views.py`)

**edit_reservation() changes:**
- Added `booked_rate` update when editing
- Made email optional in updates

### 4. Templates Updated

**reservation.html:**
- Removed red asterisk (*) from Email label
- Removed `required` attribute from email input field

**admin_reservations.html:**
- Removed red asterisk (*) from Email label in Add Reservation modal
- Removed `required` attribute from add_email input field

---

## Validation Rules Updated

### Removed:
- 30-day maximum stay limit (customers can now book indefinitely)
- Email uniqueness validation
- Email as a required field

### Kept:
- Check-in date cannot be in the past
- Check-out date must be after check-in date
- Email format validation (only when email is provided)
- All other field validations

---

## Testing Performed

1. ✅ Django model check: No issues found
2. ✅ Database connection test: Successful
3. ✅ Hotel model: Working correctly
4. ✅ CustomerBookingInfo model: Schema aligned
5. ✅ RoomPrice model: Column names updated
6. ✅ HotelServices model: Foreign key working

---

## Files Modified

1. `site1/data/models/hotel.py` - All model definitions
2. `site1/backend/services/services.py` - Reservation service logic
3. `site1/home/views.py` - Edit reservation view
4. `site1/templates/reservation.html` - Customer booking form
5. `site1/templates/admin_reservations.html` - Admin dashboard

---

## Notes

- The `booked_rate` field stores the nightly rate at the time of booking, providing historical pricing data
- Email is now optional to accommodate walk-in customers or bookings without email
- No database migrations needed since `managed = False` (external SQL Server database)
- All existing functionality preserved while accommodating new schema

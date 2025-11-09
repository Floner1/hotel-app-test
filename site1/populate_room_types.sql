-- Check current room_price table and identify missing room types
-- Run this in SQL Server Management Studio or Azure Data Studio

USE hotelbooking;
GO

-- Step 1: See what's currently in the table
SELECT 
    hotel_id,
    room_type,
    price_per_night,
    room_description
FROM room_price
ORDER BY hotel_id, price_per_night;

-- Step 2: List all required room types
PRINT 'Required room types:';
PRINT '1. one_bed_balcony_room';
PRINT '2. one_bed_window_room';
PRINT '3. one_bed_no_window_room';
PRINT '4. two_bed_no_window_room';
PRINT '5. two_bed_condotel_balcony';

-- Step 3: Check which ones are missing
PRINT '';
PRINT 'Missing room types (add these manually with YOUR prices):';
PRINT '';

IF NOT EXISTS (SELECT 1 FROM room_price WHERE room_type = 'one_bed_balcony_room')
    PRINT '❌ Missing: one_bed_balcony_room';
ELSE
    PRINT '✓ Found: one_bed_balcony_room';

IF NOT EXISTS (SELECT 1 FROM room_price WHERE room_type = 'one_bed_window_room')
    PRINT '❌ Missing: one_bed_window_room';
ELSE
    PRINT '✓ Found: one_bed_window_room';

IF NOT EXISTS (SELECT 1 FROM room_price WHERE room_type = 'one_bed_no_window_room')
    PRINT '❌ Missing: one_bed_no_window_room';
ELSE
    PRINT '✓ Found: one_bed_no_window_room';

IF NOT EXISTS (SELECT 1 FROM room_price WHERE room_type = 'two_bed_no_window_room')
    PRINT '❌ Missing: two_bed_no_window_room';
ELSE
    PRINT '✓ Found: two_bed_no_window_room';

IF NOT EXISTS (SELECT 1 FROM room_price WHERE room_type = 'two_bed_condotel_balcony')
    PRINT '❌ Missing: two_bed_condotel_balcony';
ELSE
    PRINT '✓ Found: two_bed_condotel_balcony';

PRINT '';
PRINT 'To add missing room types, use this template:';
PRINT 'INSERT INTO room_price (hotel_id, room_type, price_per_night, room_description)';
PRINT 'VALUES (YOUR_HOTEL_ID, ''room_type_name'', YOUR_PRICE, ''Description'');';
GO

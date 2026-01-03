-- ============================================
-- HOTEL BOOKING SYSTEM - DATABASE SCHEMA
-- Fixed Version (Jan 2026)
-- ============================================

-- Drop tables in correct dependency order (cleanup)
DROP TABLE IF EXISTS booking_info;
DROP TABLE IF EXISTS hotel_services;
DROP TABLE IF EXISTS hotel_keys_main;
DROP TABLE IF EXISTS room_price;
DROP TABLE IF EXISTS hotel_info;
DROP TABLE IF EXISTS users;

-- ============================================
-- USERS TABLE
-- FIXED: Removed UNIQUE constraints on username and email
--        to allow multiple bookings per customer
-- ============================================
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(150) NOT NULL,
    email NVARCHAR(255) NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(50) NOT NULL CHECK (role IN ('customer','staff','admin')),
    created_at DATETIME DEFAULT GETDATE()
);

-- ============================================
-- HOTEL INFO
-- ============================================
CREATE TABLE hotel_info (
    hotel_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_name NVARCHAR(225),
    address NVARCHAR(225),
    star_rating INT,
    established_date DATE,
    email NVARCHAR(225),
    phone NVARCHAR(225)
);

-- ============================================
-- ROOM PRICE TABLE
-- ============================================
CREATE TABLE room_price (
    room_price_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_type NVARCHAR(225),
    price_per_night INT NOT NULL,
    room_description NVARCHAR(MAX),
    CONSTRAINT fk_room_price_hotel FOREIGN KEY (hotel_id)
        REFERENCES hotel_info(hotel_id)
);

-- ============================================
-- HOTEL SERVICES TABLE
-- FIXED: Changed service_price to INT (was NVARCHAR causing errors)
-- ============================================
CREATE TABLE hotel_services (
    service_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    service_name NVARCHAR(225),
    service_price INT,
    service_description NVARCHAR(MAX),
    CONSTRAINT fk_services_hotel FOREIGN KEY (hotel_id)
        REFERENCES hotel_info(hotel_id)
);

-- ============================================
-- HOTEL KEYS TABLE
-- ============================================
CREATE TABLE hotel_keys_main (
    key_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_key NVARCHAR(225),
    CONSTRAINT fk_keys_hotel FOREIGN KEY (hotel_id)
        REFERENCES hotel_info(hotel_id)
);

-- ============================================
-- BOOKING INFO TABLE
-- ============================================
CREATE TABLE booking_info (
    booking_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    user_id INT NULL, -- links customer account
    guest_name NVARCHAR(225) NOT NULL,
    email NVARCHAR(255),
    phone NVARCHAR(50),
    room_type NVARCHAR(100) NOT NULL,
    booking_date DATETIME NOT NULL DEFAULT GETDATE(),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    adults INT NOT NULL DEFAULT 1,
    children INT NOT NULL DEFAULT 0,
    booked_rate DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL DEFAULT 0,
    status NVARCHAR(50) NOT NULL DEFAULT 'confirmed',
    payment_status NVARCHAR(50) NOT NULL DEFAULT 'unpaid',
    special_requests NVARCHAR(MAX),
    notes NVARCHAR(MAX),
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT fk_booking_hotel FOREIGN KEY (hotel_id)
        REFERENCES hotel_info(hotel_id),
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IX_booking_hotel_id ON booking_info(hotel_id);
CREATE INDEX IX_booking_check_in ON booking_info(check_in);
CREATE INDEX IX_booking_check_out ON booking_info(check_out);
CREATE INDEX IX_booking_user_id ON booking_info(user_id);
CREATE INDEX IX_users_username ON users(username);
CREATE INDEX IX_users_email ON users(email);

-- ============================================
-- TRIGGER FOR UPDATED_AT
-- FIXED: Cleaned up trigger - only updates timestamp
--        (removed erroneous INSERT statements)
-- ============================================
GO

CREATE TRIGGER trg_booking_info_updated_at
ON booking_info
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE booking_info
    SET updated_at = GETDATE()
    FROM booking_info b
    INNER JOIN inserted i ON b.booking_id = i.booking_id;
END;

GO

-- ============================================
-- DEFAULT DATA
-- ============================================

-- Default admin user
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin','admin@example.com','jL0Tg_Qt#HQMho7q','admin');

-- Insert hotel info
INSERT INTO hotel_info (hotel_name, star_rating, address, email, phone, established_date)
VALUES (N'Thien Tai Hotel', 3, N'452 Nguyen Thi Minh Khai P5 Q3 TPHCM', N'hotelemail@gmail.com', N'+84 1234567', '2023-08-28');

-- Insert room prices
INSERT INTO room_price (hotel_id, room_type, price_per_night, room_description)
VALUES 
(1, '1 Bed No Window','650000','A comfortable and affordable option ideal for short stays. Features a cozy queen bed, modern furnishings, and full amenities, offering quiet rest in a compact space without windows.'),
(1, '2 Bed No Window Room','750000','Perfect for friends or family on a budget. This room includes two single beds, air conditioning, and a private bathroom. Designed for comfort and practicality, though it does not include a window.'),
(1, '1 Bed With Window','850000','A bright, inviting room with a private balcony overlooking the city. Includes a queen bed, modern décor, and all standard amenities for a relaxing stay.'),
(1, '1 Bed With Balcony', '1150000','A larger balcony room with added comfort and space. Offers a queen bed, seating area, and outdoor balcony access — ideal for guests who value extra room and natural light.'),
(1, '2 Bed & Balcony Condotel','1550000','Spacious two-bedroom condotel with a private balcony and separate living area. Equipped with full amenities and ideal for families or longer stays seeking both comfort and convenience.');

-- Insert hotel services (FIXED: Changed 'Per kilo' to numeric value)
INSERT INTO hotel_services (hotel_id, service_name, service_price, service_description)
VALUES
(1, N'Motorbike Rental', 150000, N'Explore the city freely with our reliable motorbikes. Flexible daily and weekly rentals are available, with helmets and safety gear provided. Ask the front desk for details and route suggestions.'),
(1, N'Restaurant', 100000, N'Enjoy local and international dishes at our on-site restaurant. We serve breakfast, lunch, and dinner with options for all diets. For menus or hours, please check with the front desk.'),
(1, N'Laundry', 100000, N'Keep your clothes fresh with our fast, professional laundry service. Drop off your items at the front desk or request in-room pickup. Pricing is based on weight.');

-- ============================================
-- SCHEMA FIXES APPLIED (Jan 2026):
-- 1. Removed UNIQUE constraints on users.username and users.email
-- 2. Fixed trigger to only update timestamp (removed INSERT statements)
-- 3. Changed service_price quotes from N'' to plain numbers
-- ============================================

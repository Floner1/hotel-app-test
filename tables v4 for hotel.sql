USE hotelbooking;
GO

/* =====================================================
   CLEANUP: DROP VIEWS, TRIGGERS, AND TABLES
   (Reverse dependency order)
===================================================== */
IF OBJECT_ID('v_customer_bookings', 'V') IS NOT NULL DROP VIEW v_customer_bookings;
IF OBJECT_ID('v_customer_requests', 'V') IS NOT NULL DROP VIEW v_customer_requests;
IF OBJECT_ID('v_room_dashboard', 'V') IS NOT NULL DROP VIEW v_room_dashboard;

IF OBJECT_ID('trg_prevent_role_escalation', 'TR') IS NOT NULL DROP TRIGGER trg_prevent_role_escalation;
IF OBJECT_ID('trg_booking_ownership', 'TR') IS NOT NULL DROP TRIGGER trg_booking_ownership;
IF OBJECT_ID('trg_booking_updated_at', 'TR') IS NOT NULL DROP TRIGGER trg_booking_updated_at;

IF OBJECT_ID('trg_block_customer_writes_hotel_services', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_hotel_services;
IF OBJECT_ID('trg_block_customer_writes_room_price', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_room_price;
IF OBJECT_ID('trg_block_customer_writes_hotel_keys', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_hotel_keys;

IF OBJECT_ID('room_assignments', 'U') IS NOT NULL DROP TABLE room_assignments;
IF OBJECT_ID('rooms', 'U') IS NOT NULL DROP TABLE rooms;
IF OBJECT_ID('customer_requests', 'U') IS NOT NULL DROP TABLE customer_requests;
IF OBJECT_ID('audit_log', 'U') IS NOT NULL DROP TABLE audit_log;
IF OBJECT_ID('booking_info', 'U') IS NOT NULL DROP TABLE booking_info;
IF OBJECT_ID('hotel_services', 'U') IS NOT NULL DROP TABLE hotel_services;
IF OBJECT_ID('hotel_keys_main', 'U') IS NOT NULL DROP TABLE hotel_keys_main;
IF OBJECT_ID('room_price', 'U') IS NOT NULL DROP TABLE room_price;
IF OBJECT_ID('hotel_info', 'U') IS NOT NULL DROP TABLE hotel_info;
IF OBJECT_ID('ImagesRef', 'U') IS NOT NULL DROP TABLE ImagesRef;
IF OBJECT_ID('site_content', 'U') IS NOT NULL DROP TABLE site_content;
IF OBJECT_ID('users', 'U') IS NOT NULL DROP TABLE users;
GO

/* =====================================================
   USERS (Updated with Admin, Staff, Customer roles)
===================================================== */
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(150) NOT NULL UNIQUE,
    email NVARCHAR(255) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(50) NOT NULL CHECK (role IN ('customer','staff','admin')),
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    last_login DATETIME NULL,
    created_by INT NULL,
    CONSTRAINT fk_users_created_by FOREIGN KEY (created_by)
        REFERENCES users(user_id)
);
GO

/* =====================================================
   HOTEL CORE TABLES
===================================================== */
CREATE TABLE hotel_info (
    hotel_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_name NVARCHAR(225),
    address NVARCHAR(225),
    star_rating INT,
    established_date DATE,
    email NVARCHAR(225),
    phone NVARCHAR(225)
);
GO

CREATE TABLE room_price (
    room_price_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_type NVARCHAR(225),
    price_per_night INT NOT NULL,
    room_description NVARCHAR(MAX),
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id)
);
GO

CREATE TABLE hotel_services (
    service_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    service_name NVARCHAR(225),
    service_price INT,
    service_description NVARCHAR(MAX),
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id)
);
GO

CREATE TABLE hotel_keys_main (
    key_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_key NVARCHAR(225),
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id)
);
GO

/* =====================================================
   ROOMS — Physical room inventory
===================================================== */
CREATE TABLE rooms (
    room_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_code NVARCHAR(10) NOT NULL UNIQUE,
    floor_number INT NOT NULL,
    room_number INT NOT NULL,
    room_type NVARCHAR(225) NULL,
    current_status NVARCHAR(50) NOT NULL DEFAULT 'empty_clean'
        CHECK (current_status IN ('empty_clean','empty_dirty','occupied','out_of_order','reserved')),
    notes NVARCHAR(MAX) NULL,
    updated_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_rooms_hotel FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id),
    CONSTRAINT uq_rooms_floor_room UNIQUE (hotel_id, floor_number, room_number)
);
GO

/* =====================================================
   BOOKINGS
===================================================== */
CREATE TABLE booking_info (
    booking_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    user_id INT NULL,
    guest_name NVARCHAR(225) NOT NULL,
    email NVARCHAR(255),
    phone NVARCHAR(50),
    room_type NVARCHAR(100) NOT NULL,
    booking_date DATETIME DEFAULT GETDATE(),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    adults INT DEFAULT 1,
    children INT DEFAULT 0,
    booked_rate DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) DEFAULT 0,
    status NVARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending','confirmed','cancelled','completed')),
    payment_status NVARCHAR(50) DEFAULT 'unpaid'
        CHECK (payment_status IN ('unpaid','partial','paid','refunded')),
    special_requests NVARCHAR(MAX),
    notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    created_by INT NULL,
    modified_by INT NULL,
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    FOREIGN KEY (modified_by) REFERENCES users(user_id)
);
GO

/* =====================================================
   ROOM ASSIGNMENTS — Links bookings to physical rooms
===================================================== */
CREATE TABLE room_assignments (
    assignment_id INT IDENTITY(1,1) PRIMARY KEY,
    booking_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    assigned_at DATETIME DEFAULT GETDATE(),
    assigned_by INT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','completed','cancelled','transferred')),
    notes NVARCHAR(MAX) NULL,
    CONSTRAINT fk_ra_booking FOREIGN KEY (booking_id) REFERENCES booking_info(booking_id),
    CONSTRAINT fk_ra_room FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    CONSTRAINT fk_ra_assigned_by FOREIGN KEY (assigned_by) REFERENCES users(user_id)
);
GO

/* =====================================================
   CUSTOMER REQUESTS
===================================================== */
CREATE TABLE customer_requests (
    request_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    booking_id INT NULL,
    request_type NVARCHAR(50)
        CHECK (request_type IN ('new_booking','edit_booking','cancel_booking')),
    request_status NVARCHAR(50) DEFAULT 'pending'
        CHECK (request_status IN ('pending','approved','rejected','completed')),
    request_data NVARCHAR(MAX) NOT NULL,
    customer_message NVARCHAR(MAX),
    deadline DATETIME NULL,
    created_at DATETIME DEFAULT GETDATE(),
    handled_at DATETIME NULL,
    handled_by INT NULL,
    staff_notes NVARCHAR(MAX),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (booking_id) REFERENCES booking_info(booking_id),
    FOREIGN KEY (handled_by) REFERENCES users(user_id)
);
GO

/* =====================================================
   AUDIT LOG & CONTENT TABLES
===================================================== */
CREATE TABLE audit_log (
    log_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    action_type NVARCHAR(50)
        CHECK (action_type IN ('CREATE','UPDATE','DELETE','ROLE_CHANGE','LOGIN')),
    table_name NVARCHAR(100) NOT NULL,
    record_id INT NULL,
    old_values NVARCHAR(MAX),
    new_values NVARCHAR(MAX),
    ip_address NVARCHAR(50),
    timestamp DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
GO

CREATE TABLE ImagesRef (
    ImageId   INT IDENTITY(1,1) PRIMARY KEY,
    ImageName NVARCHAR(100) NOT NULL UNIQUE,
    ImageData VARBINARY(MAX) NOT NULL,
    ImageContentType NVARCHAR(50) NOT NULL DEFAULT 'image/jpeg'
);
GO

CREATE TABLE site_content (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    content_key   NVARCHAR(100) NOT NULL UNIQUE,
    content_value NVARCHAR(MAX) NOT NULL,
    updated_at    DATETIME DEFAULT GETDATE()
);
GO

/* =====================================================
   TRIGGERS & VIEWS
===================================================== */
CREATE TRIGGER trg_prevent_role_escalation
ON users
AFTER UPDATE
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN deleted d ON i.user_id = d.user_id
        WHERE i.role <> d.role
          AND SESSION_CONTEXT(N'user_role') <> 'admin'
    )
    BEGIN
        ROLLBACK;
        THROW 50001, 'Only admins can change roles', 1;
    END
END;
GO

CREATE TRIGGER trg_booking_ownership
ON booking_info
AFTER UPDATE, DELETE
AS
BEGIN
    IF SESSION_CONTEXT(N'user_role') = 'customer'
       AND EXISTS (
           SELECT 1 FROM deleted
           WHERE user_id <> SESSION_CONTEXT(N'user_id')
       )
    BEGIN
        ROLLBACK;
        THROW 50002, 'Customers can only modify their own bookings', 1;
    END
END;
GO

CREATE VIEW v_customer_bookings AS
SELECT *
FROM booking_info
WHERE user_id = SESSION_CONTEXT(N'user_id');
GO

CREATE VIEW v_customer_requests AS
SELECT *
FROM customer_requests
WHERE user_id = SESSION_CONTEXT(N'user_id');
GO

/* =====================================================
   ROOM DASHBOARD VIEW — Single query for the dashboard
===================================================== */
CREATE VIEW v_room_dashboard AS
SELECT
    r.room_id,
    r.room_code,
    r.floor_number,
    r.room_number,
    r.room_type,
    r.current_status,
    r.notes AS room_notes,
    ra.assignment_id,
    ra.booking_id,
    b.guest_name,
    ra.check_in,
    ra.check_out,
    DATEDIFF(DAY, ra.check_in, ra.check_out) AS duration_nights
FROM rooms r
LEFT JOIN room_assignments ra
    ON ra.room_id = r.room_id AND ra.status = 'active'
LEFT JOIN booking_info b
    ON b.booking_id = ra.booking_id;
GO

/* =====================================================
   DEFAULT DATA INSERTS
===================================================== */
--Insert hotel info
INSERT INTO hotel_info (hotel_name, star_rating, address, email, phone, established_date)
VALUES (N'Thien Tai Hotel', 3, N'452 Nguyen Thi Minh Khai P5 Q3 TPHCM', N'hotelemail@gmail.com', N'+84 1234567', '2023-08-28');
GO

-- Insert room prices
INSERT INTO room_price (hotel_id, room_type, price_per_night, room_description) VALUES
(1, '1 Bed No Window','650000','A comfortable and affordable option ideal for short stays. Features a cozy queen bed, modern furnishings, and full amenities, offering quiet rest in a compact space without windows.'),
(1, '2 Bed No Window Room','750000','Perfect for friends or family on a budget. This room includes two single beds, air conditioning, and a private bathroom. Designed for comfort and practicality, though it does not include a window.'),
(1, '1 Bed With Window','850000','A bright, inviting room with a private balcony overlooking the city. Includes a queen bed, modern décor, and all standard amenities for a relaxing stay.'),
(1, '1 Bed With Balcony', '1150000','A larger balcony room with added comfort and space. Offers a queen bed, seating area, and outdoor balcony access  ideal for guests who value extra room and natural light.'),
(1, '2 Bed & Balcony Condotel','1550000','Spacious two-bedroom condotel with a private balcony and separate living area. Equipped with full amenities and ideal for families or longer stays seeking both comfort and convenience.');
GO

INSERT INTO hotel_services (hotel_id, service_name, service_price, service_description) VALUES
(1, N'Motorbike Rental', 150000, N'Explore the city freely with our reliable motorbikes. Flexible daily and weekly rentals are available, with helmets and safety gear provided. Ask the front desk for details and route suggestions.'),
(1, N'Restaurant', 100000, N'Enjoy local and international dishes at our on-site restaurant. We serve breakfast, lunch, and dinner with options for all diets. For menus or hours, please check with the front desk.'),
(1, N'Laundry', 100000, N'Keep your clothes fresh with our fast, professional laundry service. Drop off your items at the front desk or request in-room pickup. Pricing is based on weight.');
GO

/* =====================================================
   SEED ROOMS — 53 physical rooms
   Floors 4-8, 10: 8 rooms each (48)
   Floor 9:        4 rooms       (4)
   Floor 11:       1 room        (1)
   Total:                        53

   Room type layout per floor (floors 4-8 and 10):
     Rooms 1-2: 1 Bed With Balcony
     Rooms 3-4: 1 Bed No Window
     Rooms 5-6: 2 Bed No Window Room
     Rooms 7-8: 1 Bed With Window
   Floor 9 (all 4 rooms): 2 Bed & Balcony Condotel
   Floor 11 (1 room):     1 Bed No Window
===================================================== */
INSERT INTO rooms (hotel_id, room_code, floor_number, room_number, room_type) VALUES
-- Floor 4 (8 rooms)
(1, '401', 4, 1, '1 Bed With Balcony'),
(1, '402', 4, 2, '1 Bed With Balcony'),
(1, '403', 4, 3, '1 Bed No Window'),
(1, '404', 4, 4, '1 Bed No Window'),
(1, '405', 4, 5, '2 Bed No Window Room'),
(1, '406', 4, 6, '2 Bed No Window Room'),
(1, '407', 4, 7, '1 Bed With Window'),
(1, '408', 4, 8, '1 Bed With Window'),
-- Floor 5 (8 rooms)
(1, '501', 5, 1, '1 Bed With Balcony'),
(1, '502', 5, 2, '1 Bed With Balcony'),
(1, '503', 5, 3, '1 Bed No Window'),
(1, '504', 5, 4, '1 Bed No Window'),
(1, '505', 5, 5, '2 Bed No Window Room'),
(1, '506', 5, 6, '2 Bed No Window Room'),
(1, '507', 5, 7, '1 Bed With Window'),
(1, '508', 5, 8, '1 Bed With Window'),
-- Floor 6 (8 rooms)
(1, '601', 6, 1, '1 Bed With Balcony'),
(1, '602', 6, 2, '1 Bed With Balcony'),
(1, '603', 6, 3, '1 Bed No Window'),
(1, '604', 6, 4, '1 Bed No Window'),
(1, '605', 6, 5, '2 Bed No Window Room'),
(1, '606', 6, 6, '2 Bed No Window Room'),
(1, '607', 6, 7, '1 Bed With Window'),
(1, '608', 6, 8, '1 Bed With Window'),
-- Floor 7 (8 rooms)
(1, '701', 7, 1, '1 Bed With Balcony'),
(1, '702', 7, 2, '1 Bed With Balcony'),
(1, '703', 7, 3, '1 Bed No Window'),
(1, '704', 7, 4, '1 Bed No Window'),
(1, '705', 7, 5, '2 Bed No Window Room'),
(1, '706', 7, 6, '2 Bed No Window Room'),
(1, '707', 7, 7, '1 Bed With Window'),
(1, '708', 7, 8, '1 Bed With Window'),
-- Floor 8 (8 rooms)
(1, '801', 8, 1, '1 Bed With Balcony'),
(1, '802', 8, 2, '1 Bed With Balcony'),
(1, '803', 8, 3, '1 Bed No Window'),
(1, '804', 8, 4, '1 Bed No Window'),
(1, '805', 8, 5, '2 Bed No Window Room'),
(1, '806', 8, 6, '2 Bed No Window Room'),
(1, '807', 8, 7, '1 Bed With Window'),
(1, '808', 8, 8, '1 Bed With Window'),
-- Floor 9 (4 rooms) — all 2 Bed & Balcony Condotel
(1, '901', 9, 1, '2 Bed & Balcony Condotel'),
(1, '902', 9, 2, '2 Bed & Balcony Condotel'),
(1, '903', 9, 3, '2 Bed & Balcony Condotel'),
(1, '904', 9, 4, '2 Bed & Balcony Condotel'),
-- Floor 10 (8 rooms)
(1, '1001', 10, 1, '1 Bed With Balcony'),
(1, '1002', 10, 2, '1 Bed With Balcony'),
(1, '1003', 10, 3, '1 Bed No Window'),
(1, '1004', 10, 4, '1 Bed No Window'),
(1, '1005', 10, 5, '2 Bed No Window Room'),
(1, '1006', 10, 6, '2 Bed No Window Room'),
(1, '1007', 10, 7, '1 Bed With Window'),
(1, '1008', 10, 8, '1 Bed With Window'),
-- Floor 11 (1 room) — 1 Bed No Window
(1, '1101', 11, 1, '1 Bed No Window');
GO

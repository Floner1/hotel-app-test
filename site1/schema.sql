USE hotelbooking;
GO

/* =====================================================
   CLEANUP
===================================================== */
IF OBJECT_ID('v_customer_bookings', 'V') IS NOT NULL DROP VIEW v_customer_bookings;
IF OBJECT_ID('v_customer_requests', 'V') IS NOT NULL DROP VIEW v_customer_requests;

IF OBJECT_ID('trg_prevent_role_escalation', 'TR') IS NOT NULL DROP TRIGGER trg_prevent_role_escalation;
IF OBJECT_ID('trg_booking_ownership', 'TR') IS NOT NULL DROP TRIGGER trg_booking_ownership;
IF OBJECT_ID('trg_booking_updated_at', 'TR') IS NOT NULL DROP TRIGGER trg_booking_updated_at;

IF OBJECT_ID('trg_block_customer_writes_hotel_services', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_hotel_services;
IF OBJECT_ID('trg_block_customer_writes_room_price', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_room_price;
IF OBJECT_ID('trg_block_customer_writes_hotel_keys', 'TR') IS NOT NULL DROP TRIGGER trg_block_customer_writes_hotel_keys;

IF OBJECT_ID('customer_requests', 'U') IS NOT NULL DROP TABLE customer_requests;
IF OBJECT_ID('audit_log', 'U') IS NOT NULL DROP TABLE audit_log;
IF OBJECT_ID('booking_info', 'U') IS NOT NULL DROP TABLE booking_info;
IF OBJECT_ID('hotel_services', 'U') IS NOT NULL DROP TABLE hotel_services;
IF OBJECT_ID('hotel_keys_main', 'U') IS NOT NULL DROP TABLE hotel_keys_main;
IF OBJECT_ID('room_price', 'U') IS NOT NULL DROP TABLE room_price;
IF OBJECT_ID('hotel_info', 'U') IS NOT NULL DROP TABLE hotel_info;
IF OBJECT_ID('users', 'U') IS NOT NULL DROP TABLE users;
GO

/* =====================================================
   USERS
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
   AUDIT LOG
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

/* =====================================================
   TRIGGERS
===================================================== */
CREATE TRIGGER trg_booking_updated_at
ON booking_info
AFTER UPDATE
AS
BEGIN
    UPDATE booking_info
    SET updated_at = GETDATE()
    FROM booking_info b
    JOIN inserted i ON b.booking_id = i.booking_id;
END;
GO

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

CREATE TRIGGER trg_block_customer_writes_hotel_services
ON hotel_services
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    IF SESSION_CONTEXT(N'user_role') = 'customer'
    BEGIN
        ROLLBACK;
        THROW 50003, 'Customers cannot modify hotel configuration data', 1;
    END
END;
GO

CREATE TRIGGER trg_block_customer_writes_room_price
ON room_price
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    IF SESSION_CONTEXT(N'user_role') = 'customer'
    BEGIN
        ROLLBACK;
        THROW 50003, 'Customers cannot modify hotel configuration data', 1;
    END
END;
GO

CREATE TRIGGER trg_block_customer_writes_hotel_keys
ON hotel_keys_main
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    IF SESSION_CONTEXT(N'user_role') = 'customer'
    BEGIN
        ROLLBACK;
        THROW 50003, 'Customers cannot modify hotel configuration data', 1;
    END
END;
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
   CUSTOMER VIEWS
===================================================== */
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
   AUDIT PROTECTION
===================================================== */
DENY UPDATE, DELETE ON audit_log TO PUBLIC;
GO

/* =====================================================
   DEFAULT DATA
===================================================== */
INSERT INTO hotel_info (hotel_name, star_rating, address, email, phone, established_date) VALUES (N'Thien Tai Hotel', 3, N'452 Nguyen Thi Minh Khai P5 Q3 TPHCM', N'hotelemail@gmail.com', N'+84 1234567', '2023-08-28');

INSERT INTO room_price (hotel_id, room_type, price_per_night, room_description) VALUES
(1, '1 Bed No Window','650000','A comfortable and affordable option ideal for short stays. Features a cozy queen bed, modern furnishings, and full amenities, offering quiet rest in a compact space without windows.'),
(1, '2 Bed No Window Room','750000','Perfect for friends or family on a budget. This room includes two single beds, air conditioning, and a private bathroom. Designed for comfort and practicality, though it does not include a window.'), 
(1, '1 Bed With Window','850000','A bright, inviting room with a private balcony overlooking the city. Includes a queen bed, modern décor, and all standard amenities for a relaxing stay.'), 
(1, '1 Bed With Balcony', '1150000','A larger balcony room with added comfort and space. Offers a queen bed, seating area, and outdoor balcony access — ideal for guests who value extra room and natural light.'),
(1, '2 Bed & Balcony Condotel','1550000','Spacious two-bedroom condotel with a private balcony and separate living area. Equipped with full amenities and ideal for families or longer stays seeking both comfort and convenience.');

INSERT INTO hotel_services (hotel_id, service_name, service_price, service_description) VALUES
(1, N'Motorbike Rental', 150000, N'Explore the city freely with our reliable motorbikes. Flexible daily and weekly rentals are available, with helmets and safety gear provided. Ask the front desk for details and route suggestions.'), 
(1, N'Restaurant', 100000, N'Enjoy local and international dishes at our on-site restaurant. We serve breakfast, lunch, and dinner with options for all diets. For menus or hours, please check with the front desk.'), 
(1, N'Laundry', 100000, N'Keep your clothes fresh with our fast, professional laundry service. Drop off your items at the front desk or request in-room pickup. Pricing is based on weight.');

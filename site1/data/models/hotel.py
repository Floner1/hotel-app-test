# Import Django's model system for database interaction
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserManager(BaseUserManager):
    """Custom user manager for User model."""
    
    def create_user(self, username, email, password=None, role='customer', **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and save a superuser (admin)."""
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser):
    """Custom user model mapped to users table."""
    
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, db_column='password_hash')
    role = models.CharField(
        max_length=50,
        choices=[
            ('customer', 'Customer'),
            ('staff', 'Staff'),
            ('admin', 'Administrator'),
        ],
        default='customer'
    )
    is_active = models.BooleanField(default=True, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True, db_column='created_by')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    PASSWORD_FIELD = 'password_hash'  # Map to password_hash column
    
    class Meta:
        db_table = 'users'
        managed = False
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    # Map password property to password_hash field
    @property
    def password(self):
        """Django expects a 'password' attribute."""
        return self.password_hash
    
    @password.setter
    def password(self, value):
        """Allow setting password via password attribute."""
        self.password_hash = value
    
    def set_password(self, raw_password):
        """Set password (stores in password_hash field)."""
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check password against password_hash."""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)
    
    # Backward compatibility properties for Django admin
    @property
    def is_staff(self):
        """Compatibility with Django admin - staff and admin can access admin site."""
        return self.role in ['admin', 'staff']
    
    @property
    def is_superuser(self):
        """Compatibility with Django admin - only admin role."""
        return self.role == 'admin'
    
    def has_perm(self, perm, obj=None):
        """Does user have a specific permission? Admins have all permissions."""
        return self.role == 'admin'
    
    def has_module_perms(self, app_label):
        """Does user have permissions to view the app? Admins and staff yes."""
        return self.role in ['admin', 'staff']
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_staff_member(self):
        return self.role in ['admin', 'staff']
    
    @property
    def is_customer(self):
        return self.role == 'customer'


class Hotel(models.Model):
    """Model mapped to the SQL Server `hotel_info` table."""

    hotel_id = models.AutoField(primary_key=True)
    hotel_name = models.CharField(max_length=225, null=True, blank=True)
    address = models.CharField(max_length=225, null=True, blank=True)
    star_rating = models.IntegerField(null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)
    email = models.CharField(max_length=225, null=True, blank=True)
    phone = models.CharField(max_length=225, null=True, blank=True)

    class Meta:
        db_table = 'hotel_info'
        managed = False

    def __str__(self) -> str:
        return self.hotel_name or 'Unnamed Hotel'


class CustomerBookingInfo(models.Model):
    """Model mapped to SQL Server's booking_info table."""

    booking_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING)
    user = models.ForeignKey('User', models.DO_NOTHING, null=True, blank=True, db_column='user_id')
    
    # Guest Information
    guest_name = models.CharField(max_length=225)
    email = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    
    # Booking Details
    room_type = models.CharField(max_length=100)
    
    # Dates
    booking_date = models.DateTimeField()
    check_in = models.DateField()
    check_out = models.DateField()
    
    # Guest Count
    adults = models.IntegerField(default=1)
    children = models.IntegerField(null=True, blank=True, default=0)
    
    # Pricing
    booked_rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status Tracking
    status = models.CharField(max_length=50, default='pending')
    payment_status = models.CharField(max_length=50, default='unpaid')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional Information
    special_requests = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Audit Fields
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by = models.IntegerField(null=True, blank=True, db_column='created_by')
    modified_by = models.IntegerField(null=True, blank=True, db_column='modified_by')

    class Meta:
        db_table = 'booking_info'
        managed = False
        ordering = ['-booking_date']

    def __str__(self) -> str:
        return f"Booking #{self.booking_id} - {self.guest_name}"


class RoomPrice(models.Model):
    """Room pricing information."""

    room_price_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    room_type = models.CharField(max_length=225, null=True, blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    room_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'room_price'
        managed = False

    def __str__(self) -> str:
        return f"RoomPrice #{self.room_price_id} - {self.room_type}"


class HotelServices(models.Model):
    """Model mapped to the SQL Server `hotel_services` table."""

    service_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    name_of_service = models.CharField(max_length=225, null=True, blank=True, db_column='service_name')
    service_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'hotel_services'
        managed = False

    def __str__(self) -> str:
        return f"{self.name_of_service}"


class HotelKeysMain(models.Model):
    """Model mapped to the SQL Server `hotel_keys_main` table."""

    key_id = models.AutoField(primary_key=True)
    hotel = models.ForeignKey('Hotel', models.DO_NOTHING, null=True, blank=True)
    room_key = models.CharField(max_length=225, null=True, blank=True)

    class Meta:
        db_table = 'hotel_keys_main'
        managed = False

    def __str__(self) -> str:
        return f"Key #{self.key_id} - {self.room_key}"


# RBAC Models - Customer Request System
class CustomerRequest(models.Model):
    """Model for customer booking/edit/cancel requests."""
    
    request_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('User', models.DO_NOTHING, related_name='requests')
    booking = models.ForeignKey(
        'CustomerBookingInfo',
        models.DO_NOTHING,
        null=True,
        blank=True,
        related_name='requests'
    )
    request_type = models.CharField(
        max_length=50,
        choices=[
            ('new_booking', 'New Booking'),
            ('edit_booking', 'Edit Booking'),
            ('cancel_booking', 'Cancel Booking'),
        ]
    )
    request_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('completed', 'Completed'),
        ],
        default='pending'
    )
    request_data = models.TextField()  # JSON string with request details
    customer_message = models.TextField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)  # 24hrs before check-in
    created_at = models.DateTimeField(auto_now_add=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(
        'User',
        models.DO_NOTHING,
        null=True,
        blank=True,
        related_name='requests_handled',
        db_column='handled_by'
    )
    staff_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'customer_requests'
        managed = False
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Request #{self.request_id} - {self.get_request_type_display()} by {self.user.username}"
    
    @property
    def is_overdue(self):
        """Check if request is past deadline."""
        if self.deadline and self.request_status == 'pending':
            from django.utils import timezone
            return timezone.now() > self.deadline
        return False


class AuditLog(models.Model):
    """Model for audit trail of all changes."""
    
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('User', models.DO_NOTHING, related_name='audit_logs')
    action_type = models.CharField(
        max_length=50,
        choices=[
            ('CREATE', 'Create'),
            ('UPDATE', 'Update'),
            ('DELETE', 'Delete'),
            ('ROLE_CHANGE', 'Role Change'),
            ('LOGIN', 'Login'),
        ]
    )
    table_name = models.CharField(max_length=100)
    record_id = models.IntegerField(null=True, blank=True)
    old_values = models.TextField(null=True, blank=True)  # JSON string
    new_values = models.TextField(null=True, blank=True)  # JSON string
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_log'
        managed = False
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action_type} on {self.table_name} by {self.user.username} at {self.timestamp}"

# Accounts App Documentation

## Overview
The accounts app manages user authentication, profiles, and account-related functionality for the Sudamall e-commerce platform. It provides comprehensive user management with support for different account types, business owners, and integrated cart management.

---

## 🏗️ Architecture

### Core Models

#### User Model
**File:** `models.py`

The central user model extending Django's `AbstractBaseUser` and `PermissionsMixin`:

```python
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email as the primary identifier.
    Supports both buyer and seller account types with comprehensive profile management.
    """
    
    # Identity Fields
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, default="Unknown")
    last_name = models.CharField(max_length=50, default="Unknown")
    
    # Contact Information
    phone_number = PhoneNumberField(blank=True, null=True, unique=True)
    whatsapp_number = PhoneNumberField(blank=True, null=True, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # Account Management
    account_type = models.CharField(max_length=10, choices=[('seller', 'Seller'), ('buyer', 'Buyer')])
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_store_owner = models.BooleanField(default=False)
    
    # Security & Verification
    otp = models.CharField(max_length=64, blank=True, null=True)  # Hashed OTP
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Profile & Preferences
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True)
    is_subscribed = models.BooleanField(default=False)
    
    # E-commerce Integration
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    favourite_products = models.ManyToManyField('products.Product', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Features:**
- ✅ Email-based authentication (no username)
- ✅ Dual account types (buyer/seller)
- ✅ Comprehensive profile management
- ✅ OTP-based verification system
- ✅ International phone number support
- ✅ Favorite products functionality
- ✅ Spending tracking integration

#### BusinessOwner Model
**File:** `models.py`

Extends user functionality for business owners:

```python
class BusinessOwner(models.Model):
    """
    One-to-one extension of User model for business owners.
    Links users to their owned stores.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_owner_profile')
    store = models.OneToOneField('stores.Store', on_delete=models.CASCADE, related_name='owner')
```

**Features:**
- ✅ One-to-one relationship with User
- ✅ Store ownership management
- ✅ Business profile extension

#### Cart Model
**File:** `models.py`

User shopping cart management:

```python
class Cart(models.Model):
    """
    User shopping cart with status tracking and purchase history.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_spent = models.FloatField(default=0.0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 🔧 Core Functionality

### User Manager
**File:** `userManager.py`

Custom user manager handling user creation and management:

```python
class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password."""
        
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password."""
```

**Features:**
- ✅ Email validation and normalization
- ✅ Password strength enforcement
- ✅ Superuser creation support
- ✅ Field validation and defaults

### OTP System

#### OTP Generation
```python
def generate_otp(self):
    """
    Generates a 6-digit OTP, hashes it for security, and saves it to the model.
    Returns the plain OTP for sending via email/SMS.
    """
    otp_code = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
    hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()
    self.otp = hashed_otp
    self.otp_expires_at = now() + timedelta(minutes=5)  # 5-minute expiry
    self.save()
    return otp_code
```

#### OTP Verification
```python
def verify_otp(self, otp_input):
    """
    Verify the provided OTP against the stored hashed OTP.
    Returns True if verification succeeds, False otherwise.
    """
    if not otp_input or not self.otp_expires_at or now() > self.otp_expires_at:
        return False
    
    hashed_input_otp = hashlib.sha256(otp_input.encode()).hexdigest()
    if self.otp != hashed_input_otp:
        return False
    
    # Clear OTP after successful verification
    self.otp = None
    self.otp_expires_at = None
    self.save()
    return True
```

**Security Features:**
- ✅ Cryptographically secure OTP generation
- ✅ SHA-256 hashing for storage
- ✅ 5-minute expiration window
- ✅ Automatic cleanup after verification
- ✅ Comprehensive logging

---

## 🔒 Security Features

### Password Management
- **Hashing**: Django's built-in password hashing
- **Validation**: Custom password strength requirements
- **Reset**: Secure password reset flow with OTP

### OTP Security
- **Generation**: Cryptographically secure random numbers
- **Storage**: SHA-256 hashed, never stored in plain text
- **Expiration**: 5-minute automatic expiry
- **Rate Limiting**: Protection against brute force attacks

### Authentication
- **Email-based**: No username required
- **JWT Integration**: Token-based authentication
- **OAuth Support**: Google OAuth integration ready

---

## 📊 Database Schema

### User Table
```sql
CREATE TABLE accounts_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(254) UNIQUE NOT NULL,
    first_name VARCHAR(50) DEFAULT 'Unknown',
    last_name VARCHAR(50) DEFAULT 'Unknown',
    phone_number VARCHAR(128) UNIQUE,
    whatsapp_number VARCHAR(128) UNIQUE,
    otp VARCHAR(64),
    otp_expires_at DATETIME,
    is_active BOOLEAN DEFAULT FALSE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_store_owner BOOLEAN DEFAULT FALSE,
    is_subscribed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    account_type VARCHAR(10) DEFAULT 'buyer',
    gender CHAR(1),
    location VARCHAR(255),
    total_spent DECIMAL(10,2) DEFAULT 0.00,
    profile_picture VARCHAR(100),
    password VARCHAR(128) NOT NULL,
    last_login DATETIME,
    is_superuser BOOLEAN DEFAULT FALSE,
    
    INDEX idx_email (email),
    INDEX idx_phone (phone_number),
    INDEX idx_whatsapp (whatsapp_number),
    INDEX idx_otp (otp),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
);
```

### BusinessOwner Table
```sql
CREATE TABLE accounts_businessowner (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT UNIQUE NOT NULL,
    store_id BIGINT UNIQUE NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores_store(id) ON DELETE CASCADE
);
```

### Cart Table
```sql
CREATE TABLE accounts_cart (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    total_spent DOUBLE DEFAULT 0.0,
    last_purchase_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE,
    INDEX idx_user_status (user_id, status),
    INDEX idx_created_at (created_at)
);
```

---

## 🧪 Testing

### Test Coverage
**File:** `tests.py`

The accounts app includes comprehensive tests covering:

#### User Model Tests
- ✅ User creation and validation
- ✅ Email uniqueness enforcement
- ✅ Password hashing verification
- ✅ OTP generation and verification
- ✅ Profile management

#### Authentication Tests
- ✅ User registration flow
- ✅ Login/logout functionality
- ✅ JWT token generation
- ✅ Password reset process
- ✅ OTP verification flow

#### BusinessOwner Tests
- ✅ Business owner profile creation
- ✅ Store assignment validation
- ✅ Permission management

#### Security Tests
- ✅ OTP security validation
- ✅ Password strength requirements
- ✅ Rate limiting verification
- ✅ SQL injection protection

### Running Tests
```bash
# Run all accounts tests
python3 manage.py test accounts

# Run specific test classes
python3 manage.py test accounts.tests.UserModelTest
python3 manage.py test accounts.tests.AuthenticationTest
python3 manage.py test accounts.tests.BusinessOwnerTest

# Run with coverage
coverage run --source='.' manage.py test accounts
coverage report -m
```

---

## 🔗 Integration Points

### Authentication App
- JWT token generation and validation
- OAuth integration support
- Login/logout endpoint management

### Products App
- Favorite products relationship
- User-product interaction tracking
- Product ownership validation

### Stores App
- Business owner store assignment
- Store management permissions
- Multi-store support

### Orders App
- User order history
- Spending calculation
- Order permission validation

### Carts App
- User cart management
- Cart item tracking
- Checkout integration

---

## 📋 API Endpoints

### User Management
```
GET    /api/accounts/profile/        # Get user profile
PUT    /api/accounts/profile/        # Update user profile
DELETE /api/accounts/profile/        # Delete user account
```

### Favorites
```
GET    /api/accounts/favorites/      # List favorite products
POST   /api/accounts/favorites/      # Add product to favorites
DELETE /api/accounts/favorites/{id}/ # Remove from favorites
```

### Business Owner
```
GET    /api/accounts/business/       # Get business owner profile
PUT    /api/accounts/business/       # Update business profile
```

---

## 🚀 Usage Examples

### User Registration
```python
from accounts.models import User

# Create a new user
user = User.objects.create_user(
    email='user@example.com',
    password='secure_password',
    first_name='John',
    last_name='Doe',
    account_type='buyer'
)
```

### OTP Generation and Verification
```python
# Generate OTP
otp_code = user.generate_otp()
# Send OTP via email/SMS (implementation in notifications app)

# Verify OTP
is_valid = user.verify_otp('123456')
if is_valid:
    user.is_active = True
    user.save()
```

### Business Owner Creation
```python
from accounts.models import BusinessOwner
from stores.models import Store

# Create business owner profile
business_owner = BusinessOwner.objects.create(
    user=user,
    store=store
)
user.is_store_owner = True
user.account_type = 'seller'
user.save()
```

---

## 🔧 Configuration

### Settings
```python
# In settings.py
AUTH_USER_MODEL = 'accounts.User'
USERNAME_FIELD = 'email'
REQUIRED_FIELDS = ['first_name', 'last_name']

# OTP Configuration
OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6

# Profile Picture Settings
PROFILE_PIC_MAX_SIZE = 5 * 1024 * 1024  # 5MB
PROFILE_PIC_ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
```

### Admin Configuration
```python
# In admin.py
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'account_type', 'is_active', 'created_at')
    list_filter = ('account_type', 'is_active', 'is_staff', 'is_store_owner', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
```

---

## 📈 Performance Considerations

### Database Optimization
- **Indexes**: Strategic indexing on frequently queried fields
- **Queries**: Optimized query patterns with select_related/prefetch_related
- **Caching**: Redis-based session and query caching

### Security Optimization
- **Password Hashing**: Argon2 for production environments
- **Rate Limiting**: django-ratelimit for OTP and login endpoints
- **HTTPS**: Enforce HTTPS in production

### File Handling
- **Profile Pictures**: Compressed and resized automatically
- **Storage**: S3 or similar for production file storage
- **CDN**: CloudFront for static file delivery

---

## 🔮 Future Enhancements

### Planned Features
- [ ] Two-factor authentication (2FA) support
- [ ] Social login (Facebook, Twitter, GitHub)
- [ ] User activity logging and analytics
- [ ] Advanced profile customization
- [ ] Multi-language support
- [ ] Account suspension/deactivation workflows

### API Improvements
- [ ] GraphQL endpoint support
- [ ] Advanced filtering and pagination
- [ ] Bulk operations support
- [ ] Real-time user status updates

---

## 🤝 Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Maintain test coverage above 90%
- Document all public methods

### Testing Requirements
- Write tests for all new features
- Include edge case testing
- Test security vulnerabilities
- Validate database constraints

---

**This accounts app provides the foundation for user management in the Sudamall e-commerce platform, with robust security, comprehensive profiles, and seamless integration with all other system components.**

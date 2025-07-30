# Sudamall E-Commerce Backend

A comprehensive Django-based e-commerce platform providing complete order management, inventory control, payment processing, and user management with advanced product history tracking and real-time cart synchronization.

---

## 🚀 Key Features

### 🔐 **Authentication & User Management**
- **Multi-Authentication Support**
  - Email/password login and registration
  - JWT-based authentication (access & refresh tokens)
  - Google OAuth2 integration
  - OTP verification for sensitive operations
  - Rate limiting and security throttling

- **User Profiles**
  - Business owner and buyer account types
  - Profile management with image uploads
  - Phone and WhatsApp number validation
  - Favorite products management
  - Comprehensive user activity tracking

### 🛍️ **E-Commerce Core**
- **Product Management**
  - Full CRUD operations with soft delete
  - Product history tracking for audit trails
  - Size variations and inventory management
  - Category and tag organization
  - Offer and pricing management
  - Elasticsearch integration for search

- **Advanced Cart System**
  - Real-time cart synchronization
  - Stock reservation during checkout
  - Product change detection and updates
  - Size-based product variations
  - Automatic cleanup and validation

- **Order Processing**
  - Complete order lifecycle management
  - Product history snapshots at order time
  - Order status tracking and updates
  - Integration with payment timers
  - Comprehensive order validation

### 💳 **Payment Integration**
- **Multi-Gateway Support**
  - Test payment gateway for development
  - Stripe integration ready
  - PayPal integration ready
  - Webhook handling for payment confirmation

- **Payment Features**
  - 15-minute payment timers
  - Automatic stock unreservation on timeout
  - Payment attempt tracking
  - Refund management
  - Payment history and analytics

### 📊 **Inventory & Stock Management**
- **Real-Time Stock Control**
  - Atomic stock operations
  - Stock reservation system
  - Sized product inventory tracking
  - Concurrent operation handling
  - Stock availability validation

### 🔔 **Notifications & Communication**
- **Email System**
  - Template-based email notifications
  - Celery-powered background sending
  - Email styling and attachments
  - Transactional email support

- **Real-Time Chat**
  - WebSocket-based messaging
  - User-to-user communication
  - Chat history and persistence

### 🏪 **Store Management**
- **Multi-Store Support**
  - Store creation and management
  - Owner assignment and permissions
  - Store-specific product catalogs
  - Location-based services

### 🔍 **Search & Discovery**
- **Advanced Search**
  - Elasticsearch-powered search
  - Product filtering and sorting
  - Category-based browsing
  - Search analytics and insights

---

## 🛠️ Tech Stack

### Backend Framework
- **Django 5.2+** - High-level Python web framework
- **Django REST Framework** - Powerful toolkit for building APIs
- **Python 3.12+** - Modern Python runtime

### Database & Storage
- **MySQL** - Primary database for production
- **SQLite** - In-memory database for testing
- **Redis** - Caching and session storage

### Authentication & Security
- **SimpleJWT** - JSON Web Token authentication
- **django-oauth-toolkit** - OAuth2 provider
- **django-ratelimit** - Rate limiting protection

### Search & Analytics
- **Elasticsearch** - Full-text search and analytics
- **django-elasticsearch-dsl** - Elasticsearch integration

### Asynchronous Processing
- **Celery** - Distributed task queue
- **django-celery-beat** - Periodic task scheduler
- **Redis** - Message broker for Celery

### API Documentation
- **drf-spectacular** - OpenAPI 3.0 schema generation
- **Swagger UI** - Interactive API documentation

### Media & File Handling
- **Pillow** - Image processing and validation
- **django-phonenumber-field** - International phone number handling

### Testing & Quality
- **pytest** - Modern testing framework
- **pytest-django** - Django-specific pytest plugins
- **factory-boy** - Test data generation

---

## 📁 Project Structure

```
sudamall-backend/
├── api/                          # Main Django project
│   ├── accounts/                 # User management & authentication
│   │   ├── models.py            # User, BusinessOwner, Cart models
│   │   ├── views.py             # Authentication endpoints
│   │   ├── serializers.py       # User data serialization
│   │   ├── userManager.py       # Custom user manager
│   │   └── tests.py             # Authentication tests
│   │
│   ├── authentication/          # JWT & OAuth authentication
│   │   ├── views.py             # Login, register, OAuth endpoints
│   │   ├── serializers.py       # Auth data validation
│   │   ├── services.py          # Auth business logic
│   │   └── tests.py             # Authentication flow tests
│   │
│   ├── products/                # Product catalog management
│   │   ├── models.py            # Product, Size, Category, ProductHistory
│   │   ├── views.py             # Product CRUD operations
│   │   ├── serializers.py       # Product data serialization
│   │   ├── documents.py         # Elasticsearch mapping
│   │   └── tests.py             # Product functionality tests
│   │
│   ├── carts/                   # Shopping cart system
│   │   ├── models.py            # Cart, CartItem models
│   │   ├── views.py             # Cart management endpoints
│   │   ├── services.py          # Cart business logic
│   │   ├── managers.py          # Custom cart managers
│   │   └── tests.py             # Cart functionality tests
│   │
│   ├── orders/                  # Order management
│   │   ├── models.py            # Order model with history tracking
│   │   ├── views.py             # Order processing endpoints
│   │   ├── serializers.py       # Order data validation
│   │   └── tests.py             # Order workflow tests
│   │
│   ├── payments/                # Payment processing
│   │   ├── models.py            # Payment, PaymentGateway, PaymentAttempt
│   │   ├── views.py             # Payment endpoints
│   │   ├── services.py          # Payment gateway integration
│   │   └── tests.py             # Payment flow tests
│   │
│   ├── stores/                  # Store management
│   │   ├── models.py            # Store model
│   │   ├── views.py             # Store operations
│   │   └── tests.py             # Store functionality tests
│   │
│   ├── notifications/           # Email & notification system
│   │   ├── models.py            # EmailTemplate, EmailStyle models
│   │   ├── views.py             # Notification endpoints
│   │   ├── tasks.py             # Celery email tasks
│   │   └── tests.py             # Notification tests
│   │
│   ├── chat/                    # Real-time messaging
│   │   ├── models.py            # ChatMessage model
│   │   ├── consumers.py         # WebSocket consumers
│   │   ├── routing.py           # WebSocket routing
│   │   └── tests.py             # Chat functionality tests
│   │
│   ├── search/                  # Search & discovery
│   │   ├── documents.py         # Elasticsearch documents
│   │   ├── views.py             # Search endpoints
│   │   └── tests.py             # Search functionality tests
│   │
│   └── api/                     # Main project configuration
│       ├── settings.py          # Django settings
│       ├── urls.py              # URL routing
│       ├── celery.py            # Celery configuration
│       └── asgi.py              # ASGI configuration
│
├── requirements/                # Dependencies
│   ├── dev.txt                 # Development dependencies
│   ├── prod.txt                # Production dependencies
│   └── test.txt                # Testing dependencies
│
├── mysql-init/                  # Database initialization
│   ├── init.sql                # Main database setup
│   └── init1.sql               # Additional permissions
│
├── docs/                        # Documentation
└── logs/                        # Application logs
```

---

## ⚡ Quickstart

1. **Clone the repository**
   ```bash
   git clone [git@github.com:Code-for-sudan/back-end.git](https://github.com/Code-for-sudan/back-end.git)
   cd Code-for-sudan/back-end
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Configure environment variables**
   - Make sure all the env files in the app dir.

5. **Apply migrations**
   ```bash
   python manage.py makemigrations 
   python manage.py migrate
   ```

6. **Run the development server**
   ```bash
   DJANGO_ENV=dev python manage.py runserver
   ```

7. **Start Celery worker (in a separate terminal)**
   ```bash
   celery -A api worker --loglevel=info
   ```

8. **Start Celery beat (in a separate terminal)**
   ```bash
   celery -A api beat --loglevel=info
   ```

9. **Access API docs**
   - Visit [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)

---

## 🧪 Testing

### Run All Tests
```bash
cd api
python3 manage.py test
```

### Run Specific App Tests
```bash
python3 manage.py test accounts
python3 manage.py test products
python3 manage.py test orders
python3 manage.py test carts
python3 manage.py test payments
```

### Test Coverage
The project includes **139 comprehensive tests** covering:
- ✅ Authentication flows (15 tests)
- ✅ Product management (35 tests)
- ✅ Cart operations (25 tests)
- ✅ Order processing (20 tests)
- ✅ Payment integration (18 tests)
- ✅ User management (12 tests)
- ✅ Store operations (8 tests)
- ✅ Notification system (6 tests)

### Test Database
Tests use SQLite in-memory database for fast execution:
- No setup required
- Automatic cleanup
- Isolated test environments

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- MySQL 8.0+
- Redis (optional, for Celery and caching)
- Elasticsearch (optional, for search functionality)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd E-Commerc-Sudan/back-end
```

2. **Create and activate virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements/dev.txt
```

4. **Database setup**
```bash
# Create MySQL database
mysql -u root -p < mysql-init/init.sql

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials
```

5. **Run migrations**
```bash
cd api
python3 manage.py migrate
```

6. **Create superuser**
```bash
python3 manage.py createsuperuser
```

7. **Start development server**
```bash
python3 manage.py runserver
```

### Environment Configuration

Create a `.env` file in the `api/` directory:

```env
# Database Configuration
DB_NAME=sudamall_db
DB_USER=api
DB_PASSWORD=sudamall_password
DB_HOST=localhost
DB_PORT=3306

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis Configuration (optional)
REDIS_DATABASE_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Elasticsearch Configuration (optional)
ELASTICSEARCH_URL=elasticsearch://localhost:9200
```

---

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Key API Endpoints

#### Authentication
```
POST /api/auth/register/          # User registration
POST /api/auth/login/             # User login
POST /api/auth/refresh/           # Token refresh
POST /api/auth/logout/            # User logout
POST /api/auth/google/            # Google OAuth
```

#### Products
```
GET    /api/products/             # List products
POST   /api/products/             # Create product
GET    /api/products/{id}/        # Get product details
PUT    /api/products/{id}/        # Update product
DELETE /api/products/{id}/        # Delete product (soft delete)
```

#### Cart
```
GET    /api/cart/                 # Get user cart
POST   /api/cart/add/             # Add item to cart
PUT    /api/cart/items/{id}/      # Update cart item
DELETE /api/cart/items/{id}/      # Remove cart item
POST   /api/cart/checkout/        # Checkout cart
```

#### Orders
```
GET    /api/orders/               # List user orders
POST   /api/orders/               # Create order
GET    /api/orders/{id}/          # Get order details
PUT    /api/orders/{id}/status/   # Update order status
```

#### Payments
```
POST   /api/payments/create/      # Create payment
POST   /api/payments/confirm/     # Confirm payment
GET    /api/payments/{id}/        # Get payment details
POST   /api/payments/webhook/     # Payment webhook
```

---

## 🔧 Development

### Code Quality
- **Linting**: Follow PEP 8 standards
- **Testing**: Maintain test coverage above 90%
- **Documentation**: Document all public APIs
- **Type Hints**: Use Python type annotations

### Database Migrations
```bash
# Create new migrations
python3 manage.py makemigrations

# Apply migrations
python3 manage.py migrate

# Check migration status
python3 manage.py showmigrations
```

### Background Tasks
```bash
# Start Celery worker (in separate terminal)
celery -A api worker --loglevel=info

# Start Celery beat scheduler (in separate terminal)
celery -A api beat --loglevel=info
```

---

## � Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up Redis for caching
- [ ] Configure Elasticsearch
- [ ] Set up SSL certificates
- [ ] Configure static file serving
- [ ] Set up monitoring and logging
- [ ] Configure backup strategies

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## � Key Features Documentation

### Product History Tracking
Every product change is automatically tracked:
- Price changes recorded with timestamps
- Product information snapshots at order time
- Historical data preserved for audit trails
- Order consistency validation

### Real-Time Cart Management
- Instant cart synchronization across sessions
- Stock reservation during checkout process
- Automatic product change detection
- Size-based inventory tracking

### Payment Timer System
- 15-minute payment windows
- Automatic stock unreservation on timeout
- Payment attempt tracking
- Multiple gateway support

### Advanced Stock Management
- Atomic stock operations
- Concurrent transaction handling
- Size-specific inventory control
- Real-time availability checking

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Write tests for new features
- Follow existing code style
- Update documentation
- Add type hints
- Ensure tests pass

---

## 📞 Support

For questions and support:
- Create an issue on GitHub
- Check the documentation
- Review existing tests for examples

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ for the Sudamall E-Commerce Platform**

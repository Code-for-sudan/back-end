# Payments App Documentation

## Overview
The payments app manages all payment processing for the Sudamall e-commerce platform. It supports multiple payment gateways, handles payment workflows, manages payment attempts, provides payment security, and integrates with order processing.

---

## 🏗️ Architecture

### Core Models

#### PaymentGateway Model
**File:** `models.py`

```python
class PaymentGateway(models.Model):
    """
    Configuration for different payment gateways.
    """
    
    # Gateway Identification
    gateway_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    
    # Gateway Configuration
    is_active = models.BooleanField(default=True)
    is_sandbox = models.BooleanField(default=False)
    
    # API Configuration
    api_key = models.CharField(max_length=255, blank=True)
    secret_key = models.CharField(max_length=255, blank=True)
    merchant_id = models.CharField(max_length=100, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    
    # Gateway Settings
    supported_currencies = models.JSONField(default=list)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Processing Configuration
    auto_capture = models.BooleanField(default=True)
    supports_refunds = models.BooleanField(default=True)
    supports_partial_refunds = models.BooleanField(default=True)
    
    # Fee Configuration
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    percentage_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Additional Settings
    timeout_seconds = models.IntegerField(default=300)  # 5 minutes
    retry_attempts = models.IntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
```

#### Payment Model
**File:** `models.py`

```python
class Payment(models.Model):
    """
    Main payment model for tracking all payment transactions.
    """
    
    # Payment Status Choices
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
        ('expired', 'Expired'),
    ]
    
    # Payment Identification
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Related Objects
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='SDG')
    
    # Gateway-specific Information
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_reference = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Payment Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True, null=True)
    
    # Payment Methods
    payment_method = models.CharField(max_length=50, blank=True)  # card, mobile_money, bank_transfer
    payment_details = models.JSONField(default=dict, blank=True)  # Store payment-specific data
    
    # Processing Information
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timing Information
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Refund Information
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    refund_reason = models.TextField(blank=True, null=True)
    
    # Security and Audit
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Additional Data
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status', 'gateway']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Calculate net amount before saving."""
        if not self.net_amount:
            self.net_amount = self.amount - self.processing_fee
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if payment has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
    
    @property
    def can_be_refunded(self):
        """Check if payment can be refunded."""
        return (
            self.status == 'completed' and
            self.gateway.supports_refunds and
            self.refunded_amount < self.amount
        )
    
    def calculate_refundable_amount(self):
        """Calculate the amount that can be refunded."""
        return self.amount - self.refunded_amount
```

#### PaymentAttempt Model
**File:** `models.py`

```python
class PaymentAttempt(models.Model):
    """
    Track individual payment attempts for a payment.
    """
    
    ATTEMPT_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
        ('cancelled', 'Cancelled'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.PositiveIntegerField()
    
    status = models.CharField(max_length=20, choices=ATTEMPT_STATUS_CHOICES, default='initiated')
    
    # Gateway Response
    gateway_response = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Request/Response Data
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['payment', 'attempt_number']
        ordering = ['-started_at']
```

**Key Features:**
- ✅ Multi-gateway payment processing
- ✅ Secure payment handling
- ✅ Payment attempt tracking
- ✅ Refund management
- ✅ Payment expiration handling
- ✅ Comprehensive audit trail
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict)
    
    # User information
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    billing_address = models.JSONField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
```

## Test Mode Implementation

### Environment Configuration

#### Django Settings
```python
# settings.py
PAYMENT_SETTINGS = {
    'DEFAULT_CURRENCY': 'USD',
    'TEST_MODE': True,  # Set to False in production
    'PAYMENT_TIMEOUT_MINUTES': 30,
    'ENABLE_PAYMENT_SIMULATION': True,  # For development only
    
    # Test Gateway Configuration
    'TEST_GATEWAYS': {
        'stripe_test': {
            'name': 'stripe_test',
            'display_name': 'Stripe (Test)',
            'api_key': 'pk_test_...',
            'secret_key': 'sk_test_...',
            'webhook_secret': 'whsec_...',
            'is_test_mode': True
        },
        'paypal_sandbox': {
            'name': 'paypal_sandbox',
            'display_name': 'PayPal (Sandbox)',
            'api_key': 'sandbox_client_id',
            'secret_key': 'sandbox_secret',
            'is_test_mode': True
        }
    }
}
```

### Test Payment Processing

#### 1. Creating Test Payments
```python
# Example: Creating a test payment
from payments.services import PaymentService

# Create payment for orders
payment = PaymentService.create_payment_for_orders(
    orders=[order1, order2],
    payment_method='credit_card',
    gateway_name='stripe_test'
)

# In test mode, payment is automatically marked for simulation
print(f"Payment ID: {payment.payment_id}")
print(f"Test Mode: {payment.gateway.is_test_mode}")
```

#### 2. Test Card Numbers (Stripe Test Mode)
```python
TEST_CARDS = {
    'success': {
        'card_number': '4242424242424242',
        'exp_month': 12,
        'exp_year': 2025,
        'cvc': '123',
        'expected_result': 'success'
    },
    'declined': {
        'card_number': '4000000000000002',
        'exp_month': 12,
        'exp_year': 2025,
        'cvc': '123',
        'expected_result': 'card_declined'
    },
    'insufficient_funds': {
        'card_number': '4000000000009995',
        'exp_month': 12,
        'exp_year': 2025,
        'cvc': '123',
        'expected_result': 'insufficient_funds'
    },
    'expired_card': {
        'card_number': '4000000000000069',
        'exp_month': 12,
        'exp_year': 2020,
        'cvc': '123',
        'expected_result': 'expired_card'
    }
}
```

#### 3. Payment Simulation API
```python
# API Endpoint: POST /api/payments/simulate/
{
    "payment_id": "PAY-ABC123",
    "simulation_type": "success",  # success, declined, insufficient_funds, expired_card
    "test_card_number": "4242424242424242",
    "delay_seconds": 2  # Simulate processing delay
}

# Response:
{
    "success": true,
    "payment_id": "PAY-ABC123",
    "simulation_result": "success",
    "new_status": "completed",
    "message": "Payment simulation completed successfully",
    "gateway_response": {
        "transaction_id": "sim_txn_123456",
        "test_mode": true,
        "simulated_at": "2025-07-25T10:30:00Z"
    }
}
```

### Complete Test Transaction Flow

#### Step 1: Create Orders (Cart Checkout)
```bash
# Single item checkout
curl -X POST http://localhost:8000/api/carts/checkout/single/ \
-H "Authorization: Bearer YOUR_JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
    "cart_item_id": 123,
    "payment_method": "credit_card",
    "gateway_name": "stripe_test",
    "shipping_address": {
        "street": "123 Test St",
        "city": "Khartoum",
        "state": "Khartoum",
        "postal_code": "12345"
    }
}'

# Response includes payment_id for next step
{
    "checkout_type": "single_item",
    "payment_id": "PAY-ABC123",
    "payment_hash": "HASH-XYZ789",
    "order": {...}
}
```

#### Step 2: Simulate Payment Processing
```bash
# Simulate successful payment
curl -X POST http://localhost:8000/api/payments/simulate/ \
-H "Authorization: Bearer YOUR_JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
    "payment_id": "PAY-ABC123",
    "simulation_type": "success",
    "test_card_number": "4242424242424242"
}'

# Simulate declined payment
curl -X POST http://localhost:8000/api/payments/simulate/ \
-H "Authorization: Bearer YOUR_JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
    "payment_id": "PAY-ABC123",
    "simulation_type": "declined",
    "test_card_number": "4000000000000002"
}'
```

#### Step 3: Webhook Simulation (Optional)
```bash
# Simulate webhook callback
curl -X POST http://localhost:8000/api/payments/webhook/stripe/ \
-H "Content-Type: application/json" \
-d '{
    "id": "evt_test_webhook",
    "object": "event",
    "type": "payment_intent.succeeded",
    "data": {
        "object": {
            "id": "pi_test_123",
            "status": "succeeded",
            "metadata": {
                "payment_id": "PAY-ABC123"
            }
        }
    }
}'
```

## API Endpoints Reference

### Payment Management
- `POST /api/payments/create/` - Create new payment
- `GET /api/payments/{payment_id}/` - Get payment details
- `POST /api/payments/{payment_id}/process/` - Process payment
- `POST /api/payments/{payment_id}/cancel/` - Cancel payment
- `POST /api/payments/{payment_id}/refund/` - Create refund

### Test Mode Specific
- `POST /api/payments/simulate/` - Simulate payment processing
- `GET /api/payments/test-cards/` - Get test card numbers
- `POST /api/payments/reset-test-data/` - Reset test environment

### Webhook Endpoints
- `POST /api/payments/webhook/stripe/` - Stripe webhook handler
- `POST /api/payments/webhook/paypal/` - PayPal webhook handler

## PaymentService Methods

### Core Payment Methods
```python
class PaymentService:
    @staticmethod
    def create_payment_for_orders(orders, payment_method, gateway_name):
        """Create payment for one or multiple orders"""
        
    @staticmethod
    def process_payment(payment_id, payment_data):
        """Process payment with gateway"""
        
    @staticmethod
    def simulate_payment(payment_id, simulation_type, test_card_data=None):
        """Simulate payment processing (test mode only)"""
        
    @staticmethod
    def handle_webhook(gateway_name, webhook_data):
        """Process webhook from payment gateway"""
        
    @staticmethod
    def create_refund(payment_id, amount, reason):
        """Create refund for payment"""
```

### Test Mode Methods
```python
@staticmethod
def simulate_payment_scenarios():
    """Get available test scenarios"""
    return {
        'success': 'Payment succeeds immediately',
        'declined': 'Payment is declined by bank',
        'insufficient_funds': 'Insufficient funds in account',
        'expired_card': 'Card has expired',
        'processing_error': 'Gateway processing error',
        'timeout': 'Payment processing timeout'
    }

@staticmethod
def get_test_cards():
    """Get test card numbers for different scenarios"""
    return TEST_CARDS

@staticmethod
def reset_test_environment():
    """Reset all test payments and orders"""
    if not settings.PAYMENT_SETTINGS.get('TEST_MODE'):
        raise ValidationError("Reset only available in test mode")
    
    # Reset test payments
    Payment.objects.filter(gateway__is_test_mode=True).delete()
    # Reset associated orders
    Order.objects.filter(status='under_paying', payment_hash__startswith='TEST-').delete()
```

## Error Handling

### Payment Errors
```python
PAYMENT_ERRORS = {
    'INVALID_CARD': 'Card number is invalid',
    'EXPIRED_CARD': 'Card has expired',
    'INSUFFICIENT_FUNDS': 'Insufficient funds',
    'DECLINED': 'Payment was declined',
    'PROCESSING_ERROR': 'Payment processing failed',
    'GATEWAY_ERROR': 'Gateway communication error',
    'TIMEOUT': 'Payment processing timeout'
}
```

### Error Response Format
```json
{
    "success": false,
    "error_code": "INSUFFICIENT_FUNDS",
    "error_message": "Insufficient funds",
    "payment_id": "PAY-ABC123",
    "gateway_response": {
        "code": "card_declined",
        "decline_code": "insufficient_funds"
    },
    "retry_allowed": true,
    "suggested_action": "Try a different payment method"
}
```

## Security Considerations

### Test Mode Security
- Test mode data is clearly marked and segregated
- Test API keys cannot process real transactions
- Webhook signatures are validated even in test mode
- Test data can be reset without affecting production

### Production Security
- API keys stored securely in environment variables
- Webhook signatures validated for authenticity
- PCI compliance for card data handling
- Encrypted storage of sensitive payment data

## Integration Examples

### Frontend Integration (JavaScript)
```javascript
// Create payment and handle test scenarios
async function processTestPayment(orderId, testScenario = 'success') {
    try {
        // Create payment
        const paymentResponse = await fetch('/api/payments/create/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                payment_method: 'credit_card',
                gateway_name: 'stripe_test'
            })
        });
        
        const payment = await paymentResponse.json();
        
        // Simulate payment processing
        const simulationResponse = await fetch('/api/payments/simulate/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                payment_id: payment.payment_id,
                simulation_type: testScenario,
                test_card_number: getTestCardNumber(testScenario)
            })
        });
        
        const result = await simulationResponse.json();
        
        if (result.success) {
            console.log('Payment simulation successful:', result);
            // Redirect to success page
            window.location.href = `/payment/success/${payment.payment_id}`;
        } else {
            console.error('Payment simulation failed:', result);
            // Show error message
            showErrorMessage(result.error_message);
        }
        
    } catch (error) {
        console.error('Payment processing error:', error);
    }
}

function getTestCardNumber(scenario) {
    const testCards = {
        'success': '4242424242424242',
        'declined': '4000000000000002',
        'insufficient_funds': '4000000000009995',
        'expired_card': '4000000000000069'
    };
    
    return testCards[scenario] || testCards['success'];
}
```

### Testing Scenarios
```python
# Unit test example
class PaymentTestCase(TestCase):
    def setUp(self):
        self.test_gateway = PaymentGateway.objects.create(
            name='test_gateway',
            display_name='Test Gateway',
            is_test_mode=True,
            api_key='test_key',
            secret_key='test_secret'
        )
    
    def test_successful_payment_simulation(self):
        # Create test order
        order = Order.objects.create(...)
        
        # Create payment
        payment = PaymentService.create_payment_for_orders(
            orders=[order],
            payment_method='credit_card',
            gateway_name='test_gateway'
        )
        
        # Simulate successful payment
        result = PaymentService.simulate_payment(
            payment_id=payment.payment_id,
            simulation_type='success'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'completed')
        
        # Verify order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'completed')
    
    def test_declined_payment_simulation(self):
        # Similar test for declined payment scenario
        pass
```

## Monitoring and Analytics

### Payment Metrics Dashboard
- Total transaction volume
- Success/failure rates by gateway
- Average processing time
- Error frequency by type
- Test vs production transaction counts

### Logging
```python
import logging

payment_logger = logging.getLogger('payments')

# Log all payment events
payment_logger.info(f"Payment created: {payment.payment_id}")
payment_logger.info(f"Payment processed: {payment.payment_id} - Status: {payment.status}")
payment_logger.error(f"Payment failed: {payment.payment_id} - Error: {error_message}")
```

This comprehensive payment system provides robust test mode capabilities, complete transaction simulation, and production-ready payment processing with multiple gateway support.

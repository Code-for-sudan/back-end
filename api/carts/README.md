# Cart System Documentation

## Overview
The cart system provides comprehensive shopping cart functionality with support for single-item and full-cart checkout scenarios. It integrates with the stock management system for inventory control and the payment system for order processing with automatic payment timer functionality.

## Architecture

### Core Components
- **Cart**: User's shopping cart container
- **CartItem**: Individual items in the cart with quantity and variations
- **CartService**: Business logic for cart operations
- **Stock Integration**: Real-time inventory management
- **Payment Timer**: 15-minute checkout window with automatic cleanup

### Database Schema

#### Cart Model
```python
class Cart(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def is_empty(self):
        return not self.items.exists()
```

#### CartItem Model
```python
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=20, blank=True, null=True)
    product_properties = models.JSONField(blank=True, null=True)
    is_stock_reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity
    
    @property
    def unit_price(self):
        return self.product.price
```

## Key Features

### 1. Enhanced Checkout Logic
- **Single Item Checkout**: Purchase one specific item from cart (item removed after checkout)
- **Full Cart Checkout**: Purchase all items in cart (cart cleared after checkout)
- **Stock Validation**: Real-time stock checking before checkout
- **Payment Integration**: Seamless payment creation and processing
- **Payment Timer**: 15-minute payment window with automatic cleanup

### 2. Stock Management Integration
- **Stock Reservation**: Automatically reserves stock when items added to cart
- **Stock Validation**: Checks availability before checkout
- **Size Support**: Handles products with and without size variations
- **Inventory Control**: Uses existing StockService for all operations
- **Automatic Unreservation**: Stock released after payment timeout

### 3. Payment System Integration
- **Unified Payment Hash**: Multiple orders share same payment identifier
- **Gateway Support**: Supports multiple payment gateways
- **Test Environment**: Simulation capabilities for development
- **Timer Integration**: Orders expire after 15 minutes without payment

## API Endpoints

### Cart Management
```http
GET /api/carts/                    # Get cart details with all items
GET /api/carts/count/              # Get cart item count and total
POST /api/carts/add/               # Add item to cart
PUT /api/carts/update/<cart_item_id>/  # Update item quantity
DELETE /api/carts/remove/<cart_item_id>/  # Remove item from cart
DELETE /api/carts/clear/           # Clear entire cart
```

### Validation
```http
POST /api/carts/validate/          # Validate cart before checkout
```

### Enhanced Checkout
```http
POST /api/carts/checkout/single/   # Checkout single item from cart
POST /api/carts/checkout/full/     # Checkout all items in cart
```

## Detailed API Reference

### Add to Cart
```http
POST /api/carts/add/
```

**Request Body:**
```json
{
    "product_id": 123,
    "quantity": 2,
    "size": "L",
    "product_properties": {
        "color": "red",
        "material": "cotton"
    }
}
```

**Response:**
```json
{
    "message": "Item added to cart successfully",
    "cart_item_id": 456,
    "cart_summary": {
        "total_items": 3,
        "total_price": "299.99"
    }
}
```

### Update Cart Item
```http
PUT /api/carts/update/456/
```

**Request Body:**
```json
{
    "quantity": 3
}
```

**Response:**
```json
{
    "message": "Cart item updated successfully",
    "new_quantity": 3,
    "new_subtotal": "149.97"
}
```

### Cart Validation
```http
POST /api/carts/validate/
```

**Request Body (Optional - validates specific items):**
```json
{
    "cart_item_ids": [456, 789]
}
```

**Response:**
```json
{
    "is_valid": true,
    "total_valid_amount": "299.99",
    "validation_details": [
        {
            "cart_item_id": 456,
            "product_name": "T-Shirt",
            "requested_quantity": 2,
            "is_valid": true,
            "available_quantity": 50,
            "item_total": "149.98"
        }
    ]
}
```

### Single Item Checkout
```http
POST /api/carts/checkout/single/
```

**Request Body:**
```json
{
    "cart_item_id": 456,
    "payment_method": "credit_card",
    "gateway_name": "stripe",
    "shipping_address": {
        "street": "123 Main St",
        "city": "Khartoum",
        "state": "Khartoum",
        "postal_code": "12345",
        "country": "Sudan"
    }
}
```

**Response:**
```json
{
    "checkout_type": "single_item",
    "total_amount": "74.99",
    "order_count": 1,
    "payment_id": "PAY-ABC123",
    "payment_hash": "HASH-XYZ789",
    "payment_expires_at": "2025-07-25T11:45:00Z",
    "time_remaining_seconds": 900,
    "order": {
        "order_id": "ORD-001",
        "product_name": "T-Shirt",
        "quantity": 1,
        "total_price": "74.99",
        "status": "under_paying"
    }
}
```

### Full Cart Checkout
```http
POST /api/carts/checkout/full/
```

**Request Body:**
```json
{
    "payment_method": "credit_card",
    "gateway_name": "stripe",
    "shipping_address": {
        "street": "123 Main St",
        "city": "Khartoum",
        "state": "Khartoum",
        "postal_code": "12345",
        "country": "Sudan"
    }
}
```

**Response:**
```json
{
    "checkout_type": "full_cart",
    "total_amount": "299.99",
    "order_count": 3,
    "payment_id": "PAY-DEF456",
    "payment_hash": "HASH-ABC123",
    "payment_expires_at": "2025-07-25T11:45:00Z",
    "time_remaining_seconds": 900,
    "orders": [
        {
            "order_id": "ORD-002",
            "product_name": "T-Shirt",
            "quantity": 2,
            "total_price": "149.98",
            "status": "under_paying"
        },
        {
            "order_id": "ORD-003",
            "product_name": "Jeans",
            "quantity": 1,
            "total_price": "149.99",
            "status": "under_paying"
        }
    ]
}
```

## Business Logic Flow

### Cart Operations Flow
```mermaid
graph TD
    A[User adds item to cart] --> B[Check product availability]
    B --> C[Reserve stock]
    C --> D[Create cart item]
    D --> E[Update cart totals]
    
    F[User updates quantity] --> G[Check new quantity availability]
    G --> H[Adjust stock reservation]
    H --> I[Update cart item]
    
    J[User removes item] --> K[Unreserve stock]
    K --> L[Delete cart item]
```

### Checkout Flow
```mermaid
graph TD
    A[User initiates checkout] --> B[Validate cart items]
    B --> C{Single or Full?}
    
    C -->|Single| D[Validate single item]
    C -->|Full| E[Validate all items]
    
    D --> F[Create single order]
    E --> G[Create multiple orders]
    
    F --> H[Set 15min timer]
    G --> H
    
    H --> I[Create payment record]
    I --> J[Remove/Clear cart items]
    J --> K[Return payment details]
    
    K --> L[User has 15 minutes to pay]
    L --> M{Payment completed?}
    
    M -->|Yes| N[Convert to actual order]
    M -->|No| O[Auto-cancel & unreserve stock]
```

### Stock Management Integration
```mermaid
graph TD
    A[Add to Cart] --> B[Reserve Stock]
    B --> C[Mark cart item as reserved]
    
    D[Update Quantity] --> E[Adjust Reservation]
    
    F[Remove Item] --> G[Unreserve Stock]
    
    H[Checkout] --> I[Validate Reservations]
    I --> J[Create Orders]
    
    K[Payment Success] --> L[Convert Reserved to Sold]
    
    M[Payment Timeout] --> N[Unreserve All Stock]
    N --> O[Cancel Orders]
```

## CartService Methods

### Core Cart Methods
```python
class CartService:
    @staticmethod
    def get_or_create_cart(user):
        """Get user's cart or create if doesn't exist"""
        
    @staticmethod
    def add_to_cart(user, product_id, quantity, size=None, product_properties=None):
        """Add item to cart with stock reservation"""
        
    @staticmethod
    def update_cart_item_quantity(user, cart_item_id, quantity):
        """Update cart item quantity and adjust stock reservation"""
        
    @staticmethod
    def remove_from_cart(user, cart_item_id):
        """Remove item from cart and unreserve stock"""
        
    @staticmethod
    def clear_cart(user):
        """Clear entire cart and unreserve all stock"""
        
    @staticmethod
    def get_cart_summary(user):
        """Get complete cart summary with totals"""
```

### Enhanced Checkout Methods
```python
@staticmethod
def checkout_single_item(user, cart_item_id, shipping_address=None, payment_method='credit_card'):
    """
    Checkout single item from cart
    - Validates item and stock
    - Creates order with payment timer
    - Removes item from cart
    - Returns order and payment details
    """
    
@staticmethod
def checkout_full_cart(user, shipping_address=None, payment_method='credit_card'):
    """
    Checkout entire cart
    - Validates all items and stock
    - Creates multiple orders with shared payment
    - Clears entire cart
    - Returns orders and payment details
    """
    
@staticmethod
def validate_cart_for_checkout(user, cart_item_ids=None):
    """
    Validate cart items before checkout
    - Checks stock availability
    - Validates product status
    - Returns detailed validation results
    """
```

## Error Handling

### Common Cart Errors
```python
CART_ERRORS = {
    'CART_EMPTY': 'Cart is empty',
    'ITEM_NOT_FOUND': 'Cart item not found',
    'INSUFFICIENT_STOCK': 'Insufficient stock available',
    'PRODUCT_INACTIVE': 'Product is no longer available',
    'SIZE_REQUIRED': 'Size selection required for this product',
    'SIZE_NOT_AVAILABLE': 'Selected size is not available',
    'INVALID_QUANTITY': 'Invalid quantity specified',
    'RESERVATION_FAILED': 'Stock reservation failed',
    'CHECKOUT_VALIDATION_FAILED': 'Cart validation failed for checkout'
}
```

### Error Response Format
```json
{
    "success": false,
    "error_code": "INSUFFICIENT_STOCK",
    "error_message": "Only 5 items available (requested 10)",
    "cart_item_id": 456,
    "available_quantity": 5,
    "suggested_action": "Reduce quantity or try different size"
}
```

## Frontend Integration Examples

### JavaScript Cart Management
```javascript
class CartManager {
    constructor() {
        this.baseURL = '/api/carts/';
        this.authToken = localStorage.getItem('authToken');
    }
    
    async addToCart(productId, quantity, size = null, properties = null) {
        try {
            const response = await fetch(`${this.baseURL}add/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    size: size,
                    product_properties: properties
                })
            });
            
            const result = await response.json();
            
            if (result.success !== false) {
                this.updateCartCounter(result.cart_summary.total_items);
                this.showSuccessMessage('Item added to cart');
            } else {
                this.handleError(result);
            }
            
            return result;
        } catch (error) {
            console.error('Add to cart error:', error);
            this.showErrorMessage('Failed to add item to cart');
        }
    }
    
    async updateQuantity(cartItemId, newQuantity) {
        try {
            const response = await fetch(`${this.baseURL}update/${cartItemId}/`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ quantity: newQuantity })
            });
            
            const result = await response.json();
            
            if (result.success !== false) {
                this.updateCartDisplay();
            } else {
                this.handleError(result);
            }
            
            return result;
        } catch (error) {
            console.error('Update quantity error:', error);
        }
    }
    
    async checkoutSingleItem(cartItemId, shippingAddress, paymentMethod = 'credit_card') {
        try {
            const response = await fetch(`${this.baseURL}checkout/single/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cart_item_id: cartItemId,
                    payment_method: paymentMethod,
                    gateway_name: 'stripe',
                    shipping_address: shippingAddress
                })
            });
            
            const result = await response.json();
            
            if (result.success !== false) {
                // Start payment timer
                this.startPaymentTimer(result.payment_id, result.time_remaining_seconds);
                // Redirect to payment page
                window.location.href = `/payment/${result.payment_id}/`;
            } else {
                this.handleError(result);
            }
            
            return result;
        } catch (error) {
            console.error('Single checkout error:', error);
        }
    }
    
    async checkoutFullCart(shippingAddress, paymentMethod = 'credit_card') {
        try {
            const response = await fetch(`${this.baseURL}checkout/full/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    payment_method: paymentMethod,
                    gateway_name: 'stripe',
                    shipping_address: shippingAddress
                })
            });
            
            const result = await response.json();
            
            if (result.success !== false) {
                // Start payment timer
                this.startPaymentTimer(result.payment_id, result.time_remaining_seconds);
                // Redirect to payment page
                window.location.href = `/payment/${result.payment_id}/`;
            } else {
                this.handleError(result);
            }
            
            return result;
        } catch (error) {
            console.error('Full cart checkout error:', error);
        }
    }
    
    startPaymentTimer(paymentId, remainingSeconds) {
        const timerElement = document.getElementById('payment-timer');
        if (!timerElement) return;
        
        const timer = setInterval(() => {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (remainingSeconds <= 0) {
                clearInterval(timer);
                alert('Payment time expired. Please try again.');
                window.location.href = '/cart/';
            }
            
            remainingSeconds--;
        }, 1000);
    }
    
    handleError(result) {
        const errorMessage = result.error_message || 'An error occurred';
        this.showErrorMessage(errorMessage);
        
        // Handle specific error types
        if (result.error_code === 'INSUFFICIENT_STOCK') {
            this.showStockError(result);
        }
    }
    
    showSuccessMessage(message) {
        // Implement your notification system
        console.log('Success:', message);
    }
    
    showErrorMessage(message) {
        // Implement your notification system
        console.error('Error:', message);
    }
}

// Usage
const cartManager = new CartManager();

// Add item to cart
document.getElementById('add-to-cart-btn').addEventListener('click', () => {
    const productId = document.getElementById('product-id').value;
    const quantity = document.getElementById('quantity').value;
    const size = document.getElementById('size').value;
    
    cartManager.addToCart(productId, quantity, size);
});

// Checkout single item
document.querySelectorAll('.checkout-single-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const cartItemId = e.target.dataset.cartItemId;
        const shippingAddress = getShippingAddress();
        
        cartManager.checkoutSingleItem(cartItemId, shippingAddress);
    });
});
```

## Testing

### Unit Tests
```python
class CartServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com')
        self.product = Product.objects.create(
            product_name='Test Product',
            price=99.99,
            available_quantity=10
        )
    
    def test_add_to_cart(self):
        cart_item = CartService.add_to_cart(
            user=self.user,
            product_id=self.product.id,
            quantity=2
        )
        
        self.assertEqual(cart_item.quantity, 2)
        self.assertTrue(cart_item.is_stock_reserved)
        
        # Verify stock reservation
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_quantity, 2)
    
    def test_single_item_checkout(self):
        # Add item to cart
        cart_item = CartService.add_to_cart(
            user=self.user,
            product_id=self.product.id,
            quantity=1
        )
        
        # Checkout single item
        result = CartService.checkout_single_item(
            user=self.user,
            cart_item_id=cart_item.id,
            shipping_address='123 Test St'
        )
        
        self.assertEqual(result['checkout_type'], 'single_item')
        self.assertIsNotNone(result['order'])
        
        # Verify item removed from cart
        cart = CartService.get_or_create_cart(self.user)
        self.assertTrue(cart.is_empty)
    
    def test_payment_timer_integration(self):
        # Test that orders are created with payment expiration
        cart_item = CartService.add_to_cart(
            user=self.user,
            product_id=self.product.id,
            quantity=1
        )
        
        result = CartService.checkout_single_item(
            user=self.user,
            cart_item_id=cart_item.id
        )
        
        order = result['order']
        self.assertIsNotNone(order.payment_expires_at)
        self.assertFalse(order.is_payment_expired)
        self.assertGreater(order.payment_time_remaining, 0)
```

## Performance Considerations

### Database Optimization
- Proper indexing on cart and cart_item tables
- Use select_related() for product information
- Prefetch related items for cart summaries
- Cache cart totals for frequent access

### Stock Management Efficiency
- Batch stock operations when possible
- Use database transactions for consistency
- Implement proper locking for concurrent access
- Monitor reservation vs actual stock levels

### Scalability
- Consider Redis for cart storage in high-traffic scenarios
- Implement cart cleanup for abandoned carts
- Use async tasks for stock operations
- Cache product information to reduce database queries

This comprehensive cart system provides a robust foundation for e-commerce operations with proper stock management, payment integration, and user experience optimization.

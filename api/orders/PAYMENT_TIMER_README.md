# Payment Timer System Documentation

## Overview
The payment timer system automatically manages orders in `under_paying` status by setting expiration times and cleaning up expired orders. This prevents stock from being reserved indefinitely and ensures accurate inventory management.

## Key Features

### 1. Payment Expiration Timer
- **Default Timeout**: 15 minutes (configurable via `ORDER_PAYMENT_TIMEOUT_MINUTES` setting)
- **Automatic Expiration**: Orders automatically expire if payment is not completed within the time limit
- **Stock Unreservation**: Expired orders automatically unreserve their stock

### 2. Automatic Cleanup System
- **Celery Task**: Runs every 5 minutes to clean up expired orders
- **Atomic Operations**: All cleanup operations are database transaction-safe
- **Error Handling**: Failed cleanups are logged and retried

### 3. Real-time Monitoring
- **Payment Status API**: Check remaining payment time for any order
- **Admin Dashboard**: View count of expired orders needing cleanup
- **Manual Triggers**: Force cleanup operations when needed

## Database Changes

### Order Model Additions
```python
payment_expires_at = models.DateTimeField(null=True, blank=True, help_text="Payment deadline for under_paying orders")

@property
def is_payment_expired(self):
    """Check if payment time limit has been exceeded"""
    if self.status != 'under_paying' or not self.payment_expires_at:
        return False
    return timezone.now() > self.payment_expires_at

@property
def payment_time_remaining(self):
    """Get remaining time for payment in seconds"""
    if self.status != 'under_paying' or not self.payment_expires_at:
        return 0
    remaining = self.payment_expires_at - timezone.now()
    return max(0, int(remaining.total_seconds()))
```

## API Endpoints

### User Endpoints
- `GET /api/orders/payment-status/<order_id>/` - Check payment status and remaining time
- `POST /api/orders/check-payment/<order_id>/` - Trigger async payment status check

### Admin Endpoints
- `GET /api/orders/admin/expired-count/` - Get count of expired orders
- `POST /api/orders/admin/cleanup/expired/` - Manually trigger cleanup
- `POST /api/orders/admin/trigger-cleanup-task/` - Start async cleanup task

## Payment Flow

### 1. Order Creation
```python
# When creating orders from cart
payment_expires_at = timezone.now() + timedelta(minutes=OrderService.PAYMENT_TIMEOUT_MINUTES)

order = Order.objects.create(
    # ... other fields
    payment_expires_at=payment_expires_at,
    status='under_paying'
)
```

### 2. Payment Window Management
```python
# Check if payment is still valid
if order.is_payment_expired:
    return {'error': 'Payment window has expired'}

# Get remaining time
remaining_seconds = order.payment_time_remaining
```

### 3. Automatic Cleanup
```python
# Celery task runs every 5 minutes
@shared_task(bind=True, max_retries=3)
def cleanup_expired_payment_orders(self):
    expired_orders = Order.objects.filter(
        status='under_paying',
        payment_expires_at__lt=timezone.now()
    )
    
    for order in expired_orders:
        # Unreserve stock
        StockService.unreserve_stock(order.product.id, order.quantity, size=order.size)
        
        # Update order status
        order.status = 'cancelled'
        order.payment_status = 'expired'
        order.save()
```

## Configuration

### Django Settings
```python
# settings.py
ORDER_PAYMENT_TIMEOUT_MINUTES = 15  # Default payment window
```

### Celery Beat Schedule
```python
# celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-expired-payments': {
        'task': 'orders.tasks.cleanup_expired_payment_orders',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'expires': 240}
    },
}
```

## Usage Examples

### Frontend Integration
```javascript
// Check payment status
async function checkPaymentStatus(orderId) {
    const response = await fetch(`/api/orders/payment-status/${orderId}/`);
    const data = await response.json();
    
    if (data.is_payment_window_active) {
        // Show countdown timer
        updateCountdown(data.time_remaining_seconds);
    } else {
        // Payment expired, redirect to cart
        window.location.href = '/cart/';
    }
}

// Start countdown timer
function updateCountdown(remainingSeconds) {
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    document.getElementById('timer').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
```

### API Response Examples

#### Payment Status Check
```json
GET /api/orders/payment-status/ORD-ABC123/

Response:
{
    "order_id": "ORD-ABC123",
    "status": "under_paying",
    "payment_status": "pending",
    "is_payment_window_active": true,
    "time_remaining_seconds": 720,
    "payment_expires_at": "2025-07-25T10:30:00Z",
    "message": "Payment window is still active"
}
```

#### Expired Order Response
```json
{
    "order_id": "ORD-ABC123",
    "status": "under_paying",
    "payment_status": "pending",
    "is_payment_window_active": false,
    "time_remaining_seconds": 0,
    "message": "Payment window has expired. Order will be cancelled automatically."
}
```

## Management Commands

### Manual Cleanup
```bash
# Run cleanup manually
python manage.py cleanup_expired_orders

# Dry run to see what would be cleaned
python manage.py cleanup_expired_orders --dry-run

# Verbose output
python manage.py cleanup_expired_orders --verbose
```

## Monitoring and Logging

### Log Messages
- `INFO`: Normal cleanup operations and results
- `WARNING`: Orders about to expire or expired
- `ERROR`: Failed cleanup operations or stock issues

### Metrics to Monitor
- Number of expired orders per cleanup cycle
- Failed cleanup operations
- Average payment completion time
- Stock reservation efficiency

## Error Handling

### Common Scenarios
1. **Stock Unreservation Fails**: Order marked as failed, admin notification sent
2. **Database Lock Conflicts**: Cleanup retried with exponential backoff
3. **High Volume Expiration**: Cleanup batched to prevent performance issues

### Recovery Procedures
1. **Manual Cleanup**: Use management command for immediate cleanup
2. **Stock Reconciliation**: Verify stock levels match reservations
3. **Order Status Audit**: Check for orphaned orders in wrong states

## Performance Considerations

### Database Optimization
- Index on `payment_expires_at` for efficient expired order queries
- Use `select_for_update()` to prevent race conditions
- Batch cleanup operations for high volume scenarios

### Celery Configuration
- Set appropriate task expiration times
- Configure retry policies for failed tasks
- Monitor task queue sizes and processing times

## Security Considerations

### Access Control
- Payment status endpoints require order ownership verification
- Admin endpoints require staff permissions
- Cleanup tasks run with system privileges

### Data Protection
- Payment expiration times logged for audit trails
- Stock operations recorded for inventory reconciliation
- Failed operations logged for investigation

## Testing Strategy

### Unit Tests
- Payment expiration logic
- Stock unreservation operations
- Order status transitions

### Integration Tests
- Full checkout to expiration flow
- Cleanup task execution
- API endpoint responses

### Load Tests
- High volume order creation
- Concurrent payment attempts
- Cleanup performance under load

## Future Enhancements

### Planned Features
1. **Dynamic Timeout**: Adjust timeout based on payment method
2. **Grace Period**: Allow brief extension for nearly-completed payments
3. **Notification System**: Email/SMS reminders before expiration
4. **Analytics Dashboard**: Payment completion rates and timing analysis

### Scalability Improvements
1. **Distributed Cleanup**: Parallel processing across multiple workers
2. **Event-Driven**: Real-time expiration using message queues
3. **Predictive Analytics**: Machine learning for optimal timeout periods

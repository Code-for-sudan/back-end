from django.db import models
from django.utils import timezone
import uuid
from .managers import OrderManager


class Order(models.Model):
    """
    Represents an order
    | Status | Description | Trigger | Business Owner Action Required |
    |--------|-------------|---------|-------------------------------|
    | `on_cart` | Order in cart, no status yet | User adds to cart | No |
    | `under_paying` | Order reserved, payment pending | User initiates checkout | No |
    | `pending` | Payment completed, awaiting processing | Payment confirmation | Yes |
    | `on_process` | Business owner processing order | Business owner action | Yes |
    | `on_shipping` | Order shipped, in transit | Business owner action | Yes |
    | `arrived` | Order delivered successfully | Business owner action | No |

    """
    # Order information
    order_id = models.CharField(max_length=100, unique=True)
    user_id = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20,
        choices=[
        ('on_cart', 'On Cart'),
        ('under_paying', 'Under Paying'),
        ('pending', 'Pending'),
        ('on_process', 'On Process'),
        ('on_shipping', 'On Shipping'),
        ('arrived', 'Arrived'),
        ('cancelled', 'Cancelled'),
    ],
    default='on_cart'
)
    # Order details
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='orders')
    product_variation = models.JSONField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Product history tracking - store product state at order time
    product_history = models.ForeignKey(
        'products.ProductHistory', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Snapshot of product state when order was created"
    )
    
    # Store product details at order time (fallback)
    product_name_at_order = models.CharField(max_length=255, blank=True)
    product_price_at_order = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Address information
    shipping_address = models.CharField(max_length=255)

    # Payment information
    payment_method = models.CharField(max_length=20, choices=[
        ('credit_card', 'Credit Card'),
        ('after_delivery', 'Cash on Delivery'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
    ], default='credit_card')
    payment_status = models.CharField(
        max_length=20,
        choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    ], default='pending')
    payment_reference = models.ForeignKey(
        'payments.Payment', on_delete=models.CASCADE, related_name='orders', blank=True, null=True)
    
    # Payment hash and key for payment processing
    payment_hash = models.CharField(max_length=100, null=True, blank=True)
    payment_key = models.CharField(max_length=100, null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_expires_at = models.DateTimeField(null=True, blank=True, help_text="Payment deadline for under_paying orders")
    
    # Notes and additional info
    customer_notes = models.TextField(blank=True, help_text="Customer order notes")
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")
    
    # Custom manager
    objects = OrderManager()
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Store product details at order time
        if self.product and not self.product_name_at_order:
            self.product_name_at_order = self.product.product_name
            self.product_price_at_order = self.product.current_price
            
        super().save(*args, **kwargs)
    
    def create_product_history_snapshot(self):
        """Create a product history snapshot when order is confirmed"""
        if self.product and not self.product_history:
            from products.models import ProductHistory
            self.product_history = ProductHistory.create_from_product(self.product)
            self.save(update_fields=['product_history'])
    
    def get_product_name(self):
        """Get product name, preferring historical data"""
        if self.product_history:
            return self.product_history.product_name
        elif self.product_name_at_order:
            return self.product_name_at_order
        elif self.product:
            return self.product.product_name
        return "Unknown Product"
    
    def get_product_price(self):
        """Get product price at time of order"""
        if self.product_history:
            return self.product_history.current_price
        elif self.product_price_at_order:
            return self.product_price_at_order
        elif self.product:
            return self.product.current_price
        return self.unit_price
    
    def validate_product_consistency(self):
        """Check if current product state matches order expectations"""
        if not self.product:
            return {'valid': False, 'reason': 'Product no longer exists', 'changes': ['product_deleted']}
        
        changes = []
        
        # If we have product history, compare against it for comprehensive validation
        if self.product_history:
            # Check all important fields for changes
            if self.product.product_name != self.product_history.product_name:
                changes.append('product_name')
            
            if self.product.product_description != self.product_history.product_description:
                changes.append('product_description')
            
            if self.product.category != self.product_history.category:
                changes.append('category')
            
            # Check price (with tolerance for rounding)
            current_price = float(self.product.current_price)
            history_price = float(self.product_history.current_price)
            if abs(current_price - history_price) > 0.01:
                changes.append('price')
            
            if self.product.color != self.product_history.color:
                changes.append('color')
            
            if self.product.brand != self.product_history.brand:
                changes.append('brand')
        else:
            # Fallback to basic price comparison if no history
            current_price = self.product.current_price
            order_price = self.get_product_price()
            
            # Allow small price differences (rounding)
            price_diff = abs(float(current_price) - float(order_price))
            if price_diff > 0.01:  # More than 1 cent difference
                changes.append('price')
        
        if changes:
            if len(changes) == 1 and changes[0] == 'price':
                # Maintain backward compatibility for price-only changes
                if self.product_history:
                    history_price = self.product_history.current_price
                    current_price = self.product.current_price
                else:
                    history_price = self.get_product_price()
                    current_price = self.product.current_price
                
                reason = f"Price changed from {history_price} to {current_price}"
            else:
                reason = f"Product has changed: {', '.join(changes)}"
                
            return {
                'valid': False, 
                'reason': reason,
                'changes': changes
            }
        
        return {'valid': True, 'changes': []}
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user_id.email}"
    
    @property
    def is_cart_item(self):
        return self.status == 'on_cart'
    
    @property
    def is_paid(self):
        return self.payment_status == 'completed'
    
    @property
    def can_be_cancelled(self):
        return self.status in ['on_cart', 'pending', 'on_process']
    
    @property
    def is_delivered(self):
        return self.status == 'arrived'
    
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
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
        ]
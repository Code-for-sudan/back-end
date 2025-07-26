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
        super().save(*args, **kwargs)
    
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
        return self.status in ['pending', 'on_process']
    
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
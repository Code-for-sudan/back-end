from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from decimal import Decimal


class PaymentGateway(models.Model):
    """
    Different payment gateways available in the system
    """
    GATEWAY_TYPES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('test_gateway', 'Test Gateway (For Testing)'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)
    is_active = models.BooleanField(default=True)
    is_test_mode = models.BooleanField(default=False)
    configuration = models.JSONField(
        default=dict,
        help_text="Gateway-specific configuration (API keys, endpoints, etc.)"
    )
    
    # Fee structure
    fixed_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Fixed fee per transaction"
    )
    percentage_fee = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage fee (e.g., 2.5 for 2.5%)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({'Test' if self.is_test_mode else 'Live'})"
    
    def calculate_fee(self, amount):
        """Calculate the fee for a given amount"""
        percentage_amount = (amount * self.percentage_fee) / Decimal('100')
        return self.fixed_fee + percentage_amount
    
    class Meta:
        db_table = 'payments_gateway'


class Payment(models.Model):
    """
    Main payment model that tracks all payment attempts and statuses
    """
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_METHOD = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('test_payment', 'Test Payment'),
    ]
    
    # Unique payment identifier
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Reference to the order (from orders app)
    order_reference = models.CharField(
        max_length=100,
        help_text="Reference to the order this payment is for"
    )
    
    # User who made the payment
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment gateway used
    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Fee charged by payment gateway"
    )
    net_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Amount after deducting fees"
    )
    
    # Payment method and status
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # External payment gateway references
    gateway_transaction_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Transaction ID from payment gateway"
    )
    gateway_reference = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Gateway-specific reference"
    )
    
    # Payment metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional payment data (gateway responses, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Failure information
    failure_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} {self.currency} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Calculate net amount
        if not self.net_amount:
            self.fee_amount = self.gateway.calculate_fee(self.amount)
            self.net_amount = self.amount - self.fee_amount
        super().save(*args, **kwargs)
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status in ['failed', 'cancelled']
    
    @property
    def can_be_refunded(self):
        return self.status in ['completed'] and self.gateway.gateway_type != 'cash_on_delivery'
    
    class Meta:
        db_table = 'payments_payment'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['created_at']),
        ]


class PaymentAttempt(models.Model):
    """
    Track individual payment attempts (for retry scenarios)
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Payment.PAYMENT_STATUS)
    gateway_response = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, null=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attempt {self.attempt_number} for Payment {self.payment.payment_id}"
    
    class Meta:
        db_table = 'payments_payment_attempt'
        unique_together = ['payment', 'attempt_number']
        ordering = ['-attempted_at']


class Refund(models.Model):
    """
    Track refunds for payments
    """
    REFUND_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    refund_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    
    # Gateway information
    gateway_refund_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(default=dict)
    
    # User who initiated the refund
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_refunds'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Refund {self.refund_id} - {self.amount} for Payment {self.payment.payment_id}"
    
    def clean(self):
        if self.amount > self.payment.amount:
            raise ValidationError("Refund amount cannot exceed payment amount")
    
    class Meta:
        db_table = 'payments_refund'
        ordering = ['-created_at']

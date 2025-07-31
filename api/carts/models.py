from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .managers import CartManager, CartItemManager


class Cart(models.Model):
    """
    Represents a user's shopping cart
    Can hold multiple cart items before checkout
    """
    user = models.OneToOneField(
        'accounts.User', 
        on_delete=models.CASCADE, 
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = CartManager()
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def total_price(self):
        total = 0
        for item in self.items.all():
            total += item.subtotal
        return total
    
    @property
    def is_empty(self):
        return self.items.count() == 0
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()
    
    class Meta:
        db_table = 'carts_cart'


class CartItem(models.Model):
    """
    Individual item in a cart with proper stock reservation
    """
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    
    # Product variations - store size if product has sizes
    size = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Size variation for products that have sizes"
    )
    
    # Additional product properties (color, etc.)
    product_properties = models.JSONField(
        blank=True, 
        null=True,
        help_text="Additional product properties like color, etc."
    )
    
    # Stock reservation tracking
    is_stock_reserved = models.BooleanField(
        default=False,
        help_text="Whether stock is currently reserved for this cart item"
    )
    
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = CartItemManager()
    
    def __str__(self):
        size_info = f" (Size: {self.size})" if self.size else ""
        return f"{self.quantity}x {self.product.product_name}{size_info} in {self.cart.user.email}'s cart"
    
    @property
    def subtotal(self):
        return self.product.current_price * self.quantity
    
    @property
    def unit_price(self):
        return self.product.current_price
    
    def check_product_changes(self):
        """Check if product has changed since added to cart"""
        if not hasattr(self, '_original_price'):
            # Store original price when item is first loaded
            self._original_price = self.product.current_price
            return {'changed': False}
        
        current_price = self.product.current_price
        price_diff = abs(float(current_price) - float(self._original_price))
        
        changes = {
            'changed': price_diff > 0.01,  # More than 1 cent difference
            'price_change': price_diff if price_diff > 0.01 else 0,
            'old_price': self._original_price,
            'new_price': current_price
        }
        
        return changes
    
    def update_for_product_changes(self):
        """Update cart item if product has changed"""
        changes = self.check_product_changes()
        if changes['changed']:
            # Log the change
            import logging
            logger = logging.getLogger('cart_service')
            logger.info(
                f"Product price changed for cart item {self.id}: "
                f"{changes['old_price']} -> {changes['new_price']}"
            )
            
            # Update the stored price reference
            self._original_price = changes['new_price']
            self.updated_at = timezone.now()
            self.save(update_fields=['updated_at'])
            
        return changes
    
    def get_variation_key(self):
        """Get a unique key for this product variation"""
        variation_parts = []
        if self.size:
            variation_parts.append(f"size:{self.size}")
        if self.product_properties:
            for key, value in sorted(self.product_properties.items()):
                variation_parts.append(f"{key}:{value}")
        return "|".join(variation_parts) if variation_parts else "no_variation"
    
    def clean(self):
        # Validate that size is provided for products that have sizes
        if self.product.has_sizes and not self.size:
            raise ValidationError("Size must be specified for products with size variations")
        
        if not self.product.has_sizes and self.size:
            raise ValidationError("Size cannot be specified for products without size variations")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        # Ensure unique combinations of cart, product, size, and properties
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'size'],
                condition=models.Q(size__isnull=False),
                name='unique_cart_product_size'
            ),
            models.UniqueConstraint(
                fields=['cart', 'product'],
                condition=models.Q(size__isnull=True),
                name='unique_cart_product_no_size'
            ),
        ]
        db_table = 'carts_cart_item'
        indexes = [
            models.Index(fields=['cart', 'product']),
            models.Index(fields=['added_at']),
            models.Index(fields=['is_stock_reserved']),
        ]

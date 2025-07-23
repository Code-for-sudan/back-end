from django.db import models
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
    Individual item in a cart
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
    product_variation = models.JSONField(
        blank=True, 
        null=True,
        help_text="Product variations like size, color, etc."
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = CartItemManager()
    
    def __str__(self):
        return f"{self.quantity}x {self.product.product_name} in {self.cart.user.email}'s cart"
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity
    
    @property
    def unit_price(self):
        return self.product.price
    
    def clean(self):
        # Validate stock availability
        if self.quantity > self.product.quantity:
            raise models.ValidationError(
                f"Only {self.product.quantity} items available in stock"
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ('cart', 'product', 'product_variation')
        db_table = 'carts_cart_item'
        indexes = [
            models.Index(fields=['cart', 'product']),
            models.Index(fields=['added_at']),
        ]

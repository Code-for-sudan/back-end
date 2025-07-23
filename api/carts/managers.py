from django.db import models


class CartManager(models.Manager):
    """Custom manager for Cart model"""
    
    def get_or_create_cart(self, user):
        """Get or create cart for user"""
        cart, created = self.get_or_create(user=user)
        return cart
    
    def get_cart_with_items(self, user):
        """Get cart with prefetched items"""
        return self.select_related('user').prefetch_related(
            'items__product'
        ).get(user=user)


class CartItemManager(models.Manager):
    """Custom manager for CartItem model"""
    
    def get_queryset(self):
        return super().get_queryset().select_related('product', 'cart__user')
    
    def for_user(self, user):
        """Get cart items for specific user"""
        return self.filter(cart__user=user)
    
    def by_product(self, product):
        """Get cart items for specific product"""
        return self.filter(product=product)

from django.db import models


class OrderManager(models.Manager):
    """Custom manager for Order model"""
    
    def get_orders(self, user):
        """Get all orders for a user"""
        return self.filter(user_id=user)
    
    def get_pending_orders(self, user):
        """Get pending orders for a user"""
        return self.filter(user_id=user, status='pending')
    
    def get_active_orders(self, user):
        """Get active orders (not delivered, not cancelled)"""
        return self.filter(
            user_id=user,
            status__in=['pending', 'processing', 'shipped']
        )
    
    def by_product(self, product):
        """Get cart items for specific product"""
        return self.filter(product=product)

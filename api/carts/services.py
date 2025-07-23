from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Cart, CartItem
from products.models import Product


class CartService:
    """Service class for cart operations"""
    
    @staticmethod
    def get_or_create_cart(user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        return cart
    
    @staticmethod
    def add_to_cart(user, product_id, quantity=1, product_variation=None):
        """Add item to cart"""
        try:
            # Get or create cart
            cart = CartService.get_or_create_cart(user)
            
            # Get product
            product = Product.objects.get(id=product_id)
            
            # Check stock availability
            if quantity > product.quantity:
                raise ValidationError(f"Only {product.quantity} items available in stock")
            
            # Check if item already exists in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                product_variation=product_variation,
                defaults={'quantity': quantity}
            )
            
            if not created:
                # Update quantity if item already exists
                new_quantity = cart_item.quantity + quantity
                if new_quantity > product.quantity:
                    raise ValidationError(f"Cannot add {quantity} more. Only {product.quantity - cart_item.quantity} more available")
                cart_item.quantity = new_quantity
                cart_item.save()
            
            return cart_item
            
        except Product.DoesNotExist:
            raise ValidationError("Product not found")
    
    @staticmethod
    def remove_from_cart(user, cart_item_id):
        """Remove item from cart"""
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            cart_item.delete()
            return True
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            raise ValidationError("Cart item not found")
    
    @staticmethod
    def update_cart_item_quantity(user, cart_item_id, quantity):
        """Update cart item quantity"""
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            
            if quantity <= 0:
                cart_item.delete()
                return None
            
            # Check stock availability
            if quantity > cart_item.product.quantity:
                raise ValidationError(f"Only {cart_item.product.quantity} items available in stock")
            
            cart_item.quantity = quantity
            cart_item.save()
            return cart_item
            
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            raise ValidationError("Cart item not found")
    
    @staticmethod
    def clear_cart(user):
        """Clear all items from cart"""
        try:
            cart = Cart.objects.get(user=user)
            cart.clear()
            return True
        except Cart.DoesNotExist:
            return False
    
    @staticmethod
    def get_cart_summary(user):
        """Get cart summary with totals"""
        try:
            cart = Cart.objects.prefetch_related('items__product').get(user=user)
            
            summary = {
                'total_items': cart.total_items,
                'total_price': cart.total_price,
                'items': []
            }
            
            for item in cart.items.all():
                summary['items'].append({
                    'id': item.id,
                    'product_id': item.product.id,
                    'product_name': item.product.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'subtotal': item.subtotal,
                    'product_variation': item.product_variation,
                    'stock_available': item.product.quantity
                })
            
            return summary
            
        except Cart.DoesNotExist:
            return {
                'total_items': 0,
                'total_price': 0,
                'items': []
            }

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order
from carts.models import Cart, CartItem
from carts.services import CartService as BaseCartService
from products.models import Product
import uuid


class OrderService:
    """Service class for order operations"""
    
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user, shipping_address=None, payment_method='credit_card'):
        """Convert cart items to orders"""
        try:
            # Use CartService from carts app
            cart = BaseCartService.get_or_create_cart(user)
            cart_items = Cart.objects.prefetch_related('items__product').get(user=user)
            
            if cart_items.is_empty:
                raise ValidationError("Cart is empty")
            
            # Use user's default address if not provided
            if not shipping_address:
                if hasattr(user, 'default_address') and user.default_address:
                    shipping_address = user.default_address
                else:
                    raise ValidationError("Please provide shipping address or complete your profile")
            
            orders = []
            
            # Create individual orders for each cart item
            for cart_item in cart_items.items.all():
                # Final stock check
                if cart_item.quantity > cart_item.product.quantity:
                    raise ValidationError(
                        f"Insufficient stock for {cart_item.product.product_name}. "
                        f"Only {cart_item.product.quantity} available"
                    )
                
                # Generate payment hash and key
                payment_hash = f"PAY-{uuid.uuid4().hex[:8].upper()}"
                payment_key = f"KEY-{uuid.uuid4().hex[:12].upper()}"
                
                # Calculate prices
                unit_price = cart_item.product.price
                total_price = unit_price * cart_item.quantity
                
                # Create order
                order = Order.objects.create(
                    user_id=user,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    product_variation=cart_item.product_variation,
                    unit_price=unit_price,
                    total_price=total_price,
                    payment_amount=total_price,
                    shipping_address=shipping_address,
                    payment_method=payment_method,
                    payment_hash=payment_hash,
                    payment_key=payment_key,
                    status='under_paying'
                )
                
                orders.append(order)
            
            # Clear cart after creating orders
            BaseCartService.clear_cart(user)
            
            return orders
            
        except Cart.DoesNotExist:
            raise ValidationError("Cart not found")
    
    @staticmethod
    @transaction.atomic
    def confirm_payment(order_id, payment_data):
        """Confirm payment and update order status"""
        try:
            order = Order.objects.get(order_id=order_id)
            
            # Verify payment hash and key
            if order.payment_hash != payment_data.get('payment_hash'):
                raise ValidationError("Invalid payment hash")
            
            if order.payment_key != payment_data.get('payment_key'):
                raise ValidationError("Invalid payment key")
            
            # Final stock check and deduction
            if order.quantity > order.product.quantity:
                raise ValidationError("Insufficient stock available")
            
            # Deduct stock
            order.product.quantity -= order.quantity
            order.product.save()
            
            # Update order status
            order.payment_status = 'completed'
            order.status = 'pending'
            order.paid_at = timezone.now()
            order.save()
            
            return order
            
        except Order.DoesNotExist:
            raise ValidationError("Order not found")
    
    @staticmethod
    def update_order_status(order_id, new_status, user=None, admin_notes=None):
        """Update order status (business owner action)"""
        try:
            order = Order.objects.get(order_id=order_id)
            
            # Validate status transition
            valid_transitions = {
                'pending': ['on_process', 'cancelled'],
                'on_process': ['on_shipping', 'cancelled'],
                'on_shipping': ['arrived'],
                'under_paying': ['pending', 'cancelled']
            }
            
            if order.status not in valid_transitions:
                raise ValidationError(f"Cannot change status from {order.status}")
            
            if new_status not in valid_transitions[order.status]:
                raise ValidationError(f"Invalid status transition from {order.status} to {new_status}")
            
            # Update order status
            order.status = new_status
            
            # Add admin notes if provided
            if admin_notes:
                order.admin_notes = admin_notes
            
            order.save()
            
            return order
            
        except Order.DoesNotExist:
            raise ValidationError("Order not found")

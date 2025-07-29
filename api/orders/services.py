from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from .models import Order
from carts.models import Cart, CartItem
from carts.services import CartService as BaseCartService
from products.models import Product
from products.services.stock_service import StockService
import uuid
from datetime import timedelta


class OrderService:
    """Service class for order operations"""
    
    # Payment timeout settings (can be moved to Django settings)
    PAYMENT_TIMEOUT_MINUTES = getattr(settings, 'ORDER_PAYMENT_TIMEOUT_MINUTES', 15)  # Default 15 minutes
    
    @staticmethod
    @transaction.atomic
    def create_order_from_cart_item(user, cart_item, shipping_address, payment_method='credit_card'):
        """
        Create a single order from one cart item
        """
        try:
            # Generate payment hash and key
            payment_hash = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            payment_key = f"KEY-{uuid.uuid4().hex[:12].upper()}"
            
            # Calculate payment expiration time
            payment_expires_at = timezone.now() + timedelta(minutes=OrderService.PAYMENT_TIMEOUT_MINUTES)
            
            # Calculate prices
            unit_price = cart_item.product.price
            total_price = unit_price * cart_item.quantity
            
            # Create order with proper variation data
            order = Order.objects.create(
                user_id=user,
                product=cart_item.product,
                quantity=cart_item.quantity,
                product_variation={
                    'size': cart_item.size,
                    'properties': cart_item.product_properties or {}
                } if cart_item.size or cart_item.product_properties else None,
                unit_price=unit_price,
                total_price=total_price,
                payment_amount=total_price,
                shipping_address=shipping_address,
                payment_method=payment_method,
                payment_hash=payment_hash,
                payment_key=payment_key,
                payment_expires_at=payment_expires_at,
                status='under_paying'
            )
            
            return order
            
        except Exception as e:
            raise ValidationError(f"Failed to create order: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def create_orders_from_cart(user, cart_items, shipping_address, payment_method='credit_card'):
        """
        Create multiple orders from cart items with shared payment identifiers
        """
        try:
            # Generate shared payment identifiers for all orders
            shared_payment_hash = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            shared_payment_key = f"KEY-{uuid.uuid4().hex[:12].upper()}"
            
            # Calculate payment expiration time
            payment_expires_at = timezone.now() + timedelta(minutes=OrderService.PAYMENT_TIMEOUT_MINUTES)
            
            orders = []
            total_payment_amount = 0
            
            # Create individual orders for each cart item
            for cart_item in cart_items:
                # Calculate prices
                unit_price = cart_item.product.price
                total_price = unit_price * cart_item.quantity
                total_payment_amount += total_price
                
                # Create order with shared payment identifiers
                order = Order.objects.create(
                    user_id=user,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    product_variation={
                        'size': cart_item.size,
                        'properties': cart_item.product_properties or {}
                    } if cart_item.size or cart_item.product_properties else None,
                    unit_price=unit_price,
                    total_price=total_price,
                    payment_amount=total_payment_amount,  # Total amount for all orders
                    shipping_address=shipping_address,
                    payment_method=payment_method,
                    payment_hash=shared_payment_hash,
                    payment_key=shared_payment_key,
                    payment_expires_at=payment_expires_at,
                    status='under_paying'
                )
                
                orders.append(order)
            
            return orders
            
        except Exception as e:
            raise ValidationError(f"Failed to create orders: {str(e)}")
    
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
                # Validate that stock is reserved for this cart item
                if not cart_item.is_stock_reserved:
                    # Try to reserve stock if not already reserved
                    try:
                        StockService.reserve_stock(
                            cart_item.product.id, 
                            cart_item.quantity, 
                            size=cart_item.size
                        )
                        cart_item.is_stock_reserved = True
                        cart_item.save()
                    except ValidationError as e:
                        raise ValidationError(
                            f"Cannot create order for {cart_item.product.product_name}: {str(e)}"
                        )
                
                # Generate payment hash and key
                payment_hash = f"PAY-{uuid.uuid4().hex[:8].upper()}"
                payment_key = f"KEY-{uuid.uuid4().hex[:12].upper()}"
                
                # Calculate prices
                unit_price = cart_item.product.price
                total_price = unit_price * cart_item.quantity
                
                # Create order with proper variation data
                order = Order.objects.create(
                    user_id=user,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    product_variation={
                        'size': cart_item.size,
                        'properties': cart_item.product_properties or {}
                    } if cart_item.size or cart_item.product_properties else None,
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
    def confirm_payment_for_orders(payment_hash, payment_key):
        """
        Confirm payment for one or multiple orders with the same payment hash
        """
        try:
            # Get all orders with the same payment hash
            orders = Order.objects.filter(
                payment_hash=payment_hash,
                payment_key=payment_key,
                status='under_paying'
            )
            
            if not orders.exists():
                raise ValidationError("No pending orders found for this payment")
            
            # Validate payment keys match
            for order in orders:
                if order.payment_hash != payment_hash or order.payment_key != payment_key:
                    raise ValidationError("Invalid payment credentials")
            
            # Process stock deduction for all orders
            processed_orders = []
            
            for order in orders:
                # Convert reserved stock to actual stock deduction
                size = None
                if order.product_variation and 'size' in order.product_variation:
                    size = order.product_variation['size']
                
                try:
                    # Convert reserved stock to actual sale using StockService
                    size = None
                    if order.product_variation and 'size' in order.product_variation:
                        size = order.product_variation['size']
                    
                    # Use StockService to handle the stock conversion
                    # First unreserve the stock, then confirm the sale
                    StockService.unreserve_stock(order.product.id, order.quantity, size=size)
                    StockService.confirm_stock_sale(order.product.id, order.quantity, size=size)
                    
                    # Update order status
                    order.payment_status = 'completed'
                    order.status = 'pending'
                    order.paid_at = timezone.now()
                    order.save()
                    
                    processed_orders.append(order)
                    
                except Exception as e:
                    # If any order fails, rollback all changes
                    raise ValidationError(f"Stock processing failed for {order.product.product_name}: {str(e)}")
            
            return processed_orders
            
        except Exception as e:
            raise ValidationError(f"Payment confirmation failed: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def confirm_payment(order_id, payment_data):
        """Confirm payment and convert reserved stock to actual deduction"""
        try:
            order = Order.objects.get(order_id=order_id)
            
            # Verify payment hash and key
            if order.payment_hash != payment_data.get('payment_hash'):
                raise ValidationError("Invalid payment hash")
            
            if order.payment_key != payment_data.get('payment_key'):
                raise ValidationError("Invalid payment key")
            
            # Convert reserved stock to actual stock deduction
            # First unreserve the stock
            size = None
            if order.product_variation and 'size' in order.product_variation:
                size = order.product_variation['size']
            
            try:
                # Convert reserved stock to actual sale using StockService
                size = None
                if order.product_variation and 'size' in order.product_variation:
                    size = order.product_variation['size']
                
                # Use StockService to handle the stock conversion
                StockService.unreserve_stock(order.product.id, order.quantity, size=size)
                StockService.confirm_stock_sale(order.product.id, order.quantity, size=size)
                
            except Exception as e:
                raise ValidationError(f"Stock processing failed: {str(e)}")
            
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
    
    @staticmethod
    @transaction.atomic
    def cleanup_expired_payments():
        """
        Find and process all expired under_paying orders
        - Unreserve stock
        - Mark payment as expired
        - Update order status to cancelled
        """
        try:
            # Find all expired orders
            expired_orders = Order.objects.filter(
                status='under_paying',
                payment_expires_at__lt=timezone.now()
            ).select_for_update()
            
            cleanup_results = {
                'processed_count': 0,
                'failed_count': 0,
                'errors': []
            }
            
            for order in expired_orders:
                try:
                    # Unreserve stock for this order
                    size = None
                    if order.product_variation and 'size' in order.product_variation:
                        size = order.product_variation['size']
                    
                    # Unreserve the stock
                    StockService.unreserve_stock(
                        product_id=order.product.id,
                        quantity=order.quantity,
                        size=size
                    )
                    
                    # Update order status and payment status
                    order.status = 'cancelled'
                    order.payment_status = 'expired'
                    order.admin_notes = f"Payment expired at {order.payment_expires_at}. Stock unreserved automatically."
                    order.save()
                    
                    cleanup_results['processed_count'] += 1
                    
                except Exception as e:
                    cleanup_results['failed_count'] += 1
                    cleanup_results['errors'].append({
                        'order_id': order.order_id,
                        'error': str(e)
                    })
                    # Continue processing other orders even if one fails
                    continue
            
            return cleanup_results
            
        except Exception as e:
            raise ValidationError(f"Cleanup process failed: {str(e)}")
    
    @staticmethod
    def get_expired_orders_count():
        """Get count of orders that need cleanup"""
        return Order.objects.filter(
            status='under_paying',
            payment_expires_at__lt=timezone.now()
        ).count()
    
    @staticmethod
    def check_order_payment_status(order_id):
        """
        Check if an order's payment window is still valid
        Returns order status and remaining time
        """
        try:
            order = Order.objects.get(order_id=order_id)
            
            if order.status != 'under_paying':
                return {
                    'order_id': order_id,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'is_payment_window_active': False,
                    'time_remaining_seconds': 0,
                    'message': f"Order is not in payment status. Current status: {order.status}"
                }
            
            if order.is_payment_expired:
                return {
                    'order_id': order_id,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'is_payment_window_active': False,
                    'time_remaining_seconds': 0,
                    'message': "Payment window has expired. Order will be cancelled automatically."
                }
            
            return {
                'order_id': order_id,
                'status': order.status,
                'payment_status': order.payment_status,
                'is_payment_window_active': True,
                'time_remaining_seconds': order.payment_time_remaining,
                'payment_expires_at': order.payment_expires_at.isoformat(),
                'message': "Payment window is still active"
            }
            
        except Order.DoesNotExist:
            raise ValidationError("Order not found")

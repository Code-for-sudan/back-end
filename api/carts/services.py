from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Cart, CartItem
from products.models import Product, Size
from products.services.stock_service import StockService


class CartService:
    """Service             # Create order using OrderService
            order = OrderService.create_order_fro            # Create orders using OrderService
            orders = OrderService.create_orders_from_cart(
                user=user,
                cart_items=cart_items,
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            # Schedule payment reminders for all orders (optional)
            try:
                from orders.tasks import send_payment_reminder
                # Schedule reminder 5 minutes before expiration
                reminder_delay = (OrderService.PAYMENT_TIMEOUT_MINUTES - 5) * 60
                if reminder_delay > 0:
                    for order in orders:
                        send_payment_reminder.apply_async(
                            args=[order.order_id, 5],
                            countdown=reminder_delay
                        )
            except ImportError:
                # Notification system not available, continue without reminders
                pass
            
            # Calculate total amount
            total_amount = sum(order.total_price for order in orders)
            
            # Clear the entire cart after order creation
            cart.clear()
            
            return {
                'orders': orders,
                'total_amount': total_amount,
                'order_count': len(orders),
                'checkout_type': 'full_cart'
            }            user=user,
                cart_item=cart_item,
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            # Schedule payment reminder (optional - can be enabled if notification system exists)
            try:
                from orders.tasks import send_payment_reminder
                # Schedule reminder 5 minutes before expiration
                reminder_delay = (OrderService.PAYMENT_TIMEOUT_MINUTES - 5) * 60
                if reminder_delay > 0:
                    send_payment_reminder.apply_async(
                        args=[order.order_id, 5],
                        countdown=reminder_delay
                    )
            except ImportError:
                # Notification system not available, continue without reminder
                pass
            
            # Remove item from cart after order creation
            cart_item.delete()
            
            return {
                'order': order,
                'total_amount': order.total_price,
                'checkout_type': 'single_item'
            }perations"""
    
    @staticmethod
    def get_or_create_cart(user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        return cart
    
    @staticmethod
    @transaction.atomic
    def add_to_cart(user, product_id, quantity=1, size=None, product_properties=None):
        """Add item to cart with stock reservation"""
        try:
            # Get or create cart
            cart = CartService.get_or_create_cart(user)
            
            # Get product
            product = Product.objects.get(id=product_id)
            
            # Validate size requirement
            if product.has_sizes and not size:
                raise ValidationError("Size must be specified for products with size variations")
            
            if not product.has_sizes and size:
                raise ValidationError("Size cannot be specified for products without size variations")
            
            # Check if item already exists in cart with same variations
            existing_item = CartItem.objects.filter(
                cart=cart,
                product=product,
                size=size,
                product_properties=product_properties
            ).first()
            
            if existing_item:
                # Update quantity for existing item
                old_quantity = existing_item.quantity
                new_quantity = old_quantity + quantity
                
                # Reserve additional stock
                try:
                    StockService.reserve_stock(product_id, quantity, size=size)
                    
                    existing_item.quantity = new_quantity
                    existing_item.is_stock_reserved = True
                    existing_item.save()
                    
                    return existing_item
                    
                except ValidationError as e:
                    raise ValidationError(f"Cannot add to cart: {str(e)}")
            else:
                # Create new cart item
                try:
                    # Reserve stock first
                    StockService.reserve_stock(product_id, quantity, size=size)
                    
                    # Create cart item
                    cart_item = CartItem.objects.create(
                        cart=cart,
                        product=product,
                        quantity=quantity,
                        size=size,
                        product_properties=product_properties,
                        is_stock_reserved=True
                    )
                    
                    return cart_item
                    
                except ValidationError as e:
                    raise ValidationError(f"Cannot add to cart: {str(e)}")
            
        except Product.DoesNotExist:
            raise ValidationError("Product not found")
    
    @staticmethod
    @transaction.atomic
    def remove_from_cart(user, cart_item_id):
        """Remove item from cart and unreserve stock"""
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            
            # Unreserve stock if it was reserved
            if cart_item.is_stock_reserved:
                try:
                    StockService.unreserve_stock(
                        cart_item.product.id, 
                        cart_item.quantity, 
                        size=cart_item.size
                    )
                except Exception as e:
                    # Log the error but don't fail the removal
                    print(f"Warning: Could not unreserve stock for cart item {cart_item_id}: {e}")
            
            cart_item.delete()
            return True
            
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            raise ValidationError("Cart item not found")
    
    @staticmethod
    @transaction.atomic
    def update_cart_item_quantity(user, cart_item_id, quantity):
        """Update cart item quantity with stock reservation"""
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            
            if quantity <= 0:
                # Remove item if quantity is 0 or negative
                return CartService.remove_from_cart(user, cart_item_id)
            
            old_quantity = cart_item.quantity
            quantity_diff = quantity - old_quantity
            
            if quantity_diff > 0:
                # Increasing quantity - reserve more stock
                try:
                    StockService.reserve_stock(
                        cart_item.product.id, 
                        quantity_diff, 
                        size=cart_item.size
                    )
                except ValidationError as e:
                    raise ValidationError(f"Cannot update quantity: {str(e)}")
                    
            elif quantity_diff < 0:
                # Decreasing quantity - unreserve stock
                try:
                    StockService.unreserve_stock(
                        cart_item.product.id, 
                        abs(quantity_diff), 
                        size=cart_item.size
                    )
                except Exception as e:
                    # Log warning but don't fail the update
                    print(f"Warning: Could not unreserve stock: {e}")
            
            # Update cart item
            cart_item.quantity = quantity
            cart_item.is_stock_reserved = True
            cart_item.save()
            
            return cart_item
            
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            raise ValidationError("Cart item not found")
    
    @staticmethod
    @transaction.atomic
    def clear_cart(user):
        """Clear all items from cart and unreserve all stock"""
        try:
            cart = Cart.objects.get(user=user)
            
            # Unreserve stock for all items
            for item in cart.items.filter(is_stock_reserved=True):
                try:
                    StockService.unreserve_stock(
                        item.product.id, 
                        item.quantity, 
                        size=item.size
                    )
                except Exception as e:
                    # Log warning but continue clearing
                    print(f"Warning: Could not unreserve stock for item {item.id}: {e}")
            
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
                    'size': item.size,
                    'product_properties': item.product_properties,
                    'is_stock_reserved': item.is_stock_reserved,
                    'variation_key': item.get_variation_key(),
                })
            
            return summary
            
        except Cart.DoesNotExist:
            return {
                'total_items': 0,
                'total_price': 0,
                'items': []
            }

    @staticmethod
    @transaction.atomic
    def checkout_single_item(user, cart_item_id, shipping_address=None, payment_method='credit_card'):
        """
        Checkout a single item from cart
        Creates one order and one payment for the selected item
        """
        try:
            cart = Cart.objects.get(user=user)
            cart_item = CartItem.objects.select_related('product').get(
                id=cart_item_id, 
                cart=cart
            )
            
            # Validate that stock is still reserved
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
                    raise ValidationError(f"Cannot checkout item: {str(e)}")
            
            # Use user's default address if not provided
            if not shipping_address:
                if hasattr(user, 'default_address') and user.default_address:
                    shipping_address = user.default_address
                else:
                    raise ValidationError("Please provide shipping address or complete your profile")
            
            # Import here to avoid circular imports
            from orders.services import OrderService
            
            # Create single order
            order = OrderService.create_order_from_cart_item(
                user=user,
                cart_item=cart_item,
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            # Remove the item from cart after order creation
            cart_item.delete()
            
            return {
                'order': order,
                'total_amount': order.payment_amount,
                'checkout_type': 'single_item'
            }
            
        except Cart.DoesNotExist:
            raise ValidationError("Cart not found")
        except CartItem.DoesNotExist:
            raise ValidationError("Cart item not found")
    
    @staticmethod
    @transaction.atomic
    def checkout_full_cart(user, shipping_address=None, payment_method='credit_card'):
        """
        Checkout all items in cart
        Creates multiple orders but one payment for all items
        """
        try:
            cart = Cart.objects.prefetch_related('items__product').get(user=user)
            
            if cart.is_empty:
                raise ValidationError("Cart is empty")
            
            # Validate all items have reserved stock
            total_amount = 0
            validated_items = []
            
            for cart_item in cart.items.all():
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
                        raise ValidationError(f"Cannot checkout {cart_item.product.product_name}: {str(e)}")
                
                validated_items.append(cart_item)
                total_amount += cart_item.subtotal
            
            # Use user's default address if not provided
            if not shipping_address:
                if hasattr(user, 'default_address') and user.default_address:
                    shipping_address = user.default_address
                else:
                    raise ValidationError("Please provide shipping address or complete your profile")
            
            # Import here to avoid circular imports
            from orders.services import OrderService
            
            # Create orders for all items
            orders = OrderService.create_orders_from_cart(
                user=user,
                cart_items=validated_items,
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            # Clear the entire cart after order creation
            cart.clear()
            
            return {
                'orders': orders,
                'total_amount': total_amount,
                'order_count': len(orders),
                'checkout_type': 'full_cart'
            }
            
        except Cart.DoesNotExist:
            raise ValidationError("Cart not found")
    
    @staticmethod
    def validate_cart_for_checkout(user, cart_item_ids=None):
        """
        Validate cart items before checkout
        If cart_item_ids provided, validate only those items (for single/partial checkout)
        Otherwise validate entire cart
        """
        try:
            cart = Cart.objects.prefetch_related('items__product').get(user=user)
            
            if cart.is_empty:
                return {'valid': False, 'error': 'Cart is empty'}
            
            # Determine which items to validate
            if cart_item_ids:
                items_to_validate = cart.items.filter(id__in=cart_item_ids)
                if items_to_validate.count() != len(cart_item_ids):
                    return {'valid': False, 'error': 'Some cart items not found'}
            else:
                items_to_validate = cart.items.all()
            
            validation_results = []
            total_amount = 0
            
            for cart_item in items_to_validate:
                item_validation = {
                    'cart_item_id': cart_item.id,
                    'product_name': cart_item.product.product_name,
                    'quantity': cart_item.quantity,
                    'subtotal': cart_item.subtotal,
                    'valid': True,
                    'errors': []
                }
                
                # Check if product still exists and is active
                if not cart_item.product:
                    item_validation['valid'] = False
                    item_validation['errors'].append('Product no longer available')
                
                # Check stock availability
                try:
                    if cart_item.product.has_sizes:
                        if not cart_item.size:
                            item_validation['valid'] = False
                            item_validation['errors'].append('Size not specified')
                        else:
                            size_obj = Size.objects.get(
                                product=cart_item.product,
                                size=cart_item.size
                            )
                            available = size_obj.available_quantity + (
                                size_obj.reserved_quantity if cart_item.is_stock_reserved else 0
                            )
                            if cart_item.quantity > available:
                                item_validation['valid'] = False
                                item_validation['errors'].append(
                                    f'Only {available} items available (requested {cart_item.quantity})'
                                )
                    else:
                        available = cart_item.product.available_quantity + (
                            cart_item.product.reserved_quantity if cart_item.is_stock_reserved else 0
                        )
                        if cart_item.quantity > available:
                            item_validation['valid'] = False
                            item_validation['errors'].append(
                                f'Only {available} items available (requested {cart_item.quantity})'
                            )
                            
                except Size.DoesNotExist:
                    item_validation['valid'] = False
                    item_validation['errors'].append('Size not available')
                
                if item_validation['valid']:
                    total_amount += cart_item.subtotal
                
                validation_results.append(item_validation)
            
            # Overall validation result
            all_valid = all(item['valid'] for item in validation_results)
            
            return {
                'valid': all_valid,
                'total_amount': total_amount,
                'item_count': len(validation_results),
                'items': validation_results,
                'cart_total': cart.total_price
            }
            
        except Cart.DoesNotExist:
            return {'valid': False, 'error': 'Cart not found'}

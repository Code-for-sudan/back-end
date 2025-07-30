from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .services import CartService
from .serializers import (
    CartSerializer, AddToCartSerializer, CartItemSerializer,
    CheckoutSingleItemSerializer, CheckoutFullCartSerializer,
    CartValidationSerializer, CheckoutResponseSerializer
)
from .models import Cart, CartItem
import logging

logger = logging.getLogger(__name__)


class CartDetailView(APIView):
    """Get user's cart with all items"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            cart_summary = CartService.get_cart_summary(request.user)
            return Response(cart_summary, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AddToCartView(APIView):
    """Add item to cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_item = CartService.add_to_cart(
                    user=request.user,
                    product_id=serializer.validated_data['product_id'],
                    quantity=serializer.validated_data['quantity'],
                    size=serializer.validated_data.get('size'),
                    product_properties=serializer.validated_data.get('product_properties')
                )
                
                return Response(
                    {'message': 'Item added to cart successfully', 'cart_item_id': cart_item.id},
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateCartItemView(APIView):
    """Update cart item quantity"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, cart_item_id):
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_item = CartService.update_cart_item_quantity(
                    user=request.user,
                    cart_item_id=cart_item_id,
                    quantity=serializer.validated_data['quantity']
                )
                
                if cart_item:
                    return Response(
                        {'message': 'Cart item updated successfully'},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'message': 'Cart item removed (quantity was 0)'},
                        status=status.HTTP_200_OK
                    )
                    
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(APIView):
    """Remove item from cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, cart_item_id):
        try:
            CartService.remove_from_cart(request.user, cart_item_id)
            return Response(
                {'message': 'Item removed from cart successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ClearCartView(APIView):
    """Clear entire cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        try:
            CartService.clear_cart(request.user)
            return Response(
                {'message': 'Cart cleared successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ValidateCartView(APIView):
    """Validate cart before checkout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CartValidationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_item_ids = serializer.validated_data.get('cart_item_ids')
                validation_result = CartService.validate_cart_for_checkout(
                    user=request.user,
                    cart_item_ids=cart_item_ids
                )
                
                return Response(validation_result, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckoutSingleItemView(APIView):
    """Checkout a single item from cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSingleItemSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            try:
                # Checkout single item
                checkout_result = CartService.checkout_single_item(
                    user=request.user,
                    cart_item_id=serializer.validated_data['cart_item_id'],
                    shipping_address=serializer.validated_data.get('shipping_address'),
                    payment_method=serializer.validated_data['payment_method']
                )
                
                # Create payment for the order
                from payments.services import PaymentService
                payment = PaymentService.create_payment_for_orders(
                    orders=[checkout_result['order']],
                    payment_method=serializer.validated_data['payment_method'],
                    gateway_name=serializer.validated_data['gateway_name']
                )
                
                # Prepare response
                response_data = {
                    'checkout_type': checkout_result['checkout_type'],
                    'total_amount': checkout_result['total_amount'],
                    'order_count': 1,
                    'payment_id': payment.payment_id,
                    'payment_hash': checkout_result['order'].payment_hash,
                    'order': {
                        'order_id': checkout_result['order'].order_id,
                        'product_name': checkout_result['order'].product.product_name,
                        'quantity': checkout_result['order'].quantity,
                        'total_price': checkout_result['order'].total_price,
                        'status': checkout_result['order'].status
                    }
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Single item checkout failed: {str(e)}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckoutFullCartView(APIView):
    """Checkout all items in cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = CheckoutFullCartSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Checkout full cart
                checkout_result = CartService.checkout_full_cart(
                    user=request.user,
                    shipping_address=serializer.validated_data.get('shipping_address'),
                    payment_method=serializer.validated_data['payment_method']
                )
                
                # Create payment for all orders
                from payments.services import PaymentService
                payment = PaymentService.create_payment_for_orders(
                    orders=checkout_result['orders'],
                    payment_method=serializer.validated_data['payment_method'],
                    gateway_name=serializer.validated_data['gateway_name']
                )
                
                # Prepare response
                response_data = {
                    'checkout_type': checkout_result['checkout_type'],
                    'total_amount': checkout_result['total_amount'],
                    'order_count': checkout_result['order_count'],
                    'payment_id': payment.payment_id,
                    'payment_hash': checkout_result['orders'][0].payment_hash,
                    'orders': [
                        {
                            'order_id': order.order_id,
                            'product_name': order.product.product_name,
                            'quantity': order.quantity,
                            'total_price': order.total_price,
                            'status': order.status
                        } for order in checkout_result['orders']
                    ]
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Full cart checkout failed: {str(e)}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Utility views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def cart_count(request):
    """Get total item count in user's cart"""
    try:
        cart_summary = CartService.get_cart_summary(request.user)
        return Response({
            'total_items': cart_summary['total_items'],
            'total_price': cart_summary['total_price']
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

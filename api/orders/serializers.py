from rest_framework import serializers
from .models import Order
from products.serializers import ProductSerializer


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_image = serializers.ImageField(source='product.picture', read_only=True)
    store_name = serializers.CharField(source='product.store.name', read_only=True)
    is_cart_item = serializers.BooleanField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    is_delivered = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'user_id', 'status', 'product', 'product_name', 
            'product_image', 'store_name', 'product_variation', 'quantity',
            'unit_price', 'total_price', 'shipping_address', 'payment_method',
            'payment_status', 'customer_notes', 'created_at', 'updated_at', 
            'paid_at', 'is_cart_item', 'is_paid', 'can_be_cancelled', 'is_delivered'
        ]
        read_only_fields = [
            'order_id', 'user_id', 'payment_hash', 'payment_key', 
            'payment_amount', 'admin_notes', 'created_at', 'updated_at', 'paid_at'
        ]


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process"""
    shipping_address = serializers.CharField(max_length=255, required=False)
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'Credit Card'),
            ('after_delivery', 'Cash on Delivery'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
        ],
        default='credit_card'
    )
    customer_notes = serializers.CharField(max_length=500, required=False)


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('on_process', 'On Process'),
            ('on_shipping', 'On Shipping'),
            ('arrived', 'Arrived'),
            ('cancelled', 'Cancelled'),
        ]
    )
    admin_notes = serializers.CharField(required=False)


class PaymentConfirmationSerializer(serializers.Serializer):
    """Serializer for payment confirmation - Updated to work with payments app"""
    payment_id = serializers.UUIDField()
    
    def validate_payment_id(self, value):
        try:
            from payments.models import Payment
            payment = Payment.objects.get(payment_id=value)
            if payment.status != 'completed':
                raise serializers.ValidationError("Payment has not been completed")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking information"""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    store_name = serializers.CharField(source='product.store.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'product_name', 'store_name', 'status', 
            'created_at', 'paid_at'
        ]
        read_only_fields = '__all__'

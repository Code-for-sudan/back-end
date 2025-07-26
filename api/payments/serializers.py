from rest_framework import serializers
from .models import Payment, PaymentGateway, PaymentAttempt, Refund


class PaymentGatewaySerializer(serializers.ModelSerializer):
    """Serializer for PaymentGateway model"""
    
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'name', 'gateway_type', 'is_active', 'is_test_mode',
            'fixed_fee', 'percentage_fee'
        ]
        read_only_fields = ['id']


class PaymentAttemptSerializer(serializers.ModelSerializer):
    """Serializer for PaymentAttempt model"""
    
    class Meta:
        model = PaymentAttempt
        fields = [
            'id', 'attempt_number', 'status', 'error_message', 'attempted_at'
        ]
        read_only_fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)
    gateway_type = serializers.CharField(source='gateway.gateway_type', read_only=True)
    attempts = PaymentAttemptSerializer(many=True, read_only=True)
    is_successful = serializers.BooleanField(read_only=True)
    is_failed = serializers.BooleanField(read_only=True)
    can_be_refunded = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'order_reference', 'user', 'gateway_name', 'gateway_type',
            'amount', 'currency', 'fee_amount', 'net_amount', 'payment_method',
            'status', 'gateway_transaction_id', 'gateway_reference',
            'created_at', 'updated_at', 'processed_at', 'failure_reason',
            'attempts', 'is_successful', 'is_failed', 'can_be_refunded'
        ]
        read_only_fields = [
            'payment_id', 'fee_amount', 'net_amount', 'gateway_transaction_id',
            'gateway_reference', 'created_at', 'updated_at', 'processed_at',
            'failure_reason'
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating a new payment"""
    order_id = serializers.CharField(max_length=100)
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('cash_on_delivery', 'Cash on Delivery'),
            ('test_payment', 'Test Payment'),
        ]
    )
    gateway_name = serializers.CharField(max_length=100, default='test_gateway')
    
    def validate_order_id(self, value):
        from orders.models import Order
        try:
            order = Order.objects.get(order_id=value)
            if order.payment_status == 'completed':
                raise serializers.ValidationError("Order has already been paid")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")


class ProcessPaymentSerializer(serializers.Serializer):
    """Serializer for processing a payment"""
    payment_id = serializers.UUIDField()
    
    # For test payments
    test_card = serializers.CharField(max_length=20, required=False)
    force_failure = serializers.BooleanField(required=False, default=False)
    
    # For Stripe payments
    payment_method_id = serializers.CharField(max_length=255, required=False)
    
    # For other gateways
    gateway_data = serializers.JSONField(required=False)
    
    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(payment_id=value)
            if payment.status in ['completed', 'refunded']:
                raise serializers.ValidationError("Payment has already been processed")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for Refund model"""
    payment_id = serializers.UUIDField(source='payment.payment_id', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'refund_id', 'payment_id', 'amount', 'reason', 'status',
            'gateway_refund_id', 'initiated_by', 'created_at', 'processed_at'
        ]
        read_only_fields = [
            'refund_id', 'gateway_refund_id', 'created_at', 'processed_at'
        ]


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for creating a refund"""
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=500)
    
    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(payment_id=value)
            if not payment.can_be_refunded:
                raise serializers.ValidationError("Payment cannot be refunded")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")
    
    def validate(self, data):
        try:
            payment = Payment.objects.get(payment_id=data['payment_id'])
            
            # Check refund amount
            total_refunded = sum(
                refund.amount for refund in payment.refunds.filter(status='completed')
            )
            remaining_amount = payment.amount - total_refunded
            
            if data['amount'] > remaining_amount:
                raise serializers.ValidationError(
                    f"Refund amount cannot exceed remaining amount: {remaining_amount}"
                )
                
        except Payment.DoesNotExist:
            pass  # Already validated in validate_payment_id
        
        return data


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status response"""
    payment_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gateway = serializers.CharField(read_only=True)
    method = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    processed_at = serializers.DateTimeField(read_only=True)


class WebhookSimulationSerializer(serializers.Serializer):
    """Serializer for simulating payment webhooks (testing only)"""
    payment_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(
        choices=[
            ('payment.succeeded', 'Payment Succeeded'),
            ('payment.failed', 'Payment Failed'),
            ('payment.canceled', 'Payment Canceled'),
        ],
        default='payment.succeeded'
    )
    
    def validate_payment_id(self, value):
        try:
            Payment.objects.get(payment_id=value)
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")


class TestPaymentDataSerializer(serializers.Serializer):
    """Serializer for test payment data"""
    scenario = serializers.ChoiceField(
        choices=[
            ('success', 'Successful Payment'),
            ('decline', 'Card Declined'),
            ('insufficient_funds', 'Insufficient Funds'),
            ('expired_card', 'Expired Card'),
            ('incorrect_cvc', 'Incorrect CVC'),
        ],
        default='success'
    )
    custom_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    delay_seconds = serializers.IntegerField(min_value=0, max_value=10, default=1)

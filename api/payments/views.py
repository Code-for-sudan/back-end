from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.db import transaction
from .services import PaymentService, TestPaymentHelper
from .serializers import (
    PaymentSerializer, CreatePaymentSerializer, ProcessPaymentSerializer,
    PaymentStatusSerializer, WebhookSimulationSerializer, TestPaymentDataSerializer,
    RefundSerializer, CreateRefundSerializer
)
from .models import Payment, PaymentGateway
import logging

logger = logging.getLogger(__name__)


class CreatePaymentView(APIView):
    """Create a new payment for an order"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment = PaymentService.create_payment(
                    order_id=serializer.validated_data['order_id'],
                    payment_method=serializer.validated_data['payment_method'],
                    gateway_name=serializer.validated_data['gateway_name']
                )
                
                return Response(
                    PaymentSerializer(payment).data,
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProcessPaymentView(APIView):
    """Process a payment through the selected gateway"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ProcessPaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Prepare payment data
                payment_data = {}
                
                # Add test-specific data
                if 'test_card' in serializer.validated_data:
                    payment_data['test_card'] = serializer.validated_data['test_card']
                if 'force_failure' in serializer.validated_data:
                    payment_data['force_failure'] = serializer.validated_data['force_failure']
                
                # Add Stripe-specific data
                if 'payment_method_id' in serializer.validated_data:
                    payment_data['payment_method_id'] = serializer.validated_data['payment_method_id']
                
                # Add other gateway data
                if 'gateway_data' in serializer.validated_data:
                    payment_data.update(serializer.validated_data['gateway_data'])
                
                payment = PaymentService.process_payment(
                    payment_id=serializer.validated_data['payment_id'],
                    payment_data=payment_data
                )
                
                return Response(
                    PaymentSerializer(payment).data,
                    status=status.HTTP_200_OK
                )
                
            except Exception as e:
                logger.error(f"Payment processing failed: {str(e)}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentStatusView(APIView):
    """Get payment status for an order"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, order_reference):
        try:
            payment_status = PaymentService.get_payment_status(order_reference)
            
            if payment_status:
                return Response(
                    PaymentStatusSerializer(payment_status).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'message': 'No payment found for this order'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentDetailView(APIView):
    """Get detailed payment information"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            # Check if user owns this payment or is admin
            if payment.user != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_200_OK
            )
            
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserPaymentsView(APIView):
    """Get all payments for the authenticated user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        
        # Add pagination if needed
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_payments = payments[start:end]
        
        return Response({
            'payments': PaymentSerializer(paginated_payments, many=True).data,
            'total': payments.count(),
            'page': page,
            'page_size': page_size
        })


# Test-specific views (only available in test mode)
class TestPaymentView(APIView):
    """Test payment endpoints (only available when testing is enabled)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if test mode is enabled
        config = PaymentService.get_gateway_config()
        if not config['test_mode']:
            return Response(
                {'error': 'Test payments are not enabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TestPaymentDataSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Create test payment data
                test_data = TestPaymentHelper.create_test_payment_data(
                    scenario=serializer.validated_data['scenario']
                )
                
                return Response({
                    'test_data': test_data,
                    'message': f"Test payment data for scenario: {serializer.validated_data['scenario']}"
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SimulateWebhookView(APIView):
    """Simulate payment gateway webhooks for testing"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if test mode is enabled
        config = PaymentService.get_gateway_config()
        if not config['test_mode']:
            return Response(
                {'error': 'Webhook simulation is only available in test mode'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = WebhookSimulationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = PaymentService.simulate_webhook(
                    payment_id=serializer.validated_data['payment_id'],
                    event_type=serializer.validated_data['event_type']
                )
                
                return Response(result, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentGatewaysView(APIView):
    """Get available payment gateways"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Filter gateways based on test mode
        config = PaymentService.get_gateway_config()
        
        if config['test_mode']:
            gateways = PaymentGateway.objects.filter(is_active=True)
        else:
            gateways = PaymentGateway.objects.filter(is_active=True, is_test_mode=False)
        
        from .serializers import PaymentGatewaySerializer
        return Response(
            PaymentGatewaySerializer(gateways, many=True).data,
            status=status.HTTP_200_OK
        )


# Refund views
class CreateRefundView(APIView):
    """Create a refund for a payment"""
    permission_classes = [permissions.IsAdminUser]  # Only admins can create refunds
    
    def post(self, request):
        serializer = CreateRefundSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    from .models import Refund
                    
                    payment = Payment.objects.get(
                        payment_id=serializer.validated_data['payment_id']
                    )
                    
                    refund = Refund.objects.create(
                        payment=payment,
                        amount=serializer.validated_data['amount'],
                        reason=serializer.validated_data['reason'],
                        initiated_by=request.user,
                        status='pending'
                    )
                    
                    # TODO: Process refund through payment gateway
                    # For now, just mark as completed for test mode
                    config = PaymentService.get_gateway_config()
                    if config['test_mode']:
                        refund.status = 'completed'
                        refund.save()
                    
                    return Response(
                        RefundSerializer(refund).data,
                        status=status.HTTP_201_CREATED
                    )
                    
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Configuration view
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_config(request):
    """Get payment configuration for frontend"""
    config = PaymentService.get_gateway_config()
    
    # Only return safe configuration data
    safe_config = {
        'test_mode': config['test_mode'],
        'stripe_public_key': config.get('stripe_public_key', ''),
        'available_methods': [
            'credit_card',
            'debit_card',
            'cash_on_delivery',
        ]
    }
    
    # Add test methods if in test mode
    if config['test_mode']:
        safe_config['available_methods'].append('test_payment')
        safe_config['test_cards'] = TestPaymentHelper.TEST_CARDS
    
    return Response(safe_config)

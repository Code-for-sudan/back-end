from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import uuid
import logging
from .models import Payment, PaymentGateway, PaymentAttempt
from orders.models import Order
import os

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service class for handling payments with test/production modes
    """
    
    @staticmethod
    def get_gateway_config():
        """
        Get payment gateway configuration based on environment
        Supports separate test configuration even on production server
        """
        # Check if we're in test mode (can be enabled even on prod server)
        is_test_mode = getattr(settings, 'PAYMENT_TEST_MODE', False)
        
        # You can also check for specific test flag in environment
        force_test_mode = os.getenv('FORCE_PAYMENT_TEST_MODE', 'false').lower() == 'true'
        
        if is_test_mode or force_test_mode:
            return {
                'test_mode': True,
                'stripe_public_key': os.getenv('STRIPE_TEST_PUBLIC_KEY', ''),
                'stripe_secret_key': os.getenv('STRIPE_TEST_SECRET_KEY', ''),
                'paypal_client_id': os.getenv('PAYPAL_TEST_CLIENT_ID', ''),
                'paypal_client_secret': os.getenv('PAYPAL_TEST_CLIENT_SECRET', ''),
                'webhook_secret': os.getenv('PAYMENT_TEST_WEBHOOK_SECRET', ''),
            }
        else:
            return {
                'test_mode': False,
                'stripe_public_key': os.getenv('STRIPE_LIVE_PUBLIC_KEY', ''),
                'stripe_secret_key': os.getenv('STRIPE_LIVE_SECRET_KEY', ''),
                'paypal_client_id': os.getenv('PAYPAL_LIVE_CLIENT_ID', ''),
                'paypal_client_secret': os.getenv('PAYPAL_LIVE_CLIENT_SECRET', ''),
                'webhook_secret': os.getenv('PAYMENT_LIVE_WEBHOOK_SECRET', ''),
            }
    
    @staticmethod
    @transaction.atomic
    def create_payment_for_orders(orders, payment_method, gateway_name='test_gateway'):
        """
        Create a single payment for one or multiple orders
        """
        try:
            if not orders:
                raise ValidationError("No orders provided")
            
            # Calculate total amount from all orders
            total_amount = sum(order.total_price for order in orders)
            
            # Use the first order's details for payment metadata
            primary_order = orders[0]
            
            # Get payment gateway
            gateway = PaymentGateway.objects.get(
                name=gateway_name,
                is_active=True
            )
            
            # Create payment record
            payment = Payment.objects.create(
                order_reference=primary_order.payment_hash or f"ORDER-{primary_order.id}",  # Use payment_hash or generate fallback
                user=primary_order.user_id,
                gateway=gateway,
                amount=total_amount,
                payment_method=payment_method,
                currency='USD',  # You can make this configurable
                metadata={
                    'order_count': len(orders),
                    'order_ids': [order.order_id for order in orders],
                    'payment_hash': primary_order.payment_hash,
                    'payment_key': primary_order.payment_key,
                    'order_details': [
                        {
                            'order_id': order.order_id,
                            'product_name': order.product.product_name,
                            'quantity': order.quantity,
                            'unit_price': str(order.unit_price),
                            'total_price': str(order.total_price)
                        } for order in orders
                    ]
                }
            )
            
            logger.info(f"Payment created: {payment.payment_id} for {len(orders)} orders (Total: {total_amount})")
            return payment
            
        except PaymentGateway.DoesNotExist:
            raise ValidationError("Payment gateway not found")
    
    @staticmethod
    @transaction.atomic
    def create_payment(order_id, payment_method, gateway_name='test_gateway'):
        """
        Create a new payment for an order
        """
        try:
            # Get the order
            order = Order.objects.get(order_id=order_id)
            
            # Get payment gateway
            gateway = PaymentGateway.objects.get(
                name=gateway_name,
                is_active=True
            )
            
            # Create payment record
            payment = Payment.objects.create(
                order_reference=order.order_id,
                user=order.user_id,
                gateway=gateway,
                amount=order.payment_amount,
                payment_method=payment_method,
                currency='USD',  # You can make this configurable
                metadata={
                    'order_details': {
                        'product_name': order.product.product_name,
                        'quantity': order.quantity,
                        'unit_price': str(order.unit_price)
                    }
                }
            )
            
            logger.info(f"Payment created: {payment.payment_id} for order {order_id}")
            return payment
            
        except Order.DoesNotExist:
            raise ValidationError("Order not found")
        except PaymentGateway.DoesNotExist:
            raise ValidationError("Payment gateway not found")
    
    @staticmethod
    @transaction.atomic
    def process_payment(payment_id, payment_data=None):
        """
        Process a payment through the appropriate gateway
        """
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            # Create payment attempt
            attempt_number = payment.attempts.count() + 1
            attempt = PaymentAttempt.objects.create(
                payment=payment,
                attempt_number=attempt_number,
                status='processing'
            )
            
            # Update payment status
            payment.status = 'processing'
            payment.save()
            
            # Process based on gateway type
            if payment.gateway.gateway_type == 'test_gateway':
                result = PaymentService._process_test_payment(payment, payment_data)
            elif payment.gateway.gateway_type == 'stripe':
                result = PaymentService._process_stripe_payment(payment, payment_data)
            elif payment.gateway.gateway_type == 'paypal':
                result = PaymentService._process_paypal_payment(payment, payment_data)
            elif payment.gateway.gateway_type == 'cash_on_delivery':
                result = PaymentService._process_cod_payment(payment)
            else:
                raise ValidationError(f"Unsupported gateway type: {payment.gateway.gateway_type}")
            
            # Update attempt and payment based on result
            if result['success']:
                attempt.status = 'completed'
                payment.status = 'completed'
                payment.gateway_transaction_id = result.get('transaction_id')
                payment.gateway_reference = result.get('reference')
                payment.processed_at = timezone.now()
                
                # Update order status
                PaymentService._update_order_status(payment.order_reference, 'paid')
                
            else:
                attempt.status = 'failed'
                attempt.error_message = result.get('error_message')
                payment.status = 'failed'
                payment.failure_reason = result.get('error_message')
            
            attempt.gateway_response = result.get('gateway_response', {})
            attempt.save()
            payment.save()
            
            return payment
            
        except Payment.DoesNotExist:
            raise ValidationError("Payment not found")
    
    @staticmethod
    def _process_test_payment(payment, payment_data):
        """
        Simulate payment processing for testing
        """
        # Check if test payment should fail (for testing failure scenarios)
        force_failure = payment_data and payment_data.get('force_failure', False)
        test_card = payment_data and payment_data.get('test_card', '4242424242424242')
        
        # Simulate processing delay
        import time
        time.sleep(1)
        
        # Test card numbers for different scenarios
        if test_card in ['4000000000000002', '4000000000009995'] or force_failure:
            return {
                'success': False,
                'error_message': 'Test payment failed - card declined',
                'gateway_response': {
                    'test_mode': True,
                    'error_code': 'card_declined',
                    'test_card_used': test_card
                }
            }
        
        # Successful test payment
        return {
            'success': True,
            'transaction_id': f'test_txn_{uuid.uuid4().hex[:12]}',
            'reference': f'test_ref_{uuid.uuid4().hex[:8]}',
            'gateway_response': {
                'test_mode': True,
                'status': 'succeeded',
                'test_card_used': test_card,
                'amount_charged': str(payment.amount),
                'currency': payment.currency
            }
        }
    
    @staticmethod
    def _process_stripe_payment(payment, payment_data):
        """
        Process payment through Stripe
        """
        try:
            import stripe
            
            config = PaymentService.get_gateway_config()
            stripe.api_key = config['stripe_secret_key']
            
            # Create payment intent or charge
            if payment_data and 'payment_method_id' in payment_data:
                intent = stripe.PaymentIntent.create(
                    amount=int(payment.amount * 100),  # Stripe uses cents
                    currency=payment.currency.lower(),
                    payment_method=payment_data['payment_method_id'],
                    confirmation_method='manual',
                    confirm=True,
                    metadata={
                        'payment_id': str(payment.payment_id),
                        'order_reference': payment.order_reference,
                    }
                )
                
                if intent.status == 'succeeded':
                    return {
                        'success': True,
                        'transaction_id': intent.id,
                        'reference': intent.client_secret,
                        'gateway_response': dict(intent)
                    }
                else:
                    return {
                        'success': False,
                        'error_message': f"Payment failed: {intent.status}",
                        'gateway_response': dict(intent)
                    }
            else:
                raise ValidationError("Missing payment method for Stripe payment")
                
        except Exception as e:
            logger.error(f"Stripe payment failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'gateway_response': {'error': str(e)}
            }
    
    @staticmethod
    def _process_paypal_payment(payment, payment_data):
        """
        Process payment through PayPal
        """
        # Implementation for PayPal would go here
        # This is a placeholder for now
        return {
            'success': False,
            'error_message': 'PayPal integration not implemented yet',
            'gateway_response': {}
        }
    
    @staticmethod
    def _process_cod_payment(payment):
        """
        Handle Cash on Delivery payments
        """
        return {
            'success': True,
            'transaction_id': f'cod_{uuid.uuid4().hex[:12]}',
            'reference': f'cod_ref_{payment.payment_id}',
            'gateway_response': {
                'payment_method': 'cash_on_delivery',
                'status': 'pending_delivery',
                'note': 'Payment will be collected upon delivery'
            }
        }
    
    @staticmethod
    def _update_order_status(order_reference, status):
        """
        Update order status after payment processing
        """
        try:
            from orders.services import OrderService
            
            if status == 'paid':
                # Update order to pending after successful payment
                order = Order.objects.get(order_id=order_reference)
                order.payment_status = 'completed'
                order.status = 'pending'
                order.paid_at = timezone.now()
                order.save()
                
        except Exception as e:
            logger.error(f"Failed to update order status: {str(e)}")
    
    @staticmethod
    def get_payment_status(order_reference):
        """
        Get payment status for an order
        """
        try:
            payment = Payment.objects.filter(
                order_reference=order_reference
            ).order_by('-created_at').first()
            
            if payment:
                return {
                    'payment_id': payment.payment_id,
                    'status': payment.status,
                    'amount': payment.amount,
                    'gateway': payment.gateway.name,
                    'method': payment.payment_method,
                    'created_at': payment.created_at,
                    'processed_at': payment.processed_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return None
    
    @staticmethod
    def simulate_webhook(payment_id, event_type='payment.succeeded'):
        """
        Simulate payment gateway webhooks for testing
        """
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            if event_type == 'payment.succeeded':
                payment.status = 'completed'
                payment.processed_at = timezone.now()
                PaymentService._update_order_status(payment.order_reference, 'paid')
            elif event_type == 'payment.failed':
                payment.status = 'failed'
                payment.failure_reason = 'Simulated webhook failure'
            
            payment.metadata['webhook_simulation'] = {
                'event_type': event_type,
                'simulated_at': timezone.now().isoformat()
            }
            payment.save()
            
            return {'success': True, 'message': f'Webhook {event_type} simulated'}
            
        except Payment.DoesNotExist:
            return {'success': False, 'message': 'Payment not found'}


class TestPaymentHelper:
    """
    Helper class for testing payment scenarios
    """
    
    TEST_CARDS = {
        'success': '4242424242424242',
        'decline': '4000000000000002',
        'insufficient_funds': '4000000000009995',
        'expired_card': '4000000000000069',
        'incorrect_cvc': '4000000000000127'
    }
    
    @staticmethod
    def create_test_payment_data(scenario='success', **kwargs):
        """
        Create test payment data for different scenarios
        """
        base_data = {
            'test_card': TestPaymentHelper.TEST_CARDS[scenario],
            'force_failure': scenario != 'success',
            'test_mode': True
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def setup_test_gateways():
        """
        Set up test payment gateways
        """
        test_gateway, created = PaymentGateway.objects.get_or_create(
            name='test_gateway',
            defaults={
                'gateway_type': 'test_gateway',
                'is_active': True,
                'is_test_mode': True,
                'configuration': {
                    'test_mode': True,
                    'auto_confirm': True
                },
                'fixed_fee': Decimal('0.30'),
                'percentage_fee': Decimal('2.9')
            }
        )
        return test_gateway

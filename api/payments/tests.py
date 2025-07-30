"""
Comprehensive tests for Payments app
Tests payment creation, processing, product consistency, and integration with orders/carts
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
import uuid

from payments.models import Payment, PaymentGateway, PaymentAttempt
from payments.services import PaymentService, TestPaymentHelper
from orders.models import Order
from products.models import Product, ProductHistory
from stores.models import Store

User = get_user_model()


class PaymentModelTest(TestCase):
    """Test Payment model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='payment@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.gateway = PaymentGateway.objects.create(
            name='test_gateway',
            gateway_type='test_gateway',
            is_active=True,
            is_test_mode=True,
            fixed_fee=Decimal('0.30'),
            percentage_fee=Decimal('2.9')
        )
        
        self.store = Store.objects.create(
            name='Payment Store',
            location='Payment Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Payment Product',
            product_description='Payment Description',
            price=Decimal('100.00'),
            owner_id=self.user,
            store=self.store,
            category='payment_test',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='payment.jpg'
        )
    
    def test_payment_creation(self):
        """Test basic payment creation"""
        payment = Payment.objects.create(
            order_reference='TEST_ORDER_001',
            user=self.user,
            gateway=self.gateway,
            amount=Decimal('100.00'),
            net_amount=Decimal('97.00'),  # After fees
            payment_method='credit_card'
        )
        
        self.assertIsNotNone(payment.payment_id)
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.gateway, self.gateway)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.currency, 'USD')
    
    def test_payment_status_transitions(self):
        """Test payment status changes"""
        payment = Payment.objects.create(
            order_reference='TEST_ORDER_002',
            user=self.user,
            gateway=self.gateway,
            amount=Decimal('50.00'),
            net_amount=Decimal('48.50'),
            payment_method='debit_card'
        )
        
        # Test initial status
        self.assertEqual(payment.status, 'pending')
        
        # Test status changes
        payment.status = 'processing'
        payment.save()
        self.assertEqual(payment.status, 'processing')
        
        payment.status = 'completed'
        payment.processed_at = timezone.now()
        payment.save()
        self.assertEqual(payment.status, 'completed')
        self.assertIsNotNone(payment.processed_at)
    
    def test_payment_with_metadata(self):
        """Test payment metadata storage"""
        metadata = {
            'order_details': {
                'product_name': self.product.product_name,
                'quantity': 2
            },
            'customer_info': {
                'ip_address': '192.168.1.1'
            }
        }
        
        payment = Payment.objects.create(
            order_reference='TEST_ORDER_003',
            user=self.user,
            gateway=self.gateway,
            amount=Decimal('200.00'),
            net_amount=Decimal('194.00'),
            payment_method='mobile_money',
            metadata=metadata
        )
        
        self.assertEqual(payment.metadata['order_details']['product_name'], 
                        self.product.product_name)
        self.assertEqual(payment.metadata['customer_info']['ip_address'], 
                        '192.168.1.1')


class PaymentGatewayTest(TestCase):
    """Test PaymentGateway model functionality"""
    
    def test_gateway_creation(self):
        """Test payment gateway creation"""
        gateway = PaymentGateway.objects.create(
            name='stripe_test',
            gateway_type='stripe',
            is_active=True,
            is_test_mode=True,
            fixed_fee=Decimal('0.30'),
            percentage_fee=Decimal('2.9'),
            configuration={'api_key': 'test_key'}
        )
        
        self.assertEqual(gateway.name, 'stripe_test')
        self.assertEqual(gateway.gateway_type, 'stripe')
        self.assertTrue(gateway.is_active)
        self.assertTrue(gateway.is_test_mode)
        self.assertEqual(gateway.fixed_fee, Decimal('0.30'))
        self.assertEqual(gateway.percentage_fee, Decimal('2.9'))
    
    def test_gateway_fee_calculation(self):
        """Test gateway fee calculation"""
        gateway = PaymentGateway.objects.create(
            name='fee_test_gateway',
            gateway_type='test_gateway',
            is_active=True,
            fixed_fee=Decimal('0.50'),
            percentage_fee=Decimal('3.0')
        )
        
        # Test fee calculation (would be implemented in gateway service)
        amount = Decimal('100.00')
        expected_percentage_fee = amount * (gateway.percentage_fee / 100)
        expected_total_fee = gateway.fixed_fee + expected_percentage_fee
        expected_net = amount - expected_total_fee
        
        self.assertEqual(expected_percentage_fee, Decimal('3.00'))
        self.assertEqual(expected_total_fee, Decimal('3.50'))
        self.assertEqual(expected_net, Decimal('96.50'))


class PaymentAttemptTest(TestCase):
    """Test PaymentAttempt model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='attempt@example.com',
            password='testpass123',
            phone_number='2345678901'
        )
        
        self.gateway = PaymentGateway.objects.create(
            name='attempt_gateway',
            gateway_type='test_gateway',
            is_active=True
        )
        
        self.payment = Payment.objects.create(
            order_reference='ATTEMPT_001',
            user=self.user,
            gateway=self.gateway,
            amount=Decimal('75.00'),
            net_amount=Decimal('72.50'),
            payment_method='credit_card'
        )
    
    def test_payment_attempt_creation(self):
        """Test payment attempt creation"""
        attempt = PaymentAttempt.objects.create(
            payment=self.payment,
            attempt_number=1,
            status='processing'
        )
        
        self.assertEqual(attempt.payment, self.payment)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.status, 'processing')
        self.assertIsNotNone(attempt.attempted_at)
    
    def test_multiple_payment_attempts(self):
        """Test multiple payment attempts"""
        # First attempt
        attempt1 = PaymentAttempt.objects.create(
            payment=self.payment,
            attempt_number=1,
            status='failed',
            error_message='Card declined'
        )
        
        # Second attempt
        attempt2 = PaymentAttempt.objects.create(
            payment=self.payment,
            attempt_number=2,
            status='completed'
        )
        
        self.assertEqual(self.payment.attempts.count(), 2)
        self.assertEqual(attempt1.status, 'failed')
        self.assertEqual(attempt2.status, 'completed')


class PaymentServiceTest(TestCase):
    """Test PaymentService functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='service@example.com',
            password='testpass123',
            phone_number='3456789012'
        )
        
        self.store = Store.objects.create(
            name='Service Store',
            location='Service Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Service Product',
            product_description='Service Description',
            price=Decimal('80.00'),
            owner_id=self.user,
            store=self.store,
            category='service_test',
            has_sizes=False,
            available_quantity=15,
            reserved_quantity=0,
            picture='service.jpg'
        )
        
        self.order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Service Address',
            payment_amount=self.product.price
        )
        
        # Set up test gateway
        TestPaymentHelper.setup_test_gateways()
    
    def test_payment_service_gateway_config(self):
        """Test payment service gateway configuration"""
        config = PaymentService.get_gateway_config()
        
        self.assertIn('test_mode', config)
        self.assertIn('stripe_public_key', config)
        self.assertIn('stripe_secret_key', config)
    
    def test_create_payment_for_order(self):
        """Test payment creation for single order"""
        payment = PaymentService.create_payment(
            order_id=self.order.order_id,
            payment_method='credit_card'
        )
        
        self.assertIsNotNone(payment)
        self.assertEqual(payment.order_reference, self.order.order_id)
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount, self.order.payment_amount)
        self.assertEqual(payment.payment_method, 'credit_card')
    
    def test_create_payment_for_multiple_orders(self):
        """Test payment creation for multiple orders"""
        # Create second order
        order2 = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='Service Address 2',
            payment_amount=self.product.price * 2,
            payment_hash='test_hash_123'
        )
        
        orders = [self.order, order2]
        payment = PaymentService.create_payment_for_orders(
            orders=orders,
            payment_method='mobile_money'
        )
        
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, self.order.payment_amount + order2.payment_amount)
        self.assertEqual(payment.metadata['order_count'], 2)
        self.assertIn(self.order.order_id, payment.metadata['order_ids'])
        self.assertIn(order2.order_id, payment.metadata['order_ids'])
    
    def test_process_test_payment_success(self):
        """Test successful test payment processing"""
        payment = PaymentService.create_payment(
            order_id=self.order.order_id,
            payment_method='test_payment'
        )
        
        test_data = TestPaymentHelper.create_test_payment_data('success')
        processed_payment = PaymentService.process_payment(
            payment_id=payment.payment_id,
            payment_data=test_data
        )
        
        self.assertEqual(processed_payment.status, 'completed')
        self.assertIsNotNone(processed_payment.gateway_transaction_id)
        self.assertIsNotNone(processed_payment.processed_at)
    
    def test_process_test_payment_failure(self):
        """Test failed test payment processing"""
        payment = PaymentService.create_payment(
            order_id=self.order.order_id,
            payment_method='test_payment'
        )
        
        test_data = TestPaymentHelper.create_test_payment_data('decline')
        processed_payment = PaymentService.process_payment(
            payment_id=payment.payment_id,
            payment_data=test_data
        )
        
        self.assertEqual(processed_payment.status, 'failed')
        self.assertIsNotNone(processed_payment.failure_reason)
        self.assertEqual(processed_payment.attempts.count(), 1)
    
    def test_get_payment_status(self):
        """Test payment status retrieval"""
        payment = PaymentService.create_payment(
            order_id=self.order.order_id,
            payment_method='bank_transfer'
        )
        
        status_info = PaymentService.get_payment_status(self.order.order_id)
        
        self.assertIsNotNone(status_info)
        self.assertEqual(status_info['payment_id'], payment.payment_id)
        self.assertEqual(status_info['status'], 'pending')
        self.assertEqual(status_info['amount'], payment.amount)
    
    def test_simulate_webhook(self):
        """Test payment webhook simulation"""
        payment = PaymentService.create_payment(
            order_id=self.order.order_id,
            payment_method='credit_card'
        )
        
        # Simulate successful webhook
        result = PaymentService.simulate_webhook(
            payment_id=payment.payment_id,
            event_type='payment.succeeded'
        )
        
        self.assertTrue(result['success'])
        
        # Refresh payment from database
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'completed')
        self.assertIn('webhook_simulation', payment.metadata)


class PaymentIntegrationTest(TransactionTestCase):
    """Test Payment integration with orders and product changes"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='integration@example.com',
            password='testpass123',
            phone_number='4567890123'
        )
        
        self.store = Store.objects.create(
            name='Integration Store',
            location='Integration Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Integration Product',
            product_description='Integration Description',
            price=Decimal('60.00'),
            owner_id=self.user,
            store=self.store,
            category='integration',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=0,
            picture='integration.jpg'
        )
        
        # Set up test gateway
        TestPaymentHelper.setup_test_gateways()
    
    def test_payment_with_product_price_change(self):
        """Test payment consistency when product price changes"""
        # Create order
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Integration Address',
            payment_amount=self.product.price
        )
        
        # Create payment
        payment = PaymentService.create_payment(
            order_id=order.order_id,
            payment_method='credit_card'
        )
        
        # Store original price
        original_price = self.product.price
        
        # Change product price after payment creation
        new_price = Decimal('90.00')
        self.product.price = new_price
        self.product.save()
        
        # Payment should maintain original amount
        self.assertEqual(payment.amount, original_price)
        self.assertNotEqual(payment.amount, new_price)
        
        # Order validation should detect change
        validation = order.validate_product_consistency()
        self.assertFalse(validation['valid'])
    
    def test_payment_with_product_history(self):
        """Test payment integration with product history"""
        # Create order with product history
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='History Address',
            payment_amount=self.product.price * 2
        )
        
        # Create product history snapshot
        order.create_product_history_snapshot()
        
        # Create payment
        payment = PaymentService.create_payment(
            order_id=order.order_id,
            payment_method='mobile_money'
        )
        
        # Verify payment metadata includes product history info
        self.assertIn('product_name', payment.metadata['order_details'])
        self.assertEqual(
            payment.metadata['order_details']['product_name'],
            self.product.product_name
        )
        
        # Change product after payment
        self.product.product_name = 'Changed Product Name'
        self.product.save()
        
        # Payment metadata should maintain original product info
        self.assertEqual(
            payment.metadata['order_details']['product_name'],
            order.product_history.product_name
        )
        self.assertNotEqual(
            payment.metadata['order_details']['product_name'],
            self.product.product_name
        )
    
    @patch('orders.services.OrderService.update_order_status')
    def test_payment_order_status_update(self, mock_update_status):
        """Test order status update after payment"""
        # Create order
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Status Address',
            payment_amount=self.product.price,
            status='under_paying'
        )
        
        # Create and process payment
        payment = PaymentService.create_payment(
            order_id=order.order_id,
            payment_method='test_payment'
        )
        
        test_data = TestPaymentHelper.create_test_payment_data('success')
        PaymentService.process_payment(
            payment_id=payment.payment_id,
            payment_data=test_data
        )
        
        # Verify order was updated
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'completed')
        self.assertEqual(order.status, 'pending')
        self.assertIsNotNone(order.paid_at)
    
    def test_payment_failure_order_impact(self):
        """Test order handling when payment fails"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Failure Address',
            payment_amount=self.product.price,
            status='under_paying'
        )
        
        # Create and process failed payment
        payment = PaymentService.create_payment(
            order_id=order.order_id,
            payment_method='test_payment'
        )
        
        test_data = TestPaymentHelper.create_test_payment_data('decline')
        PaymentService.process_payment(
            payment_id=payment.payment_id,
            payment_data=test_data
        )
        
        # Verify payment failed
        self.assertEqual(payment.status, 'failed')
        
        # Order should remain in under_paying status
        order.refresh_from_db()
        self.assertEqual(order.status, 'under_paying')
        self.assertEqual(order.payment_status, 'pending')


class TestPaymentHelperTest(TestCase):
    """Test TestPaymentHelper functionality"""
    
    def test_test_card_scenarios(self):
        """Test different test card scenarios"""
        # Test success scenario
        success_data = TestPaymentHelper.create_test_payment_data('success')
        self.assertEqual(success_data['test_card'], '4242424242424242')
        self.assertFalse(success_data['force_failure'])
        
        # Test decline scenario
        decline_data = TestPaymentHelper.create_test_payment_data('decline')
        self.assertEqual(decline_data['test_card'], '4000000000000002')
        self.assertTrue(decline_data['force_failure'])
        
        # Test custom scenario
        custom_data = TestPaymentHelper.create_test_payment_data(
            'success', 
            custom_field='custom_value'
        )
        self.assertEqual(custom_data['custom_field'], 'custom_value')
    
    def test_setup_test_gateways(self):
        """Test test gateway setup"""
        gateway = TestPaymentHelper.setup_test_gateways()
        
        self.assertEqual(gateway.name, 'test_gateway')
        self.assertEqual(gateway.gateway_type, 'test_gateway')
        self.assertTrue(gateway.is_active)
        self.assertTrue(gateway.is_test_mode)

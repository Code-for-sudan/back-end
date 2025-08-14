"""
Comprehensive tests for Orders app
Tests order creation, product history integration, payment timer, and stock management
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
import uuid
from datetime import timedelta

from orders.models import Order
from products.models import Product, ProductHistory, Size
from stores.models import Store
from carts.models import Cart, CartItem
from payments.models import Payment, PaymentGateway

User = get_user_model()


class OrderModelTest(TestCase):
    """Test Order model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Test Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Test Product',
            product_description='Test Description',
            price=Decimal('99.99'),
            owner_id=self.user,
            store=self.store,
            category='electronics',
            has_sizes=False,
            available_quantity=100,
            reserved_quantity=0,
            picture='test.jpg'
        )
    
    def test_order_creation_basic(self):
        """Test basic order creation"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='123 Test St'
        )
        
        self.assertIsNotNone(order.order_id)
        self.assertTrue(order.order_id.startswith('ORD-'))
        self.assertEqual(order.user_id, self.user)
        self.assertEqual(order.product, self.product)
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.status, 'on_cart')
        self.assertEqual(order.payment_status, 'pending')
    
    def test_order_product_history_integration(self):
        """Test product history snapshot creation"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='123 Test St'
        )
        
        # Test product details stored at order time
        self.assertEqual(order.product_name_at_order, self.product.product_name)
        self.assertEqual(order.product_price_at_order, self.product.current_price)
        
        # Test product history snapshot creation
        order.create_product_history_snapshot()
        self.assertIsNotNone(order.product_history)
        self.assertEqual(order.product_history.product_name, self.product.product_name)
    
    def test_order_get_product_methods(self):
        """Test methods for getting product information"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='123 Test St'
        )
        
        # Test without history
        self.assertEqual(order.get_product_name(), self.product.product_name)
        self.assertEqual(order.get_product_price(), self.product.current_price)
        
        # Test with history
        order.create_product_history_snapshot()
        self.assertEqual(order.get_product_name(), self.product.product_name)
        self.assertEqual(order.get_product_price(), self.product.current_price)
    
    def test_order_product_consistency_validation(self):
        """Test product consistency validation"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='123 Test St'
        )
        
        # Test valid consistency
        validation = order.validate_product_consistency()
        self.assertTrue(validation['valid'])
        
        # Test price change
        self.product.price = Decimal('150.00')
        self.product.save()
        
        validation = order.validate_product_consistency()
        self.assertFalse(validation['valid'])
        self.assertIn('Price changed', validation['reason'])
    
    def test_order_payment_timer_properties(self):
        """Test payment timer related properties"""
        # Create order with payment expiration
        future_time = timezone.now() + timedelta(minutes=15)
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='123 Test St',
            status='under_paying',
            payment_expires_at=future_time
        )
        
        # Test not expired
        self.assertFalse(order.is_payment_expired)
        self.assertGreater(order.payment_time_remaining, 0)
        
        # Test expired
        past_time = timezone.now() - timedelta(minutes=1)
        order.payment_expires_at = past_time
        order.save()
        
        self.assertTrue(order.is_payment_expired)
        self.assertEqual(order.payment_time_remaining, 0)
    
    def test_order_status_properties(self):
        """Test order status related properties"""
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='123 Test St'
        )
        
        # Test initial state
        self.assertTrue(order.is_cart_item)
        self.assertFalse(order.is_paid)
        self.assertFalse(order.is_delivered)
        self.assertTrue(order.can_be_cancelled)
        
        # Test paid state
        order.payment_status = 'completed'
        order.status = 'pending'
        order.save()
        
        self.assertTrue(order.is_paid)
        self.assertFalse(order.is_cart_item)
        self.assertTrue(order.can_be_cancelled)
        
        # Test delivered state
        order.status = 'arrived'
        order.save()
        
        self.assertTrue(order.is_delivered)
        self.assertFalse(order.can_be_cancelled)


class OrderServiceIntegrationTest(TransactionTestCase):
    """Test Order integration with services"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='service@example.com',
            password='testpass123',
            phone_number='0987654321'
        )
        
        self.store = Store.objects.create(
            name='Service Test Store',
            location='Service Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Service Test Product',
            product_description='Service Test Description',
            price=Decimal('50.00'),
            owner_id=self.user,
            store=self.store,
            category='books',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='service_test.jpg'
        )
    
    @patch('products.services.stock_service.StockService.reserve_stock')
    def test_order_with_stock_reservation(self, mock_reserve_stock):
        """Test order creation with stock reservation"""
        mock_reserve_stock.return_value = self.product
        
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='456 Service St'
        )
        
        # Verify order created
        self.assertIsNotNone(order)
        self.assertEqual(order.quantity, 2)
        
        # Note: Stock reservation would typically be handled by OrderService
        # This test verifies the order model integrates properly
    
    @patch('payments.services.PaymentService.create_payment')
    def test_order_with_payment_creation(self, mock_create_payment):
        """Test order integration with payment service"""
        # Create payment gateway
        gateway = PaymentGateway.objects.create(
            name='test_gateway',
            gateway_type='test_gateway',
            is_active=True,
            is_test_mode=True
        )
        
        # Mock payment creation
        mock_payment = Payment.objects.create(
            order_reference='TEST_REF',
            user=self.user,
            gateway=gateway,
            amount=Decimal('100.00'),
            net_amount=Decimal('100.00'),
            payment_method='credit_card'
        )
        mock_create_payment.return_value = mock_payment
        
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='789 Payment St',
            payment_reference=mock_payment
        )
        
        # Verify integration
        self.assertEqual(order.payment_reference, mock_payment)
        self.assertEqual(order.total_price, self.product.price * 2)
    
    def test_order_product_history_on_price_change(self):
        """Test order behavior when product price changes"""
        # Create order
        original_price = self.product.price
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=original_price,
            total_price=original_price,
            shipping_address='123 History St'
        )
        
        # Create history snapshot
        order.create_product_history_snapshot()
        
        # Change product price
        new_price = Decimal('75.00')
        self.product.price = new_price
        self.product.save()
        
        # Verify order maintains original price info
        self.assertEqual(order.get_product_price(), original_price)
        self.assertEqual(order.product_history.price, original_price)
        self.assertEqual(order.product.price, new_price)  # Product has new price
        
        # Verify consistency validation
        validation = order.validate_product_consistency()
        self.assertFalse(validation['valid'])
        self.assertIn('Price changed', validation['reason'])


class OrderTimerTest(TestCase):
    """Test payment timer functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='timer@example.com',
            password='testpass123',
            phone_number='1111111111'
        )
        
        self.store = Store.objects.create(
            name='Timer Store',
            location='Timer Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Timer Product',
            product_description='Timer Description',
            price=Decimal('25.00'),
            owner_id=self.user,
            store=self.store,
            category='timer',
            has_sizes=False,
            available_quantity=5,
            reserved_quantity=0,
            picture='timer.jpg'
        )
    
    def test_payment_timer_creation(self):
        """Test payment timer setup"""
        expiry_time = timezone.now() + timedelta(minutes=15)
        
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Timer St',
            status='under_paying',
            payment_expires_at=expiry_time,
            payment_hash=uuid.uuid4().hex,
            payment_key=uuid.uuid4().hex
        )
        
        self.assertEqual(order.status, 'under_paying')
        self.assertIsNotNone(order.payment_expires_at)
        self.assertIsNotNone(order.payment_hash)
        self.assertIsNotNone(order.payment_key)
        self.assertFalse(order.is_payment_expired)
        self.assertGreater(order.payment_time_remaining, 0)
    
    def test_payment_timer_expiry(self):
        """Test payment timer expiry"""
        # Create expired order
        past_time = timezone.now() - timedelta(minutes=1)
        
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            total_price=self.product.price,
            shipping_address='Expired St',
            status='under_paying',
            payment_expires_at=past_time
        )
        
        self.assertTrue(order.is_payment_expired)
        self.assertEqual(order.payment_time_remaining, 0)
    
    @patch('products.services.stock_service.StockService.unreserve_stock')
    def test_expired_order_stock_cleanup(self, mock_unreserve):
        """Test stock cleanup for expired orders"""
        mock_unreserve.return_value = self.product
        
        # Create expired order
        past_time = timezone.now() - timedelta(minutes=1)
        
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2,
            shipping_address='Cleanup St',
            status='under_paying',
            payment_expires_at=past_time
        )
        
        # Verify timer expired
        self.assertTrue(order.is_payment_expired)
        
        # Stock cleanup would typically be handled by a background task
        # This test ensures the order state is correct for cleanup
        self.assertEqual(order.status, 'under_paying')
        self.assertEqual(order.quantity, 2)  # Available for cleanup

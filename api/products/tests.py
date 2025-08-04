"""
Comprehensive tests for Products app
Tests Product model, ProductHistory, Stock management, and product history tracking
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from decimal import Decimal
from unittest.mock import patch, MagicMock
import uuid

from products.models import Product, ProductHistory, Size
from stores.models import Store
from orders.models import Order
from carts.models import Cart, CartItem
from carts.models import Cart, CartItem

User = get_user_model()


class ProductModelTest(TestCase):
    """Test Product model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='product@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Product Store',
            location='Product Location',
            store_type='retail'
        )
    
    def test_product_creation(self):
        """Test basic product creation"""
        product = Product.objects.create(
            product_name='Test Product',
            product_description='Test Description',
            price=Decimal('99.99'),
            owner_id=self.user,
            store=self.store,
            category='test_category',
            has_sizes=False,
            available_quantity=100,
            reserved_quantity=0,
            picture='test.jpg'
        )
        
        self.assertEqual(product.product_name, 'Test Product')
        self.assertEqual(product.price, Decimal('99.99'))
        self.assertEqual(product.owner_id, self.user)
        self.assertEqual(product.store, self.store)
        self.assertFalse(product.has_sizes)
        self.assertEqual(product.available_quantity, 100)
        self.assertEqual(product.reserved_quantity, 0)
    
    def test_product_with_sizes(self):
        """Test product creation with sizes"""
        product = Product.objects.create(
            product_name='Sized Product',
            product_description='Product with sizes',
            price=Decimal('79.99'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            picture='sized.jpg'
        )
        
        # Create sizes for the product
        from products.models import Size
        Size.objects.create(product=product, size='S', available_quantity=10, reserved_quantity=0)
        Size.objects.create(product=product, size='M', available_quantity=15, reserved_quantity=0)
        Size.objects.create(product=product, size='L', available_quantity=12, reserved_quantity=0)
        
        self.assertTrue(product.has_sizes)
        self.assertEqual(product.sizes.count(), 3)
        self.assertEqual(product.get_total_stock(), 37)  # Sum of sizes
    
    def test_product_validation(self):
        """Test product field validation"""
        with self.assertRaises(ValidationError):
            product = Product(
                product_name='',  # Empty name should fail
                product_description='Test Description',
                price=Decimal('99.99'),
                owner_id=self.user,
                store=self.store,
                category='test_category'
            )
            product.full_clean()
        
        with self.assertRaises(ValidationError):
            product = Product(
                product_name='Test Product',
                product_description='Test Description',
                price=Decimal('-10.00'),  # Negative price should fail
                owner_id=self.user,
                store=self.store,
                category='test_category'
            )
            product.full_clean()
    
    def test_product_stock_methods(self):
        """Test product stock management methods"""
        product = Product.objects.create(
            product_name='Stock Product',
            product_description='Stock testing',
            price=Decimal('50.00'),
            owner_id=self.user,
            store=self.store,
            category='stock_test',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=5
        )
        
        # Test stock levels
        self.assertEqual(product.get_total_stock(), 25)
        self.assertEqual(product.get_available_stock(), 20)
        self.assertEqual(product.get_reserved_stock(), 5)
        
        # Test stock availability
        self.assertTrue(product.has_stock(10))
        self.assertFalse(product.has_stock(25))
        
        # Test stock operations
        product.reserve_stock(5)
        self.assertEqual(product.reserved_quantity, 10)
        self.assertEqual(product.available_quantity, 15)
        
        product.unreserve_stock(3)
        self.assertEqual(product.reserved_quantity, 7)
        self.assertEqual(product.available_quantity, 18)
        
        product.confirm_sale(2)
        self.assertEqual(product.reserved_quantity, 5)
        # Total stock should decrease by 2
    
    def test_product_with_sizes_stock(self):
        """Test stock operations for products with sizes"""
        product = Product.objects.create(
            product_name='Sized Stock Product',
            product_description='Stock testing with sizes',
            price=Decimal('60.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True
        )
        
        # Create sizes for the product
        from products.models import Size
        Size.objects.create(product=product, size='S', available_quantity=4, reserved_quantity=1)  # Only 4 available for new reservations
        Size.objects.create(product=product, size='M', available_quantity=8, reserved_quantity=2)  # 8 available for new reservations
        Size.objects.create(product=product, size='L', available_quantity=8, reserved_quantity=0)
        
        # Test size-specific stock
        size_s = product.sizes.get(size='S')
        size_m = product.sizes.get(size='M')
        size_l = product.sizes.get(size='L')
        
        self.assertTrue(size_m.has_stock(5))  # 8 available, asking for 5 -> True
        self.assertFalse(size_s.has_stock(5))  # Only 4 available, asking for 5 -> False
        
        # Test size stock operations
        size_l.reserve_stock(3)
        self.assertEqual(size_l.reserved_quantity, 3)
        
        size_m.confirm_stock_sale(1)
        size_m.refresh_from_db()
        self.assertEqual(size_m.reserved_quantity, 1)  # Was 2, now 1
    
    def test_product_string_representation(self):
        """Test product string representation"""
        product = Product.objects.create(
            product_name='String Test Product',
            product_description='Testing string representation',
            price=Decimal('25.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            available_quantity=10,
            reserved_quantity=0
        )
        
        expected_str = f"String Test Product - {self.store.name}"
        self.assertEqual(str(product), expected_str)


class ProductHistoryTest(TestCase):
    """Test ProductHistory model and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='history@example.com',
            password='testpass123',
            phone_number='2345678901'
        )
        
        self.store = Store.objects.create(
            name='History Store',
            location='History Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='History Product',
            product_description='Product for history testing',
            price=Decimal('75.00'),
            owner_id=self.user,
            store=self.store,
            category='history_test',
            has_sizes=False,
            available_quantity=50,
            reserved_quantity=0
        )
    
    def test_product_history_creation(self):
        """Test ProductHistory creation from product"""
        history = ProductHistory.create_from_product(self.product)
        
        self.assertEqual(history.product, self.product)
        self.assertEqual(history.product_name, self.product.product_name)
        self.assertEqual(history.product_price, self.product.price)
        self.assertEqual(history.product_description, self.product.product_description)
        self.assertEqual(history.category, self.product.category)
        self.assertEqual(history.has_sizes, self.product.has_sizes)
        # Compare sizes as lists
        expected_sizes = list(self.product.sizes.values_list("size", flat=True))
        self.assertEqual(history.sizes, expected_sizes)
        self.assertIsNotNone(history.snapshot_taken_at)
    
    def test_product_change_detection(self):
        """Test product change detection"""
        # Create history snapshot
        history = ProductHistory.create_from_product(self.product)
        
        # No changes initially
        self.assertFalse(history.has_product_changed(self.product))
        
        # Change product name
        self.product.product_name = 'Changed Product Name'
        self.product.save()
        
        # Should detect change
        self.assertTrue(history.has_product_changed(self.product))
        
        # Change product price
        original_name = self.product.product_name
        self.product.product_name = history.product_name  # Revert name
        self.product.price = Decimal('85.00')
        self.product.save()
        
        # Should detect price change
        self.assertTrue(history.has_product_changed(self.product))
    
    def test_product_history_with_sizes(self):
        """Test ProductHistory with sized products"""
        sized_product = Product.objects.create(
            product_name='Sized History Product',
            product_description='Sized product for history',
            price=Decimal('65.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            available_quantity=None,
            reserved_quantity=None
        )
        
        # Create size objects for the product
        from products.models import Size
        Size.objects.create(product=sized_product, size='XS', available_quantity=3, reserved_quantity=0)
        Size.objects.create(product=sized_product, size='S', available_quantity=8, reserved_quantity=0)
        Size.objects.create(product=sized_product, size='M', available_quantity=12, reserved_quantity=0)
        
        history = ProductHistory.create_from_product(sized_product)
        
        self.assertTrue(history.has_sizes)
        # Compare sizes as lists for sized products
        expected_sizes = list(sized_product.sizes.values_list("size", flat=True))
        self.assertEqual(history.sizes, expected_sizes)
        
        # Change sizes and test detection - add a new size
        Size.objects.create(product=sized_product, size='L', available_quantity=10, reserved_quantity=0)
        
        self.assertTrue(history.has_product_changed(sized_product))
    
    def test_multiple_history_snapshots(self):
        """Test multiple history snapshots for same product"""
        # Clear any existing history and verify it's clean
        ProductHistory.objects.filter(product=self.product).delete()
        self.assertEqual(ProductHistory.objects.filter(product=self.product).count(), 0)
        
        # Create first snapshot manually
        history1 = ProductHistory.create_from_product(self.product)
        original_price = self.product.price
        self.assertEqual(ProductHistory.objects.filter(product=self.product).count(), 1)
        
        # Change product (this will trigger signal to create history automatically)
        self.product.price = Decimal('85.00')
        self.product.save()
        
        # Get the latest history created by the signal
        history2 = ProductHistory.objects.filter(product=self.product).order_by('-snapshot_taken_at').first()
        
        # Verify both snapshots exist
        self.assertEqual(ProductHistory.objects.filter(product=self.product).count(), 2)
        
        # Verify they captured different states
        self.assertEqual(history1.product_price, original_price)
        self.assertEqual(history2.product_price, Decimal('85.00'))
        
        # Change product again
        self.product.product_name = 'Final Product Name'
        self.product.save()
        
        # First history should detect changes
        self.assertTrue(history1.has_product_changed(self.product))
        
        # Second history should detect name change but not price change
        self.assertTrue(history2.has_product_changed(self.product))
    
    def test_product_history_string_representation(self):
        """Test ProductHistory string representation"""
        history = ProductHistory.create_from_product(self.product)
        
        expected_str = f"History for {self.product.product_name} at {history.snapshot_taken_at}"
        self.assertEqual(str(history), expected_str)


class ProductIntegrationTest(TransactionTestCase):
    """Test Product integration with other models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='integration@example.com',
            password='testpass123',
            phone_number='3456789012'
        )
        
        self.store = Store.objects.create(
            name='Integration Store',
            location='Integration Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Integration Product',
            product_description='Product for integration testing',
            price=Decimal('100.00'),
            owner_id=self.user,
            store=self.store,
            category='integration',
            has_sizes=False,
            available_quantity=25,
            reserved_quantity=0
        )
    
    def test_product_order_integration(self):
        """Test product integration with orders"""
        # Create order
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=3,
            unit_price=self.product.price,
            total_price=self.product.price * 3,
            shipping_address='Integration Address',
            payment_amount=self.product.price * 3
        )
        
        # Verify order references product
        self.assertEqual(order.product, self.product)
        self.assertEqual(order.unit_price, self.product.price)
        
        # Create product history for order
        order.create_product_history_snapshot()
        
        # Verify history was created
        self.assertIsNotNone(order.product_history)
        self.assertEqual(order.product_history.product, self.product)
        
        # Change product and verify order detects change
        self.product.price = Decimal('120.00')
        self.product.save()
        
        validation = order.validate_product_consistency()
        self.assertFalse(validation['valid'])
        self.assertIn('price', validation['changes'])
    
    def test_product_cart_integration(self):
        """Test product integration with carts"""
        # Create cart
        cart = Cart.objects.create(user=self.user)
        
        # Add product to cart
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
            unit_price_at_time=self.product.price
        )
        
        # Verify cart item references product
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.unit_price, self.product.price)
        
        # Test product change detection
        changes = cart_item.check_product_changes()
        self.assertFalse(changes['changed'])  # No changes initially
        
        # Change product
        self.product.product_name = 'Updated Integration Product'
        self.product.price = Decimal('110.00')
        self.product.save()
        
        # Check for changes
        changes = cart_item.check_product_changes()
        self.assertTrue(changes['changed'])  # Price changed
        
        # Update cart item for changes
        cart_item.update_for_product_changes()
        
        # Verify cart item was updated
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.unit_price, Decimal('110.00'))
    
    def test_product_stock_reservation_integration(self):
        """Test product stock reservation with orders/carts"""
        initial_available = self.product.available_quantity
        initial_reserved = self.product.reserved_quantity
        
        # Create cart item and manually reserve stock
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=5,
            unit_price_at_time=self.product.price
        )
        
        # Manually reserve stock for cart item
        self.product.reserve_stock(cart_item.quantity)
        cart_item.is_stock_reserved = True
        cart_item.save()
        
        # Stock should be reserved
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_quantity, initial_available - 5)
        self.assertEqual(self.product.reserved_quantity, initial_reserved + 5)
        
        # Create order from cart item (should confirm reservation)
        order = Order.objects.create(
            user_id=self.user,
            product=self.product,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.unit_price * cart_item.quantity,
            shipping_address='Stock Address',
            payment_amount=cart_item.unit_price * cart_item.quantity
        )
        
        # Simulate order confirmation (stock service would handle this)
        self.product.confirm_sale(order.quantity)
        
        # Reserved stock should be reduced
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserved_quantity, initial_reserved)
        
        # Delete cart item (should unreserve remaining stock)
        cart_item.delete()
    
    def test_product_history_order_consistency(self):
        """Test product history consistency with orders"""
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
        
        order.create_product_history_snapshot()
        original_history = order.product_history
        
        # Change product multiple times
        changes = [
            {'product_name': 'First Change'},
            {'price': Decimal('110.00')},
            {'product_description': 'Changed description'},
            {'category': 'new_category'}
        ]
        
        for change in changes:
            for field, value in change.items():
                setattr(self.product, field, value)
            self.product.save()
        
        # Order history should still reflect original state
        self.assertEqual(original_history.product_name, 'Integration Product')
        self.assertEqual(original_history.product_price, Decimal('100.00'))
        
        # Validate should detect all changes
        validation = order.validate_product_consistency()
        self.assertFalse(validation['valid'])
        self.assertEqual(len(validation['changes']), 4)


class ProductStockManagementTest(TransactionTestCase):
    """Test advanced product stock management scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='stock@example.com',
            password='testpass123',
            phone_number='4567890123'
        )
        
        self.store = Store.objects.create(
            name='Stock Store',
            location='Stock Location',
            store_type='retail'
        )
    
    def test_concurrent_stock_operations(self):
        """Test concurrent stock operations"""
        product = Product.objects.create(
            product_name='Concurrent Stock Product',
            product_description='Testing concurrent operations',
            price=Decimal('80.00'),
            owner_id=self.user,
            store=self.store,
            category='concurrent',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0
        )
        
        # Simulate concurrent reservations
        with transaction.atomic():
            # First reservation
            product.reserve_stock(5)
            
            # Second reservation (should work)
            product.reserve_stock(3)
            
            # Third reservation (should fail - not enough stock)
            with self.assertRaises(ValidationError):
                product.reserve_stock(5)  # Only 2 remaining
        
        # Verify final state
        product.refresh_from_db()
        self.assertEqual(product.available_quantity, 2)
        self.assertEqual(product.reserved_quantity, 8)
    
    def test_sized_product_stock_management(self):
        """Test stock management for sized products"""
        product = Product.objects.create(
            product_name='Sized Stock Product',
            product_description='Stock management with sizes',
            price=Decimal('70.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True
        )
        
        # Create sizes for the product
        from products.models import Size
        size_s = Size.objects.create(product=product, size='S', available_quantity=5, reserved_quantity=0)
        size_m = Size.objects.create(product=product, size='M', available_quantity=10, reserved_quantity=0)
        size_l = Size.objects.create(product=product, size='L', available_quantity=8, reserved_quantity=0)
        size_xl = Size.objects.create(product=product, size='XL', available_quantity=3, reserved_quantity=0)
        
        # Test size reservations
        size_m.reserve_stock(4)
        size_l.reserve_stock(2)
        
        # Verify reservations
        self.assertEqual(size_m.reserved_quantity, 4)
        self.assertEqual(size_l.reserved_quantity, 2)
        
        # Test over-reservation
        with self.assertRaises(ValidationError):
            size_s.reserve_stock(6)  # Only 5 available
        
        # Test size sales
        product.confirm_size_sale('M', 2)
        
        # Verify sale confirmed - refresh size objects
        size_m.refresh_from_db()
        self.assertEqual(size_m.available_quantity, 6)  # Unchanged from after reservation (10-4)
        self.assertEqual(size_m.reserved_quantity, 2)  # 4 - 2
        
        # Test total stock calculation
        # After sale confirmation, total stock = S(5+0) + M(6+2) + L(6+2) + XL(3+0) = 24
        expected_total = (5 + 0) + (6 + 2) + (6 + 2) + (3 + 0)  # (avail + reserved) for each size after sale
        self.assertEqual(product.get_total_stock(), expected_total)
    
    def test_stock_operations_validation(self):
        """Test stock operation validation"""
        product = Product.objects.create(
            product_name='Validation Product',
            product_description='Stock validation testing',
            price=Decimal('90.00'),
            owner_id=self.user,
            store=self.store,
            category='validation',
            has_sizes=False,
            available_quantity=15,
            reserved_quantity=5
        )
        
        # Test invalid unreserve (more than reserved)
        with self.assertRaises(ValidationError):
            product.unreserve_stock(6)
        
        # Test invalid confirm sale (more than reserved)
        with self.assertRaises(ValidationError):
            product.confirm_sale(6)
        
        # Test negative stock operations
        with self.assertRaises(ValidationError):
            product.reserve_stock(-1)
        
        with self.assertRaises(ValidationError):
            product.unreserve_stock(-1)
        
        with self.assertRaises(ValidationError):
            product.confirm_sale(-1)
    
    def test_product_availability_checks(self):
        """Test product availability checking methods"""
        product = Product.objects.create(
            product_name='Availability Product',
            product_description='Availability testing',
            price=Decimal('95.00'),
            owner_id=self.user,
            store=self.store,
            category='availability',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=3
        )
        
        # Test stock availability
        self.assertTrue(product.has_stock(15))
        self.assertTrue(product.has_stock(20))
        self.assertFalse(product.has_stock(21))
        
        # Test exact availability
        self.assertEqual(product.get_available_stock(), 20)
        self.assertEqual(product.get_reserved_stock(), 3)
        self.assertEqual(product.get_total_stock(), 23)
        
        # Test availability after operations
        product.reserve_stock(10)
        self.assertEqual(product.get_available_stock(), 10)
        self.assertEqual(product.get_reserved_stock(), 13)
        
        self.assertTrue(product.has_stock(5))
        self.assertFalse(product.has_stock(15))

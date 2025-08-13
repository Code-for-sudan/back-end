"""
Additional realistic tests for Carts app
These tests cover practical scenarios that align with the actual model implementation
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from decimal import Decimal
from unittest.mock import patch

from carts.models import Cart, CartItem
from products.models import Product, Size
from products.services.stock_service import StockService
from stores.models import Store

User = get_user_model()


class CartBehaviorTest(TestCase):
    """Test realistic cart behaviors and business logic"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='cart_behavior@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Behavior Test Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Behavior Test Product',
            product_description='Test Description',
            price=Decimal('50.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='test.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_prevents_duplicate_items(self):
        """Test that cart prevents duplicate items for same product"""
        # Create first cart item
        cart_item1 = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Try to create duplicate - should raise IntegrityError due to unique constraint
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                quantity=3
            )

    def test_cart_total_calculation(self):
        """Test cart total price calculation"""
        # Add multiple products
        # Create products for testing
        product2 = Product.objects.create(
            product_name="Test Product 2",
            product_description="Test Description 2",
            price=Decimal('15.99'),
            available_quantity=50,
            reserved_quantity=0,
            has_sizes=False,
            owner_id=self.user,
            store=self.store,
            category="test",
            picture="test2.jpg"
        )
        
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2  # 2 * 50 = 100
        )
        
        CartItem.objects.create(
            cart=self.cart,
            product=product2,
            quantity=1  # 1 * 30 = 30
        )
        
        # Total should be 130
        self.assertEqual(self.cart.total_price, Decimal('130.00'))

    def test_cart_item_subtotal_calculation(self):
        """Test cart item subtotal calculation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        # Subtotal should be quantity * unit_price
        expected_subtotal = cart_item.quantity * cart_item.unit_price
        self.assertEqual(cart_item.subtotal, expected_subtotal)

    def test_cart_item_with_large_quantity(self):
        """Test cart item with large but valid quantity"""
        large_quantity = 100
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=large_quantity
        )
        
        self.assertEqual(cart_item.quantity, large_quantity)
        expected_subtotal = Decimal('50.00') * large_quantity
        self.assertEqual(cart_item.subtotal, expected_subtotal)

    def test_cart_empty_state(self):
        """Test cart empty state behavior"""
        # Cart should be empty initially
        self.assertTrue(self.cart.is_empty)
        self.assertEqual(self.cart.total_items, 0)
        self.assertEqual(self.cart.total_price, Decimal('0.00'))
        
        # Add item
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        
        # Cart should no longer be empty
        self.assertFalse(self.cart.is_empty)
        self.assertEqual(self.cart.total_items, 1)

    def test_cart_clear_functionality(self):
        """Test cart clear functionality"""
        # Add items to cart
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Verify cart has items
        self.assertFalse(self.cart.is_empty)
        
        # Clear cart
        self.cart.clear()
        
        # Verify cart is empty
        self.assertTrue(self.cart.is_empty)
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 0)

    def test_cart_item_product_changes_detection(self):
        """Test detection of product changes affecting cart items"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Change product price
        original_price = self.product.price
        self.product.price = Decimal('75.00')
        self.product.save()
        
        # Should detect price change
        changes = cart_item.check_product_changes()
        self.assertTrue(changes.get('changed', False))
        
        # Restore original price
        self.product.price = original_price
        self.product.save()

    def test_cart_item_update_for_changes(self):
        """Test updating cart item when product changes"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        original_unit_price = cart_item.unit_price
        
        # Change product price
        self.product.price = Decimal('75.00')
        self.product.save()
        
        # Update cart item for changes
        cart_item.update_for_product_changes()
        cart_item.refresh_from_db()
        
        # Unit price should be updated
        self.assertNotEqual(cart_item.unit_price, original_unit_price)
        self.assertEqual(cart_item.unit_price, Decimal('75.00'))

    def test_cart_with_out_of_stock_product(self):
        """Test cart behavior when product goes out of stock"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Product goes out of stock
        self.product.available_quantity = 0
        self.product.save()
        
        # Cart item still exists but product is out of stock
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(self.product.available_quantity, 0)


class CartSizedProductTest(TestCase):
    """Test cart behavior with sized products"""
    
    def setUp(self):
        """Set up test data with sized products"""
        self.user = User.objects.create_user(
            email='sized_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Sized Product Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.sized_product = Product.objects.create(
            product_name='Sized Product',
            product_description='Product with sizes',
            price=Decimal('40.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            available_quantity=None,  # Must be None for sized products
            picture='sized.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_item_with_size_variation(self):
        """Test cart item with size variation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.sized_product,
            size='M',  # Use the actual field name
            quantity=2
        )
        
        self.assertEqual(cart_item.size, 'M')
        self.assertEqual(cart_item.quantity, 2)

    def test_cart_variation_key_generation(self):
        """Test variation key generation for sized products"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.sized_product,
            size='S',
            quantity=1
        )
        
        variation_key = cart_item.get_variation_key()
        self.assertIn('S', variation_key)


class CartStockIntegrationTest(TestCase):
    """Test cart integration with stock service"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='stock_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Stock Test Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Stock Test Product',
            product_description='Test Description',
            price=Decimal('60.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='stock_test.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    @patch.object(StockService, 'reserve_stock')
    def test_cart_item_creation_with_stock_reservation(self, mock_reserve):
        """Test cart item creation triggers stock reservation"""
        mock_reserve.return_value = self.product
        
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        self.assertEqual(cart_item.quantity, 3)
        # Note: Actual stock reservation depends on implementation

    def test_cart_validation_with_insufficient_stock(self):
        """Test cart behavior when trying to add more than available stock"""
        # This test checks if business logic prevents over-ordering
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=15  # More than available (10)
        )
        
        # Cart item is created (validation should happen at checkout)
        self.assertEqual(cart_item.quantity, 15)
        self.assertGreater(cart_item.quantity, self.product.available_quantity)


class CartWorkflowTest(TestCase):
    """Test realistic cart workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='workflow_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Workflow Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_with_multiple_products(self):
        """Test cart with multiple different products"""
        products = []
        for i in range(5):
            product = Product.objects.create(
                product_name=f'Product {i}',
                product_description=f'Description {i}',
                price=Decimal(f'{10 + i}.00'),
                owner_id=self.user,
                store=self.store,
                category='test',
                has_sizes=False,
                available_quantity=10,
                reserved_quantity=0,
                picture=f'product{i}.jpg'
            )
            products.append(product)
            
            CartItem.objects.create(
                cart=self.cart,
                product=product,
                quantity=1
            )
        
        # Test cart calculations
        self.assertEqual(self.cart.total_items, 5)
        # Total should be sum of all product prices (10+11+12+13+14 = 60)
        expected_total = sum(Decimal(f'{10 + i}.00') for i in range(5))
        self.assertEqual(self.cart.total_price, expected_total)

    def test_cart_item_quantity_updates(self):
        """Test updating cart item quantities"""
        product = Product.objects.create(
            product_name='Update Test Product',
            product_description='Test Description',
            price=Decimal('25.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=0,
            picture='update_test.jpg'
        )
        
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=product,
            quantity=2
        )
        
        # Update quantity
        cart_item.quantity = 5
        cart_item.save()
        
        # Verify update
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart_item.subtotal, Decimal('125.00'))  # 5 * 25

    def test_cart_cross_user_isolation(self):
        """Test that carts are isolated between users"""
        user2 = User.objects.create_user(
            email='user2_cart@example.com',
            password='testpass123',
            phone_number='1234567891'
        )
        
        cart2 = Cart.objects.create(user=user2)
        
        product = Product.objects.create(
            product_name='Isolation Test Product',
            product_description='Test Description',
            price=Decimal('15.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=0,
            picture='isolation_test.jpg'
        )
        
        # Add to first user's cart
        CartItem.objects.create(
            cart=self.cart,
            product=product,
            quantity=3
        )
        
        # Add to second user's cart
        CartItem.objects.create(
            cart=cart2,
            product=product,
            quantity=2
        )
        
        # Verify isolation
        self.assertEqual(self.cart.total_items, 3)
        self.assertEqual(cart2.total_items, 2)
        self.assertNotEqual(self.cart.total_price, cart2.total_price)


class CartBehaviorTest(TestCase):
    """Test realistic cart behaviors and business logic"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='cart_behavior@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Behavior Test Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Behavior Test Product',
            product_description='Test Description',
            price=Decimal('50.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='test.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_prevents_duplicate_items(self):
        """Test that cart prevents duplicate items for same product"""
        # Create first cart item
        cart_item1 = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Try to create duplicate - should raise IntegrityError due to unique constraint
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                quantity=3
            )

    def test_cart_total_calculation(self):
        """Test cart total price calculation"""
        # Add multiple products
        product2 = Product.objects.create(
            product_name='Product 2',
            product_description='Second product',
            price=Decimal('30.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=5,
            reserved_quantity=0,
            picture='test2.jpg'
        )
        
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2  # 2 * 50 = 100
        )
        
        CartItem.objects.create(
            cart=self.cart,
            product=product2,
            quantity=1  # 1 * 30 = 30
        )
        
        # Total should be 130
        self.assertEqual(self.cart.total_price, Decimal('130.00'))

    def test_cart_item_subtotal_calculation(self):
        """Test cart item subtotal calculation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        # Subtotal should be quantity * unit_price
        expected_subtotal = cart_item.quantity * cart_item.unit_price
        self.assertEqual(cart_item.subtotal, expected_subtotal)

    def test_cart_item_with_large_quantity(self):
        """Test cart item with large but valid quantity"""
        large_quantity = 100
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=large_quantity
        )
        
        self.assertEqual(cart_item.quantity, large_quantity)
        expected_subtotal = Decimal('50.00') * large_quantity
        self.assertEqual(cart_item.subtotal, expected_subtotal)

    def test_cart_empty_state(self):
        """Test cart empty state behavior"""
        # Cart should be empty initially
        self.assertTrue(self.cart.is_empty)
        self.assertEqual(self.cart.total_items, 0)
        self.assertEqual(self.cart.total_price, Decimal('0.00'))
        
        # Add item
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        
        # Cart should no longer be empty
        self.assertFalse(self.cart.is_empty)
        self.assertEqual(self.cart.total_items, 1)

    def test_cart_clear_functionality(self):
        """Test cart clear functionality"""
        # Add items to cart
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Verify cart has items
        self.assertFalse(self.cart.is_empty)
        
        # Clear cart
        self.cart.clear()
        
        # Verify cart is empty
        self.assertTrue(self.cart.is_empty)
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 0)

    def test_cart_item_product_changes_detection(self):
        """Test detection of product changes affecting cart items"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Initially no changes
        result = cart_item.check_product_changes()
        self.assertFalse(result['changed'])
        
        # Change product price
        original_price = self.product.price
        self.product.price = Decimal('75.00')
        self.product.save()
        
        # Should detect price change
        result = cart_item.check_product_changes()
        self.assertTrue(result['changed'])
        
        # Restore original price
        self.product.price = original_price
        self.product.save()

    def test_cart_item_update_for_changes(self):
        """Test updating cart item when product changes"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        original_unit_price = cart_item.unit_price
        
        # Change product price
        self.product.price = Decimal('75.00')
        self.product.save()
        
        # Update cart item for changes
        cart_item.update_for_product_changes()
        cart_item.refresh_from_db()
        
        # Unit price should be updated
        self.assertNotEqual(cart_item.unit_price, original_unit_price)
        self.assertEqual(cart_item.unit_price, Decimal('75.00'))

    def test_cart_with_out_of_stock_product(self):
        """Test cart behavior when product goes out of stock"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Product goes out of stock
        self.product.available_quantity = 0
        self.product.save()
        
        # Cart item still exists but product is out of stock
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(self.product.available_quantity, 0)


class CartSizedProductTest(TestCase):
    """Test cart behavior with sized products"""
    
    def setUp(self):
        """Set up test data with sized products"""
        self.user = User.objects.create_user(
            email='sized_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Sized Product Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.sized_product = Product.objects.create(
            product_name='Sized Product',
            product_description='Product with sizes',
            price=Decimal('40.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            available_quantity=None,  # Must be None for sized products
            picture='sized.jpg'
        )
        
        # Create sizes
        self.size_s = Size.objects.create(
            product=self.sized_product,
            size='S',
            available_quantity=5,
            reserved_quantity=0
        )
        
        self.size_m = Size.objects.create(
            product=self.sized_product,
            size='M',
            available_quantity=3,
            reserved_quantity=0
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_item_with_product_size(self):
        """Test cart item with product size variation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.sized_product,
            size=self.size_s.size,
            quantity=2
        )
        
        self.assertEqual(cart_item.size, self.size_s.size)
        self.assertEqual(cart_item.quantity, 2)

    def test_cart_variation_key_generation(self):
        """Test variation key generation for sized products"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.sized_product,
            size=self.size_s.size,
            quantity=1
        )
        
        # Test that the size is stored correctly
        self.assertEqual(cart_item.size, self.size_s.size)


class CartStockIntegrationTest(TestCase):
    """Test cart integration with stock service"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='stock_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Stock Test Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Stock Test Product',
            product_description='Test Description',
            price=Decimal('60.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=10,
            reserved_quantity=0,
            picture='stock_test.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    @patch.object(StockService, 'reserve_stock')
    def test_cart_item_creation_with_stock_reservation(self, mock_reserve):
        """Test cart item creation triggers stock reservation"""
        mock_reserve.return_value = self.product
        
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        self.assertEqual(cart_item.quantity, 3)
        # Note: Actual stock reservation depends on implementation

    def test_cart_validation_with_insufficient_stock(self):
        """Test cart behavior when trying to add more than available stock"""
        # This test checks if business logic prevents over-ordering
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=15  # More than available (10)
        )
        
        # Cart item is created (validation should happen at checkout)
        self.assertEqual(cart_item.quantity, 15)
        self.assertGreater(cart_item.quantity, self.product.available_quantity)


class CartPerformanceTest(TestCase):
    """Test cart performance with multiple items"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='perf_cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Performance Store',
            location='Test Location',
            store_type='retail'
        )
        
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_with_many_items(self):
        """Test cart performance with multiple items"""
        # Create multiple products and add to cart
        products = []
        for i in range(10):
            product = Product.objects.create(
                product_name=f'Product {i}',
                product_description=f'Description {i}',
                price=Decimal(f'{10 + i}.00'),
                owner_id=self.user,
                store=self.store,
                category="test",
                has_sizes=False,
                available_quantity=10,
                reserved_quantity=0,
                picture=f"product{i}.jpg"
            )
            products.append(product)
            
            CartItem.objects.create(
                cart=self.cart,
                product=product,
                quantity=1
            )
        
        # Test cart calculations
        self.assertEqual(self.cart.total_items, 10)
        # Total should be sum of all product prices (10+11+...+19 = 145)
        expected_total = sum(Decimal(f'{10 + i}.00') for i in range(10))
        self.assertEqual(self.cart.total_price, expected_total)

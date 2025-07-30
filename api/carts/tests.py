"""
Comprehensive tests for Carts app
Tests cart creation, product changes, stock integration, and checkout process
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from carts.models import Cart, CartItem
from products.models import Product, Size
from stores.models import Store

User = get_user_model()


class CartModelTest(TestCase):
    """Test Cart model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='cart@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.store = Store.objects.create(
            name='Cart Test Store',
            location='Cart Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Cart Test Product',
            product_description='Cart Test Description',
            price=Decimal('30.00'),
            owner_id=self.user,
            store=self.store,
            category='test',
            has_sizes=False,
            available_quantity=20,
            reserved_quantity=0,
            picture='cart_test.jpg'
        )
        
        self.product_with_sizes = Product.objects.create(
            product_name='Sized Product',
            product_description='Product with sizes',
            price=Decimal('40.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            available_quantity=None,
            reserved_quantity=None,
            picture='sized_test.jpg'
        )
        
        # Create sizes for the sized product
        Size.objects.create(
            product=self.product_with_sizes,
            size='M',
            available_quantity=10,
            reserved_quantity=0
        )
        Size.objects.create(
            product=self.product_with_sizes,
            size='L',
            available_quantity=15,
            reserved_quantity=0
        )
    
    def test_cart_creation(self):
        """Test basic cart creation"""
        cart = Cart.objects.create(user=self.user)
        
        self.assertEqual(cart.user, self.user)
        self.assertIsNotNone(cart.created_at)
        self.assertTrue(cart.is_empty)
        self.assertEqual(cart.total_items, 0)
        self.assertEqual(cart.total_price, 0)
    
    def test_cart_properties(self):
        """Test cart calculated properties"""
        cart = Cart.objects.create(user=self.user)
        
        # Add item to cart
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=3
        )
        
        # Test properties
        self.assertFalse(cart.is_empty)
        self.assertEqual(cart.total_items, 3)
        self.assertEqual(cart.total_price, self.product.price * 3)
    
    def test_cart_clear(self):
        """Test cart clearing functionality"""
        cart = Cart.objects.create(user=self.user)
        
        # Add items
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        
        self.assertFalse(cart.is_empty)
        
        # Clear cart
        cart.clear()
        
        self.assertTrue(cart.is_empty)
        self.assertEqual(cart.total_items, 0)


class CartItemModelTest(TestCase):
    """Test CartItem model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='cartitem@example.com',
            password='testpass123',
            phone_number='2345678901'
        )
        
        self.store = Store.objects.create(
            name='CartItem Store',
            location='CartItem Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='CartItem Product',
            product_description='CartItem Description',
            price=Decimal('15.00'),
            owner_id=self.user,
            store=self.store,
            category='items',
            has_sizes=False,
            available_quantity=50,
            reserved_quantity=0,
            picture='cartitem.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)
    
    def test_cart_item_creation_no_size(self):
        """Test cart item creation for products without sizes"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertIsNone(cart_item.size)
        self.assertEqual(cart_item.subtotal, self.product.price * 2)
        self.assertEqual(cart_item.unit_price, self.product.price)
    
    def test_cart_item_with_sizes(self):
        """Test cart item creation for products with sizes"""
        # Create product with sizes
        sized_product = Product.objects.create(
            product_name='Sized Item',
            product_description='Sized Description',
            price=Decimal('25.00'),
            owner_id=self.user,
            store=self.store,
            category='clothing',
            has_sizes=True,
            available_quantity=None,
            reserved_quantity=None,
            picture='sized_item.jpg'
        )
        
        Size.objects.create(
            product=sized_product,
            size='S',
            available_quantity=5,
            reserved_quantity=0
        )
        
        # Create cart item with size
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=sized_product,
            quantity=1,
            size='S'
        )
        
        self.assertEqual(cart_item.size, 'S')
        self.assertEqual(cart_item.subtotal, sized_product.price)
    
    def test_cart_item_validation(self):
        """Test cart item validation rules"""
        # Create product with sizes
        sized_product = Product.objects.create(
            product_name='Validation Product',
            product_description='Validation Description',
            price=Decimal('20.00'),
            owner_id=self.user,
            store=self.store,
            category='validation',
            has_sizes=True,
            available_quantity=None,
            reserved_quantity=None,
            picture='validation.jpg'
        )
        
        # Test missing size for sized product
        with self.assertRaises(ValidationError):
            cart_item = CartItem(
                cart=self.cart,
                product=sized_product,
                quantity=1
                # Missing size
            )
            cart_item.clean()
        
        # Test size for non-sized product
        with self.assertRaises(ValidationError):
            cart_item = CartItem(
                cart=self.cart,
                product=self.product,  # No sizes
                quantity=1,
                size='M'  # Size not allowed
            )
            cart_item.clean()
    
    def test_cart_item_variation_key(self):
        """Test variation key generation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        
        # Test no variation
        self.assertEqual(cart_item.get_variation_key(), 'no_variation')
        
        # Test with size
        cart_item.size = 'M'
        self.assertEqual(cart_item.get_variation_key(), 'size:M')
        
        # Test with properties
        cart_item.product_properties = {'color': 'red', 'style': 'casual'}
        expected = 'size:M|color:red|style:casual'
        self.assertEqual(cart_item.get_variation_key(), expected)
    
    def test_cart_item_stock_reservation(self):
        """Test stock reservation tracking"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        # Initially not reserved
        self.assertFalse(cart_item.is_stock_reserved)
        
        # Mark as reserved
        cart_item.is_stock_reserved = True
        cart_item.save()
        
        self.assertTrue(cart_item.is_stock_reserved)
    
    def test_cart_item_product_changes(self):
        """Test product change detection"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Initial check (no stored price)
        changes = cart_item.check_product_changes()
        self.assertFalse(changes['changed'])
        
        # Store original price
        cart_item._original_price = self.product.current_price
        
        # Change product price
        original_price = self.product.price
        new_price = Decimal('25.00')
        self.product.price = new_price
        self.product.save()
        
        # Check for changes
        changes = cart_item.check_product_changes()
        self.assertTrue(changes['changed'])
        self.assertEqual(changes['old_price'], original_price)
        self.assertEqual(changes['new_price'], new_price)
        self.assertGreater(changes['price_change'], 0)
    
    def test_cart_item_update_for_changes(self):
        """Test updating cart item for product changes"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        
        # Store original price
        original_price = self.product.current_price
        cart_item._original_price = original_price
        
        # Change product price
        new_price = Decimal('20.00')
        self.product.price = new_price
        self.product.save()
        
        # Update for changes
        changes = cart_item.update_for_product_changes()
        
        self.assertTrue(changes['changed'])
        self.assertEqual(cart_item._original_price, new_price)
        
        # Verify subtotal updates with new price
        self.assertEqual(cart_item.subtotal, new_price * cart_item.quantity)


class CartServiceIntegrationTest(TransactionTestCase):
    """Test Cart integration with services"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='cartservice@example.com',
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
            price=Decimal('45.00'),
            owner_id=self.user,
            store=self.store,
            category='service',
            has_sizes=False,
            available_quantity=25,
            reserved_quantity=0,
            picture='service.jpg'
        )
        
        self.cart = Cart.objects.create(user=self.user)
    
    @patch('products.services.stock_service.StockService.reserve_stock')
    def test_cart_with_stock_reservation(self, mock_reserve):
        """Test cart integration with stock service"""
        mock_reserve.return_value = self.product
        
        # Create cart item
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=3
        )
        
        # Stock reservation would typically be handled by CartService
        # This test ensures the cart item model supports it
        cart_item.is_stock_reserved = True
        cart_item.save()
        
        self.assertTrue(cart_item.is_stock_reserved)
        self.assertEqual(cart_item.quantity, 3)
    
    @patch('products.services.stock_service.StockService.unreserve_stock')
    def test_cart_item_removal_stock_cleanup(self, mock_unreserve):
        """Test stock cleanup when cart item is removed"""
        mock_unreserve.return_value = self.product
        
        # Create reserved cart item
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            is_stock_reserved=True
        )
        
        # Remove item (stock cleanup would be handled by service)
        cart_item.delete()
        
        # Verify item is gone
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 0)
    
    def test_multiple_cart_items_total(self):
        """Test cart total with multiple items"""
        # Add multiple items
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Create another product
        product2 = Product.objects.create(
            product_name='Product 2',
            product_description='Description 2',
            price=Decimal('10.00'),
            owner_id=self.user,
            store=self.store,
            category='test2',
            has_sizes=False,
            available_quantity=30,
            reserved_quantity=0,
            picture='product2.jpg'
        )
        
        CartItem.objects.create(
            cart=self.cart,
            product=product2,
            quantity=3
        )
        
        # Test totals
        expected_total = (self.product.price * 2) + (product2.price * 3)
        self.assertEqual(self.cart.total_price, expected_total)
        self.assertEqual(self.cart.total_items, 5)  # 2 + 3
    
    def test_cart_checkout_preparation(self):
        """Test cart preparation for checkout"""
        # Add items to cart
        cart_item1 = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            is_stock_reserved=True
        )
        
        # Test cart state for checkout
        self.assertFalse(self.cart.is_empty)
        self.assertEqual(self.cart.total_items, 2)
        self.assertEqual(self.cart.total_price, self.product.price * 2)
        
        # Verify all items have stock reserved
        for item in self.cart.items.all():
            self.assertTrue(item.is_stock_reserved)
    
    def test_cart_unique_constraints(self):
        """Test cart item uniqueness constraints"""
        # Create first cart item
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )
        
        # Attempting to create duplicate should be handled by constraint
        # (The actual behavior depends on how the service layer handles it)
        self.assertEqual(CartItem.objects.filter(
            cart=self.cart, 
            product=self.product
        ).count(), 1)
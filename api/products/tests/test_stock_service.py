from django.test import TestCase
import pytest
from django.core.exceptions import ValidationError
from accounts.models import BusinessOwner, User
from stores.models import Store
from products.models import Product, Size
from products.services.stock_service import StockService


class TestStockService(TestCase):

    def setUp(self):
        """Create a product and a sized product for testing."""
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.store = Store.objects.create(
            name='Test Store',
            location='Test Location'
        )
        self.business_owner = BusinessOwner.objects.create(
            user=self.user,
            store=self.store
        )
        self.product = Product.objects.create(
            product_name="Test Product",
            product_description="No size product",
            price=20.00,
            available_quantity=10,
            reserved_quantity=0,
            has_sizes=False,
            category="General",
            owner_id=self.user,
            store=self.store,
        )

        self.sized_product = Product.objects.create(
            product_name="Sized Product",
            product_description="With sizes",
            price=30.00,
            has_sizes=True,
            category="Clothing",
            owner_id=self.user,
            store=self.store,
        )
        self.size_m = Size.objects.create(
            product=self.sized_product,
            size="M",
            available_quantity=5,
            reserved_quantity=0,
        )
        self.size_l = Size.objects.create(
            product=self.sized_product,
            size="L",
            available_quantity=2,
            reserved_quantity=0,
        )

    # -------------------------------
    # Reserve Stock (No Sizes)
    # -------------------------------
    def test_reserve_stock_no_sizes_success(self):
        result = StockService.reserve_stock(
            product_id=self.product.id, quantity=3)
        self.product.refresh_from_db()

        assert result == self.product
        assert self.product.available_quantity == 7
        assert self.product.reserved_quantity == 3

    def test_reserve_stock_no_sizes_insufficient_stock(self):
        with pytest.raises(ValidationError, match="Not enough stock available."):
            StockService.reserve_stock(product_id=self.product.id, quantity=20)

    # -------------------------------
    # Reserve Stock (With Sizes)
    # -------------------------------
    def test_reserve_stock_with_size_success(self):
        result = StockService.reserve_stock(
            product_id=self.sized_product.id,
            quantity=2,
            size="M",
        )
        self.size_m.refresh_from_db()
        assert result == self.size_m
        assert self.size_m.available_quantity == 3
        assert self.size_m.reserved_quantity == 2

    def test_reserve_stock_with_size_not_enough_quantity(self):
        with pytest.raises(ValidationError, match="Not enough stock available for this size."):
            StockService.reserve_stock(
                product_id=self.sized_product.id,
                quantity=10,
                size="M",
            )

    def test_reserve_stock_with_size_missing_size_param(self):
        with pytest.raises(ValidationError, match="Size must be specified for products with sizes."):
            StockService.reserve_stock(
                product_id=self.sized_product.id,
                quantity=2,
            )

    # -------------------------------
    # Unreserve Stock (No Sizes)
    # -------------------------------
    def test_unreserve_stock_no_sizes_returned(self):
        StockService.reserve_stock(product_id=self.product.id, quantity=4)
        StockService.unreserve_stock(product_id=self.product.id, quantity=2)

        self.product.refresh_from_db()
        assert self.product.available_quantity == 8
        assert self.product.reserved_quantity == 2

    def test_unreserve_stock_no_sizes_not_returned(self):
        StockService.reserve_stock(product_id=self.product.id, quantity=4)
        StockService.unreserve_stock(
            product_id=self.product.id, quantity=2, returned=False)

        self.product.refresh_from_db()
        assert self.product.available_quantity == 6
        assert self.product.reserved_quantity == 2

    def test_unreserve_stock_no_sizes_negative_reserved(self):
        # Reserved 2, unreserve 5 -> reserved must not go below 0
        StockService.reserve_stock(product_id=self.product.id, quantity=2)
        StockService.unreserve_stock(product_id=self.product.id, quantity=5)

        self.product.refresh_from_db()
        assert self.product.available_quantity == 10 - 2 + 5  # fully returned
        assert self.product.reserved_quantity == 0

    # -------------------------------
    # Unreserve Stock (With Sizes)
    # -------------------------------
    def test_unreserve_stock_with_sizes_returned(self):
        StockService.reserve_stock(
            product_id=self.sized_product.id, quantity=2, size="L")
        StockService.unreserve_stock(
            product_id=self.sized_product.id, quantity=1, size="L")

        self.size_l.refresh_from_db()
        assert self.size_l.available_quantity == 1
        assert self.size_l.reserved_quantity == 1

    def test_unreserve_stock_with_sizes_not_returned(self):
        StockService.reserve_stock(
            product_id=self.sized_product.id, quantity=2, size="L")
        StockService.unreserve_stock(
            product_id=self.sized_product.id,
            quantity=1,
            size="L",
            returned=False,
        )

        self.size_l.refresh_from_db()
        assert self.size_l.available_quantity == 0
        assert self.size_l.reserved_quantity == 1

    def test_unreserve_stock_with_sizes_negative_reserved(self):
        StockService.reserve_stock(
            product_id=self.sized_product.id, quantity=2, size="M")
        StockService.unreserve_stock(
            product_id=self.sized_product.id, quantity=5, size="M")

        self.size_m.refresh_from_db()
        assert self.size_m.available_quantity == 5 - 2 + 5  # fully returned
        assert self.size_m.reserved_quantity == 0

    def test_unreserve_stock_with_sizes_missing_size_param(self):
        with pytest.raises(ValidationError, match="Size must be specified for products with sizes."):
            StockService.unreserve_stock(
                product_id=self.sized_product.id,
                quantity=2,
            )

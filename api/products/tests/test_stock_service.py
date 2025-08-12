from django.test import TestCase
import pytest
from django.core.exceptions import ValidationError
from .test_helpers import TestHelpers
from products.models import Size
from products.services.stock_service import StockService


class TestStockService(TestCase):
    no_size_quantity = 10
    s_quantity = 5
    m_quantity = 2
    l_quantity = 4

    def setUp(self):
        """Create a product and a sized product for testing."""
        self.user, self.store, self.business_owner = TestHelpers.create_seller()
        self.product_without_size = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                available_quantity=TestStockService.no_size_quantity),
            self.user,
            self.store
        )

        self.product_with_size = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=[
                    {"size": "S", "available_quantity": TestStockService.s_quantity},
                    {"size": "M", "available_quantity": TestStockService.m_quantity},
                    {"size": "L", "available_quantity": TestStockService.l_quantity},
                ]
            ),
            self.user,
            self.store
        )
    # -------------------------------
    # Reserve Stock (No Sizes)
    # -------------------------------

    def test_reserve_stock_no_sizes_success(self):
        result = StockService.reserve_stock(
            product_id=self.product_without_size.id, quantity=3)
        self.product_without_size.refresh_from_db()

        self.assertEqual(result, self.product_without_size)
        self.assertEqual(self.product_without_size.available_quantity,
                         TestStockService.no_size_quantity - 3)
        self.assertEqual(self.product_without_size.reserved_quantity, 3)

    def test_reserve_stock_no_sizes_insufficient_stock(self):
        with pytest.raises(ValidationError, match="Not enough stock available."):
            StockService.reserve_stock(
                product_id=self.product_without_size.id, quantity=100)

    # -------------------------------
    # Reserve Stock (With Sizes)
    # -------------------------------
    def test_reserve_stock_with_size_success(self):
        result = StockService.reserve_stock(
            product_id=self.product_with_size.id,
            quantity=2,
            size="M",
        )
        size_m = Size.objects.filter(
            size="M", product=self.product_with_size).first()
        self.assertEqual(result, size_m)
        self.assertEqual(size_m.available_quantity,
                         TestStockService.m_quantity - 2)
        self.assertEqual(size_m.reserved_quantity, 2)

    def test_reserve_stock_with_size_not_enough_quantity(self):
        with pytest.raises(ValidationError, match="Not enough stock available for this size."):
            StockService.reserve_stock(
                product_id=self.product_with_size.id,
                quantity=100,
                size="M",
            )

    def test_reserve_stock_with_size_missing_size_param(self):
        with pytest.raises(ValidationError, match="Size must be specified for products with sizes."):
            StockService.reserve_stock(
                product_id=self.product_with_size.id,
                quantity=2,
            )

    # -------------------------------
    # Unreserve Stock (No Sizes)
    # -------------------------------
    def test_unreserve_stock_no_sizes_returned(self):
        StockService.reserve_stock(
            product_id=self.product_without_size.id, quantity=4)
        StockService.unreserve_stock(
            product_id=self.product_without_size.id, quantity=2)

        self.product_without_size.refresh_from_db()
        self.assertEqual(self.product_without_size.available_quantity,
                         TestStockService.no_size_quantity - 4 + 2)
        self.assertEqual(self.product_without_size.reserved_quantity, 4 - 2)

    def test_unreserve_stock_no_sizes_not_returned(self):
        StockService.reserve_stock(
            product_id=self.product_without_size.id, quantity=4)
        StockService.unreserve_stock(
            product_id=self.product_without_size.id,
            quantity=2,
            returned=False)

        self.product_without_size.refresh_from_db()
        self.assertEqual(self.product_without_size.available_quantity,
                         TestStockService.no_size_quantity - 4)
        self.assertEqual(self.product_without_size.reserved_quantity, 4 - 2)

    def test_unreserve_stock_no_sizes_negative_reserved(self):
        # Reserved 2, unreserve 5 -> reserved must not go below 0
        StockService.reserve_stock(
            product_id=self.product_without_size.id, quantity=2)
        StockService.unreserve_stock(
            product_id=self.product_without_size.id, quantity=5)

        self.product_without_size.refresh_from_db()
        self.assertEqual(
            self.product_without_size.available_quantity,
            TestStockService.no_size_quantity - 2 + 5)  # fully returned
        self.assertEqual(self.product_without_size.reserved_quantity, 0)

    # -------------------------------
    # Unreserve Stock (With Sizes)
    # -------------------------------
    def test_unreserve_stock_with_sizes_returned(self):
        StockService.reserve_stock(
            product_id=self.product_with_size.id, quantity=2, size="L")
        StockService.unreserve_stock(
            product_id=self.product_with_size.id, quantity=1, size="L")
        size_l = Size.objects.filter(
            product=self.product_with_size, size='L').first()
        self.assertEqual(size_l.available_quantity,
                         TestStockService.l_quantity - 2 + 1)
        self.assertEqual(size_l.reserved_quantity, 2 - 1)

    def test_unreserve_stock_with_sizes_not_returned(self):
        StockService.reserve_stock(
            product_id=self.product_with_size.id, quantity=2, size="L")
        StockService.unreserve_stock(
            product_id=self.product_with_size.id,
            quantity=1,
            size="L",
            returned=False,
        )

        size_l = Size.objects.filter(
            product=self.product_with_size, size='L').first()
        self.assertEqual(size_l.available_quantity,
                         TestStockService.l_quantity - 2)
        self.assertEqual(size_l.reserved_quantity, 2 - 1)

    def test_unreserve_stock_with_sizes_negative_reserved(self):
        StockService.reserve_stock(
            product_id=self.product_with_size.id, quantity=2, size="M")
        StockService.unreserve_stock(
            product_id=self.product_with_size.id, quantity=5, size="M")
        size_m = Size.objects.filter(
            product=self.product_with_size, size='M').first()
        self.assertEqual(size_m.available_quantity,
                         TestStockService.m_quantity - 2 + 5)  # fully returned
        self.assertEqual(size_m.reserved_quantity, 0)

    def test_unreserve_stock_with_sizes_missing_size_param(self):
        with pytest.raises(ValidationError, match="Size must be specified for products with sizes."):
            StockService.unreserve_stock(
                product_id=self.product_with_size.id,
                quantity=2,
            )

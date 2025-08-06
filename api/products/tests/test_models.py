import logging
from django.test import TestCase
from products.models import Size
from products.tests.test_helpers import TestHelpers

logger = logging.getLogger('products_tests')


class OfferTest(TestCase):
    def setUp(self):
        self.user, self.store, self.buisness_owner = TestHelpers.create_seller()
        return super().setUp()

    def test_active_offer(self):
        data = TestHelpers.get_valid_product_data_without_sizes(price=10)
        data = TestHelpers.add_offer_to_product_data(
            data,
            *TestHelpers.get_active_offer_dates(),
            5
        )
        product = TestHelpers.creat_product(data, self.user, self.store)
        self.assertIsNotNone(product.offer)
        self.assertTrue(product.offer.is_active)
        self.assertEqual(product.current_price, 5)

    def test_expired_offer(self):
        data = TestHelpers.get_valid_product_data_without_sizes(price=10)
        data = TestHelpers.add_offer_to_product_data(
            data,
            *TestHelpers.get_expired_offer_dates(),
            5
        )
        product = TestHelpers.creat_product(data, self.user, self.store)
        self.assertIsNotNone(product.offer)
        self.assertFalse(product.offer.is_active)
        self.assertEqual(product.current_price, 10)

    def test_future_offer(self):
        data = TestHelpers.get_valid_product_data_without_sizes(price=10)
        data = TestHelpers.add_offer_to_product_data(
            data,
            *TestHelpers.get_future_offer_dates(),
            5
        )
        product = TestHelpers.creat_product(data, self.user, self.store)
        self.assertIsNotNone(product.offer)
        self.assertFalse(product.offer.is_active)
        self.assertEqual(product.current_price, 10)


class ProductSizeSoftDeleteTests(TestCase):
    """
    Test suite for soft deletion and restoration behavior of Product and Size models.
    Covers:
        - Product soft deletion cascading to its sizes.
        - Product restoration restoring its sizes.
        - Size individual soft deletion
    """

    def setUp(self):
        self.user, self.store, self.buisness_owner = TestHelpers.create_seller()
        self.product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=[
                    {"size": "S", "available_quantity": 19},
                    {"size": "M", "available_quantity": 19},
                    {"size": "L", "available_quantity": 19},
                ]
            ),
            self.user,
            self.store
        )

    def test_product_soft_delete_cascades_to_sizes(self):
        """Soft deleting a product should soft delete all its sizes."""
        self.product.delete()

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted,
                        "Product should be soft-deleted.")

        sizes = Size.all_objects.filter(product=self.product)
        for size in sizes:
            self.assertTrue(size.is_deleted,
                            f"Size {size.size} should be soft-deleted.")
            self.assertIsNotNone(
                size.deleted_at, "Size deleted_at should be set.")

        logger.info("Product soft delete cascade test passed.")

    def test_individual_size_soft_delete_and_restore(self):
        """Soft deleting and restoring an individual size should work correctly via product.sizes."""
        size = self.product.sizes.get(size="S")
        size.delete()
        size.refresh_from_db()

        self.assertTrue(size.is_deleted, "Size should be soft-deleted.")
        self.assertIsNotNone(size.deleted_at, "deleted_at should be set.")

        size.restore()
        size.refresh_from_db()
        self.assertFalse(size.is_deleted, "Size should be restored.")
        self.assertIsNone(
            size.deleted_at, "deleted_at should be None after restore.")

        logger.info("Individual size soft delete/restore test passed.")

    def test_products_sizes_only_returns_non_deleted(self):
        """`product.sizes.all()` should only return non-deleted sizes."""
        size_to_delete = self.product.sizes.get(size="S")
        size_to_delete.delete()

        sizes = self.product.sizes.all()
        self.assertEqual(sizes.count(), 2,
                         "Only non-deleted sizes should be returned.")
        returned_sizes = [s.size for s in sizes]
        self.assertNotIn("S", returned_sizes, "Size 'S' should be excluded.")
        self.assertIn("M", returned_sizes)
        self.assertIn("L", returned_sizes)

        logger.info("product.sizes.all() excludes deleted sizes test passed.")

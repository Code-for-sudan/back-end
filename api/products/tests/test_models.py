import logging
from django.test import TestCase
from products.models import Product, Size
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


class ProductAvailabilityTests(TestCase):
    def setUp(self):
        self.user, self.store, self.buisness_owner = TestHelpers.create_seller()
        self.available_product_with_sizes = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=TestHelpers.get_available_sizes()
            ),
            self.user,
            self.store,
        )
        self.unavailable_product_with_sizes = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=TestHelpers.get_unavailable_sizes()
            ),
            self.user,
            self.store,
        )
        self.paritally_available_product_with_sizes = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=TestHelpers.get_paritally_available_sizes()
            ),
            self.user,
            self.store,
        )
        self.available_product_without_sizes = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                available_quantity=10),
            self.user,
            self.store,
        )
        self.unavailable_product_without_sizes = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                available_quantity=0),
            self.user,
            self.store,
        )
        self.available_product_with_deleted_size = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=TestHelpers.get_available_sizes()
            ),
            self.user,
            self.store
        )
        deleted_size = self.available_product_with_deleted_size.sizes.first()
        deleted_size.available_quantity = 0
        deleted_size.save()
        deleted_size.delete()
        return super().setUp()

    def test_availability_property(self):
        self.assertEqual(
            self.available_product_with_sizes.availability, "available")
        self.assertEqual(
            self.unavailable_product_with_sizes.availability, "unavailable")
        self.assertEqual(
            self.paritally_available_product_with_sizes.availability, "partially_available")
        self.assertEqual(
            self.available_product_without_sizes.availability, "available")
        self.assertEqual(
            self.unavailable_product_without_sizes.availability, "unavailable")
        self.assertEqual(
            self.available_product_with_deleted_size.availability, "available")

    def test_available_filter(self):
        available = Product.objects.available()
        self.assertIn(self.available_product_with_sizes, available)
        self.assertIn(self.available_product_without_sizes, available)
        self.assertIn(self.available_product_with_deleted_size, available)
        self.assertNotIn(self.unavailable_product_with_sizes, available)
        self.assertNotIn(
            self.paritally_available_product_with_sizes, available)
        self.assertNotIn(self.unavailable_product_without_sizes, available)

    def test_unavailable_filter(self):
        unavailable = Product.objects.unavailable()
        self.assertIn(self.unavailable_product_with_sizes, unavailable)
        self.assertIn(self.unavailable_product_without_sizes, unavailable)
        self.assertNotIn(self.available_product_with_deleted_size, unavailable)
        self.assertNotIn(self.available_product_with_sizes, unavailable)
        self.assertNotIn(self.available_product_without_sizes, unavailable)
        self.assertNotIn(
            self.paritally_available_product_with_sizes, unavailable)

    def test_partially_available_filter(self):
        partial = Product.objects.partially_available()
        self.assertIn(self.paritally_available_product_with_sizes, partial)
        self.assertNotIn(self.available_product_with_sizes, partial)
        self.assertNotIn(self.available_product_with_deleted_size, partial)
        self.assertNotIn(self.unavailable_product_with_sizes, partial)
        self.assertNotIn(self.unavailable_product_without_sizes, partial)
        self.assertNotIn(self.available_product_without_sizes, partial)

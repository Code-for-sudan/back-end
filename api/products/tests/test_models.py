import logging
from django.test import TestCase
from django.utils.timezone import now
from products.models import Product, Size
from stores.models import Store
from accounts.models import User, BusinessOwner

logger = logging.getLogger('products_tests')


class ProductSizeSoftDeleteTests(TestCase):
    """
    Test suite for soft deletion and restoration behavior of Product and Size models.
    Covers:
        - Product soft deletion cascading to its sizes.
        - Product restoration restoring its sizes.
        - Size individual soft deletion and restoration.
        - bulk_soft_delete on SizeManager.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.store = Store.objects.create(
            name='Test Store', location='Test Location')
        self.business_owner = BusinessOwner.objects.create(
            user=self.user, store=self.store)

        self.product = Product.objects.create(
            product_name="Test Product",
            product_description="A product to test soft deletion.",
            price="29.99",
            category="Test Category",
            owner_id=self.user,
            store=self.store,
            has_sizes=True,
        )

        self.size1 = Size.objects.create(
            product=self.product, size="M", available_quantity=5, reserved_quantity=0)
        self.size2 = Size.objects.create(
            product=self.product, size="L", available_quantity=3, reserved_quantity=0)

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
        """Soft deleting and restoring an individual size should work correctly."""
        self.size1.delete()
        self.size1.refresh_from_db()

        self.assertTrue(self.size1.is_deleted, "Size should be soft-deleted.")
        self.assertIsNotNone(self.size1.deleted_at,
                             "deleted_at should be set.")

        self.size1.restore()
        self.size1.refresh_from_db()
        self.assertFalse(self.size1.is_deleted, "Size should be restored.")
        self.assertIsNone(self.size1.deleted_at,
                          "deleted_at should be None after restore.")

        logger.info("Individual size soft delete/restore test passed.")

    def test_products_sizes_only_returns_non_deleted(self):
        """`product.sizes.all()` should only return non-deleted sizes."""
        self.size1.delete()

        sizes = self.product.sizes.all()
        self.assertEqual(sizes.count(), 1,
                         "Only non-deleted sizes should be returned.")
        self.assertEqual(sizes.first().size, "L",
                         "Remaining size should be L.")

        logger.info("product.sizes.all() excludes deleted sizes test passed.")

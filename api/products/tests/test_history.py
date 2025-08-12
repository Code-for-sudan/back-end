from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from accounts.models import BusinessOwner, User
from products.models import Product, ProductHistory, Store
from django.utils.timezone import now, timedelta
from products.services.history_service import get_product_history_as_of


class ProductHistoryTests(TestCase):

    def setUp(self):
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
            product_description="Test Description",
            price=100.00,
            color="Red",
            brand="TestBrand",
            available_quantity=10,
            reserved_quantity=2,
            has_sizes=False,
            owner_id=self.user,
            store=self.store,
            category="TestCategory",
            properties={"key": "value"},
            picture=self.create_test_image(),
        )

    def create_test_image(self):
        """Helper to create a new SimpleUploadedFile for image field."""
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
            content_type='image/jpeg'
        )

    def test_history_created_on_product_create(self):
        """Test that creating a product generates a ProductHistory entry."""
        history = ProductHistory.objects.filter(product=self.product)
        self.assertTrue(history.exists(),
                        "ProductHistory should be created on product creation")
        self.assertEqual(history.first().product_name, "Test Product")

    def test_history_created_on_product_update(self):
        """Test that updating a product creates a new ProductHistory snapshot if changed."""
        initial_count = ProductHistory.objects.filter(
            product=self.product).count()
        self.product.product_name = "Updated Product"
        self.product.save()

        history_count = ProductHistory.objects.filter(
            product=self.product).count()
        self.assertEqual(history_count, initial_count + 1,
                         "History count should increment after update")

        latest_history = ProductHistory.objects.filter(
            product=self.product).order_by("-recorded_at").first()
        self.assertEqual(latest_history.product_name, "Updated Product")

    def test_history_created_on_soft_delete(self):
        """Test that soft-deleting a product creates a ProductHistory snapshot."""
        self.product.is_deleted = True
        self.product.save()

        latest_history = ProductHistory.objects.filter(
            product=self.product).order_by("-recorded_at").first()
        self.assertTrue(latest_history.is_deleted,
                        "Latest history should reflect soft delete")

    def test_has_product_changed(self):
        """Test the has_product_changed logic."""
        history = ProductHistory.objects.filter(product=self.product).first()

        # Initially, no change should be detected
        self.assertFalse(history.has_product_changed(),
                         "No changes should be detected initially")

        # 1. Change product price (tracked)
        self.product.price = 200.00
        self.product.save()
        self.assertTrue(history.has_product_changed(),
                        "Price change should be detected")

        # Refresh history (optional, for clarity)
        history = ProductHistory.objects.filter(
            product=self.product).order_by("-recorded_at").first()

        # 2. Change available_quantity (NOT tracked)
        self.product.available_quantity = 100
        self.assertFalse(history.has_product_changed(),
                         "Quantity change should not be detected")

        # 3. Add a new size (tracked)
        self.product.has_sizes = True
        self.product.available_quantity = None
        self.product.reserved_quantity = None
        self.product.save()
        self.product.sizes.create(
            size="M", available_quantity=5, reserved_quantity=0)
        self.assertTrue(history.has_product_changed(),
                        "Adding a new size should be detected")

        # Update history to reflect new snapshot
        history = ProductHistory.create_from_product(self.product)

        # 4. Change size quantity (NOT tracked)
        size_obj = self.product.sizes.first()
        size_obj.available_quantity = 999
        size_obj.save()
        self.assertFalse(history.has_product_changed(),
                         "Changing size quantity should not be detected")

        # 5. Change owner name (tracked)
        self.user.first_name = "Changed"
        self.user.save()
        self.assertTrue(history.has_product_changed(),
                        "Owner name change should be detected")


class ProductHistoryAsOfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner2@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.store = Store.objects.create(
            name='History Store', location='Somewhere')
        BusinessOwner.objects.create(user=self.user, store=self.store)
        self.product = Product.objects.create(
            product_name="History Product",
            product_description="Description",
            price=100.00,
            color="Blue",
            brand="HistoryBrand",
            available_quantity=10,
            reserved_quantity=1,
            has_sizes=False,
            owner_id=self.user,
            store=self.store,
            category="TestCategory",
            properties={"key": "value"},
            picture=self.create_test_image()
        )
        # Create initial history snapshot
        self.history1 = ProductHistory.objects.filter(
            product=self.product).order_by("recorded_at").first()
        self.history1.recorded_at = now() - timedelta(days=3)
        self.history1.save()

        self.product.price = 150.00
        self.product.save()

        self.history2 = ProductHistory.objects.filter(
            product=self.product).order_by("-recorded_at").first()
        self.history2.recorded_at = now() - timedelta(days=1)
        self.history2.save()

    def create_test_image(self):
        return SimpleUploadedFile(
            name='test_image2.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
            content_type='image/jpeg'
        )

    def test_get_product_history_as_of_before_any_history(self):
        """Should return None if no history exists before the given date."""
        date = now() - timedelta(days=10)
        history = get_product_history_as_of(self.product, date)
        self.assertIsNone(
            history, "Expected None when no history exists before date")

    def test_get_product_history_as_of_exact_date(self):
        """Should return history snapshot if it matches the exact date."""
        history = get_product_history_as_of(
            self.product, self.history1.recorded_at)
        self.assertEqual(history.id, self.history1.id,
                         "Expected exact history match")

    def test_get_product_history_as_of_latest_before_date(self):
        """Should return the latest history snapshot before the given date."""
        date = now()  # after both snapshots
        history = get_product_history_as_of(self.product, date)
        self.assertEqual(history.id, self.history2.id,
                         "Expected latest snapshot before given date")

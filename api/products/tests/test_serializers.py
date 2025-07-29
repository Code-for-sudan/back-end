from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import BusinessOwner, User
from stores.models import Store
from products.models import Product, Size
from products.serializers import ProductSerializer
import logging


logger = logging.getLogger('products_tests')


class ProductSerializerTests(TestCase):
    """
    Test suite for the ProductSerializer.
    Tests:
        - test_serializer_with_valid_data: Checks that the serializer is valid with all required and optional fields.
        - test_serializer_missing_required_field: Ensures the serializer is invalid if a required field is missing.
        - test_serializer_optional_fields: Confirms that omitting optional fields does not cause validation to fail.
        - test_create_product: Verifies that a Product instance can be created with valid data and related objects.
    """

    def create_test_image(self):
        """Helper to create a new SimpleUploadedFile for image field."""
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
            content_type='image/jpeg'
        )

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
        self.valid_data_without_size = {
            'product_name': 'Test Product',
            'product_description': 'A great product.',
            'price': '19.99',
            'category': 'Electronics',
            'picture': self.create_test_image(),
            'color': 'Red',
            'has_sizes': False,
            'available_quantity': 10,
        }
        self.valid_data_with_size = {
            'product_name': 'Test Product',
            'product_description': 'A great product.',
            'price': '19.99',
            'category': 'Electronics',
            'picture': self.create_test_image(),
            'color': 'Red',
            'has_sizes': True,
            'sizes': [{"size": "M", "available_quantity": 5}, {"size": "L", "available_quantity": 3}],
        }

    def test_serializer_with_valid_data_without_size(self):
        data = self.valid_data_without_size.copy()
        data['picture'] = self.create_test_image()
        serializer = ProductSerializer(data=data)
        logger.info(f"Validating serializer with valid data: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        logger.info(
            "Serializer is valid with all required and optional fields.")

    def test_serializer_with_valid_data_with_size(self):
        data = self.valid_data_with_size.copy()
        data['picture'] = self.create_test_image()
        serializer = ProductSerializer(data=data)
        logger.info(f"Validating serializer with valid data: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        logger.info(
            "Serializer is valid with all required and optional fields.")

    def test_serializer_missing_required_field(self):
        data = self.valid_data_without_size.copy()
        data.pop('product_name')
        data['picture'] = self.create_test_image()
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with missing required field 'product_name': {data}")
        self.assertFalse(serializer.is_valid())
        logger.info(f"Serializer errors: {serializer.errors}")
        self.assertIn('product_name', serializer.errors)

    def test_serializer_optional_fields(self):
        data = self.valid_data_without_size.copy()
        data.pop('color')
        data['picture'] = self.create_test_image()
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with optional fields omitted: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        logger.info("Serializer is valid without optional fields.")

    def test_create_product(self):
        data = self.valid_data_without_size.copy()
        data['picture'] = self.create_test_image()
        serializer = ProductSerializer(data=data)
        logger.info(f"Creating product with data: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)
        logger.info(f"Product created: {product}")
        self.assertEqual(product.product_name,
                         self.valid_data_without_size['product_name'])
        self.assertEqual(product.owner_id, self.user)
        self.assertEqual(product.store, self.store)
        self.assertTrue(product.picture.name.startswith('products/test_image'))


class ProductSerializerSizeTests(TestCase):
    def setUp(self):
        # Create a test user and store
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

        # Create a product
        self.product = Product.objects.create(
            product_name='T-Shirt',
            product_description='Basic T-shirt',
            price='19.99',
            category='Clothing',
            owner_id=self.user,
            store=self.store,
            has_sizes=True,
        )

        # Create initial sizes
        Size.objects.create(product=self.product, size='S',
                            available_quantity=10, reserved_quantity=2)
        Size.objects.create(product=self.product, size='M',
                            available_quantity=5, reserved_quantity=1)

    def test_update_existing_size_quantity(self):
        """Updating a product with an existing size should update its available_quantity."""
        serializer = ProductSerializer(
            instance=self.product,
            data={
                'sizes': [
                    # Update existing size
                    {'size': 'S', 'available_quantity': 20},
                ]
            },
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        updated_size = Size.objects.get(product=self.product, size='S')
        self.assertEqual(updated_size.available_quantity, 20)
        logger.info(
            f"Updated size S available_quantity to {updated_size.available_quantity}")

    def test_create_new_size(self):
        """Updating a product with a new size should create the new size with reserved_quantity=0."""
        serializer = ProductSerializer(
            instance=self.product,
            data={
                'sizes': [
                    {'size': 'L', 'available_quantity': 15},  # New size
                ]
            },
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.assertTrue(Size.objects.filter(
            product=self.product, size='L').exists())
        new_size = Size.objects.get(product=self.product, size='L')
        self.assertEqual(new_size.reserved_quantity, 0)
        logger.info(
            f"Created new size L with reserved_quantity={new_size.reserved_quantity}")

    def test_mixed_update_and_create_sizes(self):
        """Updating with a mix of existing and new sizes should update and create correctly."""
        serializer = ProductSerializer(
            instance=self.product,
            data={
                'sizes': [
                    {'size': 'M', 'available_quantity': 12},  # Update existing
                    {'size': 'XL', 'available_quantity': 7},  # New size
                ]
            },
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        updated_size = Size.objects.get(product=self.product, size='M')
        new_size = Size.objects.get(product=self.product, size='XL')

        self.assertEqual(updated_size.available_quantity, 12)
        self.assertEqual(new_size.available_quantity, 7)
        logger.info(f"Updated size M and created size XL")

    def test_missing_sizes_are_unchanged(self):
        """
        Sizes not included in the update payload should remain unchanged.
        """
        serializer = ProductSerializer(
            instance=self.product,
            data={
                'sizes': [
                    {'size': 'M', 'available_quantity': 20},  # Only update M
                ]
            },
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        # Size S should remain unchanged
        size_s = Size.objects.get(product=self.product, size='S')
        self.assertEqual(size_s.available_quantity, 10)
        self.assertEqual(size_s.reserved_quantity, 2)

        updated_size_m = Size.objects.get(product=self.product, size='M')
        self.assertEqual(updated_size_m.available_quantity, 20)
        logger.info(f"Size S unchanged, size M updated")

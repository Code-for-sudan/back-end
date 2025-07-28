from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from stores.models import Store
from products.models import Product
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

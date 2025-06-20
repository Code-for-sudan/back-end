from django.test import TestCase
from accounts.models import User
from stores.models import Store
from ..models import Product
from ..serializers import ProductSerializer

class ProductSerializerTests(TestCase):
    """
    Test suite for the ProductSerializer.
    Tests:
        - test_serializer_with_valid_data: Checks that the serializer is valid with all required and optional fields.
        - test_serializer_missing_required_field: Ensures the serializer is invalid if a required field is missing.
        - test_serializer_optional_fields: Confirms that omitting optional fields does not cause validation to fail.
        - test_create_product: Verifies that a Product instance can be created with valid data and related objects.
    """

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
        self.valid_data = {
            'product_name': 'Test Product',
            'product_description': 'A great product.',
            'price': '19.99',
            'category': 'Electronics',
            'picture': 'https://example.com/image.jpg',
            'quantity': 10,
            'color': 'Red',
            'size': 'M',
        }

    def test_serializer_with_valid_data(self):
        serializer = ProductSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_missing_required_field(self):
        data = self.valid_data.copy()
        data.pop('product_name')
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_name', serializer.errors)

    def test_serializer_optional_fields(self):
        data = self.valid_data.copy()
        data.pop('color')
        data.pop('size')
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_product(self):
        serializer = ProductSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Set owner and store in the save() call, since they're not in the serializer input
        product = serializer.save(owner_id=self.user, store=self.store)
        self.assertEqual(product.product_name, self.valid_data['product_name'])
        self.assertEqual(product.owner_id, self.user)
        self.assertEqual(product.store, self.store)

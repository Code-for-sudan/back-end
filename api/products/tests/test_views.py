import logging
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from stores.models import Store
from products.models import Product
from accounts.models import BusinessOwner


logger = logging.getLogger('products_tests')


class ProductViewSetTests(APITestCase):
    """
    Comprehensive test suite for ProductViewSet.

    This test case covers:
        - Creating a product with valid data and authentication, expecting success.
        - Creating a product with missing required fields, expecting validation failure.
        - Creating a product when the user has no associated store, expecting failure.
        - Creating a product when unauthenticated, expecting failure.
        - Retrieving a single product by ID.
        - Updating a product's fields (partial update).
        - Deleting a product by ID.
        - Listing all products for the authenticated user.
    Each test logs the response using the 'products_tests' logger for traceability.
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
        self.business_owner = BusinessOwner.objects.create(
            user=self.user,
            store=self.store
        )
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse('product-list')
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

    def test_create_product(self):
        data = self.valid_data_without_size.copy()
        data['picture'] = self.create_test_image()
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'],
                         "Product created successfully")
        self.assertEqual(response.data['product']['product_name'],
                         self.valid_data_without_size['product_name'])

    def test_retrieve_product(self):
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        url = reverse('product-detail', args=[product.id])
        response = self.client.get(url)
        logger.info(
            f"Retrieve Product Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product_name'], product.product_name)

    def test_update_product(self):
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        url = reverse('product-detail', args=[product.id])
        update_data = {"product_name": "Updated Product"}
        # PATCH with JSON is fine if not updating the image
        response = self.client.patch(url, update_data, format='json')
        logger.info(
            f"Update Product Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product']
                         ['product_name'], "Updated Product")

    def test_update_product_with_image(self):
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        url = reverse('product-detail', args=[product.id])
        update_data = {
            "product_name": "Updated Product",
            "picture": self.create_test_image()
        }
        response = self.client.patch(url, update_data, format='multipart')
        logger.info(
            f"Update Product With Image Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product']
                         ['product_name'], "Updated Product")

    def test_delete_product(self):
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        url = reverse('product-detail', args=[product.id])
        response = self.client.delete(url)
        logger.info(f"Delete Product Response: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Product.objects.filter(id=product.id).exists())
        self.assertTrue(Product.objects.get(id=product.id).is_deleted)

    def test_list_products(self):
        Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0)
        response = self.client.get(self.base_url)
        logger.info(
            f"List Products Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_product_missing_required_field(self):
        """Test creation fails if a required field is missing."""
        data = self.valid_data_without_size.copy()
        data.pop('product_name')
        data['picture'] = self.create_test_image()
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product Missing Field Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product_name', response.data)

    def test_create_product_not_business_owner(self):
        """Test creation fails if the user is not a business owner."""
        self.user.business_owner_profile = None
        self.user.save()
        data = self.valid_data_without_size.copy()
        data['picture'] = self.create_test_image()
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product No Store Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'],
                         "No store found for this user.")

    def test_create_product_unauthenticated(self):
        """Test creation fails if the user is not authenticated."""
        self.client.force_authenticate(user=None)
        data = self.valid_data_without_size.copy()
        data['picture'] = self.create_test_image()
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product Unauthenticated Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_product_with_favourite(self):
        """Check if `is_favourite` is correctly set for a single product."""
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        # Add product to favourites
        self.user.favourite_products.add(product)

        url = reverse('product-detail', args=[product.id])
        response = self.client.get(url)
        logger.info(
            f"Retrieve Product with Favourite Response: {response.status_code} - {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_favourite', response.data)
        self.assertTrue(response.data['is_favourite'])

    def test_retrieve_product_without_favourite(self):
        """Check if `is_favourite` is False when product is not favourited."""
        product = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        url = reverse('product-detail', args=[product.id])
        response = self.client.get(url)
        logger.info(
            f"Retrieve Product without Favourite Response: {response.status_code} - {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_favourite', response.data)
        self.assertFalse(response.data['is_favourite'])

    def test_list_products_with_favourites(self):
        """Check if `is_favourite` is set for all products in list."""
        product1 = Product.objects.create(
            owner_id=self.user, store=self.store, **self.valid_data_without_size, reserved_quantity=0
        )
        product2 = Product.objects.create(
            owner_id=self.user, store=self.store, product_name='Another Product',
            product_description='Another desc', price='29.99', category='Clothing',
            color='Blue', has_sizes=False, available_quantity=3,
            picture=self.create_test_image(), reserved_quantity=0
        )
        self.user.favourite_products.add(product1)

        response = self.client.get(self.base_url)
        logger.info(
            f"List Products with Favourites Response: {response.status_code} - {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
        # Check if is_favourite exists for all
        ids = {p['id']: p for p in response.data}
        self.assertTrue(ids[product1.id]['is_favourite'])
        self.assertFalse(ids[product2.id]['is_favourite'])

    def test_list_products_without_authentication(self):
        """Check if `is_favourite` is False when user is unauthenticated."""
        product = Product.objects.create(
            owner_id=self.user,
            store=self.store,
            **self.valid_data_without_size,
            reserved_quantity=0
        )
        self.client.force_authenticate(user=None)
        response = self.client.get(self.base_url)
        logger.info(
            f"List Products without Auth Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn('is_favourite', response.data[0])
        self.assertFalse(response.data[0]['is_favourite'])


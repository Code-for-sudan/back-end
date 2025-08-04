from decimal import Decimal
import json
import logging
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from .test_helpers import TestHelpers
from products.models import Offer, Product, Size


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

    def setUp(self):
        self.user, self.store, self.business_owner = TestHelpers.create_seller()
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse('product-list')

    def test_create_product(self):
        for product_entry in TestHelpers.get_valid_products_data():
            description = product_entry["description"]
            product_data = product_entry["data"]
            if product_data["has_sizes"]:
                product_data["sizes"] = json.dumps(product_data["sizes"])
            offer = product_data.get("offer", None)
            if offer is not None:
                product_data["offer"] = json.dumps(product_data["offer"])

            logger.info(f"testing: {description}")
            response = self.client.post(
                self.base_url, product_data, format='multipart')
            logger.info(
                f"Create Product Response: {response.status_code} - {response.data}")
            self.assertEqual(response.status_code,
                             status.HTTP_201_CREATED, response.data)
            self.assertEqual(response.data['message'],
                             "Product created successfully")
            self.assertEqual(response.data['product']['product_name'],
                             product_data['product_name'])

    def test_retrieve_product(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        url = reverse('product-detail', args=[product.id])
        response = self.client.get(url)
        logger.info(
            f"Retrieve Product Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product_name'], product.product_name)

    def test_update_product(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
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

    def test_update_product_add_offer(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        url = reverse('product-detail', args=[product.id])
        start_date, end_date = TestHelpers.get_active_offer_dates()
        update_data = {"offer": {
            "start_date": start_date,
            "end_date": end_date,
            "offer_price": 100
        }}
        response = self.client.patch(url, update_data, format='json')
        logger.info(
            f"Update Product Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data['product']['current_price']), Decimal(100))
        self.assertIsNotNone(response.data['product']['offer'])
        if response.data['product']['offer'] is not None:
            self.assertTrue(response.data['product']['offer']['is_active'])

    def test_update_product_with_image(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        url = reverse('product-detail', args=[product.id])
        update_data = {
            "product_name": "Updated Product",
            "picture": TestHelpers.create_test_image()
        }
        response = self.client.patch(url, update_data, format='multipart')
        logger.info(
            f"Update Product With Image Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product']
                         ['product_name'], "Updated Product")

    def test_delete_product(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        url = reverse('product-detail', args=[product.id])
        response = self.client.delete(url)
        logger.info(f"Delete Product Response: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Product.objects.filter(id=product.id).exists())
        self.assertTrue(Product.objects.get(id=product.id).is_deleted)

    def test_list_products(self):
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url)
        logger.info(
            f"List Products Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        product_ids = [p['id'] for p in response.data["results"]]
        self.assertIn(product.id, product_ids)

    def test_filter_products_by_classification(self):
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                classification="Men"),
            self.user,
            self.store
        )
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                classification="Women"),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url, {"classification": "Men"})
        logger.info(
            f"Filter by Category Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for product in response.data['results']:
            self.assertEqual(product["classification"], "Men")

    def test_filter_products_by_category(self):
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                category="Clothing"),
            self.user,
            self.store
        )
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                category="Electronics"),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url, {"category": "Clothing"})
        logger.info(
            f"Filter by Category Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for product in response.data['results']:
            self.assertEqual(product["category"], "Clothing")

    def test_filter_products_with_active_offer(self):
        # One with active offer
        TestHelpers.creat_product(
            TestHelpers.add_offer_to_product_data(
                TestHelpers.get_valid_product_data_without_sizes(),
                *TestHelpers.get_active_offer_dates(),
                offer_price=9.99
            ),
            self.user,
            self.store
        )
        # One without offer
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url, {"has_offer": "true"})
        logger.info(
            f"Filter by has_offer Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            all(p.get("offer") and p["offer"]["is_active"] for p in response.data['results']))

    def test_sort_products_by_price_ascending(self):
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(price="9.99"),
            self.user,
            self.store
        )
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(price="19.99"),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url, {"sort": "price"})
        logger.info(
            f"Sort by Price Asc Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        prices = [float(p["price"]) for p in response.data['results']]
        self.assertEqual(prices, sorted(prices))

    def test_sort_products_by_created_at_descending(self):
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        response = self.client.get(self.base_url, {"sort": "-created_at"})
        logger.info(
            f"Sort by Created At Desc Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        timestamps = [p["created_at"] for p in response.data['results']]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_create_product_missing_required_field(self):
        """Test creation fails if a required field is missing."""
        data = TestHelpers.get_valid_product_data_without_sizes()
        data.pop('product_name')
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product Missing Field Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('product_name', response.data)

    def test_create_product_not_business_owner(self):
        """Test creation fails if the user is not a business owner."""
        self.user.business_owner_profile = None
        self.user.save()
        data = TestHelpers.get_valid_product_data_without_sizes()
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
        data = TestHelpers.get_valid_product_data_without_sizes()
        response = self.client.post(self.base_url, data, format='multipart')
        logger.info(
            f"Create Product Unauthenticated Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_product_with_favourite(self):
        """Check if `is_favourite` is correctly set for a single product."""
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
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
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
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
        product1 = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        product2 = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(
                product_name='Another Product',
                product_description='Another desc',
                price='29.99',
                category='Clothing',
                color='Blue'
            ),
            self.user,
            self.store
        )
        self.user.favourite_products.add(product1)

        response = self.client.get(self.base_url)
        logger.info(
            f"List Products with Favourites Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertGreaterEqual(len(results), 2)
        ids = {p['id']: p for p in results}
        self.assertTrue(ids[product1.id]['is_favourite'])
        self.assertFalse(ids[product2.id]['is_favourite'])

    def test_list_products_without_authentication(self):
        """Check if `is_favourite` is False when user is unauthenticated."""
        TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )
        self.client.force_authenticate(user=None)
        response = self.client.get(self.base_url)
        logger.info(
            f"List Products without Auth Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertGreaterEqual(len(results), 1)
        self.assertIn('is_favourite', results[0])
        self.assertFalse(results[0]['is_favourite'])

    def test_update_product_from_non_owner(self):
        """Ensure a user who does not own the product cannot update it."""
        # Create another user (non-owner)
        another_user, _, _ = TestHelpers.create_seller(
            email='another@example.com',
            password='testpass123',
            first_name='Another',
            last_name='User',
            store_name="Another Store",
            location='Another Location'

        )

        # Create a product owned by self.user
        product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )

        # Authenticate as another_user
        self.client.force_authenticate(user=another_user)

        url = reverse('product-detail', args=[product.id])
        update_data = {"product_name": "Malicious Update"}

        response = self.client.patch(url, update_data, format='json')
        logger.info(
            f"Update Product from Non-Owner Response: {response.status_code} - {response.data}"
        )

        # Assert forbidden response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('detail', response.data)
        self.assertEqual(
            response.data['detail'],
            "You do not have permission to update this product."
        )

        # Verify product is unchanged
        product.refresh_from_db()
        self.assertEqual(product.product_name,
                         TestHelpers.get_valid_product_data_without_sizes()['product_name'])


class DeleteProductSizeViewTests(APITestCase):
    def setUp(self):
        # Create a user and store

        self.user, self.store, self.business_owner = TestHelpers.create_seller()

        # Create another user (not owner)
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )

        # Authenticate as owner by default
        self.client.force_authenticate(user=self.user)
        self.product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(
                sizes=[
                    {"size": "S", "available_quantity": 10},
                    {"size": "M", "available_quantity": 32},
                ]
            ),
            self.user,
            self.store
        )
        self.size_s = Size.objects.filter(
            size='S', product=self.product).first()
        self.size_m = Size.objects.filter(
            size='M', product=self.product).first()
        self.url = lambda p_id, s_id: reverse(
            'delete-product-size', args=[p_id, s_id]
        )

    def test_delete_size_success(self):
        """Test deleting a size successfully by the owner."""
        response = self.client.delete(
            self.url(self.product.id, self.size_s.id))
        logger.info(
            f"Delete Size Success Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Size.objects.filter(
            id=self.size_s.id, is_deleted=False).exists())

    def test_delete_size_unauthorized_user(self):
        """Test that a non-owner user cannot delete a size."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(
            self.url(self.product.id, self.size_s.id))
        logger.info(
            f"Delete Size Unauthorized Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertTrue(Size.objects.filter(
            id=self.size_s.id, is_deleted=False).exists())

    def test_delete_size_only_size_left(self):
        """Test that deleting the last size is not allowed if product has_sizes=True."""
        # Remove other size first
        self.size_m.delete()

        response = self.client.delete(
            self.url(self.product.id, self.size_s.id))
        logger.info(
            f"Delete Only Size Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot delete the only size", response.data["detail"])
        self.assertTrue(Size.objects.filter(
            id=self.size_s.id, is_deleted=False).exists())

    def test_delete_size_with_reserved_quantity(self):
        """Test that deleting a size with reserved_quantity > 0 is blocked."""
        self.size_s.reserved_quantity = 2
        self.size_s.save()
        response = self.client.delete(
            self.url(self.product.id, self.size_s.id))
        logger.info(
            f"Delete Size with Reserved Quantity Response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reserved stock", response.data["detail"])
        self.assertTrue(Size.objects.filter(
            id=self.size_s.id, is_deleted=False).exists())

    def test_delete_nonexistent_size(self):
        """Test deleting a non-existent size returns 404."""
        non_existing_size_id = 9999
        response = self.client.delete(
            self.url(self.product.id, non_existing_size_id))
        logger.info(
            f"Delete Non-existent Size Response: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_size_of_nonexistent_product(self):
        """Test deleting a size for a non-existent product returns 404."""
        non_existing_product_id = 9999
        response = self.client.delete(
            self.url(non_existing_product_id, self.size_s.id))
        logger.info(
            f"Delete Size of Non-existent Product Response: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class Delete_ProductOfferViewTest(APITestCase):
    def setUp(self):
        self.user, self.store, self.business_owner = TestHelpers.create_seller()
        self.client.force_authenticate(user=self.user)
        self.another_user, _, _ = TestHelpers.create_seller(
            email='another@example.com',
            password='testpass123',
            first_name='Another',
            last_name='User',
            store_name="Another Store",
            location='Another Location'

        )
        self.product_with_offer = TestHelpers.creat_product(
            TestHelpers.add_offer_to_product_data(
                TestHelpers.get_valid_product_data_with_size(price=20),
                *TestHelpers.get_active_offer_dates(),
                10
            ),
            self.user,
            self.store
        )
        self.product_without_offer = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_with_size(),
            self.user,
            self.store
        )
        self.url = lambda p_id: reverse(
            'delete-product-offer', args=[p_id]
        )
        return super().setUp()

    def test_delete_offer_success(self):
        """Test deleting an offer successfully by the product owner."""

        response = self.client.delete(
            self.url(self.product_with_offer.id))

        logger.info(
            f"Delete Offer Success Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code,
                         status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(Offer.objects.filter(
            product=self.product_with_offer).exists())

    def test_delete_offer_unauthorized_user(self):
        """Test that a non-owner user cannot delete a product's offer."""
        self.client.force_authenticate(user=self.another_user)

        response = self.client.delete(
            self.url(self.product_with_offer.id))

        logger.info(
            f"Delete Offer Unauthorized Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertTrue(Offer.objects.filter(
            product=self.product_with_offer).exists())

    def test_delete_offer_unauthenticated(self):
        """Test that an unauthenticated user cannot delete a product's offer."""
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url(self.product_with_offer.id))

        logger.info(
            f"Delete Offer Unauthenticated Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertTrue(Offer.objects.filter(
            product=self.product_with_offer).exists())

    def test_delete_offer_nonexistent_product(self):
        """Test deleting an offer from a non-existent product ID returns 404."""
        invalid_product_id = 99999

        response = self.client.delete(self.url(invalid_product_id))

        logger.info(
            f"Delete Offer Nonexistent Product Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_delete_offer_product_without_offer(self):
        """Test deleting an offer from a product that has no offer returns 400."""
        response = self.client.delete(self.url(self.product_without_offer.id))

        logger.info(
            f"Delete Offer Without Offer Response: {response.status_code} - {response.data}"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

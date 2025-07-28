import logging
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from stores.models import Store
from products.models import Product
from search.documents import ProductDocument
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import BusinessOwner

logger = logging.getLogger('search_tests')


class ProductSearchViewTests(TestCase):
    """
    Test suite for the ProductSearchView with role-based Elasticsearch filtering.

    This test class verifies that the search view behaves correctly across various
    authentication states and user roles. It covers the following scenarios:

    - Anonymous users can search all products.
    - Authenticated buyer users can search all products.
    - Authenticated business owners can only search products from their own store.
    - Empty search queries return a proper message and 200 OK.
    - Invalid page numbers return a 400 BAD REQUEST.
    - Queries that yield no results return an empty list and 200 OK.
    
    Elasticsearch is used as the backend search engine, and search results are 
    validated using real indexed products (manually updated via ProductDocument).
    JWT tokens are used for authentication.
    """

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()

        # Create users
        self.business_user = User.objects.create_user(
            email="business@example.com", password="testpass123", is_active=True,
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="testpass123", is_active=True,
        )

        # Create stores
        self.business_store = Store.objects.create(
            name="Business Store", description="Owned by business user", location="City A"
        )
        self.other_store = Store.objects.create(
            name="Other Store", description="Owned by other user", location="City B"
        )

        self.business_owner = BusinessOwner.objects.create(
            user=self.business_user,
            store=self.business_store
        )

        # Create and index products for both users
        self.p1 = Product.objects.create(
            product_name="iPhone 15",
            product_description="Apple smartphone",
            price=999.99,
            category="Electronics",
            picture="https://example.com/images/iphone15.jpg",
            available_quantity=10,
            reserved_quantity=0,
            color="Black",
            has_sizes=False,
            owner_id=self.business_user,
            store=self.business_store,
        )
        self.p2 = Product.objects.create(
            product_name="Galaxy S24",
            product_description="Samsung smartphone",
            price=899.99,
            category="Electronics",
            picture="https://example.com/images/galaxys24.jpg",
            available_quantity=8,
            reserved_quantity=0,
            color="Silver",
            has_sizes=False,
            owner_id=self.other_user,
            store=self.other_store,
        )
        # Index in Elasticsearch
        ProductDocument().update(self.p1)
        ProductDocument().update(self.p2)

    def _get_token_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_anonymous_user_searches_all_products(self):
        response = self.client.get('/api/v1/search/products/', {'q': 'smartphone', 'p': 1})
        logger.info(f"Anonymous search response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)

    def test_authenticated_buyer_searches_all_products(self):
        token = self._get_token_for_user(self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/search/products/', {'q': 'smartphone', 'p': 1})
        logger.info(f"Buyer search response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)

    def test_business_owner_sees_only_their_products(self):
        token = self._get_token_for_user(self.business_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/search/products/', {'q': 'smartphone', 'p': 1})
        logger.info(f"Business owner search response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['product_name'], "iPhone 15")

    def test_search_empty_query(self):
        response = self.client.get('/api/v1/search/products/', {'q': '', 'p': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('message'), "Search query is empty")

    def test_search_invalid_page(self):
        response = self.client.get(
            '/api/v1/search/products/', {'q': 'iPhone', 'p': 0})
        logger.info(
            f"Search invalid page response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('message'),
                         "Page number must be greater than 0.")

    def test_search_no_results(self):
        response = self.client.get(
            '/api/v1/search/products/', {'q': 'NonExistentProduct', 'p': 1})
        logger.info(
            f"Search no results response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('results'), [])
        self.assertEqual(response.data.get('total'), 0)

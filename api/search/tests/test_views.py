import logging
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from stores.models import Store
from products.models import Product
from search.documents import ProductDocument

logger = logging.getLogger('search_tests')

class ProductSearchViewTests(TestCase):
    """
    Test suite for the ProductSearchView.

    This class tests the product search API endpoint with various scenarios:
    
    - test_search_with_query: 
        Ensures that searching with a valid query (e.g., 'iPhone') returns the correct product(s) and a 200 OK status.
    - test_search_empty_query: 
        Ensures that searching with an empty query returns a message indicating the query is empty and a 200 OK status.
    - test_search_invalid_page: 
        Ensures that providing an invalid page number (e.g., 0) returns a 400 BAD REQUEST and an appropriate error message.
    - test_search_no_results: 
        Ensures that searching for a non-existent product returns an empty results list, total=0, and a 200 OK status.
    """
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass123"
        )
        self.store = Store.objects.create(
            name="Test Store",
            description="A test store",
            location="Test City"
        )
        # Create and index products
        p1 = Product.objects.create(
            product_name="iPhone 15",
            product_description="Apple smartphone",
            price=999.99,
            category="Electronics",
            picture="https://example.com/images/iphone15.jpg",
            quantity=10,
            color="Black",
            size="6.1 inch",
            owner_id=self.user,
            store=self.store
        )
        p2 = Product.objects.create(
            product_name="Galaxy S24",
            product_description="Samsung phone",
            price=899.99,
            category="Electronics",
            picture="https://example.com/images/galaxys24.jpg",
            quantity=8,
            color="Silver",
            size="6.2 inch",
            owner_id=self.user,
            store=self.store
        )
        p3 = Product.objects.create(
            product_name="Coffee Mug",
            product_description="Ceramic mug",
            price=12.50,
            category="Kitchen",
            picture="https://example.com/images/mug.jpg",
            quantity=100,
            color=None,
            size=None,
            owner_id=self.user,
            store=self.store
        )
        # Index products in Elasticsearch
        ProductDocument().update(p1)
        ProductDocument().update(p2)
        ProductDocument().update(p3)

    def test_search_with_query(self):
        response = self.client.get('/api/v1/search/products/', {'q': 'iPhone', 'p': 1})
        logger.info(f"Search with query response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("iPhone" in prod['product_name'] for prod in response.data.get('results', [])))

    def test_search_empty_query(self):
        response = self.client.get('/api/v1/search/products/', {'q': '', 'p': 1})
        logger.info(f"Search empty query response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('message'), "Search query is empty")

    def test_search_invalid_page(self):
        response = self.client.get('/api/v1/search/products/', {'q': 'iPhone', 'p': 0})
        logger.info(f"Search invalid page response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('message'), "Page number must be greater than 0.")

    def test_search_no_results(self):
        response = self.client.get('/api/v1/search/products/', {'q': 'NonExistentProduct', 'p': 1})
        logger.info(f"Search no results response: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('results'), [])
        self.assertEqual(response.data.get('total'), 0)
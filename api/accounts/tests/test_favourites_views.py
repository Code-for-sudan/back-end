from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User
from products.models import Product, Store
from django.core.files.uploadedfile import SimpleUploadedFile


class FavouritesViewTests(APITestCase):

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123"
        )

        # Create a store and product
        self.store = Store.objects.create(
            name="Test Store",
            location="Test Location"
        )

        self.product = Product.objects.create(
            product_name="Test Product",
            product_description="Description",
            price=50.0,
            color="Blue",
            brand="BrandX",
            available_quantity=5,
            reserved_quantity=0,
            has_sizes=False,
            owner_id=self.user,
            store=self.store,
            category="CategoryX",
            picture=self.create_test_image(),
        )

        # Login user
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # URLs
        self.add_url = reverse('add-to-favourites', args=[self.product.id])
        self.remove_url = reverse('remove-from-favourites', args=[self.product.id])
        self.list_url = reverse('list-favourites')

    def create_test_image(self):
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
            content_type='image/jpeg'
        )

    def test_add_to_favourites(self):
        """Should add product to user's favourites."""
        response = self.client.post(self.add_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.product, self.user.favourite_products.all())

    def test_add_to_favourites_twice(self):
        """Adding same product twice should not create duplicate and still return 200."""
        self.client.post(self.add_url)
        response = self.client.post(self.add_url)  # second time
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.favourite_products.count(), 1)

    def test_remove_from_favourites(self):
        """Should remove product from favourites."""
        self.user.favourite_products.add(self.product)
        response = self.client.delete(self.remove_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.product, self.user.favourite_products.all())

    def test_remove_non_existing_favourite(self):
        """Removing a non-favourited product should still return 200."""
        response = self.client.delete(self.remove_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.favourite_products.count(), 0)

    def test_list_favourites(self):
        """Should list all user's favourites."""
        self.user.favourite_products.add(self.product)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.product.id)

    def test_add_to_favourites_invalid_product(self):
        """Should return 404 if product does not exist."""
        url = reverse('add-to-favourites', args=[9999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_from_favourites_invalid_product(self):
        """Should return 404 if product does not exist."""
        url = reverse('remove-from-favourites', args=[9999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

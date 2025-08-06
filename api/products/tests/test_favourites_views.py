from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from products.tests.test_helpers import TestHelpers


class FavouritesViewTests(APITestCase):

    def setUp(self):
        self.user, self.store, self.business_owner = TestHelpers.create_seller()

        self.product = TestHelpers.creat_product(
            TestHelpers.get_valid_product_data_without_sizes(),
            self.user,
            self.store
        )

        # Login user
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # URLs
        self.add_url = reverse('set-favourite', args=[self.product.id])
        self.remove_url = reverse(
            'unset-favourite', args=[self.product.id])
        self.list_url = reverse('favourites')

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
        url = reverse('set-favourite', args=[9999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_from_favourites_invalid_product(self):
        """Should return 404 if product does not exist."""
        url = reverse('unset-favourite', args=[9999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

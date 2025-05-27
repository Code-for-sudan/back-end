from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

'''A test case for the user login API endpoint using Django's APITestCase.'''

class LoginAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
            role="user"
        )

    def test_login_success(self):
        url = reverse('login')
        data = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "test@example.com")

    def test_login_invalid_credentials(self):
        url = reverse('login')
        data = {"email": "test@example.com", "password": "wrongpass"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)

import os
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework import status # type: ignore
from rest_framework.test import APITestCase # type: ignore
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
import logging

# Get the user model
User = get_user_model()

# Create a logger for this module
logger = logging.getLogger('authentication_tests')


class GoogleLoginTests(TestCase):
    """
    Test suite for the Google Login API endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google_auth')

    def test_google_login_redirects_to_google_auth(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/o/oauth2/auth"))

class GoogleOAuthViewsTests(TestCase):
    """
    Test case for testing Google OAuth views.
    This test case includes tests for the following scenarios:
    1. Redirect behavior of the `google_login` view.
    2. Successful OAuth process in the `google_callback` view.
    3. Failed token exchange in the `google_callback` view.
    4. Missing authorization code in the `google_callback` view.
    Tested Views:
    - `google_login`: Ensures the user is redirected to the Google OAuth URL.
    - `google_callback`: Handles the callback from Google after the OAuth process.
    Mocks:
    - `requests.post`: Mocked to simulate token exchange with Google's OAuth server.
    - `requests.get`: Mocked to simulate fetching user information from Google's API.
    Test Methods:
    - `test_google_login_redirect`: Verifies the redirect to the Google OAuth URL.
    - `test_google_callback_success`: Tests the successful OAuth process, including token exchange and user info retrieval.
    - `test_google_callback_failed_token_exchange`: Tests the behavior when the token exchange fails.
    - `test_google_callback_no_code`: Tests the behavior when no authorization code is provided in the callback request.
    """

    def setUp(self):
        self.client = APIClient()
        self.google_login_url = reverse('google_auth')  # Replace with the actual name of the google_login URL
        self.google_callback_url = reverse('google_callback')  # Replace with the actual name of the google_callback URL

    def test_google_login_redirect(self):
        """
        Test that the google_login view redirects to the Google OAuth URL.
        """
        response = self.client.get(self.google_login_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("https://accounts.google.com/o/oauth2/auth", response.url)

    @patch('requests.post')
    @patch('requests.get')
    def test_google_callback_success(self, mock_get, mock_post):
        """
        Test the google_callback view when the OAuth process is successful.
        """
        # Mock the token response
        mock_post.return_value.json.return_value = {
            "access_token": "mock_access_token"
        }

        # Mock the user info response
        mock_get.return_value.json.return_value = {
            "email": "testuser@example.com",
            "given_name": "Test",
            "family_name": "User",
            "picture": "http://example.com/profile.jpg"
        }

        # Simulate the callback with a valid code
        response = self.client.post(self.google_callback_url, {'code': 'mock_code'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], "testuser@example.com")

    @patch('requests.post')
    def test_google_callback_failed_token_exchange(self, mock_post):
        """
        Test the google_callback view when the token exchange fails.
        """
        # Mock a failed token response
        mock_post.return_value.json.return_value = {}

        # Simulate the callback with an invalid code
        response = self.client.post(reverse("google_callback"), {"code": "invalid"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Failed to obtain access token")

    def test_google_callback_no_code(self):
        """
        Test the google_callback view when no code is provided.
        """
        response = self.client.post(self.google_callback_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "No code provided")


class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email='reset@example.com',
            password='oldpassword',
            first_name='Reset',
            last_name='User'
        )
        self.otp = self.user.generate_otp()
        self.reset_request_url = reverse('reset_password_request')
        self.reset_verify_url = reverse('reset_password_verify')
        self.update_password_url = reverse('request_update_password')

        # Authenticate the client for update password tests
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.otp = self.user.generate_otp()
        self.reset_request_url = reverse('reset_password_request')
        self.reset_verify_url = reverse('reset_password_verify')
        self.update_password_url = reverse('request_update_password')

    def test_password_reset_request_success(self):
        data = {"email": self.user.email}
        response = self.client.post(self.reset_request_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_password_reset_request_missing_email(self):
        response = self.client.post(self.reset_request_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_request_nonexistent_user(self):
        data = {"email": "notfound@example.com"}
        response = self.client.post(self.reset_request_url, data)
        self.assertEqual(response.status_code, 200)  # Should not reveal user existence

    def test_password_reset_verify_success(self):
        data = {"email": self.user.email, "otp": self.otp}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("user", response.data)

    def test_password_reset_verify_invalid_otp(self):
        data = {"email": self.user.email, "otp": "wrongotp"}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_verify_missing_fields(self):
        response = self.client.post(self.reset_verify_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_verify_nonexistent_user(self):
        data = {"email": "nouser@example.com", "otp": "123456"}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.data)

    def test_update_password_success(self):
        data = {"email": self.user.email, "new_password": "newsecurepassword123"}
        response = self.client.post(self.update_password_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepassword123"))

    def test_update_password_missing_fields(self):
        response = self.client.post(self.update_password_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_update_password_nonexistent_user(self):
        data = {"email": "nouser@example.com", "new_password": "newsecurepassword123"}
        response = self.client.post(self.update_password_url, data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.data)
        User = get_user_model()

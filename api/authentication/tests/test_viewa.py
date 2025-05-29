from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
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
        self.url = reverse('google_login')

    def test_google_login_redirects_to_google_auth(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/o/oauth2/auth"))


class GoogleCallbackTests(TestCase):
    """
    Test suite for the Google Callback API endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google_callback')
        self.user = User.objects.create_user(email='test@example.com', password='testpassword')

    @patch('authentication.views.requests.post')
    def test_google_callback_missing_code_returns_400(self, mock_post):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'No code provided')

    @patch('authentication.views.requests.post')
    def test_google_callback_invalid_access_token_returns_400(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": None}
        response = self.client.post(self.url, data={'code': 'invalid_code'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'Failed to obtain access token')

    @patch('authentication.views.requests.post')
    @patch('authentication.views.requests.get')
    def test_google_callback_missing_email_returns_400(self, mock_get, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "valid_token"}
        mock_get.return_value.json.return_value = {"email": None}
        response = self.client.post(self.url, data={'code': 'valid_code'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'Failed to retrieve email')

    @patch('authentication.views.requests.post')
    @patch('authentication.views.requests.get')
    @patch('authentication.views.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    def test_google_callback_creates_new_user_and_returns_tokens(self, mock_generate_jwt, mock_get, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "valid_token"}
        mock_get.return_value.json.return_value = {
            "email": "newuser@example.com",
            "given_name": "New",
            "family_name": "User",
            "picture": "http://example.com/picture.jpg"
        }
        response = self.client.post(self.url, data={'code': 'valid_code'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertEqual(response.data['message'], 'Login successful.')

        cookie = response.cookies.get('refresh_token')
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])
        self.assertEqual(cookie['samesite'], 'Lax')

    @patch('authentication.views.requests.post')
    @patch('authentication.views.requests.get')
    @patch('authentication.views.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    def test_google_callback_existing_user_returns_tokens(self, mock_generate_jwt, mock_get, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "valid_token"}
        mock_get.return_value.json.return_value = {
            "email": self.user.email,
            "given_name": "Test",
            "family_name": "User",
            "picture": "http://example.com/picture.jpg"
        }
        response = self.client.post(self.url, data={'code': 'valid_code'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertEqual(response.data['message'], 'Login successful.')


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

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch
import logging


User = get_user_model()
# logger = logging.getLogger('accounts_tests')



class VerifyOTPTests(TestCase):
    """
    Test suite for the Verify OTP API endpoint.
    This test class contains various test cases to ensure the functionality and robustness
    of the OTP verification process. It covers scenarios such as missing fields, invalid
    inputs, and successful OTP verification.
    Test Cases:
    - `test_missing_email_and_otp_returns_400`: Verifies that a 400 status code is returned
        when both email and OTP are missing in the request.
    - `test_missing_otp_returns_400`: Verifies that a 400 status code is returned when the
        OTP is missing in the request.
    - `test_missing_email_returns_400`: Verifies that a 400 status code is returned when
        the email is missing in the request.
    - `test_user_not_found_returns_404`: Verifies that a 404 status code is returned when
        the user is not found in the database.
    - `test_invalid_otp_returns_400`: Verifies that a 400 status code is returned when an
        invalid OTP is provided.
    - `test_valid_otp_returns_tokens_and_cookie`: Verifies that valid OTP returns a 200
        status code, JWT tokens in the response, and sets the refresh token as a secure,
        HTTP-only cookie.
    - `test_email_case_insensitive`: Verifies that the email field is case-insensitive
        during OTP verification.
    - `test_email_with_whitespace`: Verifies that leading and trailing whitespaces in the
        email field are ignored during OTP verification.
    - `test_otp_with_leading_zeros`: Verifies that OTPs with leading zeros are handled
        correctly.
    - `test_logging_error_on_missing_fields`: Verifies that an error is logged when both
        email and OTP are missing in the request.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('verify_otp')
        self.user = User.objects.create_user(email='test@example.com', password='testpassword')

    def test_missing_email_and_otp_returns_400(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.data)

    def test_missing_otp_returns_400(self):
        response = self.client.post(self.url, data={'email': 'test@example.com'})
        self.assertEqual(response.status_code, 400)

    def test_missing_email_returns_400(self):
        response = self.client.post(self.url, data={'otp_code': '123456'})
        self.assertEqual(response.status_code, 400)

    def test_user_not_found_returns_404(self):
        response = self.client.post(self.url, data={'email': 'nouser@example.com', 'otp_code': '123456'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['message'], 'User not found.')

    @patch('accounts.utils.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    @patch.object(User, 'verify_otp', return_value=False)
    def test_invalid_otp_returns_400(self, mock_verify_otp, mock_jwt):
        response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': 'wrong'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'Invalid OTP code.')

    @patch('accounts.utils.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    @patch.object(User, 'verify_otp', return_value=True)
    def test_valid_otp_returns_tokens_and_cookie(self, mock_verify_otp, mock_jwt):
        response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '123456'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)

        cookie = response.cookies.get('refresh_token')
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie.value.startswith('eyJ'))  # JWT tokens typically start with 'eyJ'
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])
        self.assertEqual(cookie['samesite'], 'Lax')

        response.set_cookie(
            'refresh_token',
            'refresh-token',
            httponly=True,
            secure=True,
            samesite='Lax'
        )

    @patch('accounts.utils.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    @patch.object(User, 'verify_otp', return_value=True)
    def test_email_case_insensitive(self, mock_verify_otp, mock_jwt):
        response = self.client.post(self.url, data={'email': 'TEST@EXAMPLE.COM', 'otp_code': '123456'})
        self.assertEqual(response.status_code, 200)

    @patch('accounts.utils.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    @patch.object(User, 'verify_otp', return_value=True)
    def test_email_with_whitespace(self, mock_verify_otp, mock_jwt):
        response = self.client.post(self.url, data={'email': '  test@example.com  ', 'otp_code': '123456'})
        self.assertEqual(response.status_code, 200)

    @patch('accounts.utils.generate_jwt_tokens', return_value=('access-token', 'refresh-token'))
    @patch.object(User, 'verify_otp', return_value=True)
    def test_otp_with_leading_zeros(self, mock_verify_otp, mock_jwt):
        response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '001234'})
        self.assertEqual(response.status_code, 200)

    def test_logging_error_on_missing_fields(self):
        with self.assertLogs('accounts_views', level='ERROR') as cm:
            self.client.post(self.url, data={})
        self.assertTrue(any('Missing email or OTP in request:' in message for message in cm.output))

    ###TODO: Add throttling tests for the Verify OTP endpoint
    def test_throttling(self):
        # This test assumes that you have set up throttling in your Django REST Framework settings
        for _ in range(5):  # Assuming the throttle limit is 5 requests
            response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '123456'})
            self.assertEqual(response.status_code, 200)

        # The next request should hit the throttle limit
        response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '123456'})
        self.assertEqual(response.status_code, 429)  # Too Many Requests

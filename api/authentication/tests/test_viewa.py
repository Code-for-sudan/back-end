from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework import status # type: ignorec
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
        self.url = reverse('google_auth')

    def test_google_login_redirects_to_google_auth(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://accounts.google.com/o/oauth2/auth"))


class GoogleOAuthViewsTestCase(TestCase):
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

@override_settings(REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {'anon': '1000/minute'}})
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
        cache.clear()
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
        with self.assertLogs('authentication_views', level='DEBUG') as cm:
            self.client.post(self.url, data={})
        self.assertTrue(any('Missing email or OTP in request:' in message for message in cm.output))

    ###TODO: Add throttling tests for the Verify OTP endpoint
    @override_settings(REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {'anon': '5/minute'}})
    @patch.object(User, 'verify_otp', return_value=True)
    def test_throttling(self, mock_verify_otp):
        for _ in range(10):  # Assuming the throttle limit is 5 requests
            response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '123456'})
            self.assertEqual(response.status_code, 200)

        # The next request should hit the throttle limit
        response = self.client.post(self.url, data={'email': self.user.email, 'otp_code': '123456'})
        self.assertEqual(response.status_code, 429)  # Too Many Requests

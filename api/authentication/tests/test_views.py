import os
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework import status # type: ignore
from rest_framework.test import APITestCase # type: ignore
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

@override_settings(REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {'anon': '1000/minute'}})
class ResetPasswordVerifyAPITests(APITestCase):
    """
    Test suite for the Reset Password Verify API endpoint.
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
        self.url = reverse('reset_password_verify')
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

class UserLoginAPITests(APITestCase):
    """
    Test suite for user login functionality.
    Classes:
        UserLoginTests: Test cases for user login API endpoint.
    Methods:
        setUp(self):
            Sets up the test environment by defining the signin URL and creating a test user.
        test_signin_success(self):
            Tests that a user can successfully sign in with valid credentials.
        test_signin_invalid_credentials(self):
            Tests that attempting to sign in with invalid credentials returns a 400 status code.
        test_signin_missing_credentials(self):
            Tests that attempting to sign in without providing email or password returns a 400 status code.
    """

    def setUp(self):
        cache.clear()
        self.signin_url = reverse('login')
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )
        self.valid_credentials = {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        self.invalid_credentials = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }

    def test_signin_success(self):
        response = self.client.post(self.signin_url, self.valid_credentials, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Login successful.')
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.cookies)

    def test_signin_invalid_credentials(self):
        response = self.client.post(self.signin_url, self.invalid_credentials, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid email or password.')

    def test_signin_missing_credentials(self):
        response = self.client.post(self.signin_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid email or password.')

class ResetPasswordConfirmAPITests(APITestCase):
    """
    Test suite for password reset confirmation functionality.
    Classes:
        ResetPasswordConfirmAPITest: Test cases for the reset password confirm API endpoint.
    Methods:
        setUp(self):
            Sets up the test environment by defining the reset password URL, creating a test user, and generating an OTP.
        test_reset_password_success(self):
            Tests that a user can successfully reset their password with a valid OTP.
        test_reset_password_invalid_otp(self):
            Tests that attempting to reset the password with an invalid OTP returns a 400 status code.
        test_reset_password_missing_fields(self):
            Tests that attempting to reset the password without providing all required fields returns a 400 status code.
        test_reset_password_invalid_new_password(self):
            Tests that attempting to reset the password with a new password that does not meet complexity requirements returns a 400 status code.
        test_reset_password_nonexistent_user(self):
            Tests that attempting to reset the password for a non-existent user returns a 400 status code.
    """

    def setUp(self):
        cache.clear()
        self.reset_url = reverse('reset_password_confirm')
        self.user = User.objects.create_user(
            email="reset@example.com",
            password="oldpassword",
            first_name="Reset",
            last_name="User"
        )
        self.otp = self.user.generate_otp()  # Generates and saves OTP

    def test_reset_password_success(self):
        data = {
            "email": "reset@example.com",
            "otp": self.otp,
            "new_password": "newpassword123"
        }
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_reset_password_invalid_otp(self):
        data = {
            "email": "reset@example.com",
            "otp": "wrongotp",
            "new_password": "newpassword123"
        }
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_reset_password_missing_fields(self):
        data = {
            "email": "reset@example.com",
            # Missing otp and new_password
        }
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_reset_password_invalid_new_password(self):
        data = {
            "email": "reset@example.com",
            "otp": self.otp,
            "new_password": "short"  # Invalid: too short, no digit, etc.
        }
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_reset_password_nonexistent_user(self):
        data = {
            "email": "notfound@example.com",
            "otp": "123456",
            "new_password": "newpassword123"
        }
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

# @override_settings(
#     CACHES={
#         "default": {
#             "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#             "LOCATION": "unique-snowflake",
#         }
#     },
#     CELERY_BROKER_URL='memory://',
# )
class ResetPasswordRequestAPITests(APITestCase):
    """
    Test suite for the Reset Password Request endpoint.

    Methods:
        setUp(self):
            Sets up the test environment by defining the resend OTP URL and creating a test user.
        test_reset_password_request_success(self):
            Tests that a user can successfully request a new OTP.
        test_reset_password_request_missing_email(self):
            Tests that missing email returns a 400 status code.
        test_reset_password_request_nonexistent_user(self):
            Tests that a non-existent user returns a 400 status code.
        test_reset_password_request_throttling(self):
            Tests that too many requests are throttled.
    """

    def setUp(self):
        cache.clear()
        self.resend_url = reverse('reset_password_request')
        self.user = User.objects.create_user(
            email="resend@example.com",
            password="testpassword123",
            first_name="Resend",
            last_name="User"
        )

    def test_reset_password_request_success(self):
        data = {"email": "resend@example.com"}
        response = self.client.post(self.resend_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_reset_password_request_missing_email(self):
        response = self.client.post(self.resend_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_reset_password_request_nonexistent_user(self):
        data = {"email": "notfound@example.com"}
        response = self.client.post(self.resend_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_reset_password_request_throttling(self):
        data = {"email": "resend@example.com"}
        # Exceed the throttle rate (global is 10/min for anonymous)
        for _ in range(13):
            response = self.client.post(self.resend_url, data)
        self.assertEqual(response.status_code, 429)
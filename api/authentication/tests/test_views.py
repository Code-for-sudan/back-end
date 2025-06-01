import os
from django.urls import reverse
from rest_framework.test import APITestCase # type: ignore
from rest_framework import status # type: ignore
from django.contrib.auth import get_user_model
User = get_user_model()

class UserSigninTests(APITestCase):
    """
    Test suite for user signin functionality.
    Classes:
        UserSigninTests: Test cases for user signin API endpoint.
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
        self.assertEqual(response.data['message'], 'Invalid credentials.')

    def test_signin_missing_credentials(self):
        response = self.client.post(self.signin_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Email and password are required.')


class ResetPasswordConfirmAPITest(APITestCase):
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
        self.reset_url = reverse('reset-password-confirm')
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
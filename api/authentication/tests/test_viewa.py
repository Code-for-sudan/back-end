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
        self.signin_url = reverse('signin')
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
